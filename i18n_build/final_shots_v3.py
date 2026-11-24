import threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

DOCS = Path('/workspace/neungnolstay-site/docs')
OUT = Path('/workspace/downloads/neungnolstay_v3')
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


def login(p):
    p.goto(base + '/admin/', wait_until='networkidle')
    p.wait_for_timeout(2600)
    if not p.evaluate("() => document.getElementById('app').hidden"):
        return
    for k in '0000':
        p.click(f'#keypad [data-key="{k}"]')
        p.wait_for_timeout(90)
    p.wait_for_timeout(2600)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for name, w, h, mob in (('pc', 1440, 900, False), ('mobile', 390, 844, True)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, is_mobile=mob, has_touch=mob,
                            device_scale_factor=1, reduced_motion='reduce')
        p = ctx.new_page()
        errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))

        p.goto(base + '/ko/', wait_until='networkidle')
        p.wait_for_timeout(2200)
        p.screenshot(path=str(OUT / f'01-home-{name}.png'))
        p.locator('#stays').scroll_into_view_if_needed()
        p.wait_for_timeout(600)
        p.screenshot(path=str(OUT / f'02-home-rooms-{name}.png'))

        # 문의 게시판
        p.goto(base + '/ko/heyum/#inquiry', wait_until='networkidle')
        p.locator('#inquiry').scroll_into_view_if_needed()
        p.wait_for_timeout(2200)
        p.screenshot(path=str(OUT / f'03-inquiry-{name}.png'))

        # 리뷰 + 작성 폼
        p.goto(base + '/ko/heyum/#reviews', wait_until='networkidle')
        p.locator('#reviews').scroll_into_view_if_needed()
        p.wait_for_timeout(2800)
        p.screenshot(path=str(OUT / f'04-reviews-{name}.png'))
        p.click('[data-rv-open]')
        p.wait_for_timeout(500)
        p.locator('#reviews').scroll_into_view_if_needed()
        p.screenshot(path=str(OUT / f'05-review-form-{name}.png'))

        # 예약 (비품 체크박스)
        p.goto(base + '/ko/heyum/#reserve', wait_until='networkidle')
        p.locator('#reserve').scroll_into_view_if_needed()
        p.wait_for_timeout(2600)
        avail = p.evaluate("""() => [...document.querySelectorAll('#reserve .bk-day:not(:disabled)[data-date]')].map(b => b.dataset.date)""")
        if len(avail) > 3:
            p.click(f'#reserve .bk-day[data-date="{avail[0]}"]')
            p.wait_for_timeout(200)
            p.click(f'#reserve .bk-day[data-date="{avail[1]}"]')
            p.wait_for_timeout(400)
        p.evaluate("document.querySelector('.bk-amen').scrollIntoView({block:'center'})")
        p.wait_for_timeout(400)
        p.screenshot(path=str(OUT / f'06-booking-amenities-{name}.png'))

        # 영어 페이지
        p.goto(base + '/en/orot/#inquiry', wait_until='networkidle')
        p.locator('#inquiry').scroll_into_view_if_needed()
        p.wait_for_timeout(2600)
        p.screenshot(path=str(OUT / f'07-inquiry-en-{name}.png'))

        # 관리자
        login(p)
        p.wait_for_timeout(1400)
        p.screenshot(path=str(OUT / f'08-admin-calendar-{name}.png'))
        p.click('[data-tab="reviews"]')
        p.wait_for_timeout(1200)
        p.screenshot(path=str(OUT / f'09-admin-reviews-{name}.png'))
        p.click('[data-tab="inquiries"]')
        p.wait_for_timeout(900)
        p.screenshot(path=str(OUT / f'10-admin-inquiries-{name}.png'))
        p.click('[data-tab="bookings"]')
        p.wait_for_timeout(700)
        p.screenshot(path=str(OUT / f'11-admin-bookings-{name}.png'))
        p.click('[data-tab="settings"]')
        p.wait_for_timeout(900)
        p.evaluate("document.querySelector('#icalSynced').scrollIntoView({block:'center'})")
        p.wait_for_timeout(300)
        p.screenshot(path=str(OUT / f'12-admin-settings-{name}.png'))
        print(name, 'errors', errs[:4])
        ctx.close()
    b.close()
srv.shutdown()
print('done ->', OUT)
