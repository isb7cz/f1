#!/usr/bin/env python3
"""Actions data update: retain the last good snapshot if Nova fails."""
from datetime import datetime
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PRAGUE, fetch_nova, instant
from scripts.seznam_backup import fetch_seznam


def fetch_sources():
    try:
        return fetch_nova(), 'https://tv.nova.cz/program'
    except Exception:
        logging.warning('Nova unavailable from runner; trying the verified Seznam TV backup', exc_info=True)
        return fetch_seznam(), 'https://tv.seznam.cz/'


def update(path, fetcher=None):
    path = Path(path)
    now = datetime.now(PRAGUE).isoformat()
    try:
        rows, source = fetch_sources() if fetcher is None else (fetcher(), 'https://tv.nova.cz/program')
        snapshot = {"updated_at": now, "programmes": rows, "fetch_failed_at": None, "source":source}
    except Exception:
        logging.exception("Nova update failed; retaining last successful snapshot")
        # No seed from research or fabricated dates. A missing/corrupt fallback
        # fails the build, so the already published site stays in place.
        snapshot = json.loads(path.read_text())
        instant(snapshot["updated_at"])
        if not isinstance(snapshot["programmes"], list):
            raise ValueError("Invalid saved snapshot")
        snapshot["fetch_failed_at"] = now
        print("::warning::Nova unavailable. Publishing the last good data with a stale-data notice.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)
    return snapshot


if __name__ == "__main__":
    update(Path(__file__).resolve().parents[1] / "web" / "schedule.json")
