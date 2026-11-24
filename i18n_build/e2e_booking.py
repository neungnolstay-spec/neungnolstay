import threading, json, urllib.request, time
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

DOCS = Path('/workspace/neungnolstay-site/docs')
OUT = Path('/workspace/downloads/neungnolstay_v2')
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
    page.goto(base + '/ko/heyum/', wait_until='networkidle')
    page.locator('#reserve').scroll_into_view_if_needed()
    page.wait_for_timeout(3500)

    # next month
    page.click('[data-bk-next]')
    page.wait_for_timeout(300)
    page.click('[data-bk-ci-val]')  # reset selection
    page.click('#reserve .bk-day[data-date="2026-12-15"]')
    page.wait_for_timeout(200)
    page.click('#reserve .bk-day[data-date="2026-12-17"]')
    page.wait_for_timeout(300)
    print('total', page.evaluate("document.querySelector('[data-bk-total]').textContent"))
    print('detail', page.evaluate("document.querySelector('[data-bk-detail]').textContent"))
    page.click('[data-bk-step="adults"][data-dir="1"]')
    page.wait_for_timeout(200)
    print('total after +1 adult', page.evaluate("document.querySelector('[data-bk-total]').textContent"))
    page.screenshot(path=str(OUT / 'booking-selected-pc.png'))

    page.fill('[data-bk-form] input[name="name"]', '테스트예약')
    page.fill('[data-bk-form] input[name="phone"]', '010-1234-5678')
    page.fill('[data-bk-form] input[name="email"]', 'test@example.com')
    page.fill('[data-bk-form] textarea[name="message"]', 'E2E 테스트 예약입니다.')
    page.click('[data-bk-submit]')
    page.wait_for_timeout(2500)
    print('done visible', page.evaluate("!document.querySelector('[data-bk-done]').hidden"))
    print('ref', page.evaluate("document.querySelector('[data-bk-ref]').textContent"))
    page.screenshot(path=str(OUT / 'booking-success-pc.png'))

    data = db_get('/bookings')
    print('server bookings', json.dumps({k: {kk: v[kk] for kk in ('room', 'checkin', 'checkout', 'status', 'total', 'name')} for k, v in (data or {}).items()}, ensure_ascii=False))

    # admin: confirm
    page.goto(base + '/admin/', wait_until='networkidle')
    page.wait_for_timeout(2500)
    if page.evaluate("document.getElementById('app').hidden"):
        for k in '0000':
            page.click(f'#keypad [data-key="{k}"]')
            page.wait_for_timeout(100)
        page.wait_for_timeout(2000)
    page.click('[data-tab="bookings"]')
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / 'admin-bookings-pc.png'))
    btns = page.locator('.bk--pending button:has-text("예약 확정")')
    print('pending cards', btns.count())
    if btns.count():
        btns.first.click()
        page.wait_for_timeout(2000)
    data = db_get('/bookings')
    print('after confirm', json.dumps({k: v.get('status') for k, v in (data or {}).items()}, ensure_ascii=False))

    # guest page reflects block
    page.goto(base + '/ko/heyum/', wait_until='networkidle')
    page.locator('#reserve').scroll_into_view_if_needed()
    page.wait_for_timeout(3000)
    page.click('[data-bk-next]')
    page.wait_for_timeout(500)
    print('15th disabled', page.evaluate("document.querySelector('#reserve .bk-day[data-date=\"2026-12-15\"]')?.disabled"))
    print('17th disabled', page.evaluate("document.querySelector('#reserve .bk-day[data-date=\"2026-12-17\"]')?.disabled"))
    page.screenshot(path=str(OUT / 'booking-blocked-pc.png'))
    # calendar sheet in admin
    page.goto(base + '/admin/', wait_until='networkidle')
    page.wait_for_timeout(2500)
    page.click('#nextMonth')
    page.wait_for_timeout(500)
    page.click('#calGrid .day[data-date="2026-12-15"]')
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / 'admin-day-sheet-pc.png'))
    print('sheet visible', page.evaluate("!document.getElementById('sheet').hidden"))
    print('errors', errs[:8])
    ctx.close()
    b.close()
srv.shutdown()
