import threading, json, urllib.request, time
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

DOCS = Path('/workspace/neungnolstay-site/docs')
BASE_DB = 'https://neungnol-checklist-default-rtdb.asia-southeast1.firebasedatabase.app/neungnol_booking_v1'


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DOCS), **kw)

    def log_message(self, *a):
        pass


def db_get(path=''):
    with urllib.request.urlopen(BASE_DB + path + '.json') as r:
        return json.load(r)


srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{port}'

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 950}, reduced_motion='reduce')
    page = ctx.new_page()
    errs = []
    page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(base + '/admin/', wait_until='networkidle')
    page.wait_for_timeout(3000)
    if page.evaluate("document.getElementById('app').hidden"):
        for k in '0000':
            page.click(f'#keypad [data-key="{k}"]')
            page.wait_for_timeout(100)
        page.wait_for_timeout(2200)
    # go to 2027-01 (2 months forward: Nov -> Dec -> Jan)
    page.click('#nextMonth'); page.wait_for_timeout(200)
    page.click('#nextMonth'); page.wait_for_timeout(400)
    print('month', page.evaluate("document.querySelector('#monthLabel').textContent"))
    page.click('#calGrid .day[data-date="2027-01-05"]')
    page.wait_for_timeout(700)
    page.screenshot(path=str(Path('/workspace/downloads/neungnolstay_v2') / 'admin-sheet-block-pc.png'))
    page.click('#sheetBody .btn:has-text("외부예약 차단")')
    page.wait_for_timeout(2000)
    print('blocks', db_get('/blocks/heyum'))
    page.click('#calGrid .day[data-date="2027-01-05"]')
    page.wait_for_timeout(600)
    page.click('#sheetBody .btn:has-text("차단 해제")')
    page.wait_for_timeout(1800)
    print('blocks after unblock', db_get('/blocks/heyum'))

    # rate override
    page.click('#calGrid .day[data-date="2027-01-06"]')
    page.wait_for_timeout(600)
    page.fill('#sheetBody input[type="number"]', '750000')
    page.click('#sheetBody .btn:has-text("요금 적용")')
    page.wait_for_timeout(1800)
    print('overrides', db_get('/settings/overrides/heyum'))
    page.screenshot(path=str(Path('/workspace/downloads/neungnolstay_v2') / 'admin-override-cal-pc.png'))
    page.click('[data-tab="rates"]')
    page.wait_for_timeout(800)
    page.screenshot(path=str(Path('/workspace/downloads/neungnolstay_v2') / 'admin-rates-pc.png'))
    page.click('.ovr__row button')
    page.wait_for_timeout(1500)
    print('overrides after delete', db_get('/settings/overrides/heyum'))

    # remove test booking
    data = db_get('/bookings') or {}
    for k, v in data.items():
        if v.get('name') == '테스트예약':
            req = urllib.request.Request(f'{BASE_DB}/bookings/{k}.json', method='DELETE')
            urllib.request.urlopen(req).read()
    print('bookings left', db_get('/bookings'))
    print('errors', errs[:6])
    ctx.close()
    b.close()
srv.shutdown()
