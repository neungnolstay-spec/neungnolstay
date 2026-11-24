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
from datetime import datetime, timedelta, timezone
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
EXPECTED_HREFLANG = {"ko", "en", "ja", "zh-Hans", "zh-Hant", "x-default"}
# 외부 플랫폼(에어비앤비·네이버) 링크·문구는 전용 홈페이지에서 전부 제거한다.
BANNED_PLATFORM = ("airbnb.co.kr", "airbnb.com", "place.naver.com", "talk.naver.com",
                   "booking.naver.com", "naver.me")

problems: list[str] = []

def _console_err(errors, m):
    """콘솔 오류 수집 — Firebase SDK 가 내는 unload 정책 경고는 페이지 오류가 아니므로 제외."""
    if getattr(m, "type", "") != "error":
        return
    text = getattr(m, "text", "") or ""
    if "Permissions policy violation" in text:
        return
    errors.append(text)


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

    # 외부 플랫폼 링크·문구 0건 + 홈페이지 자체 예약/문의 연결
    for needle in BANNED_PLATFORM:
        if needle in body:
            fail(f"{path} 외부 플랫폼 링크 남음: {needle}")
    for word in ("에어비앤비", "Airbnb", "네이버 톡톡", "네이버 플레이스", "Naver Place", "Naver TalkTalk"):
        if word in body:
            fail(f"{path} 외부 플랫폼 문구 남음: {word}")
    if path != "/":
        if 'href="#reserve"' not in body:
            fail(f"{path} 홈페이지 예약창(#reserve) 링크 없음")
        if 'id="reserve"' not in body:
            fail(f"{path} 예약 섹션(#reserve) 없음")
        if 'id="inquiry"' not in body:
            fail(f"{path} 문의 게시판(#inquiry) 없음")
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
            page.on("console", lambda m: _console_err(errors, m))
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




def check_geo(base: str) -> None:
    """AI 검색(GEO) 자산: robots.txt 크롤러 허용, llms.txt / llms-full.txt, FAQPage·구조화 속성."""
    status, robots = fetch(local(base, "/robots.txt"))
    if status != 200:
        fail("robots.txt HTTP %s" % status)
    else:
        for agent in (
            "GPTBot", "OAI-SearchBot", "ChatGPT-User", "Google-Extended", "PerplexityBot",
            "ClaudeBot", "anthropic-ai", "Applebot-Extended", "Bingbot",
        ):
            if f"User-agent: {agent}\nAllow: /" not in robots:
                fail(f"robots.txt 에 {agent} Allow 없음")
        if "User-agent: *\nAllow: /" not in robots:
            fail("robots.txt 기본 Allow 없음")
        if f"{build.BASE_URL}/sitemap.xml" not in robots:
            fail("robots.txt 에 sitemap 없음")

    # llms.txt / llms-full.txt
    short = ""
    for name, min_len in (("llms.txt", 3000), ("llms-full.txt", 20000)):
        status, body = fetch(local(base, "/" + name))
        if status != 200:
            fail(f"{name} HTTP {status}")
            continue
        if len(body) < min_len:
            fail(f"{name} 내용 부족 ({len(body)}자, 기대 {min_len}+)")
        if not body.startswith("# "):
            fail(f"{name} 가 Markdown H1 로 시작하지 않음")
        for needle in ("NEUNGNOL STAY", "능놀스테이", build.ADDRESS_ROAD, f"{build.BASE_URL}/ko/heyum/#reserve"):
            if needle not in body:
                fail(f"{name} 에 '{needle}' 없음")
        for t in build.LANGS:
            if not (build.BASE_URL + f"/{t['dir']}/") in body:
                fail(f"{name} 에 {t['dir']} 페이지 URL 없음")
        if name == "llms.txt":
            short = body
        else:
            CHECK_ITEMS.append(f"{name} {len(body)//1024}KB · 5개 언어·예약 링크 포함")
    if short and build.LANGS[0]["brand_name"] not in short:
        fail("llms.txt 에 한글 브랜드명 없음")

    # 홈 FAQPage + 구조화 속성
    for t in build.LANGS:
        path = f"/{t['dir']}/"
        status, body = fetch(local(base, path))
        if status != 200:
            continue
        p = Page()
        p.feed(body)
        blocks = []
        for raw in p.jsonld:
            try:
                blocks.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
        faq = next((b for b in blocks if b.get("@type") == "FAQPage"), None)
        if not faq:
            fail(f"{path} FAQPage 없음")
        elif len(faq.get("mainEntity", [])) != len(build.home_faq(t)):
            fail(f"{path} FAQPage 문항 {len(faq.get('mainEntity', []))}개 != 화면 {len(build.home_faq(t))}개")
        else:
            CHECK_ITEMS.append(f"{path} FAQPage {len(faq['mainEntity'])}문항")
        lod = next((b for b in blocks if b.get("@type") == "LodgingBusiness"), None)
        if not lod:
            fail(f"{path} LodgingBusiness 없음")
            continue
        lang = set(lod.get("knowsLanguage", []))
        if not {"ko", "en", "ja"} <= lang:
            fail(f"{path} knowsLanguage 부족: {sorted(lang)}")
        same = set(lod.get("sameAs", []))
        for need in (build.INSTAGRAM, build.GOOGLE_MAP_LINK):
            if need not in same:
                fail(f"{path} LodgingBusiness sameAs 에 {need} 없음")
        if str(lod.get("tourBookingPage", "")).find("#reserve") < 0:
            fail(f"{path} LodgingBusiness tourBookingPage 가 홈페이지 예약창이 아님")
        amen = " ".join(a.get("name", "") for a in lod.get("amenityFeature", []))
        for need in ("Ocean view", "jacuzzi", "Kids' room", "projector", "parking"):
            if need.lower() not in amen.lower():
                fail(f"{path} amenityFeature 에 {need} 없음")
        if lod.get("geo", {}).get("latitude") != build.LAT:
            fail(f"{path} LodgingBusiness geo 불일치")

    # 객실별 세탁·건조기 구분 (헤윰: 세탁기만 / 오롯: 세탁기+건조기)
    for t in build.LANGS:
        for room in build.ROOMS:
            path = f"/{t['dir']}/{room}/"
            status, body = fetch(local(base, path))
            if status != 200:
                continue
            p = Page()
            p.feed(body)
            room_ld = None
            for raw in p.jsonld:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                for block in (data if isinstance(data, list) else [data]):
                    if block.get("@type") == "HotelRoom":
                        room_ld = block
            if not room_ld:
                fail(f"{path} HotelRoom 없음 (세탁·건조기 확인 불가)")
                continue
            names = " ".join(a.get("name", "") for a in room_ld.get("amenityFeature", [])).lower()
            if "washing machine" not in names:
                fail(f"{path} HotelRoom amenityFeature 에 세탁기 없음")
            if room == "orot":
                if "dryer" not in names:
                    fail(f"{path} HotelRoom amenityFeature 에 건조기 없음")
            elif "dryer" in names:
                fail(f"{path} 건조기 없는 헤윰에 dryer 표기됨")
        CHECK_ITEMS.append(f"/{t['dir']}/ 객실별 세탁기·건조기 구분 OK")

    # llms.txt / llms-full.txt 의 세탁·건조기 구분
    _, short_txt = fetch(local(base, "/llms.txt"))
    _, full_txt = fetch(local(base, "/llms-full.txt"))
    if "건조기" not in short_txt:
        fail("llms.txt 에 건조기 정보 없음")
    for needle in ("헤윰에는 건조기 없음", "건조기는 오롯(6층)에만"):
        if needle not in short_txt:
            fail(f"llms.txt 에 '{needle}' 없음")
    dryer_terms = {"ko": "건조기", "en": "Clothes dryer", "ja": "衣類乾燥機", "zh-cn": "烘干机", "zh-tw": "烘乾機"}
    for t in build.LANGS:
        term = dryer_terms[t["dir"]]
        if term not in full_txt:
            fail(f"llms-full.txt 에 {t['dir']} 건조기 표기('{term}') 없음")
    if full_txt.count("건조기 없음") < 1 or full_txt.count("Clothes dryer") < 1:
        fail("llms-full.txt 에 건조기 유무 구분 문구 없음")

    # 금지 표기·삭제된 항목이 AI 문서에 다시 들어가지 않았는지
    files = ["llms.txt", "llms-full.txt", "robots.txt", "sitemap.xml"]
    bodies = {name: fetch(local(base, "/" + name))[1] for name in files}
    for t in build.LANGS:
        for path in (f"/{t['dir']}/", f"/{t['dir']}/heyum/", f"/{t['dir']}/orot/"):
            bodies[path] = fetch(local(base, path))[1]
    banned = ["nungnol", "NUNG NOL", "누놀", "연박", "2박", "소음", "건물주차"]
    for where, body in bodies.items():
        for word in banned:
            if word in body:
                fail(f"{where} 금지 표기·삭제 항목 포함: {word}")


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
    """대표 사진·동일 카드 크기·홈페이지 자체 예약 CTA(카드 → #reserve 객실 선택)를 렌더링으로 검사."""
    from playwright.sync_api import sync_playwright

    src = {
        "heyum": ROOT.parent / "downloads" / "neungnol_stay" / "airbnb_hewyum" / "01_living.jpg",
        "orot": ROOT.parent / "downloads" / "neungnol_stay" / "airbnb_orot" / "01_living.jpg",
    }
    # 1·2) 카드 대표 사진이 실제 객실 원본 사진과 같은지(픽셀 비교)
    for rid, source in src.items():
        local = DOCS / "assets" / f"hero-{rid}.webp"
        if not local.exists():
            fail(f"[1/2] {local.name} 없음")
            continue
        if source.exists():
            diff = _img_diff(local, source)
            if diff > 10:
                fail(f"[1/2] {rid} 대표 사진이 원본과 다름 (평균차 {diff:.1f})")
            else:
                CHECK_ITEMS.append(f"{rid} 대표 사진 = 실제 객실 원본 (평균차 {diff:.2f}/255)")
        else:
            notes.append(f"{rid} 원본 파일을 찾지 못해 픽셀 비교 생략: {source}")

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
                const btn = el.querySelector('[data-book-room]');
                const br = btn.getBoundingClientRect();
                return {room: btn.dataset.bookRoom, x: Math.round(r.x), y: Math.round(r.y),
                        w: Math.round(r.width), h: Math.round(r.height),
                        img: img.currentSrc.split('/').pop(), imgBottom: Math.round(ir.bottom),
                        btnTop: Math.round(br.top), btnH: Math.round(br.height),
                        href: btn.getAttribute('href'), visible: br.width > 0 && br.height > 0,
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
                if item["img"] != f"hero-{rid}.webp":
                    fail(f"[1/2] {vp_name} {rid} 카드 사진 {item['img']} (대표 사진 아님)")
                if not item["inCard"] or not item["visible"] or item["btnH"] < 44:
                    fail(f"[4] {vp_name} {rid} 예약 버튼이 카드 안에서 보이지 않음 {item}")
                elif item["btnTop"] < item["imgBottom"] - 1:
                    fail(f"[4] {vp_name} {rid} 버튼이 사진보다 위에 있음")
                else:
                    CHECK_ITEMS.append(f"{vp_name} {rid}: 사진 아래 예약 버튼 {item['btnH']}px")
                if item["href"] != "#reserve":
                    fail(f"[5/6] {vp_name} {rid} 예약 버튼이 홈페이지 예약창이 아님: {item['href']}")
                else:
                    CHECK_ITEMS.append(f"{vp_name} {rid}: 카드 버튼 → #reserve")

            # 카드 예약 버튼 클릭 → 예약창으로 이동하며 그 객실이 선택된다
            page.goto(base + "/ko/", wait_until="networkidle")
            page.locator("#stays").scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.click('.stay [data-book-room="orot"]')
            page.wait_for_timeout(900)
            selected = page.evaluate("() => document.querySelector('[data-booking]').dataset.room")
            reserve_top = page.evaluate("() => Math.round(document.getElementById('reserve').getBoundingClientRect().top)")
            if selected != "orot":
                fail(f"[5/6] {vp_name} 카드 버튼 클릭 후 선택 객실 {selected}")
            elif abs(reserve_top) > 220:
                fail(f"[5/6] {vp_name} 카드 버튼 클릭 후 예약창 위치 {reserve_top}px")
            else:
                CHECK_ITEMS.append(f"{vp_name}: '오롯 예약하기' → 예약창 오롯 선택 + 스크롤")

            # 하단 고정 바(모바일 전용)도 같은 방식으로 동작
            if vp_name == "mobile":
                page.click('.bookbar [data-book-room="heyum"]')
                page.wait_for_timeout(700)
                selected = page.evaluate("() => document.querySelector('[data-booking]').dataset.room")
                if selected != "heyum":
                    fail(f"[5/6] {vp_name} 하단 바 클릭 후 선택 객실 {selected}")
                else:
                    CHECK_ITEMS.append(f"{vp_name}: 하단 예약 바 → 헤윰 선택")

            # 상세 페이지 대표 사진도 동일한지
            for rid in ("heyum", "orot"):
                page.goto(base + f"/ko/{rid}/", wait_until="networkidle")
                hero = page.evaluate("() => document.querySelector('.room-hero img').currentSrc.split('/').pop()")
                if hero != f"hero-{rid}.webp":
                    fail(f"[1/2] {rid} 상세 상단 사진 {hero}")
                else:
                    CHECK_ITEMS.append(f"{rid} 상세 상단 사진 = 대표 사진")
            ctx.close()
        browser.close()


def check_room_nav_reviews(base: str) -> None:
    """객실 페이지의 뒤로가기·다른 객실 버튼과 에어비앤비 리뷰 섹션(날짜 미표시) 확인."""
    date_patterns = [
        r"20\d\d",                                   # 2023·2024·2026 …
        r"January|February|March|April|May|June|July|August|September|October|November|December",
        r"\d+\s*(일|주|개월|달|시간|분)\s*전",           # 3주 전, 2개월 전 …
        r"\d+\s*(日|週間|か月|ヶ月|年)\s*前",           # 3日前 …
        r"\d+\s*(天|週|周|个月|個月|年)\s*前",           # 3天前 …
    ]
    blocked_char = {"ko": r"[년월]", "ja": r"[年月]", "zh-Hans": r"[年月]", "zh-Hant": r"[年月]"}
    for t in build.LANGS:
        d = t["dir"]
        for room in build.ROOMS:
            other = "orot" if room == "heyum" else "heyum"
            path = f"/{d}/{room}/"
            status, body = fetch(local(base, path))
            if status != 200:
                continue
            # 1) 뒤로가기 · 다른 객실 보기 버튼 (상단 바 + 예약 CTA)
            backs = re.findall(r'href="\.\./index\.html#stays"[^>]*data-rooms-back', body)
            if len(backs) < 2:
                fail(f"{path} 전체 객실로 돌아가는 버튼 {len(backs)}개 (상단·하단 2개 필요)")
            if body.count(f'href="../{other}/"') < 1:
                fail(f"{path} 다른 객실({other}) 링크 없음")
            if 'data-room-switch=' not in body:
                fail(f"{path} 다른 객실 전환 버튼 표시 없음")
            top = body.find('class="room-nav"')
            hero = body.find('class="room-hero"')
            if top < 0 or hero < 0 or top > hero:
                fail(f"{path} 상단 객실 이동 바가 히어로 위에 없음")
            if 'class="cta-nav"' not in body:
                fail(f"{path} 예약 CTA 안의 객실 이동 버튼 없음")

            # 2) 리뷰 섹션 — Firebase 실시간 목록 + 후기 작성 폼, 정적 후기 6건은 fallback
            start = body.find('id="reviews"')
            if start < 0:
                fail(f"{path} 리뷰 섹션 없음")
                continue
            end = body.find("</section>", start)
            block = body[start:end]
            for need in ('data-reviews', 'data-rv-form', 'data-rv-open', 'data-rv-fallback',
                         'name="name"', 'name="text"', 'data-rv-star="5"'):
                if need not in block:
                    fail(f"{path} 리뷰 섹션 구성 누락: {need}")
            m = re.search(r'<script type="application/json" data-rv-fallback>(.*?)</script>', block, re.S)
            if not m:
                fail(f"{path} 리뷰 fallback 데이터 없음")
            else:
                try:
                    fallback = json.loads(m.group(1))
                    if len(fallback) != 6:
                        fail(f"{path} fallback 리뷰 {len(fallback)}개 (6개 필요)")
                    if not all(r.get("name") and r.get("text") and r.get("rating") for r in fallback):
                        fail(f"{path} fallback 리뷰에 이름/본문/별점 누락")
                except json.JSONDecodeError as ex:
                    fail(f"{path} fallback 리뷰 JSON 오류: {ex}")
            if 'data-airbnb' in block:
                fail(f"{path} 리뷰 섹션에 외부 플랫폼 링크 남음")
            text = re.sub(r"<[^>]+>", " ", block)
            for pat in date_patterns:
                hit = re.search(pat, text)
                if hit:
                    fail(f"{path} 리뷰 영역에 날짜 표기 의심: {hit.group(0)!r}")
            if t["html_lang"] in blocked_char:
                hit = re.search(blocked_char[t["html_lang"]], text)
                if hit:
                    fail(f"{path} 리뷰 영역에 날짜 단위 글자: {hit.group(0)!r}")
            CHECK_ITEMS.append(f"{path}: 리뷰 목록·작성 폼 · 뒤로가기/다른 객실 버튼 · 날짜 표기 없음")


def check_room_nav_browser(base: str) -> None:
    """실제 렌더링에서 상단 이동 바 위치와 다른 객실 전환 클릭을 확인."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        notes.append("Playwright 미설치 — 객실 이동 바 브라우저 검증 생략")
        return
    SHOTS.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, w, h in (("pc", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
            page = ctx.new_page()
            page.goto(base + "/ko/heyum/", wait_until="networkidle")
            metrics = page.evaluate("""() => {
                const bar = document.querySelector('.room-nav');
                const hero = document.querySelector('.room-hero');
                const sw = document.querySelector('.room-nav__link[data-room-switch]');
                const back = document.querySelector('.room-nav__link[data-rooms-back]');
                const r = sw.getBoundingClientRect();
                return {barTop: Math.round(bar.getBoundingClientRect().top),
                        heroTop: Math.round(hero.getBoundingClientRect().top),
                        swH: Math.round(r.height), swW: Math.round(r.width),
                        switchHref: sw.getAttribute('href'), backHref: back.getAttribute('href'),
                        overflow: document.documentElement.scrollWidth - window.innerWidth};
            }""")
            if metrics["heroTop"] <= metrics["barTop"]:
                fail(f"[room-nav {vp_name}] 이동 바가 히어로 위에 있지 않음 {metrics}")
            if metrics["swH"] < 34 or metrics["swW"] < 80:
                fail(f"[room-nav {vp_name}] 다른 객실 버튼이 너무 작음 {metrics}")
            if metrics["overflow"] > 2:
                fail(f"[room-nav {vp_name}] 가로 넘침 {metrics['overflow']}px")
            page.screenshot(path=str(SHOTS / f"room-nav-{vp_name}.png"))
            CHECK_ITEMS.append(f"{vp_name}: 상단 객실 이동 바 (다른 객실 버튼 {metrics['swW']}x{metrics['swH']}px)")

            # 다른 객실 버튼 클릭 → 오롯 페이지로 실제 이동
            page.click(".room-nav__link[data-room-switch]")
            page.wait_for_load_state("networkidle")
            if not page.url.endswith("/ko/orot/"):
                fail(f"[room-nav {vp_name}] 다른 객실 버튼 클릭 후 URL {page.url}")
            else:
                CHECK_ITEMS.append(f"{vp_name}: '다른 객실 보기' 클릭 → /ko/orot/ 이동")

            # 리뷰 섹션 렌더링 · 카드 배치
            page.goto(base + "/ko/heyum/", wait_until="networkidle")
            page.locator("#reviews").scroll_into_view_if_needed()
            page.wait_for_timeout(2600)
            page.locator("#reviews").screenshot(path=str(SHOTS / f"reviews-heyum-{vp_name}.png"))
            cards = page.evaluate("""() => [...document.querySelectorAll('#reviews .review')].map(el => {
                const r = el.getBoundingClientRect();
                return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x)};
            })""")
            if len(cards) < 6:
                fail(f"[reviews {vp_name}] 카드 {len(cards)}개 (Firebase 후기 6개 이상 필요)")
            else:
                rows = {c["x"] for c in cards}
                CHECK_ITEMS.append(f"{vp_name}: 리뷰 카드 {len(cards)}개 ({len(rows)}열, {cards[0]['w']}px 폭)")
            ctx.close()
        browser.close()


def check_gallery(base: str) -> None:
    """갤러리: 사진 파일·alt·라이트박스 데이터·필터 (정적)."""
    for t in build.LANGS:
        d = t["dir"]
        for room in build.ROOMS:
            path = f"/{d}/{room}/"
            status, body = fetch(local(base, path))
            if status != 200:
                continue
            manifest = build.GALLERY_MANIFEST[room]
            m = re.search(r'<script type="application/json" data-gal-data>(.*?)</script>', body, re.S)
            if not m:
                fail(f"{path} 갤러리 데이터 스크립트 없음")
                continue
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError as ex:
                fail(f"{path} 갤러리 데이터 파싱 실패: {ex}")
                continue
            if len(data) != len(manifest):
                fail(f"{path} 갤러리 사진 {len(data)}장 (기대 {len(manifest)})")
            if "gallery-lightbox" not in body:
                fail(f"{path} 라이트박스 마크업 없음")
            opens = len(re.findall(r'data-gal-open="', body))
            if opens < len(manifest):
                fail(f"{path} 갤러리 열기 버튼 {opens}개 (사진 {len(manifest)}장)")
            for it in manifest:
                for suffix in ("", "-t"):
                    st, _ = fetch(local(base, f"/assets/gallery/{room}/{it['slug']}{suffix}.webp"))
                    if st != 200:
                        fail(f"갤러리 이미지 HTTP {st}: {room}/{it['slug']}{suffix}.webp")
            if path.startswith("/ko/"):
                CHECK_ITEMS.append(f"{path}: 갤러리 {len(manifest)}장 + 라이트박스")


def check_gallery_browser(base: str) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        notes.append("Playwright 미설치 — 갤러리 브라우저 검증 생략")
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, w, h in (("pc", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m: _console_err(errors, m))
            page.on("pageerror", lambda ex: errors.append(str(ex)))
            page.goto(base + "/ko/heyum/", wait_until="networkidle")
            page.locator("#gallery").scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            cells = page.evaluate("() => document.querySelectorAll('.gal-cell').length")
            if cells < 30:
                fail(f"[gallery {vp_name}] 그리드 사진 {cells}장")

            page.click('[data-gal-filter="jacuzzi"]')
            page.wait_for_timeout(250)
            shown = page.evaluate("() => [...document.querySelectorAll('.gal-cell')].filter(li => !li.hidden).length")
            cats = page.evaluate("() => new Set([...document.querySelectorAll('.gal-cell')].filter(li => !li.hidden).map(li => li.dataset.cat)).size")
            if shown == 0 or cats != 1:
                fail(f"[gallery {vp_name}] 자쿠지 필터 결과 {shown}장 / 분류 {cats}종")
            page.click('[data-gal-filter="all"]')
            page.wait_for_timeout(200)

            page.locator(".gal-cell__btn").first.click()
            page.wait_for_timeout(700)
            visible = page.evaluate("() => !document.getElementById('gallery-lightbox').hidden")
            loaded = page.evaluate("() => document.querySelector('[data-gal-img]').naturalWidth")
            if not visible or not loaded:
                fail(f"[gallery {vp_name}] 라이트박스 열림 {visible} / 이미지 폭 {loaded}")
            page.screenshot(path=str(SHOTS / f"gallery-lightbox-{vp_name}.png"))
            before = page.evaluate("() => document.querySelector('[data-gal-count]').textContent")
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(500)
            after = page.evaluate("() => document.querySelector('[data-gal-count]').textContent")
            if before == after:
                fail(f"[gallery {vp_name}] 라이트박스 다음 사진 이동 실패 ({before})")
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            if page.evaluate("() => !document.getElementById('gallery-lightbox').hidden"):
                fail(f"[gallery {vp_name}] ESC 로 라이트박스가 닫히지 않음")
            if errors:
                fail(f"[gallery {vp_name}] 콘솔 오류: {errors[:2]}")
            ctx.close()
        browser.close()


def check_booking_browser(base: str) -> None:
    """직접 예약 위젯: 달력 렌더·가격 표시·날짜 선택·객실 전환."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        notes.append("Playwright 미설치 — 예약 위젯 검증 생략")
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, w, h in (("pc", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m: _console_err(errors, m))
            page.on("pageerror", lambda ex: errors.append(str(ex)))
            page.goto(base + "/ko/heyum/", wait_until="networkidle")
            page.locator("#reserve").scroll_into_view_if_needed()
            page.wait_for_timeout(3500)
            days = page.evaluate("() => document.querySelectorAll('#reserve .bk-day').length")
            if days < 40:
                fail(f"[booking {vp_name}] 달력 날짜 {days}개 (2개월 미만)")
            prices = page.evaluate("""() => [...document.querySelectorAll('#reserve .bk-day em')]
                .map(e => e.textContent).filter(Boolean)""")
            if len(prices) < 20 or not re.search(r"[0-9]", " ".join(prices)):
                fail(f"[booking {vp_name}] 1박 요금 표시 없음 ({prices[:3]})")

            available = page.evaluate("""() => [...document.querySelectorAll('#reserve .bk-day:not(:disabled)[data-date]')]
                .map(b => b.dataset.date)""")
            if len(available) < 5:
                fail(f"[booking {vp_name}] 예약 가능 날짜 {len(available)}개")
            else:
                # 연속으로 열린 날짜 2박을 골라야 총액이 계산된다
                from datetime import date as _d
                pair = None
                for i in range(len(available) - 1):
                    d0 = _d.fromisoformat(available[i])
                    d1 = _d.fromisoformat(available[i + 1])
                    if (d1 - d0).days == 1:
                        pair = (available[i], available[i + 1])
                        break
                if not pair:
                    fail(f"[booking {vp_name}] 연속 예약 가능 날짜 없음")
                    ctx.close()
                    continue
                page.click(f'#reserve .bk-day[data-date="{pair[0]}"]')
                page.wait_for_timeout(250)
                page.click(f'#reserve .bk-day[data-date="{pair[1]}"]')
                page.wait_for_timeout(500)
                total = page.evaluate("() => document.querySelector('[data-bk-total]').textContent")
                if "₩" not in total:
                    fail(f"[booking {vp_name}] 날짜 선택 후 총액 {total!r}")
                detail = page.evaluate("() => document.querySelector('[data-bk-detail]').textContent")
                if "1박" not in detail and "night" not in detail:
                    fail(f"[booking {vp_name}] 요금 상세 {detail!r}")
                page.screenshot(path=str(SHOTS / f"booking-selected-{vp_name}.png"))

            page.goto(base + "/ko/", wait_until="networkidle")
            page.locator("#reserve").scroll_into_view_if_needed()
            page.wait_for_timeout(1200)
            page.click('[data-bk-room="orot"]')
            page.wait_for_timeout(600)
            room_flag = page.evaluate("() => document.querySelector('[data-booking]').dataset.room")
            if room_flag != "orot":
                fail(f"[booking {vp_name}] 객실 전환 반영 안 됨 ({room_flag})")
            else:
                CHECK_ITEMS.append(f"{vp_name}: 예약창 객실 전환 → 오롯")

            # 무료 비품·유아용품 요청 체크박스 7종
            boxes = page.evaluate("""() => [...document.querySelectorAll('[data-bk-form] input[name="amenity"]')]
                .map(i => i.value)""")
            need = ["kidsroom", "highchair", "sterilizer", "babyshampoo", "pillow", "babydish", "bedguard"]
            if boxes != need:
                fail(f"[booking {vp_name}] 비품 요청 체크박스 {boxes}")
            else:
                CHECK_ITEMS.append(f"{vp_name}: 무료 비품 요청 7종 체크박스")
            if errors:
                fail(f"[booking {vp_name}] 콘솔 오류: {errors[:2]}")
            ctx.close()
        browser.close()


def check_admin(base: str) -> None:
    """사장님 관리 화면: noindex·PIN 잠금·탭·달력·오버플로."""
    status, body = fetch(local(base, "/admin/"))
    if status != 200:
        fail(f"/admin/ → HTTP {status}")
        return
    if "noindex" not in body:
        fail("/admin/ noindex 메타 없음")
    for need in ("data-tab=\"cal\"", "data-tab=\"bookings\"", "data-tab=\"reviews\"", "data-tab=\"inquiries\"", "data-tab=\"rates\"", "data-tab=\"settings\"", "id=\"keypad\""):
        if need not in body:
            fail(f"/admin/ 구성 요소 누락: {need}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        notes.append("Playwright 미설치 — 관리 화면 브라우저 검증 생략")
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, w, h, mobile in (("pc", 1440, 900, False), ("mobile", 390, 844, True)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile,
                                      reduced_motion="reduce")
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m: _console_err(errors, m))
            page.on("pageerror", lambda ex: errors.append(str(ex)))
            page.goto(base + "/admin/", wait_until="networkidle")
            page.wait_for_timeout(2500)
            if page.evaluate("() => document.getElementById('lock').hidden"):
                fail(f"[admin {vp_name}] 잠금 화면이 처음부터 열려 있음")
            page.screenshot(path=str(SHOTS / f"admin-lock-{vp_name}.png"))
            for ch in "0000":
                page.click(f'#keypad [data-key="{ch}"]')
                page.wait_for_timeout(90)
            page.wait_for_timeout(2500)
            if page.evaluate("() => document.getElementById('app').hidden"):
                fail(f"[admin {vp_name}] PIN 0000 으로 열리지 않음")
                ctx.close()
                continue
            days = page.evaluate("() => document.querySelectorAll('#calGrid .day[data-date]').length")
            if days < 27:
                fail(f"[admin {vp_name}] 달력 날짜 {days}개")
            overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            if overflow > 2:
                fail(f"[admin {vp_name}] 가로 넘침 {overflow}px")
            page.screenshot(path=str(SHOTS / f"admin-calendar-{vp_name}.png"))
            for tab in ("bookings", "reviews", "inquiries", "rates", "settings", "cal"):
                page.click(f'[data-tab="{tab}"]')
                page.wait_for_timeout(350)
                if not page.evaluate(f"() => document.querySelector('[data-panel=\"{tab}\"]').classList.contains('is-on')"):
                    fail(f"[admin {vp_name}] 탭 {tab} 표시 안 됨")
            page.screenshot(path=str(SHOTS / f"admin-tabs-{vp_name}.png"))
            if errors:
                fail(f"[admin {vp_name}] 콘솔 오류: {errors[:2]}")
            ctx.close()
        browser.close()
    CHECK_ITEMS.append("/admin/: PIN 잠금 · 달력 · 예약/리뷰/문의/요금/설정 탭")



# ---------------------------------------------------------------------------
# Firebase 직접 검증 (REST) — 설정·소스 색상·커뮤니티·예약 승인
# ---------------------------------------------------------------------------
DB = "https://neungnol-checklist-default-rtdb.asia-southeast1.firebasedatabase.app/neungnol_booking_v1"


def db_get(path: str = ""):
    with urllib.request.urlopen(f"{DB}{path}.json", timeout=30) as r:
        return json.load(r)


def db_put(path: str, value) -> None:
    data = json.dumps(value, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{DB}{path}.json", data=data, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def db_delete(path: str) -> None:
    req = urllib.request.Request(f"{DB}{path}.json", method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def admin_login(page, base: str) -> bool:
    page.goto(base + "/admin/", wait_until="networkidle")
    page.wait_for_timeout(2600)
    if not page.evaluate("() => document.getElementById('app').hidden"):
        return True
    for ch in "0000":
        page.click(f'#keypad [data-key="{ch}"]')
        page.wait_for_timeout(90)
    page.wait_for_timeout(2800)
    return not page.evaluate("() => document.getElementById('app').hidden")


def check_ical_blocks() -> None:
    """에어비앤비 iCal 동기화 결과와 출처 색상(파랑) 표시."""
    blocks = db_get("/blocks") or {}
    total = 0
    bad = 0
    for room in build.ROOMS:
        for ds, entry in (blocks.get(room) or {}).items():
            if isinstance(entry, dict) and entry.get("source") == "airbnb":
                total += 1
                if entry.get("reason") != "ical":
                    bad += 1
    if total < 10:
        fail(f"에어비앤비 iCal 차단 날짜 {total}일 (동기화 안 됨)")
        return
    sync = ((db_get("/settings") or {}).get("icalSync") or {})
    if not sync.get("syncedAt"):
        fail("settings/icalSync 동기화 기록 없음")
    if bad:
        fail(f"iCal 차단 {bad}건에 reason=ical 없음")
    CHECK_ITEMS.append(f"에어비앤비 iCal 차단 {total}일 · 동기화 기준일 {sync.get('syncedAtText', '?')}")


def check_source_colors(base: str) -> None:
    """관리자 달력의 출처별 색상: 네이버 초록(#03C75A) · 에어비앤비 파랑(#0077FF)."""
    from playwright.sync_api import sync_playwright

    tomorrow = (datetime.now(timezone(timedelta(hours=9))).date() + timedelta(days=2)).isoformat()
    db_put(f"/blocks/orot/{tomorrow}", {"source": "naver", "reason": "check", "createdAt": 1})
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 950}, reduced_motion="reduce")
            page = ctx.new_page()
            if not admin_login(page, base):
                fail("[colors] 관리자 로그인 실패")
                ctx.close()
                browser.close()
                return
            page.click('[data-room="orot"]')
            page.wait_for_timeout(900)
            data = page.evaluate("""(date) => {
                const cell = document.querySelector(`#calGrid .day[data-date="${date}"]`);
                if (!cell) return null;
                const badge = cell.querySelector('.day__s');
                const cs = badge ? getComputedStyle(badge).backgroundColor : '';
                return {src: cell.dataset.source, bg: cs, cls: cell.className};
            }""", tomorrow)
            if not data or data["src"] != "naver" or "rgb(3, 199, 90)" not in data["bg"]:
                fail(f"[colors] 네이버 차단 색상 {data}")
            else:
                CHECK_ITEMS.append("관리자 달력: 네이버 예약 초록(#03C75A)")
            # 에어비앤비(iCal) 날짜 색
            target = None
            for ds, entry in (db_get("/blocks/heyum") or {}).items():
                if isinstance(entry, dict) and entry.get("source") == "airbnb" and ds >= tomorrow:
                    target = ds
                    break
            if target:
                month = target[:7]
                page.click('#roomSeg [data-room="heyum"]')
                page.wait_for_timeout(500)
                for _ in range(14):
                    label = page.evaluate("() => document.querySelector('#monthLabel').textContent")
                    if month.split("-")[1].lstrip("0") in label:
                        break
                    page.click("#nextMonth")
                    page.wait_for_timeout(140)
                data = page.evaluate("""(date) => {
                    const cell = document.querySelector(`#calGrid .day[data-date="${date}"]`);
                    if (!cell) return null;
                    const badge = cell.querySelector('.day__s');
                    return {src: cell.dataset.source, bg: badge ? getComputedStyle(badge).backgroundColor : ''};
                }""", target)
                if not data or data["src"] != "airbnb" or "rgb(0, 119, 255)" not in data["bg"]:
                    fail(f"[colors] 에어비앤비 색상 {data} ({target})")
                else:
                    CHECK_ITEMS.append("관리자 달력: 에어비앤비 파랑(#0077FF)")
                page.screenshot(path=str(SHOTS / "admin-source-colors.png"))
            ctx.close()
            browser.close()
    finally:
        db_delete(f"/blocks/orot/{tomorrow}")


def check_community(base: str) -> None:
    """리뷰 작성→관리자 삭제, 문의 작성(외국어)→한국어 번역→관리자 답변→고객 화면."""
    from playwright.sync_api import sync_playwright

    created_inquiry = None
    review_text = "체크 자동화 리뷰입니다. 바다 전망이 좋았습니다."
    inquiry_text = "Hello, we are a family of four. Is parking available for a large van next weekend?"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 950}, reduced_motion="reduce")
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda ex: errors.append(str(ex)))
        try:
            # 1) 고객 리뷰 작성
            page.goto(base + "/ko/heyum/#reviews", wait_until="networkidle")
            page.locator("#reviews").scroll_into_view_if_needed()
            page.wait_for_timeout(2600)
            page.click("[data-rv-open]")
            page.fill('[data-rv-form] input[name="name"]', "체크게스트")
            page.click('[data-rv-star="4"]')
            page.fill('[data-rv-form] textarea[name="text"]', review_text)
            page.click("[data-rv-submit]")
            page.wait_for_timeout(2600)
            revs = db_get("/reviews/heyum") or {}
            mine = [k for k, v in revs.items() if isinstance(v, dict) and v.get("text") == review_text]
            if not mine:
                fail("[community] 고객 리뷰가 Firebase 에 저장되지 않음")
            else:
                CHECK_ITEMS.append("고객 리뷰 작성 → Firebase 저장")
                shown = page.evaluate("() => [...document.querySelectorAll('#reviews .review__text')].map(e => e.textContent)")
                if not any(review_text in x for x in shown):
                    fail("[community] 작성한 리뷰가 홈페이지 목록에 바로 보이지 않음")
            # 2) 관리자 리뷰 삭제
            if not admin_login(page, base):
                fail("[community] 관리자 로그인 실패")
            else:
                page.click('[data-tab="reviews"]')
                page.wait_for_timeout(900)
                card = page.locator('.bk--review', has_text=review_text)
                if card.count() == 0:
                    fail("[community] 관리자 리뷰 목록에 방금 쓴 리뷰 없음")
                else:
                    page.on("dialog", lambda d: d.accept())
                    card.first.locator("button", has_text="삭제").click()
                    page.wait_for_timeout(1800)
                    revs = db_get("/reviews/heyum") or {}
                    if any(isinstance(v, dict) and v.get("text") == review_text for v in revs.values()):
                        fail("[community] 관리자 리뷰 삭제가 반영되지 않음")
                    else:
                        CHECK_ITEMS.append("관리자 리뷰 삭제 → Firebase·홈페이지에서 제거")
                page.screenshot(path=str(SHOTS / "admin-reviews.png"))

            # 3) 외국어 문의 작성
            page.goto(base + "/en/heyum/#inquiry", wait_until="networkidle")
            page.locator("#inquiry").scroll_into_view_if_needed()
            page.wait_for_timeout(1200)
            page.fill('[data-inq-form] input[name="name"]', "Check Guest")
            page.fill('[data-inq-form] input[name="contact"]', "check@example.com")
            page.select_option('[data-inq-form] select[name="room"]', "orot")
            page.fill('[data-inq-form] textarea[name="text"]', inquiry_text)
            page.click("[data-inq-submit]")
            page.wait_for_timeout(3200)
            inqs = db_get("/inquiries") or {}
            for k, v in inqs.items():
                if isinstance(v, dict) and v.get("text") == inquiry_text:
                    created_inquiry = k
                    break
            if not created_inquiry:
                fail("[community] 문의가 Firebase 에 저장되지 않음")
            else:
                q = inqs[created_inquiry]
                if q.get("lang", "").startswith("en") and q.get("textKo"):
                    CHECK_ITEMS.append("문의 원문(영어) + 한국어 번역 저장")
                elif q.get("textKo"):
                    notes.append(f"[community] 문의 언어 감지 {q.get('lang')} · 번역 저장됨")
                else:
                    notes.append("[community] 문의 한국어 번역이 비어 있음 (번역 엔드포인트 응답 없음)")
                page.wait_for_timeout(1200)
                shown = page.evaluate("() => document.querySelector('[data-inq-list]') ? document.querySelector('[data-inq-list]').textContent : ''")
                if "Check Guest" not in shown:
                    fail("[community] 문의 게시판 목록에 문의가 표시되지 않음")

            # 4) 관리자 답변 → 고객 화면 번역 표시
            if created_inquiry:
                if not admin_login(page, base):
                    fail("[community] 관리자 로그인 실패(문의)")
                else:
                    page.click('[data-tab="inquiries"]')
                    page.wait_for_timeout(900)
                    card = page.locator('.bk--inq', has_text="Check Guest")
                    if card.count() == 0:
                        fail("[community] 관리자 문의 목록에 문의 없음")
                    else:
                        if "한국어" in card.first.inner_text():
                            CHECK_ITEMS.append("관리자 문의 탭: 원문 + 한국어 번역 표시")
                        card.first.locator("textarea").fill("네, 대형 밴 주차가 가능합니다. 차종을 미리 알려 주세요.")
                        card.first.locator("button", has_text="답변 저장").click()
                        page.wait_for_timeout(1800)
                        q = db_get(f"/inquiries/{created_inquiry}") or {}
                        if not q.get("answerKo"):
                            fail("[community] 관리자 답변이 저장되지 않음")
                        else:
                            CHECK_ITEMS.append("관리자 답변 저장(한국어)")
                    page.screenshot(path=str(SHOTS / "admin-inquiries.png"))

                # 고객 화면에서 답변(영어 번역) 노출 확인
                page.goto(base + "/en/heyum/#inquiry", wait_until="networkidle")
                page.locator("#inquiry").scroll_into_view_if_needed()
                page.wait_for_timeout(2600)
                card = page.locator(".inq__item", has_text="Check Guest")
                if card.count() == 0:
                    fail("[community] 고객 화면에 문의 없음")
                else:
                    page.wait_for_timeout(2600)  # 번역 응답 대기
                    txt = card.first.inner_text()
                    low = txt.lower()
                    answer_text = " ".join(card.first.locator(".inq__answer-text").all_inner_texts())
                    if "host's answer" not in low:
                        fail(f"[community] 고객 화면에 답변 영역 없음: {txt[:120]}")
                    elif "주차" in answer_text or answer_text.strip() == "":
                        notes.append("[community] 영어 화면에서 답변 번역이 비어 있거나 한국어 그대로 (번역 엔드포인트 응답 확인 필요)")
                        if answer_text.strip():
                            CHECK_ITEMS.append("고객 화면: 문의·답변 영역 표시 (번역은 수동 확인 필요)")
                    else:
                        CHECK_ITEMS.append("고객 화면: 한국어 답변 → 영어 자동 번역 표시")
                    page.locator("#inquiry").screenshot(path=str(SHOTS / "inquiry-answer-en.png"))
            if errors:
                fail(f"[community] 페이지 오류: {errors[:2]}")
        finally:
            if created_inquiry:
                db_delete(f"/inquiries/{created_inquiry}")
            ctx.close()
            browser.close()


def check_booking_flow(base: str) -> None:
    """홈페이지 예약 신청(승인 대기 + 비품 + 계좌 안내) → 관리자 승인 → 달력 마감."""
    from playwright.sync_api import sync_playwright

    booking_id = None
    old_bank = db_get("/settings/bank")
    checkin = (datetime.now(timezone(timedelta(hours=9))).date() + timedelta(days=40)).isoformat()
    checkout = (datetime.now(timezone(timedelta(hours=9))).date() + timedelta(days=42)).isoformat()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 950}, reduced_motion="reduce",
                                      has_touch=False)
            page = ctx.new_page()
            try:
                # 관리자: 입금 계좌 저장
                if not admin_login(page, base):
                    fail("[booking] 관리자 로그인 실패")
                else:
                    page.click('[data-tab="settings"]')
                    page.wait_for_timeout(500)
                    page.fill('#bankForm input[name="bank"]', "국민은행")
                    page.fill('#bankForm input[name="account"]', "123-456-789012")
                    page.fill('#bankForm input[name="holder"]', "문대욱")
                    page.fill('#bankForm input[name="note"]', "입금 후 연락 주시면 확정해 드립니다.")
                    page.click('#bankForm button[type="submit"]')
                    page.wait_for_timeout(1500)
                    bank = db_get("/settings/bank") or {}
                    if bank.get("account") != "123-456-789012":
                        fail(f"[booking] 입금 계좌 저장 실패 {bank}")
                    else:
                        CHECK_ITEMS.append("관리자 설정: 입금 계좌 저장")
                    if "동기화" in page.inner_text('[data-panel="settings"]'):
                        CHECK_ITEMS.append("관리자 설정: 에어비앤비 동기화 기준일 표시")
                    page.screenshot(path=str(SHOTS / "admin-settings.png"))

                # 고객: 예약 신청 (달력에서 연속으로 열린 2박을 고른다)
                page.goto(base + f"/ko/heyum/#reserve", wait_until="networkidle")
                page.locator("#reserve").scroll_into_view_if_needed()
                page.wait_for_timeout(3200)
                for _ in range(4):
                    page.click("[data-bk-next]")
                    page.wait_for_timeout(160)
                avail = page.evaluate("""() => [...document.querySelectorAll('#reserve .bk-day:not(:disabled)[data-date]')]
                    .map(b => b.dataset.date)""")
                pair = None
                for i in range(len(avail) - 1):
                    d0 = datetime.fromisoformat(avail[i]).date()
                    d1 = datetime.fromisoformat(avail[i + 1]).date()
                    if (d1 - d0).days == 1:
                        pair = (avail[i], avail[i + 1])
                        break
                if not pair:
                    fail("[booking] 달력에서 연속 예약 가능 날짜를 찾지 못함")
                    raise SystemExit
                checkin, checkout = pair
                page.click(f'#reserve .bk-day[data-date="{checkin}"]')
                page.wait_for_timeout(250)
                page.click(f'#reserve .bk-day[data-date="{checkout}"]')
                page.wait_for_timeout(400)
                total = page.evaluate("() => document.querySelector('[data-bk-total]').textContent")
                page.fill('[data-bk-form] input[name="name"]', "체크예약")
                page.fill('[data-bk-form] input[name="phone"]', "010-2222-3333")
                page.fill('[data-bk-form] input[name="email"]', "check-booking@example.com")
                page.check('[data-bk-form] input[name="amenity"][value="highchair"]')
                page.check('[data-bk-form] input[name="amenity"][value="kidsroom"]')
                page.click("[data-bk-submit]")
                page.wait_for_timeout(3000)
                done = page.evaluate("() => !document.querySelector('[data-bk-done]').hidden")
                bank_txt = page.evaluate("() => { const b=document.querySelector('[data-bk-bank]'); return b && !b.hidden ? b.textContent : ''; }")
                ref = page.evaluate("() => document.querySelector('[data-bk-ref]').textContent")
                page.screenshot(path=str(SHOTS / "booking-success.png"))
                bookings = db_get("/bookings") or {}
                for k, v in bookings.items():
                    if isinstance(v, dict) and v.get("name") == "체크예약":
                        booking_id = k
                        break
                if not booking_id:
                    fail("[booking] 예약 신청이 Firebase 에 저장되지 않음")
                else:
                    b = bookings[booking_id]
                    if b.get("status") != "pending" or b.get("source") != "direct":
                        fail(f"[booking] 저장 상태 {b.get('status')}/{b.get('source')} (pending/direct 필요)")
                    else:
                        CHECK_ITEMS.append("예약 신청 → status=pending · source=direct")
                    if sorted(b.get("amenitiesRequested") or []) != ["highchair", "kidsroom"]:
                        fail(f"[booking] 비품 요청 저장 {b.get('amenitiesRequested')}")
                    else:
                        CHECK_ITEMS.append("비품 요청(하이체어·키즈룸) 저장")
                    if not done or "123-456-789012" not in bank_txt or "NN-" not in ref:
                        fail(f"[booking] 접수 화면에 접수번호/계좌 안내 없음 ({ref!r} / {bank_txt!r})")
                    else:
                        CHECK_ITEMS.append(f"접수 번호 + 입금 계좌 안내 표시 ({ref})")

                # 홈페이지 달력: 승인 전에는 날짜가 열려 있어야 한다
                page.goto(base + f"/ko/heyum/#reserve", wait_until="networkidle")
                page.locator("#reserve").scroll_into_view_if_needed()
                page.wait_for_timeout(3200)
                for _ in range(4):
                    page.click("[data-bk-next]")
                    page.wait_for_timeout(160)
                off = page.evaluate(f"() => document.querySelector('#reserve .bk-day[data-date=\"{checkin}\"]')?.disabled")
                if off:
                    fail("[booking] 승인 대기 예약인데 달력이 이미 마감됨")
                else:
                    CHECK_ITEMS.append("승인 대기 상태에서는 달력이 열려 있음")

                # 관리자: 승인 → 달력 마감
                if booking_id:
                    if not admin_login(page, base):
                        fail("[booking] 관리자 로그인 실패(승인)")
                    else:
                        page.click('[data-tab="bookings"]')
                        page.wait_for_timeout(900)
                        card = page.locator(".bk", has_text="체크예약")
                        if card.count() == 0:
                            fail("[booking] 관리자 예약 목록에 신청 없음")
                        else:
                            if "아기 하이체어" in card.first.inner_text():
                                CHECK_ITEMS.append("관리자 예약 카드: 요청 비품 배지 표시")
                            card.first.locator("button", has_text="예약 확정").click()
                            page.wait_for_timeout(1800)
                            b = db_get(f"/bookings/{booking_id}") or {}
                            if b.get("status") != "confirmed":
                                fail("[booking] 예약 승인 반영 안 됨")
                            else:
                                CHECK_ITEMS.append("관리자 예약 승인 → confirmed")
                            # 입실 안내 미리보기
                            send = page.locator(".bk", has_text="체크예약").first.locator("button", has_text="입실 안내 보내기")
                            if send.count():
                                send.click()
                                page.wait_for_timeout(800)
                                sheet_txt = page.evaluate("() => { const t=document.querySelector('#sheetBody textarea'); return t ? t.value : document.getElementById('sheetBody').textContent; }")
                                sms = page.evaluate("() => { const a=[...document.querySelectorAll('#sheetBody a')].find(x=>x.textContent.includes('문자')); return a ? a.getAttribute('href') : ''; }")
                                page.screenshot(path=str(SHOTS / "admin-checkin-sheet.png"))
                                if "체크예약" not in sheet_txt or "아기 하이체어" not in sheet_txt:
                                    fail(f"[booking] 입실 안내 치환 실패: {sheet_txt[:160]}")
                                elif not sms.startswith("sms:"):
                                    fail("[booking] 문자 보내기 링크(sms:) 없음")
                                else:
                                    CHECK_ITEMS.append("입실 안내: 이름·비품 치환 + 문자(sms:)·이메일·복사 버튼")
                                page.click("#sheetClose")
                                page.wait_for_timeout(300)
                        page.wait_for_timeout(600)
                        page.screenshot(path=str(SHOTS / "admin-bookings.png"))

                # 고객 달력: 확정 후 마감
                page.goto(base + f"/ko/heyum/#reserve", wait_until="networkidle")
                page.locator("#reserve").scroll_into_view_if_needed()
                page.wait_for_timeout(3200)
                for _ in range(4):
                    page.click("[data-bk-next]")
                    page.wait_for_timeout(160)
                off = page.evaluate(f"() => document.querySelector('#reserve .bk-day[data-date=\"{checkin}\"]')?.disabled")
                if not off:
                    fail("[booking] 확정 후에도 달력이 열려 있음")
                else:
                    CHECK_ITEMS.append("예약 확정 → 홈페이지 달력 마감")
            finally:
                ctx.close()
                browser.close()
    finally:
        if booking_id:
            db_delete(f"/bookings/{booking_id}")
        if old_bank is None:
            db_delete("/settings/bank")
        else:
            db_put("/settings/bank", old_bank)



def check_price_edit(base: str) -> None:
    """관리자 달력에서 날짜별 요금 수정 → 달력 칸·고객 예약 계산에 즉시 반영."""
    from playwright.sync_api import sync_playwright

    blocks = (db_get("/blocks/heyum") or {})
    today = datetime.now(timezone(timedelta(hours=9))).date()
    target = None
    for offset in range(60, 200):
        d0 = today + timedelta(days=offset)
        d1 = d0 + timedelta(days=1)
        if d0.isoformat() not in blocks and d1.isoformat() not in blocks:
            target = d0
            break
    if not target:
        notes.append("[price] 요금 수정 검증에 쓸 빈 날짜를 찾지 못함")
        return
    ds, ds2 = target.isoformat(), (target + timedelta(days=1)).isoformat()
    month_txt = f"{target.year}년 {target.month}월"
    price = 777777
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 950}, reduced_motion="reduce")
            page = ctx.new_page()
            if not admin_login(page, base):
                fail("[price] 관리자 로그인 실패")
                ctx.close()
                browser.close()
                return
            page.click('#roomSeg [data-room="heyum"]')
            page.wait_for_timeout(400)
            for _ in range(14):
                if page.evaluate("() => document.querySelector('#monthLabel').textContent") == month_txt:
                    break
                page.click("#nextMonth")
                page.wait_for_timeout(180)
            page.click(f'#calGrid .day[data-date="{ds}"]')
            page.wait_for_timeout(800)
            if page.evaluate("() => document.getElementById('sheet').hidden"):
                fail("[price] 날짜 시트가 열리지 않음")
            info = page.evaluate("() => { const e=document.querySelector('.sheet__price-info'); return e ? e.textContent : ''; }")
            if "현재 적용" not in info:
                fail(f"[price] 요금 적용 상태 안내 없음: {info!r}")
            page.fill('#sheetBody input[type="number"]', str(price))
            page.click('#sheetBody button:has-text("요금 적용")')
            page.wait_for_timeout(2000)
            ov = db_get(f"/settings/overrides/heyum/{ds}")
            if ov != price:
                fail(f"[price] 날짜별 요금 저장 실패 {ov!r}")
            else:
                CHECK_ITEMS.append(f"관리자 달력: {ds} 1박 요금 {price:,}원 저장")
            cell = page.evaluate("""(date) => {
                const c = document.querySelector(`#calGrid .day[data-date="${date}"]`);
                return c ? c.textContent : '';
            }""", ds)
            if "78만" not in cell or "*" not in cell:
                fail(f"[price] 달력 칸에 수정 요금이 반영되지 않음: {cell!r}")
            else:
                CHECK_ITEMS.append(f"달력 칸 즉시 반영: {cell.strip()}")
            page.screenshot(path=str(SHOTS / "admin-price-edit.png"))
            ctx.close()
            browser.close()

        # 고객 예약 계산에도 반영
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 950}, reduced_motion="reduce")
            page = ctx.new_page()
            page.goto(base + "/ko/heyum/#reserve", wait_until="networkidle")
            page.locator("#reserve").scroll_into_view_if_needed()
            page.wait_for_timeout(3200)
            for _ in range(8):
                label = page.evaluate("() => Array.from(document.querySelectorAll('.bk-cal__head')).map(e => e.textContent).join(' ')")
                if month_txt.replace("년 ", "-").replace("월", "") and str(target.month) in label and str(target.year) in label:
                    break
                page.click("[data-bk-next]")
                page.wait_for_timeout(180)
            em = page.evaluate("""(date) => {
                const b = document.querySelector(`#reserve .bk-day[data-date="${date}"]`);
                return b ? (b.querySelector('em') ? b.querySelector('em').textContent : '') : null;
            }""", ds)
            if em is None:
                fail(f"[price] 고객 달력에 {ds} 칸 없음")
            elif "78만" not in em:
                fail(f"[price] 고객 달력 요금 표시 {em!r} (78만 기대)")
            else:
                CHECK_ITEMS.append("고객 예약 달력에도 수정 요금(78만) 표시")
            page.click(f'#reserve .bk-day[data-date="{ds}"]')
            page.wait_for_timeout(200)
            page.click(f'#reserve .bk-day[data-date="{ds2}"]')
            page.wait_for_timeout(500)
            detail = page.evaluate("() => document.querySelector('[data-bk-detail]').textContent")
            total = page.evaluate("() => document.querySelector('[data-bk-total]').textContent")
            if "777,777" not in detail:
                fail(f"[price] 예약 계산에 수정 요금 미반영 detail={detail!r} total={total!r}")
            else:
                CHECK_ITEMS.append(f"예약 총액 계산에 수정 요금 반영 ({detail.split('·')[0].strip()})")
            ctx.close()
            browser.close()
    finally:
        db_delete(f"/settings/overrides/heyum/{ds}")


def check_self_checkin_copy(base: str) -> None:
    """5개 언어 홈·객실 페이지·llms.txt 에 셀프 체크인 안내가 들어갔는지."""
    terms = {"ko": "셀프 체크인", "en": "Self check-in", "ja": "セルフチェックイン",
             "zh-cn": "自助入住", "zh-tw": "自助入住"}
    for t in build.LANGS:
        d = t["dir"]
        term = terms[d]
        for path in (f"/{d}/", f"/{d}/heyum/", f"/{d}/orot/"):
            status, body = fetch(local(base, path))
            if status != 200:
                continue
            if "guide" not in body or term not in body:
                fail(f"{path} 셀프 체크인 안내 없음 ({term})")
        CHECK_ITEMS.append(f"/{d}/ 셀프 체크인 안내(가이드·FAQ·하이라이트)")
    for name in ("llms.txt", "llms-full.txt"):
        status, body = fetch(local(base, "/" + name))
        if status == 200 and "셀프 체크인" not in body and "Self check-in" not in body:
            fail(f"{name} 에 셀프 체크인 안내 없음")


def check_chat_flow(base: str) -> None:
    """예약자 대화창 e2e: 조회 → 외국어 메시지(한국어 번역) → 관리자 답변 → 입실 안내 대화 전송."""
    from playwright.sync_api import sync_playwright

    today = datetime.now(timezone(timedelta(hours=9))).date()
    ci = (today + timedelta(days=30)).isoformat()
    co = (today + timedelta(days=32)).isoformat()
    ref = "NN-" + ci.replace("-", "")[2:] + "-CHAT"
    booking = {
        "room": "heyum", "checkin": ci, "checkout": co, "nights": 2,
        "adults": 2, "children": 0, "infants": 0,
        "name": "체크대화", "phone": "010-5555-6666", "email": "chat-check@example.com",
        "message": "", "amenitiesRequested": ["highchair"],
        "total": 1100000, "currency": "KRW", "status": "confirmed", "source": "direct",
        "createdAt": int(datetime.now(timezone(timedelta(hours=9))).timestamp() * 1000)
    }
    db_put("/bookings/checkchat", booking)
    db_delete("/bookingChats/checkchat")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 950}, reduced_motion="reduce")
            page = ctx.new_page()
            try:
                # 1) 게스트: 내 예약 조회
                page.goto(base + "/ko/#my-booking", wait_until="networkidle")
                page.locator("#my-booking").scroll_into_view_if_needed()
                page.wait_for_timeout(1800)
                page.fill('[data-mybk-form] input[name="ref"]', ref)
                page.fill('[data-mybk-form] input[name="phone4"]', "6666")
                page.click("[data-mybk-submit]")
                page.wait_for_timeout(2200)
                if page.evaluate("() => document.querySelector('[data-mybk-view]').hidden"):
                    fail("[chat] 접수번호·연락처로 예약 조회 실패")
                else:
                    state = page.evaluate("() => document.querySelector('[data-mybk-state]').textContent")
                    if "확정" not in state:
                        fail(f"[chat] 예약 상태 표시 {state!r}")
                    else:
                        CHECK_ITEMS.append(f"내 예약 조회: {ref} · {state}")
                page.screenshot(path=str(SHOTS / "my-booking-lookup.png"))

                # 2) 게스트: 영어로 메시지 전송 → 한국어 번역 저장
                page.goto(base + "/en/?booking=" + ref + "#my-booking", wait_until="networkidle")
                page.locator("#my-booking").scroll_into_view_if_needed()
                page.wait_for_timeout(1600)
                page.fill('[data-mybk-form] input[name="phone4"]', "6666")
                page.click("[data-mybk-submit]")
                page.wait_for_timeout(2000)
                page.fill('[data-chat-form] textarea[name="text"]', "Hello! What time is check-in? We arrive late at night.")
                page.click("[data-chat-send]")
                page.wait_for_timeout(3200)
                chat = db_get("/bookingChats/checkchat") or {}
                guest_msgs = [v for v in chat.values() if isinstance(v, dict) and v.get("from") == "guest"]
                if not guest_msgs:
                    fail("[chat] 게스트 메시지가 저장되지 않음")
                elif not guest_msgs[-1].get("textKo"):
                    notes.append("[chat] 게스트 메시지 한국어 번역이 비어 있음 (번역 응답 확인 필요)")
                else:
                    CHECK_ITEMS.append("게스트 외국어 메시지 + 한국어 번역 저장")
                page.screenshot(path=str(SHOTS / "my-booking-chat-en.png"))

                # 3) 관리자: 대화창 열기 → 번역 확인 → 답변
                if not admin_login(page, base):
                    fail("[chat] 관리자 로그인 실패")
                else:
                    page.click('[data-tab="bookings"]')
                    page.wait_for_timeout(900)
                    card = page.locator(".bk", has_text="체크대화").first
                    card.locator("button", has_text="대화창 열기").click()
                    page.wait_for_timeout(1800)
                    txt = page.evaluate("() => document.getElementById('sheetBody').innerText")
                    if "입실" in txt and "Hello" in txt:
                        CHECK_ITEMS.append("관리자 대화창: 원문 + 한국어 번역 표시")
                    elif "Hello" not in txt:
                        fail(f"[chat] 관리자 대화창에 게스트 메시지 없음: {txt[:120]}")
                    page.fill('#sheetBody textarea', "안녕하세요! 입실은 오후 3시부터입니다. 늦게 도착하셔도 셀프 체크인으로 바로 입실하실 수 있습니다.")
                    page.click('#sheetBody button:has-text("메시지 보내기")')
                    page.wait_for_timeout(2000)
                    chat = db_get("/bookingChats/checkchat") or {}
                    host_msgs = [v for v in chat.values() if isinstance(v, dict) and v.get("from") == "host"]
                    if not host_msgs:
                        fail("[chat] 관리자 답변이 저장되지 않음")
                    else:
                        CHECK_ITEMS.append("관리자 한국어 답변 전송")
                    page.screenshot(path=str(SHOTS / "admin-chat.png"))
                    page.click("#sheetClose")
                    page.wait_for_timeout(400)

                    # 4) 관리자: 대화창으로 입실 안내 보내기
                    card = page.locator(".bk", has_text="체크대화").first
                    card.locator("button", has_text="입실 안내 보내기").click()
                    page.wait_for_timeout(900)
                    page.fill("#sheetBody textarea", "안녕하세요 체크대화님, 헤윰 입실 안내입니다. 도어락 1234# 으로 입실하세요.")
                    page.click('#sheetBody button:has-text("대화창으로 보내기")')
                    page.wait_for_timeout(2000)
                    chat = db_get("/bookingChats/checkchat") or {}
                    checkins = [v for v in chat.values() if isinstance(v, dict) and v.get("kind") == "checkin"]
                    if not checkins:
                        fail("[chat] 입실 안내가 대화창으로 전송되지 않음")
                    elif "체크대화" not in checkins[-1].get("text", ""):
                        fail("[chat] 입실 안내 이름 치환 실패")
                    else:
                        CHECK_ITEMS.append("관리자: 입실 안내를 대화창으로 전송(이름 치환)")
                    page.screenshot(path=str(SHOTS / "admin-checkin-to-chat.png"))
                    page.click("#sheetClose")
                    page.wait_for_timeout(300)

                # 5) 게스트 화면: 관리자 메시지·입실 안내 표시
                page.goto(base + "/ko/?booking=" + ref + "#my-booking", wait_until="networkidle")
                page.locator("#my-booking").scroll_into_view_if_needed()
                page.wait_for_timeout(1400)
                page.fill('[data-mybk-form] input[name="phone4"]', "6666")
                page.click("[data-mybk-submit]")
                page.wait_for_timeout(2400)
                txt = page.evaluate("() => document.querySelector('[data-chat-list]').innerText")
                if "입실은 오후 3시" not in txt:
                    fail(f"[chat] 게스트 대화창에 호스트 답변 없음: {txt[:120]}")
                elif "CHECK-IN" not in txt.upper():
                    fail("[chat] 게스트 대화창에 입실 안내 메시지 표시 안 됨")
                else:
                    CHECK_ITEMS.append("게스트 대화창: 호스트 답변 + 입실 안내 표시")
                page.screenshot(path=str(SHOTS / "my-booking-chat-ko.png"))
            finally:
                ctx.close()
                browser.close()
    finally:
        db_delete("/bookingChats/checkchat")
        db_delete("/bookings/checkchat")


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

    # --phase 1|2|3 으로 나눠 돌릴 수 있다(느린 환경용). 인자 없으면 전부 실행.
    phase = 0
    if "--phase" in sys.argv:
        phase = int(sys.argv[sys.argv.index("--phase") + 1])

    def want(n: int) -> bool:
        return phase == 0 or phase == n

    try:
        if want(1):
            for path in PAGES:
                check_seo(base, path)
            check_sitemap_robots(base)
            check_geo(base)
            check_room_nav_reviews(base)
            check_gallery(base)
            check_self_checkin_copy(base)
        if want(2):
            check_browser(base)
            check_ten_items(base)
            check_room_nav_browser(base)
        if want(3):
            check_gallery_browser(base)
            check_booking_browser(base)
            check_admin(base)
            check_ical_blocks()
            check_source_colors(base)
            check_community(base)
            check_booking_flow(base)
            check_price_edit(base)
            check_chat_flow(base)
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
