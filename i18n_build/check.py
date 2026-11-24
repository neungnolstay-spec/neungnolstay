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
        for needle in ("NEUNGNOL STAY", "능놀스테이", build.ADDRESS_ROAD, build.AIRBNB["heyum"], build.AIRBNB["orot"]):
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
        for need in (build.INSTAGRAM, build.AIRBNB["heyum"], build.AIRBNB["orot"]):
            if need not in same:
                fail(f"{path} LodgingBusiness sameAs 에 {need} 없음")
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

            # 2) 리뷰 섹션
            start = body.find('id="reviews"')
            if start < 0:
                fail(f"{path} 리뷰 섹션 없음")
                continue
            end = body.find("</section>", start)
            block = body[start:end]
            cards = re.findall(r'<li class="review">', block)
            if len(cards) != 6:
                fail(f"{path} 리뷰 카드 {len(cards)}개 (6개 필요)")
            if block.count('class="review__stars"') != len(cards):
                fail(f"{path} 리뷰 카드에 별점 누락")
            if block.count('class="review__by"') != len(cards):
                fail(f"{path} 리뷰 카드에 게스트 이름 누락")
            if build.AIRBNB_STATS[room]["rating"] not in block:
                fail(f"{path} 리뷰 요약에 에어비앤비 평점 없음")
            if f"data-airbnb=\"{room}\" data-placement=\"reviews\"" not in block:
                fail(f"{path} 에어비앤비 리뷰 더 보기 링크 없음")
            text = re.sub(r"<[^>]+>", " ", block)
            for pat in date_patterns:
                hit = re.search(pat, text)
                if hit:
                    fail(f"{path} 리뷰 영역에 날짜 표기 의심: {hit.group(0)!r}")
            if t["html_lang"] in blocked_char:
                hit = re.search(blocked_char[t["html_lang"]], text)
                if hit:
                    fail(f"{path} 리뷰 영역에 날짜 단위 글자: {hit.group(0)!r}")
            CHECK_ITEMS.append(f"{path}: 리뷰 6개 · 뒤로가기/다른 객실 버튼 · 날짜 표기 없음")


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
            page.wait_for_timeout(500)
            page.locator("#reviews").screenshot(path=str(SHOTS / f"reviews-heyum-{vp_name}.png"))
            cards = page.evaluate("""() => [...document.querySelectorAll('#reviews .review')].map(el => {
                const r = el.getBoundingClientRect();
                return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x)};
            })""")
            if len(cards) != 6:
                fail(f"[reviews {vp_name}] 카드 {len(cards)}개")
            else:
                rows = {c["x"] for c in cards}
                CHECK_ITEMS.append(f"{vp_name}: 리뷰 카드 6개 ({len(rows)}열, {cards[0]['w']}px 폭)")
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
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
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
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
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
                page.click(f'#reserve .bk-day[data-date="{available[0]}"]')
                page.wait_for_timeout(200)
                page.click(f'#reserve .bk-day[data-date="{available[3]}"]')
                page.wait_for_timeout(400)
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
            href = page.evaluate("() => document.querySelector('[data-booking] .bk-alt a[data-airbnb]').getAttribute('href')")
            if build.AIRBNB["orot"] != href:
                fail(f"[booking {vp_name}] 객실 전환 후 에어비앤비 링크 {href}")
            room_flag = page.evaluate("() => document.querySelector('[data-booking]').dataset.room")
            if room_flag != "orot":
                fail(f"[booking {vp_name}] 객실 전환 반영 안 됨 ({room_flag})")
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
    for need in ("data-tab=\"cal\"", "data-tab=\"bookings\"", "data-tab=\"rates\"", "data-tab=\"settings\"", "id=\"keypad\""):
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
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
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
            for tab in ("bookings", "rates", "settings", "cal"):
                page.click(f'[data-tab="{tab}"]')
                page.wait_for_timeout(350)
                if not page.evaluate(f"() => document.querySelector('[data-panel=\"{tab}\"]').classList.contains('is-on')"):
                    fail(f"[admin {vp_name}] 탭 {tab} 표시 안 됨")
            page.screenshot(path=str(SHOTS / f"admin-tabs-{vp_name}.png"))
            if errors:
                fail(f"[admin {vp_name}] 콘솔 오류: {errors[:2]}")
            ctx.close()
        browser.close()
    CHECK_ITEMS.append("/admin/: PIN 잠금 · 달력 · 예약/요금/설정 탭")


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
        check_geo(base)
        check_room_nav_reviews(base)
        check_browser(base)
        check_ten_items(base)
        check_room_nav_browser(base)
        check_gallery(base)
        check_gallery_browser(base)
        check_booking_browser(base)
        check_admin(base)
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
