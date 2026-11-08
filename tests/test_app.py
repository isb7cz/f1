import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
from datetime import datetime
from zoneinfo import ZoneInfo

from app import Schedule, instant, make_handler, parse_nova, select_weekend


def row(id, event, detail, start, end, description="Přímý přenos"):
    return {"id": id, "title": f"Formule 1 - {event}" + (f" ({detail})" if detail else ""),
            "description": description, "start_at": start, "end_at": end}


def page(rows):
    return 'var PageData = ' + json.dumps({"program": [{"channels": [
        {"id": "nova-sport-5", "segments": [{"items": rows}]}]}]}) + ';'


class WeekendTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            row(1, "Velká cena A 2026", "1. trénink", "2026-11-06T16:20:00+01:00", "2026-11-06T17:30:00+01:00"),
            row(2, "Velká cena A 2026", "kvalifikace", "2026-11-07T18:50:00+01:00", "2026-11-07T20:00:00+01:00"),
            row(3, "úvodní studio 2026", "", "2026-11-08T17:00:00+01:00", "2026-11-08T17:50:00+01:00"),
            row(4, "Velká cena A 2026", "", "2026-11-08T17:50:00+01:00", "2026-11-08T19:50:00+01:00"),
            row(5, "závěrečné studio 2026", "", "2026-11-08T19:50:00+01:00", "2026-11-08T20:50:00+01:00"),
            row(6, "Velká cena B 2026", "1. trénink", "2026-11-20T01:25:00+01:00", "2026-11-20T02:30:00+01:00"),
            row(7, "Velká cena B 2026", "", "2026-11-22T04:50:00+01:00", "2026-11-22T06:50:00+01:00"),
        ]
        self.data = parse_nova(page(self.rows))

    def test_active_weekend_includes_past_sessions_then_advances(self):
        before = select_weekend(self.data, instant("2026-11-08T18:00:00+01:00"))
        self.assertEqual(before["title"], "Velká cena A 2026")
        self.assertEqual(len(before["days"]), 3)
        self.assertEqual([p["label"] for p in before["days"][-1]["items"]], ["Úvodní studio", "Závod"])
        after = select_weekend(self.data, instant("2026-11-08T19:50:00+01:00"))
        self.assertEqual(after["title"], "Velká cena B 2026")

    def test_overnight_uses_actual_prague_calendar_date(self):
        data = select_weekend(self.data, instant("2026-11-10T00:00:00Z"))
        self.assertEqual(data["days"][0]["date"], "2026-11-20")
        self.assertEqual(data["days"][0]["items"][0]["time"], "01:25")

    def test_summer_winter_and_midnight_conversion(self):
        self.assertEqual(instant("2026-07-01T22:30:00Z").isoformat(), "2026-07-02T00:30:00+02:00")
        self.assertEqual(instant("2026-11-01T22:30:00Z").isoformat(), "2026-11-01T23:30:00+01:00")
        self.assertEqual(instant("2026-10-25T00:30:00Z").strftime("%H:%M %z"), "02:30 +0200")
        self.assertEqual(instant("2026-10-25T01:30:00Z").strftime("%H:%M %z"), "02:30 +0100")

    def test_replays_unknown_conflicts_and_academy_excluded(self):
        items = [row(i, "Velká cena A 2026", "kvalifikace", "2026-11-08T10:00:00+01:00", "2026-11-08T11:00:00+01:00", desc)
                 for i, desc in enumerate(["Záznam", "", "Přímý přenos a záznam"])]
        academy = dict(self.rows[0], id=99, title="F1 Academy - závod")
        self.assertEqual(parse_nova(page(items + [academy])), [])

    def test_sprint_weekend(self):
        items = [row(i, "Velká cena C 2026", detail, f"2026-11-07T{hour}:00:00+01:00", f"2026-11-07T{hour}:50:00+01:00")
                 for i, (detail, hour) in enumerate([("kvalifikace do sprintu", "10"), ("sprint", "12"), ("kvalifikace", "16")])]
        data = select_weekend(parse_nova(page(items)), instant("2026-11-06T12:00:00+01:00"))
        self.assertEqual([p["label"] for p in data["days"][0]["items"]], ["Sprintová kvalifikace", "Sprint", "Kvalifikace"])
        self.assertTrue(data["partial"])

    def test_unavailable_after_last_race_and_empty_programme(self):
        self.assertEqual(select_weekend(self.data, instant("2026-12-01T00:00:00Z"))["state"], "unavailable")
        self.assertEqual(parse_nova(page([])), [])
        with self.assertRaises(ValueError):
            parse_nova("<html>website changed</html>")


class ServiceTests(unittest.TestCase):
    def test_failure_keeps_last_successful_cache_and_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            service = Schedule(path, fetcher=lambda: [])
            self.assertTrue(service.refresh())
            self.assertEqual(service.view()["state"], "unavailable")
            saved = path.read_bytes()
            def fail():
                raise OSError("Source unavailable (simulated)")
            service.fetcher = fail
            with self.assertLogs(level="ERROR"):
                self.assertFalse(service.refresh())
            self.assertTrue(service.view()["stale"])
            self.assertEqual(path.read_bytes(), saved)
            self.assertEqual(Schedule(path).view()["state"], "unavailable")

    def test_first_start_loading_then_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = Schedule(Path(tmp)/"cache.json", fetcher=lambda: (_ for _ in ()).throw(OSError("offline")))
            self.assertEqual(service.view()["state"], "loading")
            with self.assertLogs(level="ERROR"):
                service.refresh()
            self.assertEqual(service.view()["state"], "error")

    def test_http_empty_source_and_static_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = Schedule(Path(tmp)/"cache.json", fetcher=lambda: [])
            service.refresh()
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + "/api/weekend") as response:
                    self.assertEqual(json.load(response)["state"], "unavailable")
                with urlopen(base) as response:
                    self.assertIn("F1 víkend", response.read().decode())
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
