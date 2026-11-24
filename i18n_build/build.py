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
TALKTALK = "https://talk.naver.com/w4hhwm"
NAVER_PLACE = "https://m.place.naver.com/accommodation/1967720454"
NAVER_BOOKING = {
    "heyum": "https://m.booking.naver.com/booking/3/bizes/839642/items/4848181",
    "orot": "https://m.booking.naver.com/booking/3/bizes/839642/items/4881823",
}
AIRBNB = {
    "heyum": "https://www.airbnb.co.kr/rooms/827083520643586714",
    "orot": "https://www.airbnb.co.kr/rooms/842458938331176391",
}
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

LANGS = [ko.T, en.T, ja.T, zhcn.T, zhtw.T]
BY_DIR = {t["dir"]: t for t in LANGS}
ROOMS = ("heyum", "orot")
FLOOR = {"heyum": "3", "orot": "6"}


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
<meta name="author" content="NUNG NOL STAY">
<link rel="canonical" href="{canonical}">
{hreflang_block(page, room)}
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#1c1c1c">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NUNG NOL STAY">
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
    return t["brand_name"] if name != "NUNGNOLSTAY" else "BUSAN · GWANGALLI"


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
        about, stays, location, contact = "../#about", "../#stays", "#location", "#contact"
    else:
        about, stays, location, contact = "#about", "#stays", "#location", "#contact"
    book_href = AIRBNB[room] if room else "#stays"
    book_attr = (
        f' target="_blank" rel="noopener noreferrer" data-airbnb="{room}" data-placement="header"'
        if room else ""
    )
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
      <b>NUNG NOL STAY</b><span>{e(brand_sub_label(t))}</span>
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
          <b>NUNG NOL STAY</b><span>{e(brand_sub_label(t))}</span>
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
          <li><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">Instagram @neungnol_stay</a></li>
          <li><a href="{TALKTALK}" target="_blank" rel="noopener noreferrer">{e(t['ui']['talktalk'])}</a></li>
          <li><a href="{NAVER_PLACE}" target="_blank" rel="noopener noreferrer">{e(t['ui']['naver_place'])}</a></li>
          <li><a href="{GOOGLE_MAP_LINK}" target="_blank" rel="noopener noreferrer">Google Maps</a></li>
        </ul>
      </div>
    </div>
    <div class="foot-bottom">
      <span>{e(t['footer']['rights'])}</span>
      <span>{e(t['footer']['disclaimer'])}</span>
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
    rows = []
    for rid in ([only] if only else list(ROOMS)):
        card = t["home"]["cards"][rid]
        cls = "btn btn--light" if light else "btn btn--dark"
        rows.append(
            f'<a class="{cls}" href="{AIRBNB[rid]}" target="_blank" rel="noopener noreferrer" '
            f'data-airbnb="{rid}" data-placement="{placement}">{e(card["book_label"])} '
            f'<span class="ext" aria-hidden="true">↗</span></a>'
        )
    return '<div class="btn-row">' + "\n".join(rows) + "</div>"


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
        "alternateName": "NUNG NOL STAY",
        "description": t["home"]["desc"],
        "url": u(t),
        "image": [f"{BASE_URL}/assets/{f}" for f in ("hero.webp", "airbnb-heyum.webp", "airbnb-orot.webp")],
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
            {"@type": "LocationFeatureSpecification", "name": "Ocean view", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Beach-view jacuzzi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kids' room", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "100-inch projector", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Free parking (1 car)", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Wi-Fi", "value": True},
        ],
        "sameAs": [INSTAGRAM, NAVER_PLACE, AIRBNB["heyum"], AIRBNB["orot"]],
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
        "occupancy": {"@type": "QuantitativeValue", "value": 8, "maxValue": 12},
        "numberOfRooms": 3,
        "numberOfBathroomsTotal": 2,
        "bed": {"@type": "BedDetails", "typeOfBed": "Queen", "numberOfBeds": 5},
        "checkinTime": "15:00" if room == "heyum" else "16:00",
        "checkoutTime": "11:00" if room == "heyum" else "12:00",
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Ocean view", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Jacuzzi", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kids' room", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "100-inch projector", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Kitchen", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Washing machine", "value": True},
        ],
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
        "sameAs": [AIRBNB[room], NAVER_BOOKING[room]],
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


def faq_jsonld(t: dict, room: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
            for q in t["rooms"][room]["faq"]
        ],
    }


def website_jsonld(t: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "NUNG NOL STAY",
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
  <div class="stay__body">
    <h3><small>{e(card['tag'].split('·')[-1].strip())}</small>{e(card['name'])}</h3>
    <p class="stay__sub">{e(card['sub'])}</p>
    <p class="stay__desc">{e(card['desc'])}</p>
    <ul class="stay__facts">{facts}</ul>
    <div class="stay__actions">
      <a class="btn btn--dark btn--block" href="{AIRBNB[rid]}" target="_blank" rel="noopener noreferrer"
         data-airbnb="{rid}" data-placement="home-card">{e(card['book_label'])} <span class="ext" aria-hidden="true">↗</span></a>
      <a class="stay__more" href="{detail}">{e(t['ui']['detail'])} →</a>
    </div>
  </div>
</article>"""


# ----------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------
def build_home(t: dict) -> str:
    a = attr_links(t, 1, "home")
    h = t["home"]
    assets = a["assets"]
    jsonld = [lodgings_jsonld(t), website_jsonld(t)]

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
        for q in h["faq"]
    )
    notes = "".join(f"<li>{e(n)}</li>" for n in h["notes"])
    cta_rows = "".join(
        f'<div class="row"><span>{e(r["k"])}</span><b>{e(r["v"])}</b></div>' for r in h["cta_card_rows"]
    )

    return f"""{head(t, 1, 'home', h['title'], h['desc'], h['keywords'], h['og_title'], photos.HERO['home'], jsonld)}

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
        <a class="btn btn--light" href="#booking">{e(h['hero_cta_book'])}</a>
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
          <h3>{e(t['ui']['instagram'])}</h3>
          <p><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">@neungnol_stay ↗</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['ui']['talktalk'])}</h3>
          <p><a href="{TALKTALK}" target="_blank" rel="noopener noreferrer">{e(t['ui']['talktalk'])} ↗</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['ui']['naver_place'])}</h3>
          <p><a href="{NAVER_PLACE}" target="_blank" rel="noopener noreferrer">{e(t['brand_name'])} ↗</a></p>
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
  <a class="btn btn--dark" href="{AIRBNB['heyum']}" target="_blank" rel="noopener noreferrer" data-airbnb="heyum" data-placement="sticky">{e(t['home']['cards']['heyum']['book_label'])} ↗</a>
  <a class="btn btn--dark" href="{AIRBNB['orot']}" target="_blank" rel="noopener noreferrer" data-airbnb="orot" data-placement="sticky">{e(t['home']['cards']['orot']['book_label'])} ↗</a>
</nav>

{footer(t, 1, 'home')}

<script>window.SITE_CONFIG={{page:"home",lang:"{t['dir']}",room:""}};</script>
<script src="{assets}app.js" defer></script>
</body>
</html>
"""


def build_room(t: dict, room: str) -> str:
    a = attr_links(t, 2, "room")
    r = t["rooms"][room]
    name = t["home"]["cards"][room]["name"]
    assets = a["assets"]
    jsonld = [room_jsonld(t, room), breadcrumb_jsonld(t, room), faq_jsonld(t, room)]

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

    return f"""{head(t, 2, 'room', r['title'], r['desc'], r['keywords'], r['og_title'], photos.HERO[room], jsonld, room)}

{header(t, 2, 'room', room)}

<main id="top">
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

  <section class="section">
    <div class="wrap center reveal">
      <span class="kicker">{e(r['gallery_kicker'])}</span>
      <h2>{e(r['gallery_h2'])}</h2>
      <p class="lede">{e(r['gallery_lede'])}</p>
    </div>
    <div class="wrap"><div class="gallery reveal">
      {gallery}
    </div></div>
  </section>

  <section class="section section--ivory2">
    <div class="wrap reveal">
      <span class="kicker">{e(r['plan_kicker'])}</span>
      <h2>{e(r['plan_h2'])}</h2>
    </div>
    <div class="wrap plan-wrap reveal">
      <div>{img_tag(t, assets, photos.PLAN[room])}</div>
      <div>
        <p class="lede">{e(r['plan_p'])}</p>
        <p class="muted">{e(r['plan_cap'])}</p>
      </div>
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
          <h3>{e(t['ui']['instagram'])}</h3>
          <p><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">@neungnol_stay ↗</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['ui']['talktalk'])}</h3>
          <p><a href="{TALKTALK}" target="_blank" rel="noopener noreferrer">{e(t['ui']['talktalk'])} ↗</a></p>
        </div>
        <div class="contact-card">
          <h3>{e(t['ui']['naver_place'])}</h3>
          <p><a href="{NAVER_PLACE}" target="_blank" rel="noopener noreferrer">{e(t['brand_name'])} ↗</a></p>
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
  <a class="btn btn--dark" href="{AIRBNB[room]}" target="_blank" rel="noopener noreferrer" data-airbnb="{room}" data-placement="sticky">{e(t['home']['cards'][room]['book_label'])} ↗</a>
  <a class="btn btn--line" href="tel:{PHONE_INTL}">{PHONE_DISPLAY}</a>
</nav>

{footer(t, 2, 'room')}

<script>window.SITE_CONFIG={{page:"room",lang:"{t['dir']}",room:"{room}"}};</script>
<script src="{assets}app.js" defer></script>
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
<title>NUNG NOL STAY · 능놀스테이 | 부산 광안리 바다 바로 앞 오션뷰 풀빌라</title>
<meta name="description" content="부산 광안리 해수욕장 바로 앞, 바다가 보이는 60평대 독채 오션뷰 풀빌라 능놀스테이. 한국어 · English · 日本語 · 简体中文 · 繁體中文.">
<link rel="canonical" href="{BASE_URL}/">
{alts}
<link rel="alternate" hreflang="x-default" href="{BASE_URL}/">
<meta property="og:type" content="website">
<meta property="og:title" content="NUNG NOL STAY | A Private Stay by Gwangalli Beach">
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
    <span class="kicker">NUNG NOL STAY · BUSAN GWANGALLI</span>
    <h1>A PRIVATE STAY<br>BY GWANGALLI BEACH</h1>
    <p>부산 수영구 민락수변로 13 · 3층 헤윰과 6층 오롯.<br>Choose your language · 言語を選択 · 选择语言 · 選擇語言</p>
    <h2 class="kicker kicker--plain" style="color:#c9b08a;margin-top:34px">LANGUAGE</h2>
    <nav class="choose__list" aria-label="Language">
      {''.join(opts)}
    </nav>
    <p style="margin-top:32px;font-size:12.5px;color:#c3bcb0">
      <a href="{AIRBNB['heyum']}" target="_blank" rel="noopener noreferrer">HEYUM · Airbnb ↗</a>
      &nbsp;·&nbsp;
      <a href="{AIRBNB['orot']}" target="_blank" rel="noopener noreferrer">OROT · Airbnb ↗</a>
      &nbsp;·&nbsp;
      <a href="{NAVER_PLACE}" target="_blank" rel="noopener noreferrer">Naver Place ↗</a>
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
    <lastmod>2026-11-24</lastmod>
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
    <lastmod>2026-11-24</lastmod>
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
    return f"""User-agent: *
Allow: /

Sitemap: {BASE_URL}/sitemap.xml
"""


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
    shutil.copy2(HERE / "static" / "style.css", assets_out / "site.css")
    shutil.copy2(HERE / "static" / "app.js", assets_out / "app.js")

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
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(f"built {1 + len(LANGS) * 3} pages -> {out}")


if __name__ == "__main__":
    main()
