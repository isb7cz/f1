#!/usr/bin/env python3
"""Actions data update: retain the last good snapshot if Nova fails."""
from datetime import datetime
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PRAGUE, fetch_nova, instant


def update(path, fetcher=fetch_nova):
    path = Path(path)
    now = datetime.now(PRAGUE).isoformat()
    try:
        snapshot = {"updated_at": now, "programmes": fetcher(), "fetch_failed_at": None}
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
