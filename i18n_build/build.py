#!/usr/bin/env python3
"""능놀스테이 글로벌 다국어 SEO 정적 사이트 빌더 (부티크 호텔 스타일).

    python3 i18n_build/build.py            # docs/ 로 생성
    python3 i18n_build/build.py --out docs # 출력 폴더 지정

BASE_URL / GA4 / GTM / verification 은 아래 한 곳에서만 수정한다.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

import gallery_map

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# ----------------------------------------------------------------------------
# 배포·분석 설정 (여기만 수정)
# ----------------------------------------------------------------------------
BASE_URL = "https://neungnolstay-spec.github.io/neungnolstay"   # 끝에 / 없이
GA4_MEASUREMENT_ID = ""      # 예: "G-XXXXXXXXXX"
GTM_ID = ""                  # 예: "GTM-XXXXXXX"
GSC_VERIFICATION = ""        # Search Console HTML 태그 content 값
NAVER_VERIFICATION = ""      # 네이버 서치어드바이저 소유확인 content 값

PHONE_DISPLAY = "010-3098-2302"
PHONE_INTL = "+82-10-3098-2302"
INSTAGRAM = "https://www.instagram.com/neungnol_stay"
ADDRESS_ROAD = "부산광역시 수영구 민락수변로 13"
LAT, LNG = 35.1547316, 129.1241192
PRICE_RANGE = "₩500,000 - ₩1,200,000"

GOOGLE_MAP_EMBED = f"https://maps.google.com/maps?q={LAT},{LNG}&z=17&hl={{hl}}&output=embed"
GOOGLE_MAP_LINK = f"https://www.google.com/maps/search/?api=1&query={LAT},{LNG}"

FONT_LINKS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500&family=Noto+Sans+KR:wght@300;400;500&family=Noto+Serif+KR:wght@300;400&display=swap" rel="stylesheet">"""

sys.path.insert(0, str(HERE))
import photos  # noqa: E402
from content import ko, en, ja, zhcn, zhtw  # noqa: E402
from content import geo  # noqa: E402
from content import booking as booking_i18n  # noqa: E402
from content import site_text  # noqa: E402

LANGS = [ko.T, en.T, ja.T, zhcn.T, zhtw.T]
ROOMS = ("heyum", "orot")


def _set_path(node, path, value) -> None:
    """('rooms','heyum','facts',7,'v') 처럼 경로를 따라가 값을 바꾼다."""
    cur = node
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value


# 직접 예약·갤러리 문구를 언어 사전에 병합 (content/booking.py)
for _t in LANGS:
    _b = booking_i18n.I18N[_t["dir"]]
    _t["booking"] = _b["booking"]
    for _k, _v in _b["gallery"].items():
        _t["ui"]["gallery_" + _k] = _v
    # 전용 홈페이지 문구(content/site_text.py): 외부 플랫폼 문구 교체 + 리뷰·문의 문구 추가
    for _path, _value in site_text.OVERRIDES[_t["dir"]]:
        _set_path(_t, _path, _value)
    _t["site"] = site_text.I18N[_t["dir"]]
    _t["chat"] = site_text.CHAT[_t["dir"]]
    # 셀프 체크인 안내를 홈·객실 가이드·FAQ·하이라이트에 더한다
    _sc = site_text.SELF_CHECKIN[_t["dir"]]
    _t["home"]["guide_rows"].append({"k": _sc["guide_k"], "v": _sc["guide_v"]})
    _t["home"]["faq"].append({"q": _sc["faq_q"], "a": _sc["faq_a"]})
    for _room in ROOMS:
        _t["rooms"][_room]["guide_rows"].append({"k": _sc["guide_k"], "v": _sc["guide_v"]})
        _t["rooms"][_room]["faq"].append({"q": _sc["faq_q"], "a": _sc["faq_a"]})
        _t["rooms"][_room]["highlights"].append({"t": _sc["hi_t"], "d": _sc["hi_d"]})
BY_DIR = {t["dir"]: t for t in LANGS}
FLOOR = {"heyum": "3", "orot": "6"}
# 무료 비품·유아용품 (네이버 예약 무료 대여 옵션과 동일) — content/booking.py 의 amenities 키와 같다
AMENITY_KEYS = ("kidsroom", "highchair", "sterilizer", "babyshampoo", "pillow", "babydish", "bedguard")
# 객실별 세탁·건조기 (2026-11-24 대욱 님 확인): 세탁기는 두 객실 모두, 건조기는 오롯에만 있음
LAUNDRY_KO = {
    "heyum": "드럼세탁기 있음 · 건조기 없음",
    "orot": "드럼세탁기 + 건조기 있음",
}

# AI 검색(GEO/AEO)용 언어별 요약·질문·키워드 (content/geo.py). t["dir"] 키.
GEO = {t["dir"]: geo.GEO[t["dir"]] for t in LANGS}
LAST_MOD = "2026-11-24"

# 갤러리 사진 목록 (make_gallery.py 가 생성): assets/gallery/manifest.json
GALLERY_MANIFEST = json.loads((ROOT / "assets" / "gallery" / "manifest.json").read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def e(s: str) -> str:
    return html.escape(str(s), quote=True)


def u(t: dict, room: str | None = None) -> str:
    tail = "" if room is None else f"{room}/"
    return f"{BASE_URL}/{t['dir']}/{tail}"


def up(depth: int) -> str:
    return "../" * depth


def attr_links(t: dict, depth: int, page: str) -> dict:
    base = up(depth)
    return {
        "assets": base + "assets/",
        "home": base if page != "home" else "./",
        "heyum": ("../" if page == "room" else "") + "heyum/",
        "orot": ("../" if page == "room" else "") + "orot/",
        "root": base,
    }


def other_lang_href(depth: int, page: str, room: str | None):
    def one(target: dict) -> str:
        if page == "home":
            return up(depth) + target["dir"] + "/"
        return up(depth) + target["dir"] + f"/{room}/"
    return one


def x_default(page: str, room: str | None) -> str:
    return f"{BASE_URL}/" if room is None else u(BY_DIR["ko"], room)


def hreflang_block(page: str, room: str | None) -> str:
    rows = [
        f'<link rel="alternate" hreflang="{t["hreflang"]}" href="{u(t, room)}">' for t in LANGS
    ]
    rows.append(f'<link rel="alternate" hreflang="x-default" href="{x_default(page, room)}">')
    return "\n".join(rows)


def analytics_head() -> str:
    out = []
    if GTM_ID:
        out.append(
            "<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});"
            "var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;"
            f"j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})"
            f"(window,document,'script','dataLayer','{GTM_ID}');</script>"
        )
    if GA4_MEASUREMENT_ID:
        out.append(
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>\n'
            "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
            f"gtag('js',new Date());gtag('config','{GA4_MEASUREMENT_ID}');</script>"
        )
    if not out:
        out.append(
            "<script>window.dataLayer=window.dataLayer||[];window.gtag=window.gtag||"
            "function(){window.dataLayer.push(arguments);};"
            "document.documentElement.classList.add('js');</script>"
        )
    return "\n".join(out)


def verification_meta() -> str:
    rows = []
    if GSC_VERIFICATION:
        rows.append(f'<meta name="google-site-verification" content="{e(GSC_VERIFICATION)}">')
    if NAVER_VERIFICATION:
        rows.append(f'<meta name="naver-site-verification" content="{e(NAVER_VERIFICATION)}">')
    return "\n".join(rows)


def head(t: dict, depth: int, page: str, title: str, desc: str, keywords: str,
         og_title: str, image: str, jsonld: list[dict], room: str | None = None) -> str:
    a = attr_links(t, depth, page)
    canonical = u(t, room)
    img_url = f"{BASE_URL}/assets/{image}"
    alt_locales = "\n".join(
        f'<meta property="og:locale:alternate" content="{o["og_locale"]}">'
        for o in LANGS if o["dir"] != t["dir"]
    )
    ld = "\n".join(
        f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False, indent=1)}</script>'
        for block in jsonld
    )
    return f"""<!DOCTYPE html>
<html lang="{t['html_lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="keywords" content="{e(keywords)}">
<meta name="author" content="NEUNGNOL STAY">
<link rel="canonical" href="{canonical}">
{hreflang_block(page, room)}
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#1c1c1c">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NEUNGNOL STAY">
<meta property="og:title" content="{e(og_title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{img_url}">
<meta property="og:image:alt" content="{e(photos.ALT[image][t['dir']])}">
<meta property="og:locale" content="{t['og_locale']}">
{alt_locales}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(og_title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{img_url}">
{verification_meta()}
<link rel="icon" href="{a['assets']}app-icon.png" type="image/png">
<link rel="apple-touch-icon" href="{a['assets']}app-icon.png">
<link rel="preload" as="image" href="{a['assets']}{image}" fetchpriority="high">
{FONT_LINKS}
<link rel="stylesheet" href="{a['assets']}site.css">
{analytics_head()}
{ld}
</head>
<body>"""


def brand_sub_label(t: dict) -> str:
    name = t["brand_name"].upper().replace(" ", "")
    return t["brand_name"] if name != "NEUNGNOLSTAY" else "BUSAN · GWANGALLI"


def lang_links(t: dict, depth: int, page: str, room: str | None) -> str:
    rows = []
    for o in LANGS:
        cur = ' aria-current="true"' if o["dir"] == t["dir"] else ""
        href = other_lang_href(depth, page, room)(o)
        rows.append(
            f'<a href="{href}" hreflang="{o["hreflang"]}" lang="{o["html_lang"]}"'
            f' data-lang-switch="{o["dir"]}"{cur}>{e(o["label_short"])}</a>'
        )
    return "\n      ".join(rows)


def header(t: dict, depth: int, page: str, room: str | None = None) -> str:
    a = attr_links(t, depth, page)
    nav = t["nav"]
    home_prefix = a["home"]
    about = (home_prefix if page == "home" else home_prefix) + ("#about" if page == "home" else "#about")
    if page == "room":
        about, stays, location, contact = "../#about", "../#stays", "#location", "#inquiry"
    else:
        about, stays, location, contact = "#about", "#stays", "#location", "#inquiry"
    book_href = "#reserve"
    book_attr = ""
    langs = lang_links(t, depth, page, room)
    nav_items = [
        (nav["home"], a["home"], page == "home"),
        (nav["about"], about, False),
        (nav["stays"], stays, False),
        (nav["location"], location, False),
        (nav["contact"], contact, False),
    ]
    desktop = "\n      ".join(
        f'<a href="{href}"{" aria-current=\"page\"" if cur else ""}>{e(label)}</a>'
        for label, href, cur in nav_items
    )
    mobile = "\n      ".join(f'<a href="{href}">{e(label)}</a>' for label, href, _ in nav_items)
    return f"""<header class="site-head">
  <div class="wrap">
    <a class="brand" href="{a['home']}" aria-label="{e(t['brand_name'])} - {e(t['brand_latin'])}">
      <b>NEUNGNOL STAY</b><span>{e(brand_sub_label(t))}</span>
    </a>
    <nav class="nav" aria-label="{e(nav['home'])}">
      {desktop}
    </nav>
    <div class="langs" role="group" aria-label="{e(nav['language'])}">
      <span class="lang-label">{e(nav['language'])}</span>
      {langs}
    </div>
    <a class="head-book" href="{book_href}"{book_attr}>{e(nav['book'])}</a>
  </div>
</header>
<div class="mnav">
  <div class="wrap">
    <span class="mnav-langs" role="group" aria-label="{e(nav['language'])}">{langs}</span>
    <span aria-hidden="true" style="opacity:.3">|</span>
    <span class="mnav-links" aria-label="{e(nav['home'])}">{mobile}</span>
  </div>
</div>"""


def footer(t: dict, depth: int, page: str = "home") -> str:
    a = attr_links(t, depth, page)
    nav = t["nav"]
    return f"""<footer class="site-foot">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <a class="brand" href="{a['home']}">
          <b>NEUNGNOL STAY</b><span>{e(brand_sub_label(t))}</span>
        </a>
        <p>{e(t['footer']['about'])}</p>
      </div>
      <div>
        <h4>{e(t['footer']['explore_title'])}</h4>
        <ul>
          <li><a href="{a['home']}">{e(nav['home'])}</a></li>
          <li><a href="{a['heyum']}">{e(nav['stays'])} · {e(t['home']['cards']['heyum']['name'])}</a></li>
          <li><a href="{a['orot']}">{e(nav['stays'])} · {e(t['home']['cards']['orot']['name'])}</a></li>
          <li><a href="{a['home']}#location">{e(nav['location'])}</a></li>
        </ul>
      </div>
      <div>
        <h4>{e(t['footer']['contact_title'])}</h4>
        <ul>
          <li><a href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a></li>
          <li><a href="{a['home']}#my-booking">{e(t['chat']['my_h2'])}</a></li>
          <li><a href="{a['home']}#inquiry">{e(t['site']['inquiry']['h2'])}</a></li>
          <li><a href="#reserve">{e(t['nav']['book'])}</a></li>
          <li><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">Instagram @neungnol_stay</a></li>
          <li><a href="{GOOGLE_MAP_LINK}" target="_blank" rel="noopener noreferrer">Google Maps</a></li>
        </ul>
      </div>
    </div>
    <div class="foot-bottom">
      <span>{e(t['footer']['rights'])}</span>
      <span>{e(t['footer']['disclaimer'])}</span>
      <a class="foot-admin" href="{a['root']}admin/">{e(t['booking']['admin'])}</a>
    </div>
  </div>
</footer>"""


def img_tag(t: dict, assets: str, file: str, *, loading: str = "lazy", eager: bool = False) -> str:
    w, h = photos.SIZES[file]
    lh = "" if loading == "lazy" else f' loading="{loading}"'
    ec = ' fetchpriority="high"' if eager else ""
    return (f'<img src="{assets}{file}" alt="{e(photos.ALT[file][t["dir"]])}" '
            f'width="{w}" height="{h}"{lh}{ec} decoding="async">')


def figure(t: dict, assets: str, file: str, *, link: str | None = None) -> str:
    inner = img_tag(t, assets, file)
    if link:
        inner = f'<a href="{link}">{inner}</a>'
    return f"<figure>{inner}</figure>"


def cta_buttons(t: dict, placement: str, *, only: str | None = None, light: bool = False) -> str:
    """예약 CTA — 외부 플랫폼이 아니라 이 페이지의 실시간 예약창(#reserve)으로 보냅니다."""
    rows = []
    for rid in ([only] if only else list(ROOMS)):
        card = t["home"]["cards"][rid]
        cls = "btn btn--light" if light else "btn btn--dark"
        rows.append(
            f'<a class="{cls}" href="#reserve" data-book-room="{rid}" data-placement="{placement}">'
            f'{e(card["book_label"])}</a>'
        )
    return '<div class="btn-row">' + "\n".join(rows) + "</div>"


def other_room(room: str) -> str:
    return "orot" if room == "heyum" else "heyum"


def room_nav_links(t: dict, room: str, cls: str) -> str:
    """객실 페이지에서 홈 객실 목록으로 돌아가거나 다른 객실로 바로 넘어가는 두 링크."""
    other = other_room(room)
    other_label = f"{t['home']['cards'][other]['name']} ({t['rooms'][other]['room_floor']})"
    return (
        f'<a class="{cls}" href="../index.html#stays" data-rooms-back>'
        f'<span aria-hidden="true">←</span> {e(t["ui"]["back_all_rooms"])}</a>\n'
        f'<a class="{cls}" href="../{other}/" data-room-switch="{other}">'
        f'{e(t["ui"]["view_other_room"])} · {e(other_label)} <span aria-hidden="true">→</span></a>'
    )


def room_nav(t: dict, room: str) -> str:
    return f"""<div class="room-nav">
    <div class="wrap room-nav__inner">
      {room_nav_links(t, room, 'room-nav__link')}
    </div>
  </div>"""


def reviews_section(t: dict, room: str) -> str:
    """게스트 후기 — Firebase 실시간 목록 + 후기 작성 폼.

    정적 후기(content/*.py)는 Firebase 가 비었거나 연결되지 않을 때만 보이는 fallback 이다.
    리뷰 카드에는 날짜를 넣지 않는다(별점·본문·이름만).
    """
    r = t["rooms"][room]
    s = t["site"]["reviews"]
    static = [{"name": rv["name"], "rating": int(rv["rating"]), "text": rv["text"]} for rv in r["reviews"]]
    avg = round(sum(rv["rating"] for rv in static) / len(static), 1) if static else 0
    stars = "★" * int(round(avg))
    stars += "☆" * (5 - len(stars))
    stars_btn = "".join(
        f'<button type="button" class="rv-star" data-rv-star="{i}" aria-pressed="false" '
        f'aria-label="{i} / 5">★</button>'
        for i in range(1, 6)
    )
    return f"""<section class="section section--sand" id="reviews">
    <div class="wrap center reveal">
      <span class="kicker">{e(s['kicker'])}</span>
      <h2>{e(s['h2'])}</h2>
      <div class="review-score" data-rv-score>
        <b data-rv-avg>{avg:.1f}</b><span class="review-score__of">/ 5</span>
        <span class="review-score__stars" data-rv-stars aria-hidden="true">{stars}</span>
        <span class="review-score__meta" data-rv-count>{e(s['count'].format(n=len(static)))}</span>
      </div>
      <p class="lede">{e(r['reviews_lede'])}</p>
    </div>
    <div class="wrap">
      <ul class="reviews" data-reviews aria-live="polite"></ul>
      <p class="rv-empty" data-rv-empty hidden>{e(s['empty'])}</p>
      <div class="rv-tools">
        <button type="button" class="btn btn--dark" data-rv-open>{e(s['write_title'])}</button>
      </div>
      <form class="rv-form" data-rv-form hidden novalidate>
        <h3 class="rv-form__title">{e(s['write_title'])}</h3>
        <p class="rv-form__note">{e(s['write_lede'])}</p>
        <div class="rv-form__row">
          <label class="rv-field"><span>{e(s['name'])}</span>
            <input type="text" name="name" maxlength="40" autocomplete="name" placeholder="{e(s['name_ph'])}" required></label>
          <div class="rv-field"><span>{e(s['rating'])}</span>
            <div class="rv-stars" role="group" aria-label="{e(s['rating'])}" data-rv-stars-pick>
              {stars_btn}<b data-rv-star-val>5</b>
            </div>
          </div>
        </div>
        <label class="rv-field"><span>{e(s['text_label'])}</span>
          <textarea name="text" rows="4" maxlength="1200" placeholder="{e(s['text_ph'])}" required></textarea></label>
        <p class="rv-msg" data-rv-msg role="alert"></p>
        <div class="rv-form__actions">
          <button type="submit" class="btn btn--dark" data-rv-submit>{e(s['submit'])}</button>
          <button type="button" class="btn btn--line" data-rv-cancel>{e(s['cancel'])}</button>
        </div>
      </form>
      <script type="application/json" data-rv-fallback>{json.dumps(static, ensure_ascii=False)}</script>
      <script type="application/json" data-rv-strings>{json.dumps(s, ensure_ascii=False)}</script>
    </div>
  </section>"""


def my_booking_section(t: dict) -> str:
    """예약자 전용: 접수 번호 + 연락처 뒤 4자리로 예약 확인, 호스트와 1:1 대화."""
    c = t["chat"]
    return f"""<section class="section section--ivory2" id="my-booking">
    <div class="wrap center reveal">
      <span class="kicker">{e(c['my_kicker'])}</span>
      <h2>{e(c['my_h2'])}</h2>
      <p class="lede">{e(c['my_lede'])}</p>
    </div>
    <div class="wrap">
      <div class="mybk" data-mybook>
        <form class="mybk__form" data-mybk-form novalidate>
          <label class="mybk__field"><span>{e(c['ref'])}</span>
            <input type="text" name="ref" autocomplete="off" placeholder="{e(c['ref_ph'])}" maxlength="24" required></label>
          <label class="mybk__field"><span>{e(c['phone4'])}</span>
            <input type="text" name="phone4" inputmode="numeric" autocomplete="off" placeholder="{e(c['phone4_ph'])}" maxlength="4" required></label>
          <button type="submit" class="btn btn--dark" data-mybk-submit>{e(c['lookup'])}</button>
        </form>
        <p class="mybk__msg" data-mybk-msg role="alert"></p>

        <div class="mybk__view" data-mybk-view hidden>
          <div class="mybk__head">
            <b class="mybk__ref" data-mybk-ref></b>
            <span class="mybk__state" data-mybk-state></span>
          </div>
          <dl class="mybk__meta">
            <div><dt>{e(c['stay'])}</dt><dd data-mybk-stay></dd></div>
            <div><dt>{e(t['site']['booking']['bank_title'])}</dt><dd data-mybk-bank></dd></div>
          </dl>
          <p class="mybk__note" data-mybk-note hidden></p>

          <h3 class="mybk__chat-title">{e(c['chat_title'])}</h3>
          <ul class="chat" data-chat-list aria-live="polite"></ul>
          <p class="chat__empty" data-chat-empty>{e(c['chat_empty'])}</p>
          <form class="chat__form" data-chat-form novalidate>
            <textarea name="text" rows="2" maxlength="800" placeholder="{e(c['chat_ph'])}" required></textarea>
            <button type="submit" class="btn btn--dark" data-chat-send>{e(c['chat_send'])}</button>
          </form>
          <p class="chat__msg" data-chat-msg role="alert"></p>
          <p class="chat__hint">{e(c['chat_hint'])}</p>
        </div>
      </div>
      <script type="application/json" data-mybk-strings>{json.dumps({**c, "bank_empty": t['site']['booking']['bank_empty']}, ensure_ascii=False)}</script>
    </div>
  </section>"""


def inquiry_section(t: dict, room: str | None = None) -> str:
    """홈페이지 문의 게시판 — 고객 작성 + 호스트 답변 + 양방향 자동 번역."""
    q = t["site"]["inquiry"]
    selected = room or ""

    def opt(value: str, label: str) -> str:
        sel = " selected" if value == selected else ""
        return f'<option value="{value}"{sel}>{e(label)}</option>'

    return f"""<section class="section" id="inquiry">
    <div class="wrap center reveal">
      <span class="kicker">{e(q['kicker'])}</span>
      <h2>{e(q['h2'])}</h2>
      <p class="lede">{e(q['lede'])}</p>
    </div>
    <div class="wrap">
      <div class="inq" data-inquiry data-page-lang="{t['dir']}" data-room="{selected}">
        <div class="inq__board">
          <h3 class="inq__h3">{e(q['list_title'])}</h3>
          <ul class="inq__list" data-inq-list aria-live="polite"></ul>
          <p class="inq__empty" data-inq-empty>{e(q['empty'])}</p>
          <div class="inq__more" data-inq-more hidden>
            <button type="button" class="link-more" data-inq-more-btn>{e(q['all'])} <span aria-hidden="true">→</span></button>
          </div>
        </div>
        <form class="inq__form" data-inq-form novalidate>
          <h3 class="inq__h3">{e(q['form_title'])}</h3>
          <label class="inq__field"><span>{e(q['name'])}</span>
            <input type="text" name="name" maxlength="40" autocomplete="name" placeholder="{e(q['name_ph'])}" required></label>
          <label class="inq__field"><span>{e(q['contact'])} <i>{e(q['optional'])}</i></span>
            <input type="text" name="contact" maxlength="80" autocomplete="email" placeholder="{e(q['contact_ph'])}"></label>
          <label class="inq__field"><span>{e(q['room'])}</span>
            <select name="room">{opt('', q['general'])}{opt('heyum', t['home']['cards']['heyum']['name'] + ' · ' + t['rooms']['heyum']['room_floor'])}{opt('orot', t['home']['cards']['orot']['name'] + ' · ' + t['rooms']['orot']['room_floor'])}</select></label>
          <label class="inq__field"><span>{e(q['message'])}</span>
            <textarea name="text" rows="4" maxlength="1200" placeholder="{e(q['message_ph'])}" required></textarea></label>
          <p class="inq__note">{e(q['private_note'])}</p>
          <p class="inq__msg" data-inq-msg role="alert"></p>
          <button type="submit" class="btn btn--dark btn--block" data-inq-submit>{e(q['submit'])}</button>
        </form>
      </div>
      <script type="application/json" data-inq-strings>{json.dumps({**q, 'heyum': t['home']['cards']['heyum']['name'], 'orot': t['home']['cards']['orot']['name']}, ensure_ascii=False)}</script>
    </div>
  </section>"""


def map_block(t: dict) -> str:
    hl = {"ko": "ko", "en": "en", "ja": "ja", "zh-cn": "zh-CN", "zh-tw": "zh-TW"}[t["dir"]]
    return f"""<div class="map-frame">
        <iframe src="{GOOGLE_MAP_EMBED.format(hl=hl)}" title="{e(t['brand_name'])} Google Maps" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
      </div>
      <div class="map-meta">
        <a class="btn btn--line" href="{GOOGLE_MAP_LINK}" target="_blank" rel="noopener noreferrer">{e(t['home']['map_cta'])} <span class="ext" aria-hidden="true">↗</span></a>
        <span class="muted">{e(ADDRESS_ROAD)}</span>
      </div>"""


# ----------------------------------------------------------------------------
# JSON-LD
# ----------------------------------------------------------------------------
def lodgings_jsonld(t: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "@id": f"{BASE_URL}/#lodging",
        "name": t["brand_name"],
        "alternateName": "NEUNGNOL STAY",
        "knowsLanguage": ["ko", "en", "ja", "zh-Hans", "zh-Hant"],
        "petsAllowed": False,
        "smokingAllowed": False,
        "description": t["home"]["desc"],
        "url": u(t),
        "image": [f"{BASE_URL}/assets/{f}" for f in ("hero.webp", "hero-heyum.webp", "hero-orot.webp")],
        "telephone": PHONE_INTL,
        "priceRange": PRICE_RANGE,
        "currenciesAccepted": "KRW",
        "paymentAccepted": "Credit Card",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "민락수변로 13",
            "addressLocality": "수영구",
            "addressRegion": "부산광역시",
            "addressCountry": "KR",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": LAT, "longitude": LNG},
        "checkinTime": "15:00",
        "checkoutTime": "11:00",
        "numberOfRooms": 2,
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Ocean view (Gwangalli Beach and Gwangan Bridge)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Beach-view jacuzzi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kids' room", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "100-inch projector", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Baby high chair", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Free parking (1 car, 1 minute on foot)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Wi-Fi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Washing machine (both floors: Heyum and Orot)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Clothes dryer (Orot, 6th floor only)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kitchen (induction only)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Air purifier", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Elevator", "value": True},
        ],
        "sameAs": [INSTAGRAM, GOOGLE_MAP_LINK],
        "tourBookingPage": f"{u(t)}#reserve",
        "containsPlace": [
            {"@type": "HotelRoom", "@id": f"{BASE_URL}/#room-heyum", "name": "Heyum"},
            {"@type": "HotelRoom", "@id": f"{BASE_URL}/#room-orot", "name": "Orot"},
        ],
        "hasMap": GOOGLE_MAP_LINK,
    }


def room_jsonld(t: dict, room: str) -> dict:
    r = t["rooms"][room]
    return {
        "@context": "https://schema.org",
        "@type": "HotelRoom",
        "@id": f"{BASE_URL}/#room-{room}",
        "name": f"{t['brand_name']} {t['home']['cards'][room]['name']}",
        "description": r["desc"],
        "url": u(t, room),
        "image": [f"{BASE_URL}/assets/{f}" for f in [photos.HERO[room], *photos.GALLERY[room][:3]]],
        "floorLevel": FLOOR[room],
        "knowsLanguage": ["ko", "en", "ja", "zh-Hans", "zh-Hant"],
        "floorSize": {"@type": "QuantitativeValue", "value": 200, "unitCode": "MTK"},
        "occupancy": {"@type": "QuantitativeValue", "value": 8, "maxValue": 12},
        "numberOfBedrooms": 3,
        "numberOfBathroomsTotal": 2,
        "bed": {"@type": "BedDetails", "typeOfBed": "Queen", "numberOfBeds": 5},
        "checkinTime": "15:00" if room == "heyum" else "16:00",
        "checkoutTime": "11:00" if room == "heyum" else "12:00",
        "petsAllowed": False,
        "smokingAllowed": False,
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Ocean view (Gwangalli Beach and Gwangan Bridge)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Beach-view jacuzzi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kids' room", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "100-inch projector", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "50-inch TV (YouTube, Netflix)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Baby high chair", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kitchen (induction only)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Washing machine", "value": True},
            *([{"@type": "LocationFeatureSpecification", "name": "Clothes dryer", "value": True}] if room == "orot" else []),
            {"@type": "LocationFeatureSpecification", "name": "Air purifier", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Wi-Fi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Elevator", "value": True},
        ],
        "tourBookingPage": f"{u(t, room)}#reserve",
        "containedInPlace": {
            "@type": "LodgingBusiness",
            "@id": f"{BASE_URL}/#lodging",
            "name": t["brand_name"],
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "민락수변로 13",
                "addressLocality": "수영구",
                "addressRegion": "부산광역시",
                "addressCountry": "KR",
            },
        },
        "sameAs": [GOOGLE_MAP_LINK],
    }


def breadcrumb_jsonld(t: dict, room: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t["ui"]["breadcrumb_home"], "item": u(t)},
            {"@type": "ListItem", "position": 2, "name": t["ui"]["breadcrumb_rooms"], "item": u(t)},
            {"@type": "ListItem", "position": 3,
             "name": f"{t['brand_name']} {t['home']['cards'][room]['name']}", "item": u(t, room)},
        ],
    }


def faq_page_jsonld(items: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
            for q in items
        ],
    }


def faq_jsonld(t: dict, room: str) -> dict:
    return faq_page_jsonld(t["rooms"][room]["faq"])


def home_faq(t: dict) -> list[dict]:
    """홈 FAQ = 기본 FAQ + AI 검색용 자연어 질문(content/geo.py)."""
    return list(t["home"]["faq"]) + list(GEO[t["dir"]]["faq"])


def website_jsonld(t: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "NEUNGNOL STAY",
        "alternateName": t["brand_name"],
        "url": u(t),
        "inLanguage": t["hreflang"],
    }


# ----------------------------------------------------------------------------
# components
# ----------------------------------------------------------------------------
def stay_card(t: dict, assets: str, rid: str) -> str:
    card = t["home"]["cards"][rid]
    facts = "".join(f"<li><b>{e(v)}</b>{e(l)}</li>" for v, l in card["facts"])
    detail = attr_links(t, 1, "home")[rid]
    return f"""<article class="stay">
  <a class="stay__ph" href="{detail}" aria-label="{e(card['name'])}">
    <span class="stay__tag">{e(card['tag'])}</span>
    {img_tag(t, assets, photos.HERO[rid])}
  </a>
  {card_strip(t, assets, rid)}
  <div class="stay__body">
    <h3><small>{e(card['tag'].split('·')[-1].strip())}</small>{e(card['name'])}</h3>
    <p class="stay__sub">{e(card['sub'])}</p>
    <p class="stay__desc">{e(card['desc'])}</p>
    <ul class="stay__facts">{facts}</ul>
    <div class="stay__actions">
      <a class="btn btn--dark btn--block" href="#reserve" data-book-room="{rid}" data-placement="home-card">{e(card['book_label'])}</a>
      <a class="stay__more" href="{detail}">{e(t['ui']['detail'])} →</a>
    </div>
  </div>
</article>"""


# ----------------------------------------------------------------------------
# gallery
# ----------------------------------------------------------------------------
def gal_alt(t: dict, room: str, item: dict) -> str:
    cat = gallery_map.CAT_LABELS[t["dir"]][item["cat"]]
    tone = gallery_map.TONE_LABELS[t["dir"]][item["tone"]]
    name = t["home"]["cards"][room]["name"]
    return f"{name} {cat} · {tone}"


def gal_caption(t: dict, item: dict) -> str:
    if t["dir"] == "ko":
        return item["ko"]
    if t["dir"] == "en":
        return item["en"]
    return f"{gallery_map.CAT_LABELS[t['dir']][item['cat']]} · {gallery_map.TONE_LABELS[t['dir']][item['tone']]}"


def gallery_html(t: dict, assets: str, room: str) -> str:
    """객실 상세: 큐레이션 모자이크 + 분류 필터 그리드 + 라이트박스 데이터."""
    items = GALLERY_MANIFEST[room]
    base = f"{assets}gallery/{room}/"
    n = len(items)
    label_open = t["ui"]["gallery_open"]

    def hero_btn(i: int, cls: str = "") -> str:
        it = items[i]
        alt = gal_alt(t, room, it)
        return (
            f'<button type="button" class="gal-hero__btn {cls}" data-gal-open="{i}"'
            f' aria-label="{e(label_open)}: {e(gal_caption(t, it))}">'
            f'<img src="{base}{it["slug"]}-t.webp" alt="{e(alt)}" width="{it["tw"]}" height="{it["th"]}"'
            f' loading="lazy" decoding="async"></button>'
        )

    hero_side = "".join(hero_btn(i) for i in range(1, min(5, n)))
    hero = (
        '<div class="gal-hero reveal">'
        f'{hero_btn(0, "gal-hero__btn--main")}'
        f'<div class="gal-hero__side">{hero_side}</div>'
        '</div>'
    )

    cats = [c for c in gallery_map.CATS if any(it["cat"] == c for it in items)]
    chips = (
        f'<button type="button" class="gal-chip is-on" data-gal-filter="all" aria-pressed="true">'
        f'{e(t["ui"]["gallery_all"])} <span class="gal-chip__n">{n}</span></button>'
    ) + "".join(
        f'<button type="button" class="gal-chip" data-gal-filter="{c}" aria-pressed="false">'
        f'{e(gallery_map.CAT_LABELS[t["dir"]][c])}</button>'
        for c in cats
    )

    cells = []
    for i, it in enumerate(items):
        cells.append(
            f'<li class="gal-cell" data-cat="{it["cat"]}">'
            f'<button type="button" class="gal-cell__btn" data-gal-open="{i}">'
            f'<img src="{base}{it["slug"]}-t.webp" alt="{e(gal_alt(t, room, it))}" width="{it["tw"]}"'
            f' height="{it["th"]}" loading="lazy" decoding="async">'
            f'<span class="gal-cell__cap">{e(gal_caption(t, it))}</span></button></li>'
        )

    data = [
        {"full": f"{base}{it["slug"]}.webp", "w": it["w"], "h": it["h"], "cap": gal_caption(t, it)}
        for it in items
    ]
    return (
        hero
        + '<div class="gal-bar reveal">'
        + f'<div class="gal-filters" role="group" aria-label="{e(t["ui"]["gallery_all"])}">{chips}</div>'
        + f'<button type="button" class="link-more" data-gal-open="0">{e(t["ui"]["gallery_view_all"].format(n=n))} <span aria-hidden="true">→</span></button>'
        + "</div>"
        + f'<ul class="gal-grid" data-gal-grid>{"".join(cells)}</ul>'
        + f'<script type="application/json" data-gal-data>{json.dumps(data, ensure_ascii=False)}</script>'
    )


def gallery_lightbox(t: dict) -> str:
    return f"""<div class="gal-lb" id="gallery-lightbox" hidden>
  <div class="gal-lb__bar">
    <span class="gal-lb__count" data-gal-count></span>
    <span class="gal-lb__cap" data-gal-cap></span>
    <button type="button" class="gal-lb__close" data-gal-close aria-label="{e(t['ui']['gallery_close'])}">✕</button>
  </div>
  <button type="button" class="gal-lb__nav gal-lb__nav--prev" data-gal-prev aria-label="{e(t['ui']['gallery_prev'])}" aria-hidden="false">‹</button>
  <figure class="gal-lb__stage"><img data-gal-img src="" alt=""></figure>
  <button type="button" class="gal-lb__nav gal-lb__nav--next" data-gal-next aria-label="{e(t['ui']['gallery_next'])}">›</button>
</div>"""


def card_strip(t: dict, assets: str, rid: str) -> str:
    """홈 객실 카드 아래 대표 사진 3장 미리보기 스트립."""
    items = GALLERY_MANIFEST[rid][:3]
    base = f"{assets}gallery/{rid}/"
    cells = "".join(
        f'<a href="{attr_links(t, 1, "home")[rid]}#gallery" aria-label="{e(gal_caption(t, it))}">'
        f'<img src="{base}{it["slug"]}-t.webp" alt="{e(gal_alt(t, rid, it))}" width="{it["tw"]}"'
        f' height="{it["th"]}" loading="lazy" decoding="async"></a>'
        for it in items
    )
    return f'<div class="stay__strip">{cells}</div>'


# ----------------------------------------------------------------------------
# direct booking
# ----------------------------------------------------------------------------
def booking_block(t: dict, assets: str, room: str | None) -> str:
    b = t["booking"]
    amen = b["amenities"]
    amenity_boxes = "".join(
        f'<label class="bk-amen__item"><input type="checkbox" name="amenity" value="{key}">'
        f'<span>{e(amen[key])}</span></label>'
        for key in AMENITY_KEYS
    )
    a = attr_links(t, 1 if room is None else 2, "home" if room is None else "room")
    rooms_switch = ""
    if room is None:
        rooms_switch = (
            f'<div class="bk-rooms" role="group" aria-label="{e(b["room_label"])}">'
            f'<button type="button" class="bk-room is-on" data-bk-room="heyum" aria-pressed="true">{e(b["heyum"])}</button>'
            f'<button type="button" class="bk-room" data-bk-room="orot" aria-pressed="false">{e(b["orot"])}</button>'
            f'</div>'
        )
    current = room or "heyum"

    def stepper(key: str, label: str, hint: str = "") -> str:
        return f"""<div class="bk-step">
          <div class="bk-step__label">{e(label)}{hint}</div>
          <div class="bk-step__ctl">
            <button type="button" class="bk-step__btn" data-bk-step="{key}" data-dir="-1" aria-label="-">−</button>
            <b data-bk-num="{key}">1</b>
            <button type="button" class="bk-step__btn" data-bk-step="{key}" data-dir="1" aria-label="+">+</button>
          </div>
        </div>"""

    return f"""<div class="booking reveal" data-booking data-room="{current}" data-lang="{t['dir']}" data-base="8" data-max="12" data-extra="30000">
      <div class="booking__main">
        {rooms_switch}
        <div class="bk-dates">
          <button type="button" class="bk-date" data-bk-ci>
            <span class="bk-date__label">{e(b['checkin'])}</span>
            <b data-bk-ci-val>—</b>
          </button>
          <span class="bk-dates__arrow" aria-hidden="true">→</span>
          <button type="button" class="bk-date" data-bk-co>
            <span class="bk-date__label">{e(b['checkout'])}</span>
            <b data-bk-co-val>—</b>
          </button>
        </div>
        <div class="bk-monthbar">
          <button type="button" class="bk-monthbar__btn" data-bk-prev aria-label="‹">‹</button>
          <span class="bk-monthbar__now" data-bk-month></span>
          <button type="button" class="bk-monthbar__btn" data-bk-next aria-label="›">›</button>
        </div>
        <div class="bk-cals">
          <div class="bk-cal" data-bk-cal></div>
          <div class="bk-cal bk-cal--second" data-bk-cal2></div>
        </div>
        <p class="bk-legend"><span class="bk-dot bk-dot--open"></span>{e(b['legend_open'])}
          <span class="bk-dot bk-dot--closed"></span>{e(b['legend_closed'])}</p>
      </div>
      <aside class="booking__side">
        <div class="bk-steps">
          {stepper('adults', b['adults'], '')}
          {stepper('children', b['children'], '')}
          {stepper('infants', b['infants'], '')}
        </div>
        <p class="bk-note">{e(b['guests_note'])}</p>
        <div class="bk-total">
          <div class="bk-total__row"><span>{e(b['total'])}</span><b data-bk-total>—</b></div>
          <p class="bk-total__detail" data-bk-detail></p>
          <p class="bk-total__note">{e(b['total_note'])}</p>
          <p class="bk-total__note bk-total__note--confirm">{e(t['site']['booking']['confirm_note'])}</p>
        </div>
        <form class="bk-form" data-bk-form novalidate>
          <h3 class="bk-form__title">{e(b['form_title'])}</h3>
          <label class="bk-field"><span>{e(b['name'])}</span>
            <input type="text" name="name" autocomplete="name" placeholder="{e(b['name_ph'])}" required></label>
          <label class="bk-field"><span>{e(b['phone'])}</span>
            <input type="tel" name="phone" inputmode="tel" autocomplete="tel" placeholder="{e(b['phone_ph'])}" required></label>
          <label class="bk-field"><span>{e(b['email'])} <i>{e(b['optional'])}</i></span>
            <input type="email" name="email" autocomplete="email" placeholder="{e(b['email_ph'])}"></label>
          <label class="bk-field"><span>{e(b['message'])} <i>{e(b['optional'])}</i></span>
            <textarea name="message" rows="3" placeholder="{e(b['message_ph'])}"></textarea></label>
          <fieldset class="bk-amen">
            <legend>{e(b['amenities']['title'])} <i>{e(b['optional'])}</i></legend>
            <p class="bk-amen__note">{e(b['amenities']['note'])}</p>
            <div class="bk-amen__grid">
              {amenity_boxes}
            </div>
          </fieldset>
          <p class="bk-msg" data-bk-msg role="alert"></p>
          <button type="submit" class="btn btn--dark btn--block" data-bk-submit>{e(b['submit'])}</button>
        </form>
        <div class="bk-done" data-bk-done hidden>
          <span class="bk-done__k">{e(b['success_title'])}</span>
          <b class="bk-done__ref" data-bk-ref></b>
          <p data-bk-done-body>{e(b['success_body'])}</p>
          <div class="bk-bank" data-bk-bank hidden>
            <span class="bk-bank__k">{e(t['site']['booking']['bank_title'])}</span>
            <b class="bk-bank__line" data-bk-bank-line></b>
            <p class="bk-bank__note" data-bk-bank-note></p>
          </div>
          <a class="btn btn--dark btn--block" href="#my-booking" data-bk-open-my>{e(t['chat']['open_my'])}</a>
          <button type="button" class="btn btn--line btn--block" data-bk-again>{e(b['success_again'])}</button>
        </div>
        <p class="bk-alt">
          <a href="tel:{PHONE_INTL}">{e(b['call'])} {PHONE_DISPLAY}</a>
          <span class="bk-alt__sep" aria-hidden="true">·</span>
          <a href="#inquiry">{e(t['site']['booking']['inquiry_cta'])}</a>
        </p>
      </aside>
      <script type="application/json" data-bk-lang>{json.dumps({k: v for k, v in {**b, **t['site']['booking']}.items() if not k.startswith('airbnb')}, ensure_ascii=False)}</script>
    </div>"""


# ----------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------
def booking_section(t: dict, assets: str, room: str | None) -> str:
    b = t["booking"]
    return f"""<section class="section section--ivory2" id="reserve">
    <div class="wrap center reveal">
      <span class="kicker">{e(b['kicker'])}</span>
      <h2>{e(b['h2'])}</h2>
      <p class="lede">{e(b['lede'])}</p>
    </div>
    <div class="wrap">
      {booking_block(t, assets, room)}
    </div>
  </section>"""


def build_home(t: dict) -> str:
    a = attr_links(t, 1, "home")
    h = t["home"]
    assets = a["assets"]
    jsonld = [lodgings_jsonld(t), website_jsonld(t), faq_page_jsonld(home_faq(t))]
    keywords = f'{h["keywords"]}, {GEO[t["dir"]]["keywords_home"]}'

    badges = "".join(f"<li>{e(b)}</li>" for b in h["badges"])
    stats = "".join(f"<li><b>{e(v)}</b><span>{e(l)}</span></li>" for v, l in h["stats"])
    features = "".join(
        f'<div class="feature"><div class="feature__no">{i:02d}</div><h3>{e(f["t"])}</h3><p>{e(f["d"])}</p></div>'
        for i, f in enumerate(h["features"], 1)
    )
    gallery = "\n".join(
        figure(t, assets, f, link=(a["heyum"] if f.startswith("h") else a["orot"]))
        for f in photos.HOME_GALLERY
    )
    loc_spec = "".join(
        f'<div><div class="k">{e(r["k"])}</div><div class="v">{e(r["v"])}</div></div>'
        for r in h["location_rows"]
    )
    guide_spec = "".join(
        f'<div><div class="k">{e(r["k"])}</div><div class="v">{e(r["v"])}</div></div>' for r in h["guide_rows"]
    )
    faqs = "".join(
        f'<details><summary>{e(q["q"])}</summary><div class="a"><p>{e(q["a"])}</p></div></details>'
        for q in home_faq(t)
    )
    notes = "".join(f"<li>{e(n)}</li>" for n in h["notes"])
    cta_rows = "".join(
        f'<div class="row"><span>{e(r["k"])}</span><b>{e(r["v"])}</b></div>' for r in h["cta_card_rows"]
    )

    return f"""{head(t, 1, 'home', h['title'], h['desc'], keywords, h['og_title'], photos.HERO['home'], jsonld)}

{header(t, 1, 'home')}

<main id="top">
  <section class="hero">
    <div class="hero__media">{img_tag(t, assets, photos.HERO['home'], loading='eager', eager=True)}</div>
    <div class="wrap hero__inner">
      <span class="kicker">{e(h['hero_kicker'])}</span>
      <h1>{e(h['hero_latin'])}</h1>
      <p class="hero__sub">{e(h['hero_sub'])}</p>
      <div class="btn-row">
        <a class="btn btn--light" href="#stays">{e(h['hero_cta_stays'])}</a>
        <a class="btn btn--light" href="#reserve">{e(h['hero_cta_book'])}</a>
      </div>
    </div>
    <span class="hero__scroll" aria-hidden="true">Scroll</span>
  </section>

  <section class="section" id="about">
    <div class="wrap split reveal">
      <div>
        <span class="kicker">{e(h['intro_kicker'])}</span>
        <h2>{e(h['intro_h2'])}</h2>
        <p class="lede">{e(h['intro_p1'])}</p>
        <p>{e(h['intro_p2'])}</p>
      </div>
      <div class="split__media">{img_tag(t, assets, 'h01.webp')}</div>
    </div>
    <div class="wrap"><ul class="stats">{stats}</ul></div>
  </section>

  <section class="section section--sand" id="stays">
    <div class="wrap center reveal">
      <span class="kicker">{e(h['rooms_kicker'])}</span>
      <h2>{e(h['rooms_h2'])}</h2>
      <p class="lede">{e(h['rooms_lede'])}</p>
    </div>
    <div class="wrap">
      <div class="stays">
        {stay_card(t, assets, 'heyum')}
        {stay_card(t, assets, 'orot')}
      </div>
      <p class="ext-note center" style="margin-top:18px">{e(t['ui']['airbnb_note'])}</p>
    </div>
  </section>

  <section class="section section--ivory2" id="reserve">
    <div class="wrap center reveal">
      <span class="kicker">{e(t['booking']['kicker'])}</span>
      <h2>{e(t['booking']['h2'])}</h2>
      <p class="lede">{e(t['booking']['lede'])}</p>
    </div>
    <div class="wrap">
      {booking_block(t, assets, None)}
    </div>
  </section>

  <section class="section">
    <div class="wrap center reveal">
      <span class="kicker">{e(h['features_kicker'])}</span>
      <h2>{e(h['features_h2'])}</h2>
      <p class="lede">{e(h['features_lede'])}</p>
    </div>
    <div class="wrap"><div class="features reveal">{features}</div></div>
  </section>

  <section class="section section--ivory2">
    <div class="wrap center reveal">
      <span class="kicker">{e(h['gallery_kicker'])}</span>
      <h2>{e(h['gallery_h2'])}</h2>
      <p class="lede">{e(h['gallery_lede'])}</p>
    </div>
    <div class="wrap"><div class="gallery reveal">
      {gallery}
    </div></div>
  </section>

  <section class="section" id="location">
    <div class="wrap loc reveal">
      <div>
        <span class="kicker">{e(h['location_kicker'])}</span>
        <h2>{e(h['location_h2'])}</h2>
        <p class="lede">{e(h['location_lede'])}</p>
        <div class="spec">{loc_spec}</div>
      </div>
      <div>{map_block(t)}</div>
    </div>
  </section>

  {my_booking_section(t)}

  {inquiry_section(t)}

  <section class="section section--sand" id="contact">
    <div class="wrap reveal">
      <span class="kicker">{e(h['contact_kicker'])}</span>
      <h2>{e(h['contact_h2'])}</h2>
      <p class="lede">{e(h['contact_lede'])}</p>
      <div class="contact-grid">
        <div class="contact-card">
          <h3>{e(t['ui']['phone'])}</h3>
          <p><a href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['site']['inquiry']['h2'])}</h3>
          <p><a href="#inquiry">{e(t['site']['inquiry']['form_title'])} →</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['ui']['instagram'])}</h3>
          <p><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">@neungnol_stay ↗</a></p>
        </div>
        <div class="contact-card">
          <h3>Google Maps</h3>
          <p><a href="{GOOGLE_MAP_LINK}" target="_blank" rel="noopener noreferrer">{e(ADDRESS_ROAD)} ↗</a></p>
        </div>
      </div>
    </div>
  </section>

  <section class="section" id="guide">
    <div class="wrap reveal">
      <span class="kicker">{e(h['guide_kicker'])}</span>
      <h2>{e(h['guide_h2'])}</h2>
      <p class="lede">{e(h['guide_lede'])}</p>
      <div class="spec spec--2">{guide_spec}</div>
    </div>
  </section>

  <section class="section section--ivory2" id="faq">
    <div class="wrap reveal">
      <span class="kicker">{e(h['faq_kicker'])}</span>
      <h2>{e(h['faq_h2'])}</h2>
      <div class="faq">{faqs}</div>
      <p class="muted" style="margin-top:24px">{e(h['reviews_note'])}</p>
    </div>
  </section>

  <section class="section section--dark" id="booking">
    <div class="wrap cta-box reveal">
      <div>
        <span class="kicker">{e(h['cta_kicker'])}</span>
        <h2>{e(h['cta_h2'])}</h2>
        <p class="lede">{e(h['cta_p'])}</p>
        {cta_buttons(t, 'home-cta', light=True)}
        <p class="cta-note">{e(t['ui']['airbnb_note'])}</p>
        <ul class="ticks" style="margin-top:20px">{notes}</ul>
      </div>
      <div class="cta-card">
        <h3>{e(h['cta_card_title'])}</h3>
        {cta_rows}
        <div class="btn-row" style="margin-top:22px">
          <a class="btn btn--light" href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a>
        </div>
      </div>
    </div>
  </section>
</main>

<nav class="bookbar" aria-label="{e(t['nav']['book'])}">
  <a class="btn btn--dark" href="#reserve" data-book-room="heyum" data-placement="sticky">{e(t['home']['cards']['heyum']['book_label'])}</a>
  <a class="btn btn--dark" href="#reserve" data-book-room="orot" data-placement="sticky">{e(t['home']['cards']['orot']['book_label'])}</a>
</nav>

{footer(t, 1, 'home')}

<script>window.SITE_CONFIG={{page:"home",lang:"{t['dir']}",room:""}};</script>
<script src="{assets}app.js" defer></script>
<script src="{assets}nns.js" defer></script>
<script src="{assets}booking.js" defer></script>
<script src="{assets}mybooking.js" defer></script>
<script src="{assets}inquiry.js" defer></script>
</body>
</html>
"""


def build_room(t: dict, room: str) -> str:
    a = attr_links(t, 2, "room")
    r = t["rooms"][room]
    name = t["home"]["cards"][room]["name"]
    assets = a["assets"]
    jsonld = [room_jsonld(t, room), breadcrumb_jsonld(t, room), faq_jsonld(t, room)]
    keywords = f'{r["keywords"]}, {GEO[t["dir"]]["keywords_room"]}'

    facts = "".join(
        f'<div><div class="k">{e(f["k"])}</div><div class="v">{e(f["v"])}</div></div>' for f in r["facts"]
    )
    highlights = "".join(
        f'<div class="feature"><div class="feature__no">{i:02d}</div><h3>{e(x["t"])}</h3><p>{e(x["d"])}</p></div>'
        for i, x in enumerate(r["highlights"], 1)
    )
    gallery = "\n".join(figure(t, assets, f) for f in photos.GALLERY[room])
    facs = "".join(
        f'<div class="fac"><h3>{e(g["t"])}</h3><ul>' + "".join(f"<li>{e(i)}</li>" for i in g["items"]) + "</ul></div>"
        for g in r["fac_groups"]
    )
    loc_spec = "".join(
        f'<div><div class="k">{e(x["k"])}</div><div class="v">{e(x["v"])}</div></div>' for x in r["loc_rows"]
    )
    guide_spec = "".join(
        f'<div><div class="k">{e(x["k"])}</div><div class="v">{e(x["v"])}</div></div>' for x in r["guide_rows"]
    )
    faqs = "".join(
        f'<details><summary>{e(q["q"])}</summary><div class="a"><p>{e(q["a"])}</p></div></details>'
        for q in r["faq"]
    )
    notes = "".join(f"<li>{e(n)}</li>" for n in r["booking_notes"])
    intro_img = photos.GALLERY[room][1]

    return f"""{head(t, 2, 'room', r['title'], r['desc'], keywords, r['og_title'], photos.HERO[room], jsonld, room)}

{header(t, 2, 'room', room)}

<main id="top">
  {room_nav(t, room)}

  <div class="wrap crumbs">
    <nav aria-label="Breadcrumb">
      <ol>
        <li><a href="{a['home']}">{e(t['ui']['breadcrumb_home'])}</a></li>
        <li><a href="../">{e(t['ui']['breadcrumb_rooms'])}</a></li>
        <li aria-current="page">{e(name)}</li>
      </ol>
    </nav>
  </div>

  <section class="room-hero">
    {img_tag(t, assets, photos.HERO[room], loading='eager', eager=True)}
    <div class="wrap room-hero__inner">
      <span class="room-hero__floor">{e(r['floor_label'])}</span>
      <h1>{'<br>'.join(e(line) for line in r['h1'].split(chr(10)))}</h1>
      <p class="room-hero__lead">{e(r['lead'])}</p>
    </div>
  </section>

  <section class="section" data-room-view-marker>
    <div class="wrap split reveal">
      <div>
        <span class="kicker">{e(r['intro_kicker'])}</span>
        <h2>{e(r['intro_h2'])}</h2>
        <p class="lede">{e(r['intro_p1'])}</p>
        <p>{e(r['intro_p2'])}</p>
        <p>{e(r['intro_p3'])}</p>
        {cta_buttons(t, 'room-intro', only=room)}
        <p class="ext-note">{e(t['ui']['airbnb_note'])}</p>
      </div>
      <div class="split__media">{img_tag(t, assets, intro_img)}</div>
    </div>
    <div class="wrap"><div class="spec spec--2">{facts}</div></div>
  </section>

  <section class="section section--sand">
    <div class="wrap center reveal">
      <span class="kicker">{e(r['highlights_kicker'])}</span>
      <h2>{e(r['highlights_h2'])}</h2>
    </div>
    <div class="wrap"><div class="features reveal">{highlights}</div></div>
  </section>

  <section class="section" id="gallery">
    <div class="wrap center reveal">
      <span class="kicker">{e(r['gallery_kicker'])}</span>
      <h2>{e(r['gallery_h2'])}</h2>
      <p class="lede">{e(r['gallery_lede'])}</p>
    </div>
    <div class="wrap gal-wrap">
      {gallery_html(t, assets, room)}
    </div>
  </section>

  {booking_section(t, assets, room)}

  {reviews_section(t, room)}

  <section class="section" id="plan">
    <div class="wrap center reveal">
      <span class="kicker">{e(r['plan_kicker'])}</span>
      <h2>{e(r['plan_h2'])}</h2>
      <p class="lede">{e(r['plan_p'])}</p>
    </div>
    <div class="wrap plan-wrap reveal">
      <figure class="plan">
        <a class="plan__open" href="{assets}{photos.PLAN[room]}" target="_blank" rel="noopener"
           data-plan-open aria-label="{e(t['ui']['plan_zoom'])}">{img_tag(t, assets, photos.PLAN[room])}<span class="plan__hint" aria-hidden="true">⤢ {e(t['ui']['plan_zoom'])}</span></a>
        <figcaption class="muted">{e(r['plan_cap'])}</figcaption>
      </figure>
    </div>
  </section>

  <section class="section" id="amenities">
    <div class="wrap reveal">
      <span class="kicker">{e(r['fac_kicker'])}</span>
      <h2>{e(r['fac_h2'])}</h2>
    </div>
    <div class="wrap"><div class="cols reveal">{facs}</div></div>
  </section>

  <section class="section section--sand" id="location">
    <div class="wrap loc reveal">
      <div>
        <span class="kicker">{e(r['loc_kicker'])}</span>
        <h2>{e(r['loc_h2'])}</h2>
        <p class="lede">{e(r['loc_p'])}</p>
        <div class="spec">{loc_spec}</div>
      </div>
      <div>{map_block(t)}</div>
    </div>
  </section>

  <section class="section" id="guide">
    <div class="wrap reveal">
      <span class="kicker">{e(r['guide_kicker'])}</span>
      <h2>{e(r['guide_h2'])}</h2>
      <div class="spec spec--2">{guide_spec}</div>
    </div>
  </section>

  <section class="section section--ivory2" id="faq">
    <div class="wrap reveal">
      <span class="kicker">{e(r['faq_kicker'])}</span>
      <h2>{e(r['faq_h2'])}</h2>
      <div class="faq">{faqs}</div>
    </div>
  </section>

  {my_booking_section(t)}

  {inquiry_section(t, room)}

  <section class="section section--sand" id="contact">
    <div class="wrap reveal">
      <span class="kicker">{e(t['home']['contact_kicker'])}</span>
      <h2>{e(t['home']['contact_h2'])}</h2>
      <p class="lede">{e(t['home']['contact_lede'])}</p>
      <div class="contact-grid">
        <div class="contact-card">
          <h3>{e(t['ui']['phone'])}</h3>
          <p><a href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['site']['inquiry']['h2'])}</h3>
          <p><a href="#inquiry">{e(t['site']['inquiry']['form_title'])} →</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['ui']['instagram'])}</h3>
          <p><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">@neungnol_stay ↗</a></p>
        </div>
        <div class="contact-card">
          <h3>Google Maps</h3>
          <p><a href="{GOOGLE_MAP_LINK}" target="_blank" rel="noopener noreferrer">{e(ADDRESS_ROAD)} ↗</a></p>
        </div>
      </div>
    </div>
  </section>

  <section class="section section--dark" id="booking">
    <div class="wrap cta-box reveal">
      <div>
        <span class="kicker">{e(r['booking_kicker'])}</span>
        <h2>{e(r['booking_h2'])}</h2>
        <p class="lede">{e(r['booking_p'])}</p>
        {cta_buttons(t, 'room-cta', only=room, light=True)}
        <p class="cta-note">{e(t['ui']['airbnb_note'])}</p>
        <div class="cta-nav">
          {room_nav_links(t, room, 'btn btn--light')}
        </div>
      </div>
      <div class="cta-card">
        <h3>{e(name)}</h3>
        <ul class="ticks">{notes}</ul>
        <div class="btn-row" style="margin-top:20px">
          <a class="btn btn--light" href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a>
        </div>
        <p class="cta-note">{e(r['cta_note'])}</p>
      </div>
    </div>
  </section>
</main>

<nav class="bookbar" aria-label="{e(t['nav']['book'])}">
  <a class="btn btn--dark" href="#reserve" data-book-room="{room}" data-placement="sticky">{e(t['home']['cards'][room]['book_label'])}</a>
  <a class="btn btn--line" href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a>
</nav>

{footer(t, 2, 'room')}

{gallery_lightbox(t)}

<div class="plan-lb" id="plan-lightbox" hidden>
  <div class="plan-lb__bar">
    <span class="plan-lb__title">{e(r['plan_cap'])}</span>
    <div class="plan-lb__tools">
      <button type="button" class="plan-lb__btn" data-plan-zoom data-label-actual="{e(t['ui']['plan_actual'])}" data-label-fit="{e(t['ui']['plan_fit'])}" aria-pressed="false">{e(t['ui']['plan_actual'])}</button>
      <a class="plan-lb__btn" href="{assets}{photos.PLAN[room]}" target="_blank" rel="noopener">{e(t['ui']['plan_newwin'])} ↗</a>
      <button type="button" class="plan-lb__close" data-plan-close aria-label="{e(t['ui']['plan_close'])}">✕</button>
    </div>
  </div>
  <div class="plan-lb__stage" data-plan-stage>
    {img_tag(t, assets, photos.PLAN[room])}
  </div>
</div>

<script>window.SITE_CONFIG={{page:"room",lang:"{t['dir']}",room:"{room}"}};</script>
<script src="{assets}app.js" defer></script>
<script src="{assets}nns.js" defer></script>
<script src="{assets}gallery.js" defer></script>
<script src="{assets}booking.js" defer></script>
<script src="{assets}reviews.js" defer></script>
<script src="{assets}mybooking.js" defer></script>
<script src="{assets}inquiry.js" defer></script>
</body>
</html>
"""


def build_root() -> str:
    opts = []
    for t in LANGS:
        opts.append(
            f'<a href="{t["dir"]}/" hreflang="{t["hreflang"]}" lang="{t["html_lang"]}">'
            f'<b>{e(t["label"])}</b><span>{e(brand_sub_label(t))}</span></a>'
        )
    alts = "\n".join(f'<link rel="alternate" hreflang="{t["hreflang"]}" href="{u(t)}">' for t in LANGS)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NEUNGNOL STAY · 능놀스테이 | 부산 광안리 바다 바로 앞 오션뷰 풀빌라</title>
<meta name="description" content="부산 광안리 해수욕장 바로 앞, 바다가 보이는 60평대 독채 오션뷰 풀빌라 능놀스테이. 한국어 · English · 日本語 · 简体中文 · 繁體中文.">
<link rel="canonical" href="{BASE_URL}/">
{alts}
<link rel="alternate" hreflang="x-default" href="{BASE_URL}/">
<meta property="og:type" content="website">
<meta property="og:title" content="NEUNGNOL STAY | A Private Stay by Gwangalli Beach">
<meta property="og:description" content="Ocean-view private pool villa right on Gwangalli Beach. Choose your language.">
<meta property="og:url" content="{BASE_URL}/">
<meta property="og:image" content="{BASE_URL}/assets/hero.webp">
<meta name="theme-color" content="#1c1c1c">
<link rel="icon" href="assets/app-icon.png" type="image/png">
{FONT_LINKS}
<link rel="stylesheet" href="assets/site.css">
<script type="application/ld+json">{json.dumps(lodgings_jsonld(LANGS[0]), ensure_ascii=False, indent=1)}</script>
<script type="application/ld+json">{json.dumps(website_jsonld(LANGS[0]), ensure_ascii=False, indent=1)}</script>
<script>
(function () {{
  try {{
    var saved = sessionStorage.getItem("nns_lang");
    var nav = (navigator.language || navigator.userLanguage || "").toLowerCase();
    var map = [
      ["ko", "ko"], ["en", "en"], ["ja", "ja"],
      ["zh-tw", "zh-tw"], ["zh-hk", "zh-tw"], ["zh-hant", "zh-tw"],
      ["zh", "zh-cn"], ["zh-cn", "zh-cn"], ["zh-hans", "zh-cn"]
    ];
    var pick = saved;
    if (!pick) {{
      for (var i = 0; i < map.length; i++) {{
        if (nav.indexOf(map[i][0]) === 0) {{ pick = map[i][1]; break; }}
      }}
    }}
    if (pick && !/[?&]stay=1/.test(location.search)) {{
      sessionStorage.setItem("nns_lang", pick);
      location.replace(pick + "/");
    }}
  }} catch (err) {{}}
}})();
</script>
</head>
<body>
<main class="choose">
  <div class="choose__bg" aria-hidden="true"><img src="assets/hero.webp" alt="" aria-hidden="true" width="1590" height="1290"></div>
  <div class="wrap choose__inner">
    <span class="kicker">NEUNGNOL STAY · BUSAN GWANGALLI</span>
    <h1>A PRIVATE STAY<br>BY GWANGALLI BEACH</h1>
    <p>부산 수영구 민락수변로 13 · 3층 헤윰과 6층 오롯.<br>Choose your language · 言語を選択 · 选择语言 · 選擇語言</p>
    <h2 class="kicker kicker--plain" style="color:#c9b08a;margin-top:34px">LANGUAGE</h2>
    <nav class="choose__list" aria-label="Language">
      {''.join(opts)}
    </nav>
    <p style="margin-top:32px;font-size:12.5px;color:#c3bcb0">
      <a href="ko/#reserve">예약 · BOOK NOW</a>
      &nbsp;·&nbsp;
      <a href="ko/#inquiry">문의 · INQUIRY</a>
    </p>
    <p class="muted" style="margin-top:24px;color:#8a847a;font-size:11px">
      <a href="ko/" style="border-bottom:1px solid #55504a">한국어로 계속하기</a>
    </p>
  </div>
</main>
</body>
</html>
"""


def build_sitemap() -> str:
    entries = []
    root_links = "\n".join(
        f'    <xhtml:link rel="alternate" hreflang="{t["hreflang"]}" href="{u(t)}"/>' for t in LANGS
    )
    entries.append(
        f"""  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{LAST_MOD}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
{root_links}
    <xhtml:link rel="alternate" hreflang="x-default" href="{BASE_URL}/"/>
  </url>"""
    )
    for room in [None, *ROOMS]:
        for t in LANGS:
            links = "\n".join(
                f'    <xhtml:link rel="alternate" hreflang="{o["hreflang"]}" href="{u(o, room)}"/>' for o in LANGS
            )
            xdef = x_default("home", room)
            entries.append(
                f"""  <url>
    <loc>{u(t, room)}</loc>
    <lastmod>{LAST_MOD}</lastmod>
    <changefreq>{"weekly" if room is None else "monthly"}</changefreq>
    <priority>{"0.9" if room is None else "0.8"}</priority>
{links}
    <xhtml:link rel="alternate" hreflang="x-default" href="{xdef}"/>
  </url>"""
            )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(entries) + "\n</urlset>\n")


def build_robots() -> str:
    """검색엔진·AI 검색 크롤러를 모두 명시적으로 허용한다."""
    agents = [
        ("검색엔진 (search engines)", ["Googlebot", "Bingbot", "Yeti", "Daumoa", "Applebot"]),
        ("AI 검색·학습 크롤러 (AI search crawlers)", [
            "GPTBot", "OAI-SearchBot", "ChatGPT-User", "Google-Extended", "PerplexityBot",
            "ClaudeBot", "anthropic-ai", "Applebot-Extended", "Amazonbot", "Meta-ExternalAgent",
        ]),
    ]
    rows = [
        "# NEUNGNOL STAY · 능놀스테이 — 부산 광안리 해변 바로 앞 오션뷰 독채 풀빌라",
        "# 검색엔진과 AI 검색 크롤러 모두 허용 (AI가 숙소를 정확히 찾고 인용하도록 공개)",
        "",
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
    ]
    for title, names in agents:
        rows += ["", f"# {title}"]
        for name in names:
            rows += [f"User-agent: {name}", "Allow: /", "Disallow: /admin/"]
    rows += [
        "",
        f"Sitemap: {BASE_URL}/sitemap.xml",
        f"# AI 요약: {BASE_URL}/llms.txt · {BASE_URL}/llms-full.txt",
    ]
    return "\n".join(rows) + "\n"


def _room_spec_lines(t: dict, room: str) -> list[str]:
    skip = ("예약", "예약", "Booking", "Reservation", "予約", "预订", "預訂")
    return [f"- {f['k']}: {f['v']}" for f in t["rooms"][room]["facts"] if not any(s in f["k"] for s in skip)]


def build_llms() -> str:
    """llms.txt — AI 검색엔진용 짧은 사실 요약 + 페이지 목록."""
    ko_t = BY_DIR["ko"]
    g = GEO["ko"]
    ge = GEO["en"]
    rows: list[str] = [
        "# NEUNGNOL STAY · 능놀스테이",
        "",
        f"> {g['summary']}",
        "",
        f"> {ge['summary']}",
        "",
        f"공식 사이트 (official website): {BASE_URL}/  ·  최종 갱신 {LAST_MOD}",
        "",
        "## 핵심 정보 (Key facts)",
        "",
        "- 브랜드 / Brand: NEUNGNOL STAY · 능놀스테이 · Neungnol Stay (영문 철자 N-E-U-N-G-N-O-L)",
        f"- 주소 / Address: {ADDRESS_ROAD} (3층·6층), 대한민국  /  3F & 6F, 13 Millak-subyeon-ro, Suyeong-gu, Busan, Republic of Korea",
        "- 위치 특징: 광안리 해수욕장 도보 1분, 광안대교 정면 오션뷰",
        f"- 지도 좌표 / Coordinates: {LAT}, {LNG} ({GOOGLE_MAP_LINK})",
        f"- 전화 / Phone: {PHONE_DISPLAY} ({PHONE_INTL})",
        f"- 인스타그램 / Instagram: {INSTAGRAM}",
        "- 객실 수 / Rooms: 2 (객실별 독립 예약, 두 층 함께 이용 시 2건 예약)",
        "",
        "## 객실 (Rooms)",
        "",
    ]
    for room in ROOMS:
        card = ko_t["home"]["cards"][room]
        rows += [
            f"### {card['name']} · {card['tag']}",
            "",
            f"{card['desc']}",
            "",
            *_room_spec_lines(ko_t, room),
            f"- 세탁 / Laundry: {LAUNDRY_KO[room]}",
            f"- 예약 / Booking: {u(ko_t, room)}#reserve (실시간 달력에서 날짜·인원 선택 → 신청 → 사장님 확인으로 확정)",
            f"- 페이지 / Page: {u(ko_t, room)}",
            "",
        ]
    rows += [
        "## 핵심 특징 (Highlights)",
        "",
        "- 거실 통창과 자쿠지 창으로 광안리 해변·바다·광안대교가 보이는 전면 오션뷰",
        "- 객실 안 비치뷰 온수 자쿠지 (오롯은 거실과 벽 없이 이어짐)",
        "- 키즈룸: 정글짐·트램폴린·미끄럼틀·흔들그네, 32인치 좌식 게임기, 50인치 TV(유튜브·넷플릭스)",
        "- 100인치 빔프로젝터 (거실 벽이 스크린), 유아 하이체어",
        "- 60평대 독채: 침실 3·욕실 2·퀸베드 5, 주방(인덕션만), 공기청정기, 엘리베이터",
        "- 세탁·건조: 드럼세탁기는 헤윰·오롯 두 객실 모두, 건조기는 오롯(6층)에만 있음 (헤윰에는 건조기 없음)",
        "- 가족·단체 여행에 맞춘 구성: 기본 8인·최대 12인, 24개월 미만 무료, 초과 1인 30,000원",
        "- 셀프 체크인: 예약 확정 후 개인 디지털 도어락 비밀번호를 예약 대화창으로 발급 — 프런트 없이 비대면 입실",
        "",
        "## 이용 규정 (House rules)",
        "",
    ]
    for row in ko_t["home"]["guide_rows"]:
        rows.append(f"- {row['k']}: {row['v']}")
    rows += [
        f"- 주차: 민락회센터·민락어패류주차장 1대 무료(도보 1분, 차종 사전 협의)",
        "",
        "## 평점 (Ratings)",
        "",
        f"- {g['reviews_summary']}",
        "",
        "## 언어별 페이지 (Language versions)",
        "",
    ]
    for t in LANGS:
        rows.append(f"- [{t['label']} ({t['hreflang']})]({u(t)}): {t['home']['title']}")
    rows += ["", "### 객실 페이지 (Room pages)", ""]
    for t in LANGS:
        for room in ROOMS:
            name = t["home"]["cards"][room]["name"]
            rows.append(f"- [{t['label']} · {name}]({u(t, room)}): {t['rooms'][room]['title']}")
    rows += [
        "",
        "## 예약·문의 (Booking & contact)",
        "",
        "- 홈페이지 직접 예약 (Direct booking): " + f"{BASE_URL}/ko/heyum/#reserve" + " · " + f"{BASE_URL}/ko/orot/#reserve"
        + " — 실시간 예약 달력에서 날짜·인원을 고르고 신청하면 사장님 확인 후 확정됩니다. 확정 전에는 결제하지 않습니다.",
        f"- 문의 게시판 (Inquiry board): {BASE_URL}/ko/#inquiry — 5개 언어로 문의하고 답변받을 수 있습니다.",
        f"- 전화 (Phone): {PHONE_DISPLAY} / {PHONE_INTL}",
        f"- 인스타그램: {INSTAGRAM}",
        f"- Google Maps: {GOOGLE_MAP_LINK}",
        "",
        "## AI에게 자주 묻는 질문 (What travellers ask AI)",
        "",
    ]
    for t in LANGS:
        rows.append(f"### {t['label']}")
        rows.append("")
        for q in GEO[t["dir"]]["queries"]:
            rows.append(f"- {q}")
        rows.append("")
    rows += ["## 키워드 (Keywords)", ""]
    for t in LANGS:
        rows.append(f"- {t['label']}: {t['home']['keywords']}, {GEO[t['dir']]['keywords_home']}")
    rows += [
        "",
        "## 안내 (Notes)",
        "",
        "- 위 정보는 공식 홈페이지의 현재 내용을 그대로 요약한 것이다. 요금·예약 가능 여부는 날짜와 인원에 따라 달라지며, 홈페이지 실시간 예약 달력이 기준이다. 홈페이지 예약은 신청 후 사장님 확인으로 확정된다.",
        "- 두 객실은 같은 건물의 서로 다른 층이며, 한 번에 두 층을 쓰려면 홈페이지에서 두 건을 따로 신청해야 한다.",
        "- 사이트에서 다루지 않는 항목은 확인된 정보가 아니므로 답변에 신뢰해 사용하지 말 것.",
        f"- 전체 상세 문서: {BASE_URL}/llms-full.txt",
        "",
    ]
    return "\n".join(rows)


def build_llms_full() -> str:
    """llms-full.txt — 5개 언어 전체 상세(객실·시설·FAQ·후기·키워드)."""
    rows: list[str] = [
        "# NEUNGNOL STAY · 능놀스테이 — 전체 문서 (llms-full)",
        "",
        f"> 부산 광안리 해수욕장 바로 앞 오션뷰 독채 풀빌라 능놀스테이의 5개 언어 전체 정보. "
        f"브랜드 영문 표기 NEUNGNOL STAY / Neungnol Stay, 주소 {ADDRESS_ROAD} (3층·6층), "
        f"광안리 해수욕장 도보 1분. 최종 갱신 {LAST_MOD}.",
        "",
        f"- 짧은 요약: {BASE_URL}/llms.txt",
        f"- 공식 사이트: {BASE_URL}/",
        f"- 좌표: {LAT}, {LNG}",
        f"- 전화: {PHONE_DISPLAY} ({PHONE_INTL})",
        f"- 홈페이지 예약: {BASE_URL}/ko/#reserve",
        f"- 문의 게시판: {BASE_URL}/ko/#inquiry",
        "",
    ]
    for t in LANGS:
        g = GEO[t["dir"]]
        h = t["home"]
        rows += [
            "---",
            "",
            f"## {t['label']} ({t['hreflang']})",
            "",
            f"- 홈: {u(t)}",
            f"- 페이지 제목: {h['title']}",
            "",
            "### 요약",
            "",
            g["summary"],
            "",
            "### 숙소 개요",
            "",
            h["desc"],
            "",
            h["intro_p1"],
            "",
            h["intro_p2"],
            "",
            "### 공통 이용 안내",
            "",
        ]
        for row in h["guide_rows"]:
            rows.append(f"- {row['k']}: {row['v']}")
        rows.append("")
        for room in ROOMS:
            r = t["rooms"][room]
            card = h["cards"][room]
            rows += [
                f"### {card['name']} ({card['tag']})",
                "",
                f"- 페이지: {u(t, room)}",
                f"- 예약: {u(t, room)}#reserve (실시간 달력 → 신청 → 사장님 확인으로 확정)",
                "",
                r["desc"],
                "",
                r["lead"],
                "",
                "#### 사양",
                "",
            ]
            rows += _room_spec_lines(t, room)
            rows += ["", "#### 시설", ""]
            for grp in r["fac_groups"]:
                rows.append(f"- {grp['t']}: {', '.join(grp['items'])}")
            rows += ["", "#### 이용 안내", ""]
            for row in r["guide_rows"]:
                rows.append(f"- {row['k']}: {row['v']}")
            rows += ["", "#### 자주 묻는 질문", ""]
            for qa in r["faq"]:
                rows += [f"**Q. {qa['q']}**", "", f"A. {qa['a']}", ""]
            rows += ["#### 게스트 후기", ""]
            for rv in r["reviews"]:
                rows.append(f"- {'★' * int(rv['rating'])} — {rv['name']}: \"{rv['text']}\"")
            rows.append("")
        rows += ["### 공통 자주 묻는 질문 (AI 검색용)", ""]
        for qa in home_faq(t):
            rows += [f"**Q. {qa['q']}**", "", f"A. {qa['a']}", ""]
        rows += ["### 평점", "", f"- {g['reviews_summary']}", "", "### 검색 키워드", ""]
        rows.append(f"- {h['keywords']}, {g['keywords_home']}")
        rows.append("")
        rows += ["### AI에게 자주 묻는 질문 예시", ""]
        for q in g["queries"]:
            rows.append(f"- {q}")
        rows.append("")
    rows += [
        "---",
        "",
        "## 출처·정확성 (Source of truth)",
        "",
        "- 위 내용은 공식 사이트(5개 언어)와 실제 객실·예약 정보에서 확인한 사실이다. 사진은 모두 실제 객실에서 촬영한 것이다.",
        "- 요금(₩500,000–₩1,200,000 / 1박)과 예약 가능 여부는 날짜·인원에 따라 달라지며, 홈페이지 실시간 예약 달력이 최종 기준이다.",
        "- 두 객실은 각각 별도 예약이다. 한 팀이 두 층을 모두 쓰려면 두 건을 따로 신청한다.",
        "- 위 문서에 없는 내용은 확인된 정보가 아니므로 추측해 답하지 말고, 필요하면 전화·문의 게시판으로 확인할 것.",
        "",
    ]
    return "\n".join(rows)


def check_content_keys():
    def keys(d, prefix=""):
        out = set()
        for k, v in d.items():
            out.add(prefix + k)
            if isinstance(v, dict):
                out |= keys(v, prefix + k + ".")
        return out
    base = keys(ko.T)
    for t in LANGS[1:]:
        other = keys(t)
        missing = sorted(base - other)
        extra = sorted(other - base)
        if missing or extra:
            raise SystemExit(f"[content] {t['dir']}: missing={missing} extra={extra}")
    for t in LANGS:
        assert len(t["home"]["faq"]) == len(ko.T["home"]["faq"]), t["dir"]
        assert len(t["home"]["features"]) == 4, t["dir"]
        for rid in ROOMS:
            assert len(t["rooms"][rid]["faq"]) == len(ko.T["rooms"][rid]["faq"]), (t["dir"], rid)
            assert len(t["rooms"][rid]["facts"]) == 8, (t["dir"], rid)
            assert len(t["rooms"][rid]["reviews"]) == 6, (t["dir"], rid)
            assert all(rv["name"] and rv["text"] for rv in t["rooms"][rid]["reviews"]), (t["dir"], rid)
    base_geo = GEO["ko"]
    for d, g in GEO.items():
        for key in ("summary", "reviews_summary"):
            assert g[key].strip(), (d, key)
        assert len(g["faq"]) == len(base_geo["faq"]), (d, "faq")
        assert len(g["queries"]) == len(base_geo["queries"]), (d, "queries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs", help="출력 폴더 (repo 기준)")
    args = ap.parse_args()
    out = (ROOT / args.out).resolve()

    check_content_keys()

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    assets_out = out / "assets"
    assets_out.mkdir()
    for f in photos.SIZES:
        src = ROOT / "assets" / f
        if not src.exists():
            raise SystemExit(f"missing asset: {src}")
        shutil.copy2(src, assets_out / f)
    shutil.copy2(ROOT / "assets" / "app-icon.png", assets_out / "app-icon.png")
    shutil.copytree(ROOT / "assets" / "gallery", assets_out / "gallery", dirs_exist_ok=True)
    (assets_out / "gallery" / "manifest.json").unlink(missing_ok=True)
    shutil.copy2(HERE / "static" / "style.css", assets_out / "site.css")
    shutil.copy2(HERE / "static" / "app.js", assets_out / "app.js")
    shutil.copy2(HERE / "static" / "gallery.js", assets_out / "gallery.js")
    shutil.copy2(HERE / "static" / "booking.js", assets_out / "booking.js")
    shutil.copy2(HERE / "static" / "nns.js", assets_out / "nns.js")
    shutil.copy2(HERE / "static" / "reviews.js", assets_out / "reviews.js")
    shutil.copy2(HERE / "static" / "inquiry.js", assets_out / "inquiry.js")
    shutil.copy2(HERE / "static" / "mybooking.js", assets_out / "mybooking.js")

    # 사장님 전용 관리 화면 /admin/
    admin_out = out / "admin"
    admin_out.mkdir()
    for f in (HERE / "admin").iterdir():
        if f.is_file():
            shutil.copy2(f, admin_out / f.name)
    shutil.copy2(HERE / "static" / "nns.js", admin_out / "nns.js")

    (out / "index.html").write_text(build_root(), encoding="utf-8")
    for t in LANGS:
        d = out / t["dir"]
        (d / "heyum").mkdir(parents=True)
        (d / "orot").mkdir(parents=True)
        (d / "index.html").write_text(build_home(t), encoding="utf-8")
        (d / "heyum" / "index.html").write_text(build_room(t, "heyum"), encoding="utf-8")
        (d / "orot" / "index.html").write_text(build_room(t, "orot"), encoding="utf-8")

    (out / "sitemap.xml").write_text(build_sitemap(), encoding="utf-8")
    (out / "robots.txt").write_text(build_robots(), encoding="utf-8")
    (out / "llms.txt").write_text(build_llms(), encoding="utf-8")
    (out / "llms-full.txt").write_text(build_llms_full(), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(f"built {1 + len(LANGS) * 3} pages + admin + llms.txt/llms-full.txt/robots.txt/sitemap.xml -> {out}")


if __name__ == "__main__":
    main()
