#!/usr/bin/env python3
"""F1 víkend: standard-library server, no database or external packages."""
import argparse
import copy
from datetime import datetime, timedelta
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import re
import threading
import webbrowser
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PRAGUE = ZoneInfo("Europe/Prague")
SOURCE = "https://tv.nova.cz/program"
REFRESH_SECONDS = 6 * 60 * 60
RETRY_SECONDS = 15 * 60
MONTHS = ("", "ledna", "února", "března", "dubna", "května", "června",
          "července", "srpna", "září", "října", "listopadu", "prosince")
WEEKDAYS = ("Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle")


def instant(value):
    date = datetime.fromisoformat(value)
    if date.tzinfo is None:
        raise ValueError("Missing timezone in source")
    return date.astimezone(PRAGUE)


def session(title):
    text = title.casefold()
    if "studio" in text:
        return "intro" if "úvodní" in text else "other"
    if "sprint" in text and re.search(r"kvalifik|shootout", text):
        return "sprint_qualifying"
    if "sprint" in text:
        return "sprint"
    if "kvalifik" in text:
        return "qualifying"
    if "trénink" in text or "practice" in text:
        return "practice"
    if re.search(r"\((?:hlavní )?závod\)", text):
        return "race"
    # Unknown parenthetical specials must not be mistaken for a GP race.
    if "velká cena" in text and "(" not in text:
        return "race"
    return "other"


def parse_nova(html):
    """Extract only schedule data from the same PageData used in research/."""
    match = re.search(r"\bvar\s+PageData\s*=\s*", html)
    if not match:
        raise ValueError("Nova page has no PageData")
    data, _ = json.JSONDecoder().raw_decode(html[match.end():])
    programmes = {}
    channel_found = False
    for day in data["program"]:
        for channel in day["channels"]:
            if channel["id"] != "nova-sport-5":
                continue
            channel_found = True
            for segment in channel["segments"]:
                for item in segment["items"]:
                    # Validate the entire channel even on weeks without any F1.
                    start, end = instant(item["start_at"]), instant(item["end_at"])
                    if end <= start:
                        raise ValueError("Invalid programme duration")
                    title, description = item["title"], item.get("description") or ""
                    if not re.match(r"^Formule\s*1\b", title, re.I):
                        continue
                    live = bool(re.search(r"přímý přenos|\bživě\b", description, re.I))
                    replay = bool(re.search(r"záznam|repríz", description, re.I))
                    if not live or replay:
                        continue
                    kind = session(title)
                    if kind == "other":
                        continue
                    programmes[str(item["id"])] = {
                        "title": title, "start": start.isoformat(), "end": end.isoformat(),
                        "kind": kind,
                        "grand_prix": re.sub(r"\s*\([^)]*\)\s*$", "", re.sub(
                            r"^Formule\s*1\s*[-–:]\s*", "", title, flags=re.I)).strip()
                        if kind != "intro" else None}
    if not channel_found:
        raise ValueError("Nova Sport 5 missing from source")
    return sorted(programmes.values(), key=lambda p: instant(p["start"]))


def fetch_nova():
    request = Request(SOURCE, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    with urlopen(request, timeout=30) as response:
        body = response.read(15_000_001)
        if len(body) > 15_000_000:
            raise ValueError("Nova response too large")
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return parse_nova(body.decode("utf-8"))


def select_weekend(programmes, now):
    """Keep a weekend through race end, then advance; never guess missing times."""
    groups = {}
    for p in programmes:
        if p["kind"] != "intro":
            groups.setdefault(p["grand_prix"], []).append(p)
    candidates = []
    for name, items in groups.items():
        races = [p for p in items if p["kind"] == "race"]
        # A published partial weekend can lack the race; show its known sessions.
        end = max(instant(p["end"]) for p in (races or items))
        if end > now:
            candidates.append((min(instant(p["start"]) for p in items), name, items, races))
    if not candidates:
        return {"state": "unavailable", "message": "Program nejbližšího víkendu F1 zatím není k dispozici. Jakmile ho Nova zveřejní, objeví se zde automaticky."}
    _, name, items, races = min(candidates, key=lambda g: g[0])
    items = list(items)
    # Associate a studio by its real adjacency to this GP's race, not by date
    # alone (important for overnight events and sponsor/name variations).
    for p in programmes:
        if p["kind"] == "intro" and any(
                timedelta(0) <= instant(r["start"]) - instant(p["end"]) <= timedelta(minutes=15)
                and instant(p["start"]) < instant(r["start"]) for r in races):
            items.append(p)
    days = {}
    for p in sorted(items, key=lambda p: instant(p["start"])):
        start = instant(p["start"])
        date = start.date()
        key = date.isoformat()
        day = days.setdefault(key, {"date": key,
            "weekday": WEEKDAYS[date.weekday()],
            "label": f"{date.day}. {MONTHS[date.month]} {date.year}", "items": []})
        labels = {"race": "Závod", "intro": "Úvodní studio", "sprint": "Sprint",
                  "sprint_qualifying": "Sprintová kvalifikace", "qualifying": "Kvalifikace"}
        label = labels.get(p["kind"])
        if not label:
            number = re.search(r"(\d+)\.?\s*(?:volný\s+)?trénink", p["title"], re.I)
            label = f"{number[1]}. trénink" if number else "Trénink"
        day["items"].append({"label": label, "time": start.strftime("%H:%M"),
                             "start": start.isoformat(), "end": p["end"]})
    return {"state": "ready", "title": name, "days": list(days.values()),
            "partial": not bool(races)}


class Schedule:
    """Single automatic updater; persist only last successful parsed schedule."""
    def __init__(self, cache_path, fetcher=fetch_nova):
        self.path, self.fetcher = Path(cache_path), fetcher
        self.lock = threading.Lock()
        self.data, self.updated_at, self.failed = None, None, False
        self.attempted = False
        self.stop = threading.Event()
        try:
            cached = json.loads(self.path.read_text())
            updated = instant(cached["updated_at"])
            rows = cached["programmes"]
            for p in rows:
                instant(p["start"])
                instant(p["end"])
                for key in ("title", "kind", "grand_prix"):
                    p[key]
            if not isinstance(rows, list) or updated > datetime.now(PRAGUE) + timedelta(minutes=5):
                raise ValueError("Invalid cache")
            self.data, self.updated_at = rows, updated
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def refresh(self):
        try:
            rows = self.fetcher()
            updated = datetime.now(PRAGUE)
            with self.lock:
                self.data, self.updated_at, self.failed, self.attempted = rows, updated, False, True
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.path.with_suffix(".tmp")
                temp.write_text(json.dumps({"updated_at": updated.isoformat(), "programmes": rows}, ensure_ascii=False))
                os.replace(temp, self.path)
            except OSError:
                logging.exception("Could not persist schedule cache")
            return True
        except Exception:
            logging.exception("Could not refresh Nova schedule")
            with self.lock:
                self.failed, self.attempted = True, True
            return False

    def run(self):
        while not self.stop.is_set():
            with self.lock:
                age = (datetime.now(PRAGUE) - self.updated_at).total_seconds() if self.updated_at else REFRESH_SECONDS
            if age < REFRESH_SECONDS and not self.failed:
                delay = REFRESH_SECONDS - age
            else:
                delay = REFRESH_SECONDS if self.refresh() else RETRY_SECONDS
            self.stop.wait(delay)

    def view(self, now=None):
        now = now or datetime.now(PRAGUE)
        with self.lock:
            data, updated, failed, attempted = copy.deepcopy(self.data), self.updated_at, self.failed, self.attempted
        if data is None:
            return {"state": "error" if attempted else "loading",
                    "message": "Program se nyní nepodařilo načíst. Zkusíme to znovu automaticky." if attempted else "Načítáme program Novy…"}
        result = select_weekend(data, now)
        result.update(updated_at=updated.isoformat(), source=SOURCE,
                      stale=failed or now - updated > timedelta(hours=12))
        return result


def make_handler(schedule):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/api/weekend":
                body = json.dumps(schedule.view(), ensure_ascii=False).encode()
                content_type = "application/json; charset=utf-8"
            elif path == "/schedule.json":
                with schedule.lock:
                    snapshot = {"updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None,
                                "programmes": schedule.data or [],
                                "fetch_failed_at": datetime.now(PRAGUE).isoformat() if schedule.failed else None}
                body = json.dumps(snapshot, ensure_ascii=False).encode()
                content_type = "application/json; charset=utf-8"
            else:
                files = {"/": ("index.html", "text/html; charset=utf-8"),
                         "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                         "/schedule.js": ("schedule.js", "text/javascript; charset=utf-8"),
                         "/style.css": ("style.css", "text/css; charset=utf-8"),
                         "/favicon.svg": ("favicon.svg", "image/svg+xml")}
                if path not in files:
                    self.send_error(404)
                    return
                name, content_type = files[path]
                body = (ROOT / "web" / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store" if path == "/api/weekend" else "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache" / "nova.json")
    parser.add_argument("--open", action="store_true", help="Open the local app in your default browser")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    schedule = Schedule(args.cache)
    worker = threading.Thread(target=schedule.run, daemon=True)
    worker.start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(schedule))
    print(f"F1 víkend: http://{args.host}:{args.port}", flush=True)
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        schedule.stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
