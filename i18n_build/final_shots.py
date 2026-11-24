import threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

DOCS = Path('/workspace/neungnolstay-site/docs')
OUT = Path('/workspace/downloads/neungnolstay_v2')
OUT.mkdir(parents=True, exist_ok=True)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DOCS), **kw)

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{port}'

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for name, w, h, mob in (('pc', 1440, 900, False), ('mobile', 390, 844, True)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, is_mobile=mob, has_touch=mob,
                            device_scale_factor=1, reduced_motion='reduce')
        p = ctx.new_page()
        errs = []
        p.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        p.on('pageerror', lambda e: errs.append(str(e)))

        # 메인
        p.goto(base + '/ko/', wait_until='networkidle')
        p.wait_for_timeout(2200)
        p.screenshot(path=str(OUT / f'01-main-{name}.png'))
        p.locator('#stays').scroll_into_view_if_needed()
        p.wait_for_timeout(600)
        p.screenshot(path=str(OUT / f'02-main-rooms-{name}.png'))
        p.locator('#reserve').scroll_into_view_if_needed()
        p.wait_for_timeout(2800)
        p.screenshot(path=str(OUT / f'03-main-reserve-{name}.png'))

        # 객실 갤러리
        p.goto(base + '/ko/orot/', wait_until='networkidle')
        p.evaluate("document.querySelector('#gallery').scrollIntoView({block:'start'})")
        p.wait_for_timeout(1200)
        p.screenshot(path=str(OUT / f'04-room-gallery-{name}.png'))
        p.locator('.gal-cell__btn').nth(4).click()
        p.wait_for_timeout(900)
        p.screenshot(path=str(OUT / f'05-room-lightbox-{name}.png'))
        p.keyboard.press('Escape')

        # 예약 달력 + 선택
        p.evaluate("document.querySelector('#reserve').scrollIntoView({block:'start'})")
        p.wait_for_timeout(2800)
        avail = p.evaluate("""() => [...document.querySelectorAll('#reserve .bk-day:not(:disabled)[data-date]')].map(b => b.dataset.date)""")
        if len(avail) > 6:
            p.click(f'#reserve .bk-day[data-date="{avail[2]}"]')
            p.wait_for_timeout(250)
            p.click(f'#reserve .bk-day[data-date="{avail[5]}"]')
            p.wait_for_timeout(500)
        p.screenshot(path=str(OUT / f'06-room-booking-{name}.png'))

        # 관리자
        p.goto(base + '/admin/', wait_until='networkidle')
        p.wait_for_timeout(2500)
        p.screenshot(path=str(OUT / f'07-admin-lock-{name}.png'))
        for k in '0000':
            p.click(f'#keypad [data-key="{k}"]')
            p.wait_for_timeout(90)
        p.wait_for_timeout(2600)
        p.screenshot(path=str(OUT / f'08-admin-calendar-{name}.png'))
        p.click('#nextMonth')
        p.wait_for_timeout(400)
        p.click('#calGrid .day[data-date]')
        p.wait_for_timeout(700)
        p.screenshot(path=str(OUT / f'09-admin-day-sheet-{name}.png'))
        p.click('#sheetClose')
        p.click('[data-tab="bookings"]')
        p.wait_for_timeout(500)
        p.screenshot(path=str(OUT / f'10-admin-bookings-{name}.png'))
        p.click('[data-tab="rates"]')
        p.wait_for_timeout(500)
        p.screenshot(path=str(OUT / f'11-admin-rates-{name}.png'))
        print(name, 'errors', errs[:4])
        ctx.close()
    b.close()
srv.shutdown()
print('done')
