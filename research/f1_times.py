#!/usr/bin/env python3
"""Nova Sport 5 F1 broadcasts from Seznam's public website JSON API.

Python 3.9+, no dependencies/API keys. One request/day, no detail requests.
Output times are TV broadcast starts in Europe/Prague, not session start times.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode

from probe_epg import PRAGUE, fetch

BASE = "https://tv.seznam.cz/api"


def get(path, requests):
    result, body = fetch(BASE + path)
    requests.append(result)
    if body is None:
        raise ValueError(result["error"])
    return json.loads(body)


def session(title):
    text = title.casefold()
    # Studios are broadcasts in their own right, never race sessions.
    if "studio" in text:
        return "studio"
    if "sprint" in text and re.search(r"kvalifik|shootout", text):
        return "sprint_qualifying"
    if "sprint" in text:
        return "sprint"
    if "kvalifik" in text:
        return "qualifying"
    if "trénink" in text or "practice" in text:
        return "practice"
    # Source names its actual GP race without '(závod)'.
    if "velká cena" in text:
        return "race"
    return "other"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=dt.date.fromisoformat,
                        default=dt.datetime.now(PRAGUE).date())
    parser.add_argument("--days", type=int, default=22)
    parser.add_argument("--output", type=Path, default=Path("/tmp/f1-times.json"))
    args = parser.parse_args()
    if not 1 <= args.days <= 31:
        parser.error("--days must be 1–31")
    report = {"tested_at": dt.datetime.now(PRAGUE).isoformat(),
              "source": BASE, "timezone": "Europe/Prague", "requests": [],
              "days": [], "broadcasts": []}
    seen = set()
    try:
        index = get("", report["requests"])
        availability = index.get("_embedded", {}).get("tv:config", {}).get("schedule_availability", [])
        report["api_global_availability"] = [dt.datetime.fromtimestamp(t, PRAGUE).isoformat()
                                              for t in availability]
        broadcast = get("/broadcast", report["requests"])
        channels = broadcast["_embedded"]["tv:channel"]
        channels = [c for c in channels if c["name"].casefold() == "nova sport 5"]
        if len(channels) != 1:
            raise ValueError("Cannot uniquely identify Nova Sport 5")
        channel = channels[0]
        report["channel"] = {"id": channel["id"], "name": channel["name"]}
        for offset in range(args.days):
            date = args.start + dt.timedelta(days=offset)
            path = f'/schedule/{channel["id"]}?' + urlencode({"day": str(date)})
            data = get(path, report["requests"])
            programmes = data.get("_embedded", {}).get("tv:programme")
            if programmes is None and "_embedded" not in data and "_links" in data:
                programmes = []  # Observed API representation for an unpublished day.
            if not isinstance(programmes, list):
                raise ValueError(f"Missing programme list for {date}")
            # Day queries may include programmes overlapping midnight. Use actual
            # timestamps, filter to the requested calendar day, deduplicate IDs.
            programmes = [p for p in programmes if
                          dt.datetime.fromtimestamp(p["time_from"], PRAGUE).date() == date]
            day = {"date": str(date), "all_programme_count": len(programmes), "f1_count": 0}
            report["days"].append(day)
            for p in programmes:
                title = p["name"]
                # Main championship only: excludes F1 Academy, F2, F3 and magazines.
                if not re.match(r"^Formule\s*1\b", title, re.I):
                    continue
                if p["id"] in seen:
                    continue
                seen.add(p["id"])
                live = p.get("live")
                status = "live" if live is True else "not_live" if live is False else "unknown"
                description = p.get("short_description", "")
                report["broadcasts"].append({
                    "id": p["id"], "start": dt.datetime.fromtimestamp(p["time_from"], PRAGUE).isoformat(),
                    "title": title, "session": session(title), "status": status,
                    "replay_text_marker": bool(re.search(r"záznam|repríz", description, re.I)),
                    "description": description,
                    "source_url": BASE + path})
                day["f1_count"] += 1
            time.sleep(0.3)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report["error"] = str(exc)
    report["broadcasts"].sort(key=lambda p: p["start"])
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for p in report["broadcasts"]:
        if p["status"] == "live":
            print(f'{p["start"]} | {p["title"]} | živě')
    print(f'Saved {len(report["broadcasts"])} F1 broadcasts to {args.output}', file=sys.stderr)
    if "error" in report:
        print(report["error"], file=sys.stderr)
        return 1
    # An empty response must not masquerade as a successful feasibility proof.
    return 0 if report["broadcasts"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
