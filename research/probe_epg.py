#!/usr/bin/env python3
"""Read-only feasibility probe. Python 3.9+, no dependencies or API keys.

Nova/Seznam are discovery probes only: their HTML is NOT parsed as programmes.
The XML endpoint comes from iptv-org/epg's mujtvprogram.cz adapter (channel 1073).
Failures and unknown transmission status are deliberately preserved.
"""
import argparse
import datetime as dt
import gzip
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

PRAGUE = ZoneInfo("Europe/Prague")


def fetch(url, user_agent="F1-EPG-feasibility-probe/0.1"):
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read(10_000_001)
            if len(body) > 10_000_000:
                raise ValueError("Response exceeds 10 MB safety limit")
            if body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            return {"url": url, "final_url": response.url,
                    "http_status": response.status, "bytes": len(body)}, body
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"url": url, "error": str(exc)}, None


def classify(text):
    """Conservative textual hints, not proof that a programme is live."""
    text = text.casefold()
    live = bool(re.search(r"\bživě\b|\blive\b|přímý přenos", text))
    repeat = bool(re.search(r"repríz|záznam|\breplay\b|opakování", text))
    status = "unknown"
    if live and repeat:
        status = "conflicting_markers"
    elif repeat:
        status = "replay_marker"
    elif live:
        status = "live_marker"
    # Never identify F1 just from 'Grand Prix' (could be another sport).
    is_f1 = bool(re.search(r"\bf1\b|formul[aeiy]\s*1|formula\s*1", text))
    session = None
    if is_f1:
        if "sprint" in text and re.search(r"kvalifik|shootout", text):
            session = "sprint_qualifying"
        elif "sprint" in text:
            session = "sprint"
        elif "kvalifik" in text:
            session = "qualifying"
        elif "trénink" in text or "practice" in text:
            session = "practice"
        elif "závod" in text or re.search(r"\brace\b", text):
            session = "race"
    return {"f1_text_match": is_f1, "session_hint": session,
            "transmission_hint": status}


def parse_xml(body):
    root = ET.fromstring(body)
    if root.tag != "tv-program-programmes":
        raise ValueError(f"Unexpected XML root: {root.tag}")
    programmes = []
    for item in root.findall("programme"):
        title = item.findtext("name", "")
        raw_start = item.findtext("startDate", "")
        start = None
        for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H.%M"):
            try:
                start = dt.datetime.strptime(raw_start, fmt).replace(tzinfo=PRAGUE).isoformat()
                break
            except ValueError:
                pass
        if not start or not title:
            raise ValueError("Programme missing a valid date/time or title")
        description = " ".join(filter(None, [item.findtext("shortDescription"),
                                              item.findtext("longDescription")]))
        programmes.append({"start": start, "title": title,
                           "description": description,
                           **classify(title + " " + description)})
    return programmes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=22, help="Consecutive day offsets to probe (1–31)")
    parser.add_argument("--output", type=Path, default=Path("/tmp/f1-epg-probe.json"))
    args = parser.parse_args()
    if not 1 <= args.days <= 31:
        parser.error("--days must be between 1 and 31")
    today = dt.datetime.now(PRAGUE).date()
    report = {"tested_at": dt.datetime.now(PRAGUE).isoformat(), "today": str(today),
              "discovery": [], "xml_days": [], "notes": [
                  "Nova and Seznam discovery responses do not validate programme extraction.",
                  "A failed request is not an empty schedule or an availability boundary.",
                  "Transmission/session classifications are unverified text heuristics."]}
    for url in ["https://tv.nova.cz/program", "https://tv.seznam.cz/",
                f"https://m.tv.sms.cz/index.php?stanice=Nova+Sport+5&cas=0&den={today}"]:
        result, body = fetch(url)
        if body is not None:
            text = body.decode("utf-8", errors="replace")
            result["nova_sport_5_mentioned"] = bool(re.search(r"nova\s*sport\s*5", text, re.I))
            result["extraction_verified"] = False
        report["discovery"].append(result)
    for offset in range(args.days):
        result, body = fetch("https://services.mujtvprogram.cz/tvprogram2services/services/"
                             f"tvprogrammelist_mobile.php?channel_cid=1073&day={offset}")
        result.update(requested_date=str(today + dt.timedelta(days=offset)), offset=offset)
        report["xml_days"].append(result)
        if body is None:
            break  # Don't hammer a blocked source or label subsequent dates unavailable.
        try:
            result["programmes"] = parse_xml(body)
            result["count"] = len(result["programmes"])
        except (ET.ParseError, ValueError) as exc:
            result["parse_error"] = str(exc)
            break
        time.sleep(0.3)
    starts = [p["start"] for day in report["xml_days"] for p in day.get("programmes", [])]
    report["observed_programme_range"] = {"min": min(starts), "max": max(starts)} if starts else None
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "programme_count": len(starts),
                      "errors": [r.get("error", r.get("parse_error")) for r in
                                 report["discovery"] + report["xml_days"]
                                 if "error" in r or "parse_error" in r]}, ensure_ascii=False, indent=2))
    return 0 if starts else 1


if __name__ == "__main__":
    raise SystemExit(main())
