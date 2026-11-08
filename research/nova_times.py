#!/usr/bin/env python3
"""Official Nova Sport 5 F1 schedule; Python 3.9+, no dependencies/API keys.

Reads only PageData.program from the public TV guide. Does not run page scripts.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys

from probe_epg import PRAGUE, fetch
from f1_times import session

URL = "https://tv.nova.cz/program"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/nova-f1-times.json"))
    args = parser.parse_args()
    # Nova rejected urllib's/default probe UA, but this ordinary browser UA works.
    result, body = fetch(URL, user_agent="Mozilla/5.0")
    report = {"tested_at": dt.datetime.now(PRAGUE).isoformat(), "source": URL,
              "channel": "Nova Sport 5", "timezone": "Europe/Prague",
              "request": result, "broadcasts": []}
    try:
        if body is None:
            raise ValueError(result["error"])
        match = re.search(r"\bvar\s+PageData\s*=\s*", body.decode("utf-8"))
        if not match:
            raise ValueError("PageData not found; page format may have changed")
        data, _ = json.JSONDecoder().raw_decode(body.decode("utf-8")[match.end():])
        # Never save the complete PageData object: unrelated auth/player fields
        # are neither needed nor part of the report.
        programmes = {}
        days = []
        for day in data["program"]:
            for channel in day["channels"]:
                if channel["id"] != "nova-sport-5":
                    continue
                days.append(day["id"])
                for segment in channel["segments"]:
                    for item in segment["items"]:
                        programmes[item["id"]] = item
        if not programmes:
            raise ValueError("Nova Sport 5 schedule is empty")
        report["schedule_days"] = sorted(set(days))
        report["all_programme_count"] = len(programmes)
        report["observed_programme_range"] = {
            "first_start": min(p["start_at"] for p in programmes.values()),
            "last_start": max(p["start_at"] for p in programmes.values()),
            "last_end": max(p["end_at"] for p in programmes.values())}
        for p in programmes.values():
            if not re.match(r"^Formule\s*1\b", p["title"], re.I):
                continue
            description = p.get("description", "")
            live = bool(re.search(r"přímý přenos|\bživě\b", description, re.I))
            replay = bool(re.search(r"záznam|repríz", description, re.I))
            status = "conflict" if live and replay else "live" if live else "replay" if replay else "unknown"
            report["broadcasts"].append({"id": p["id"], "start": p["start_at"],
                                         "end": p["end_at"], "title": p["title"],
                                         "session": session(p["title"]),
                                         "status": status, "description": description})
        report["broadcasts"].sort(key=lambda p: p["start"])
        if not report["broadcasts"]:
            raise ValueError("No F1 broadcasts found; not a successful feasibility test")
    except (ValueError, KeyError, TypeError) as exc:
        report["error"] = str(exc)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    today = dt.datetime.now(PRAGUE).date()
    for p in report["broadcasts"]:
        if p["status"] == "live" and dt.datetime.fromisoformat(p["start"]).date() >= today:
            print(f'{p["start"]} | {p["title"]} | živě')
    print(f'Saved {len(report["broadcasts"])} F1 broadcasts to {args.output}', file=sys.stderr)
    if "error" in report:
        print(report["error"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
