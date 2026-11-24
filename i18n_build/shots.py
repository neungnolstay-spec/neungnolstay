#!/usr/bin/env python3
"""검수용 스크린샷: PC/모바일 주요 화면을 i18n_build/screenshots/review 에 저장."""
from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "i18n_build" / "screenshots" / "review"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DOCS), **kw)

    def log_message(self, *a):
        pass


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    def shot(page, path: str, name: str, sel: str | None = None) -> None:
        page.goto(base + path, wait_until="networkidle")
        for y in range(0, 7000, 800):
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(90)
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(250)
        if sel:
            page.locator(sel).first.scroll_into_view_if_needed()
            page.wait_for_timeout(450)
        page.screenshot(path=str(OUT / f"{name}.png"))
        print("shot", name)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pc = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        p = pc.new_page()
        shot(p, "/ko/", "pc-home-top")
        shot(p, "/ko/", "pc-home-stays", "#stays")
        shot(p, "/ko/", "pc-home-map", "#location")
        shot(p, "/ko/", "pc-home-contact", "#contact")
        shot(p, "/ko/", "pc-home-booking", "#booking")
        shot(p, "/ko/heyum/", "pc-heyum-top")
        shot(p, "/ko/heyum/", "pc-heyum-guide", "#guide")
        shot(p, "/en/", "pc-en-stays", "#stays")
        shot(p, "/zh-tw/orot/", "pc-zhtw-orot")
        pc.close()

        mob = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce",
                                  is_mobile=True, has_touch=True, device_scale_factor=2)
        m = mob.new_page()
        shot(m, "/ko/", "mo-home-top")
        shot(m, "/ko/", "mo-home-stays", "#stays")
        shot(m, "/ko/heyum/", "mo-heyum-top")
        shot(m, "/ko/heyum/", "mo-heyum-booking", "#booking")
        shot(m, "/en/", "mo-en-stays", "#stays")
        mob.close()

        r = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        q = r.new_page()
        q.goto(base + "/?stay=1", wait_until="networkidle")
        q.screenshot(path=str(OUT / "pc-root.png"))
        browser.close()
    srv.shutdown()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
