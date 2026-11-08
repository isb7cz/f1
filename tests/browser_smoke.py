"""Static Pages integration test. Start: python3 -m http.server 8001
Then: python3 tests/browser_smoke.py (development-only Playwright dependency).
F1_TEST_URL can point to the real Pages URL instead of the local static server.
"""
import json
import gzip
import os
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import instant, select_weekend
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('F1_TEST_URL', 'http://127.0.0.1:8001/web/').rstrip('/') + '/'


def main():
    with urlopen(BASE + 'schedule.json') as response:
        raw = json.load(response)
    expected = select_weekend(raw['programmes'], datetime.now().astimezone())
    assert expected['state'] == 'ready', expected
    output = ROOT / 'test-results'
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which('chromium'))
        for name, width, height in [('iphone',390,844), ('ipad',768,1024), ('mac',1440,1000)]:
            context = browser.new_context(viewport={'width':width, 'height':height}, timezone_id='America/Los_Angeles')
            # Some managed browser builds don't inherit the cloud proxy CA.
            # Optional verified transport: urllib keeps full TLS verification
            # with the platform CA, then supplies real public responses to the
            # browser. Never use ignore_https_errors or disable verification.
            if os.environ.get('F1_TEST_TRUSTED_TRANSPORT') == '1':
                def trusted_transport(route):
                    with urlopen(route.request.url, timeout=30) as response:
                        body=response.read()
                        if body[:2]==b'\x1f\x8b':
                            body=gzip.decompress(body)
                        route.fulfill(status=response.status, body=body,
                                      content_type=response.headers.get('Content-Type','application/octet-stream'))
                context.route(BASE+'**',trusted_transport)
            page = context.new_page()
            errors=[]
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(BASE)
            page.get_by_role('heading',name=expected['title'],exact=True).wait_for()
            assert page.locator('.broadcast time').all_text_contents() == [i['time'] for d in expected['days'] for i in d['items']]
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / f'static-{name}.png'),full_page=True)
            # No server and no /api calls. Simulate source failure and no EPG.
            for snapshot in [dict(raw,programmes=[]), dict(raw,fetch_failed_at=raw['updated_at'])]:
                page.route('**/schedule.json',lambda route: route.fulfill(json=snapshot))
                page.reload()
                page.locator('#content[aria-busy="false"]').wait_for()
                if not snapshot['programmes']:
                    assert page.locator('.broadcast').count()==0
                    assert 'zatím není k dispozici' in page.locator('main').inner_text()
                else:
                    assert 'Aktualizace se opozdila' in page.locator('.notice').inner_text()
                page.unroute('**/schedule.json')
            race = next(r for r in raw['programmes'] if r['kind']=='race' and r['grand_prix']==expected['title'])
            later_time=instant(race['end'])+timedelta(seconds=1)
            later=select_weekend(raw['programmes'],later_time)
            page.clock.install(time=later_time)
            page.reload()
            if later['state']=='ready':
                page.get_by_role('heading',name=later['title'],exact=True).wait_for()
                assert later['title']!=expected['title']
                assert page.locator('.broadcast time').first.inner_text()==later['days'][0]['items'][0]['time']
                assert page.locator('.day .date').first.get_attribute('datetime')==later['days'][0]['date']
            else:
                page.get_by_text(later['message'],exact=True).wait_for()
            assert not errors, errors
            context.close()
            print(f'PASS {name}: real data, Prague timezone, static subpath, layout, outage, no EPG, next weekend')
        browser.close()


if __name__=='__main__':
    main()
