#!/usr/bin/env python3
"""생성된 docs/ 사이트 전수 검증.

- 16개 페이지 HTTP 200, title/description/canonical/hreflang/og/JSON-LD
- 내부 링크 전부 200, 에어비앤비 링크 정확성, 금지 정보(타 숙소) 미포함
- sitemap.xml / robots.txt 유효성
- Playwright: PC(1440) · 모바일(390) 스크린샷, 가로 넘침·콘솔 오류 점검

    python3 i18n_build/check.py
"""
from __future__ import annotations

import json
import re
import sys
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = ROOT / "docs"
SHOTS = HERE / "screenshots"

sys.path.insert(0, str(HERE))
import build  # noqa: E402

BASE_PATH = urllib.parse.urlparse(build.BASE_URL).path.rstrip("/")  # /neungnolstay
LANGS_DIRS = [t["dir"] for t in build.LANGS]
PAGES = ["/"] + [f"/{d}/" for d in LANGS_DIRS] + [f"/{d}/{r}/" for d in LANGS_DIRS for r in build.ROOMS]
AIRBNB = build.AIRBNB
EXPECTED_HREFLANG = {"ko", "en", "ja", "zh-Hans", "zh-Hant", "x-default"}

problems: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


class Page(HTMLParser):
    """필요한 head/본문 정보만 모으는 가벼운 파서."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.metas: list[dict] = []
        self.links: list[dict] = []
        self.anchors: list[dict] = []
        self.h1 = 0
        self.h2 = 0
        self.imgs: list[dict] = []
        self.jsonld: list[str] = []
        self._in_jsonld = False
        self.lang = None
        self.text_parts: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "a":
            self.anchors.append(a)
        elif tag == "h1":
            self.h1 += 1
        elif tag == "h2":
            self.h2 += 1
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "script":
            if a.get("type") == "application/ld+json":
                self._in_jsonld = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_jsonld = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_jsonld:
            self.jsonld.append(data)
        else:
            self.text_parts.append(data)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.text_parts))


def local(base: str, path: str) -> str:
    return base.rstrip("/") + path


def fetch(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        return ex.code, ""
    except Exception as ex:  # noqa: BLE001
        return 0, str(ex)


def check_seo(base: str, path: str) -> None:
    url = local(base, path)
    status, body = fetch(url)
    if status != 200:
        fail(f"{path} → HTTP {status}")
        return
    p = Page()
    p.feed(body)

    if not p.title or len(p.title) < 12:
        fail(f"{path} title 부족: {p.title!r}")
    desc = next((m.get("content", "") for m in p.metas if m.get("name") == "description"), "")
    if len(desc) < 60:
        fail(f"{path} meta description 부족/없음 ({len(desc)}자)")
    if len(desc) > 320:
        notes.append(f"{path} description {len(desc)}자 (다소 김)")

    canon = next((l.get("href", "") for l in p.links if l.get("rel") == "canonical"), "")
    expected_canon = build.BASE_URL + path
    if canon != expected_canon:
        fail(f"{path} canonical 불일치: {canon} != {expected_canon}")

    hrefs = {l.get("hreflang"): l.get("href") for l in p.links if l.get("rel") == "alternate" and l.get("hreflang")}
    if set(hrefs) != EXPECTED_HREFLANG:
        fail(f"{path} hreflang 집합 불일치: {sorted(hrefs)}")
    for tag, href in hrefs.items():
        if tag == "x-default":
            continue
        if not href.startswith(build.BASE_URL):
            fail(f"{path} hreflang {tag} 절대 URL 아님: {href}")

    # html lang
    if p.lang not in {"ko", "en", "ja", "zh-Hans", "zh-Hant"}:
        # 한 페이지라도 lang이 없으면 치명적
        fail(f"{path} html lang 없음/부적절: {p.lang!r}")
    if path == "/" and p.lang != "ko":
        notes.append("/ lang=ko (언어 선택 페이지)")

    # OG
    og = {m.get("property"): m.get("content") for m in p.metas if m.get("property")}
    for key in ("og:title", "og:description", "og:image", "og:url"):
        if not og.get(key):
            fail(f"{path} {key} 없음")
    if og.get("og:url") != expected_canon:
        fail(f"{path} og:url 불일치: {og.get('og:url')}")

    # headings
    if p.h1 != 1:
        fail(f"{path} H1 개수 {p.h1}")
    min_h2 = 1 if path == "/" else 3
    if p.h2 < min_h2:
        fail(f"{path} H2 {p.h2}개 (구조 부족)")

    # images alt
    no_alt = [i.get("src", "?") for i in p.imgs
              if not i.get("alt") and i.get("src") and i.get("aria-hidden") != "true"]
    if no_alt:
        fail(f"{path} alt 없는 이미지 {len(no_alt)}장: {no_alt[:3]}")
    no_dim = [i.get("src", "?") for i in p.imgs if not i.get("width") or not i.get("height")]
    if no_dim:
        notes.append(f"{path} width/height 없는 이미지 {len(no_dim)}장")

    # JSON-LD
    types = []
    for raw in p.jsonld:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as ex:
            fail(f"{path} JSON-LD 파싱 실패: {ex}")
            continue
        for block in (data if isinstance(data, list) else [data]):
            if "@graph" in block:
                types += [b.get("@type") for b in block["@graph"]]
            else:
                types.append(block.get("@type"))
    if not types:
        fail(f"{path} JSON-LD 없음")
    if path == "/":
        if "LodgingBusiness" not in types:
            fail(f"{path} LodgingBusiness 없음")
    elif path.count("/") == 2:  # /ko/
        if "LodgingBusiness" not in types:
            fail(f"{path} LodgingBusiness 없음")
    else:  # room
        for need in ("HotelRoom", "BreadcrumbList", "FAQPage"):
            if need not in types:
                fail(f"{path} {need} 없음")

    # 에어비앤비 / 금지 정보
    if path == "/" or path.count("/") == 2:
        for rid in ("heyum", "orot"):
            if AIRBNB[rid] not in body:
                fail(f"{path} {rid} 에어비앤비 링크 없음")
    else:
        rid = path.strip("/").split("/")[1]
        if AIRBNB[rid] not in body:
            fail(f"{path} {rid} 에어비앤비 링크 없음")
        other = "orot" if rid == "heyum" else "heyum"
        if AIRBNB[other] in body:
            fail(f"{path} 다른 객실({other}) 에어비앤비 링크 혼입")
    for banned in ("더광안", "d광안"):
        if banned in body:
            fail(f"{path} 금지 정보 포함: {banned}")
    # 외부 링크 target/rel
    for a in p.anchors:
        href = a.get("href", "")
        if href.startswith("http") and "neungnolstay-spec.github.io" not in href:
            if a.get("target") != "_blank":
                fail(f"{path} 외부 링크 target 없음: {href}")
            if "noopener" not in a.get("rel", ""):
                fail(f"{path} 외부 링크 rel=noopener 없음: {href}")

    # 내부 링크 수집
    internal = set()
    for a in p.anchors:
        href = a.get("href", "")
        if not href or href.startswith(("http", "mailto:", "tel:", "#", "javascript:")):
            continue
        internal.add(urllib.parse.urljoin(url, href))
    for l in p.links:
        href = l.get("href", "")
        if href and not href.startswith(("http", "mailto:", "tel:")):
            internal.add(urllib.parse.urljoin(url, href))
    for target_url in sorted(internal):
        status, _ = fetch(target_url)
        if status != 200:
            fail(f"{path} 내부 링크 깨짐 ({status}): {target_url}")


def check_sitemap_robots(base: str) -> None:
    status, body = fetch(local(base, "/sitemap.xml"))
    if status != 200:
        fail(f"sitemap.xml HTTP {status}")
        return
    try:
        tree = ET.fromstring(body)
    except ET.ParseError as ex:
        fail(f"sitemap.xml XML 오류: {ex}")
        return
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "xhtml": "http://www.w3.org/1999/xhtml"}
    urls = tree.findall("sm:url", ns)
    if len(urls) != len(PAGES):
        fail(f"sitemap URL {len(urls)}개 (기대 {len(PAGES)})")
    seen = set()
    for entry in urls:
        loc = entry.findtext("sm:loc", default="", namespaces=ns)
        seen.add(urllib.parse.urlparse(loc).path)
        alts = {l.get("hreflang") for l in entry.findall("xhtml:link", ns)}
        if alts != EXPECTED_HREFLANG:
            fail(f"sitemap {loc} hreflang {sorted(alts)}")
        for l in entry.findall("xhtml:link", ns):
            path = urllib.parse.urlparse(l.get("href")).path.replace(BASE_PATH, "") or "/"
            status, _ = fetch(local(base, path))
            if status != 200:
                fail(f"sitemap alternate 깨짐: {l.get('href')}")
    for path in PAGES:
        expected = (BASE_PATH + path) if path != "/" else BASE_PATH + "/"
        if expected not in seen and path != "/":
            fail(f"sitemap 에 {expected} 없음")

    status, robots = fetch(local(base, "/robots.txt"))
    if status != 200:
        fail("robots.txt 없음")
    elif f"{build.BASE_URL}/sitemap.xml" not in robots:
        fail("robots.txt 에 sitemap 없음")


def check_browser(base: str) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        notes.append("Playwright 미설치 — 브라우저 검증 생략")
        return
    SHOTS.mkdir(exist_ok=True)
    viewports = [("pc", 1440, 900), ("mobile", 390, 844)]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, w, h in viewports:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, reduced_motion="reduce")
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda ex: errors.append(str(ex)))
            for path in PAGES:
                url = local(base, path)
                page.goto(url, wait_until="networkidle")
                slug = path.strip("/").replace("/", "-") or "root"
                shot = SHOTS / f"{slug}-{vp_name}.png"
                page.screenshot(path=str(shot), full_page=(vp_name == "pc"))
                overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth - window.innerWidth"
                )
                if overflow > 2:
                    fail(f"{path} [{vp_name}] 가로 넘침 {overflow}px")
                if vp_name == "mobile":
                    bar = page.evaluate(
                        "() => { const b=document.querySelector('.bookbar');"
                        " if(!b) return null; const s=getComputedStyle(b);"
                        " return {display:s.display, position:s.position, bottom:b.getBoundingClientRect().bottom}; }"
                    )
                    if not bar or bar["display"] == "none" or bar["position"] != "fixed":
                        fail(f"{path} [mobile] 하단 고정 예약 바 없음: {bar}")
                if not page.title():
                    fail(f"{path} [{vp_name}] title 비어 있음")
                if errors:
                    fail(f"{path} [{vp_name}] 콘솔 오류: {errors[:2]}")
                    errors.clear()
            ctx.close()
        browser.close()




# ----------------------------------------------------------------------------
# 최종 검수 10항목
# ----------------------------------------------------------------------------
CHECK_ITEMS: list[str] = []


def _img_diff(a: Path, b: Path) -> float:
    from PIL import Image, ImageChops, ImageStat
    i1 = Image.open(a).convert("RGB").resize((160, 160))
    i2 = Image.open(b).convert("RGB").resize((160, 160))
    stat = ImageStat.Stat(ImageChops.difference(i1, i2))
    return sum(stat.mean) / 3


def check_ten_items(base: str) -> None:
    """에어비앤비 대표 사진·동일 카드 크기·예약 버튼 연결을 실제 렌더링으로 검사."""
    from playwright.sync_api import sync_playwright

    src = {
        "heyum": ROOT.parent / "downloads" / "neungnol_stay" / "airbnb_hewyum" / "01_living.jpg",
        "orot": ROOT.parent / "downloads" / "neungnol_stay" / "airbnb_orot" / "01_living.jpg",
    }
    # 1·2) 파일이 에어비앤비 사진과 같은 이미지인지(픽셀 비교)
    for rid, source in src.items():
        local = DOCS / "assets" / f"airbnb-{rid}.webp"
        if not local.exists():
            fail(f"[1/2] {local.name} 없음")
            continue
        if source.exists():
            diff = _img_diff(local, source)
            if diff > 10:
                fail(f"[1/2] {rid} 대표 사진이 에어비앤비 원본과 다름 (평균차 {diff:.1f})")
            else:
                CHECK_ITEMS.append(f"{rid} 대표 사진 = 에어비앤비 01_living.jpg (평균차 {diff:.2f}/255)")
        else:
            notes.append(f"{rid} 에어비앤비 원본 파일을 찾지 못해 픽셀 비교 생략: {source}")

    SHOTS.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, w, h, mobile in (("pc", 1440, 900, False), ("mobile", 390, 844, True)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce",
                                      is_mobile=mobile, has_touch=mobile)
            page = ctx.new_page()
            page.goto(base + "/ko/", wait_until="networkidle")
            for y in range(0, 6000, 800):
                page.evaluate(f"window.scrollTo(0,{y})")
                page.wait_for_timeout(60)
            page.locator("#stays").scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / f"check-stays-{vp_name}.png"))

            boxes = page.evaluate("""() => [...document.querySelectorAll('.stay')].map(el => {
                const r = el.getBoundingClientRect();
                const img = el.querySelector('.stay__ph img');
                const ir = img.getBoundingClientRect();
                const btn = el.querySelector('[data-airbnb]');
                const br = btn.getBoundingClientRect();
                return {room: btn.dataset.airbnb, x: Math.round(r.x), y: Math.round(r.y),
                        w: Math.round(r.width), h: Math.round(r.height),
                        img: img.currentSrc.split('/').pop(), imgBottom: Math.round(ir.bottom),
                        btnTop: Math.round(br.top), btnH: Math.round(br.height),
                        href: btn.href, visible: br.width > 0 && br.height > 0,
                        inCard: el.contains(btn)};
            })""")
            if len(boxes) != 2:
                fail(f"[3] {vp_name} 객실 카드 {len(boxes)}개 (2개 필요)")
            else:
                a, b = boxes
                if abs(a["w"] - b["w"]) > 1 or abs(a["h"] - b["h"]) > 1:
                    fail(f"[3] {vp_name} 카드 크기 다름 {a['w']}x{a['h']} vs {b['w']}x{b['h']}")
                else:
                    CHECK_ITEMS.append(f"{vp_name}: 두 카드 동일 크기 {a['w']}x{a['h']}px")
            for item in boxes:
                rid = item["room"]
                if item["img"] != f"airbnb-{rid}.webp":
                    fail(f"[1/2] {vp_name} {rid} 카드 사진 {item['img']} (에어비앤비 대표 사진 아님)")
                if not item["inCard"] or not item["visible"] or item["btnH"] < 44:
                    fail(f"[4] {vp_name} {rid} 예약 버튼이 카드 안에서 보이지 않음 {item}")
                elif item["btnTop"] < item["imgBottom"] - 1:
                    fail(f"[4] {vp_name} {rid} 버튼이 사진보다 위에 있음")
                else:
                    CHECK_ITEMS.append(f"{vp_name} {rid}: 사진 아래 예약 버튼 {item['btnH']}px")
                if item["href"] != AIRBNB[rid]:
                    fail(f"[5/6] {vp_name} {rid} 버튼 링크 {item['href']}")
                else:
                    CHECK_ITEMS.append(f"{vp_name} {rid}: {AIRBNB[rid]} 연결")
            # 상세 페이지 대표 사진도 동일한지
            for rid in ("heyum", "orot"):
                page.goto(base + f"/ko/{rid}/", wait_until="networkidle")
                hero = page.evaluate("() => document.querySelector('.room-hero img').currentSrc.split('/').pop()")
                if hero != f"airbnb-{rid}.webp":
                    fail(f"[1/2] {rid} 상세 상단 사진 {hero}")
                else:
                    CHECK_ITEMS.append(f"{rid} 상세 상단 사진 = 에어비앤비 대표 사진")
            ctx.close()
        browser.close()


def main() -> None:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(DOCS), **kw)

        def log_message(self, *a):  # 조용히
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    print(f"serving {DOCS} at {base}")

    try:
        for path in PAGES:
            check_seo(base, path)
        check_sitemap_robots(base)
        check_browser(base)
        check_ten_items(base)
    finally:
        srv.shutdown()

    print(f"\n검사 페이지: {len(PAGES)}개")
    if CHECK_ITEMS:
        print("검수 항목 확인:")
        for c in CHECK_ITEMS:
            print("  ✓", c)
    if notes:
        print("참고:")
        for n in notes:
            print("  ·", n)
    if problems:
        print(f"\n문제 {len(problems)}건:")
        for p in problems:
            print("  ✗", p)
        sys.exit(1)
    print("\n✅ 모든 검사 통과")


if __name__ == "__main__":
    main()
