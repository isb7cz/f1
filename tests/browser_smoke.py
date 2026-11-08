"""Browser integration checks against a running local server.

Development-only dependency: Playwright; production needs only Python.
Run: python3 tests/browser_smoke.py
"""
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import timedelta
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Schedule, instant
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("F1_TEST_URL", "http://127.0.0.1:8000")


def main():
    with urlopen(BASE + "/api/weekend") as response:
        live = json.load(response)
    assert live["state"] == "ready", live
    assert not live["stale"], live
    output = ROOT / "test-results"
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        engines = [("chromium", p.chromium, {"executable_path": shutil.which("chromium")})]
        if Path(p.webkit.executable_path).exists():
            engines.append(("webkit", p.webkit, {}))
        for engine_name, engine, options in engines:
            browser = engine.launch(headless=True, **options)
            for name, width, height in [("iphone", 390, 844), ("ipad", 768, 1024), ("mac", 1440, 1000)]:
                # Deliberately use a non-Czech device timezone.
                context = browser.new_context(viewport={"width": width, "height": height},
                                              timezone_id="America/Los_Angeles")
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(BASE)
                page.get_by_role("heading", name=live["title"], exact=True).wait_for()
                assert page.locator(".day").count() == len(live["days"])
                assert page.locator(".broadcast").count() == sum(len(d["items"]) for d in live["days"])
                assert page.locator(".broadcast time").all_text_contents() == [i["time"] for d in live["days"] for i in d["items"]]
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name
                page.screenshot(path=str(output / f"{engine_name}-{name}.png"), full_page=True)
                # Missing programme, source error, and stale cache remain readable.
                for state in [
                    {"state": "unavailable", "message": "Program nejbližšího víkendu F1 zatím není k dispozici."},
                    {"state": "error", "message": "Program se nyní nepodařilo načíst."},
                    dict(live, stale=True),
                ]:
                    page.route("**/api/weekend", lambda route: route.fulfill(json=state))
                    page.reload()
                    page.locator('#content[aria-busy="false"]').wait_for()
                    if state["state"] != "ready":
                        assert page.locator(".broadcast").count() == 0
                        assert state["message"] in page.locator("main").inner_text()
                    else:
                        assert "Aktualizace se opozdila" in page.locator(".notice").inner_text()
                    page.unroute("**/api/weekend")
                # Real source schedule at a later date must advance to Las Vegas,
                # render the overnight session on its Prague date, and omit replays.
                cached = Schedule(ROOT / ".cache" / "nova.json")
                current_race = next(r for r in cached.data if r["kind"] == "race" and r["grand_prix"] == live["title"])
                later = cached.view(instant(current_race["end"]) + timedelta(seconds=1))
                page.route("**/api/weekend", lambda route: route.fulfill(json=later))
                page.reload()
                if later["state"] == "ready":
                    assert later["title"] != live["title"]
                    page.get_by_role("heading", name=later["title"], exact=True).wait_for()
                    first_day = later["days"][0]
                    assert page.locator(".day").first.locator(".date").get_attribute("datetime") == first_day["date"]
                    assert page.locator(".broadcast time").first.inner_text() == first_day["items"][0]["time"]
                else:
                    page.get_by_text(later["message"], exact=True).wait_for()
                    assert page.locator(".broadcast").count() == 0
                assert "F1 Academy" not in page.locator("main").inner_text()
                assert not errors, errors
                context.close()
                print(f"PASS {engine_name} {name}: live data, timezone, layout, missing/error/stale, next weekend")
            browser.close()
        if len(engines) == 1:
            print("WebKit unavailable: Apple device sizes tested in Chromium, not native Safari.")


if __name__ == "__main__":
    main()
