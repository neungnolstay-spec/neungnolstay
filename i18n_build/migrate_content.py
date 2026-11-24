#!/usr/bin/env python3
"""콘텐츠 스키마 마이그레이션 (1회성): 럭셔리 부티크 개편용 키 추가.

- nav: HOME / ABOUT / OUR STAYS / LOCATION / CONTACT / LANGUAGE
- hero_latin / hero_sub / hero_cta_stays / hero_cta_book
- 카드별 book_label
- 홈 contact 섹션 문구
"""
from pathlib import Path
import re

NAV = '''    "nav": {
        "home": "HOME",
        "about": "ABOUT",
        "stays": "OUR STAYS",
        "location": "LOCATION",
        "contact": "CONTACT",
        "language": "LANGUAGE",
        "book": "%s",
        "faq": "%s",
    },'''

LANG = {
    "ko": dict(
        book="예약하기", faq="자주 묻는 질문",
        hero_sub="광안리의 바다와 함께하는 특별한 휴식.",
        cta_stays="객실 보기", cta_book="예약하기",
        book_heyum="헤윰 예약하기", book_orot="오롯 예약하기",
        contact_h2="문의와 오시는 길",
        contact_lede="예약 전 궁금한 점은 전화나 SNS로 편하게 문의해 주세요. 아래 지도에서 숙소의 실제 위치를 확인할 수 있습니다.",
        map_cta="Google Maps에서 열기",
    ),
    "en": dict(
        book="Book", faq="FAQ",
        hero_sub="A private rest beside the Gwangalli sea.",
        cta_stays="OUR STAYS", cta_book="RESERVE",
        book_heyum="BOOK HEYUM", book_orot="BOOK OROT",
        contact_h2="Contact & directions",
        contact_lede="Questions before booking? Call or message us. The map below shows the actual location on Gwangalli Beach.",
        map_cta="Open in Google Maps",
    ),
    "ja": dict(
        book="予約", faq="よくある質問",
        hero_sub="広安里の海とともに過ごす、特別な休息。",
        cta_stays="客室を見る", cta_book="予約する",
        book_heyum="ヘユムを予約", book_orot="オロッを予約",
        contact_h2="お問い合わせとアクセス",
        contact_lede="ご予約前のご質問はお電話やSNSでお気軽にどうぞ。下の地図が実際の宿の位置です。",
        map_cta="Google マップで開く",
    ),
    "zhcn": dict(
        book="预订", faq="常见问题",
        hero_sub="与广安里的大海相伴的特别休憩。",
        cta_stays="查看客房", cta_book="预订",
        book_heyum="预订 Heyum", book_orot="预订 Orot",
        contact_h2="联系与交通",
        contact_lede="预订前如有疑问，欢迎通过电话或社交平台联系我们。下方地图为住宿的实际位置。",
        map_cta="在 Google 地图中打开",
    ),
    "zhtw": dict(
        book="訂房", faq="常見問題",
        hero_sub="與廣安里的海一同度過的特別休憩。",
        cta_stays="查看客房", cta_book="訂房",
        book_heyum="預訂 Heyum", book_orot="預訂 Orot",
        contact_h2="聯絡與交通",
        contact_lede="訂房前如有疑問，歡迎透過電話或社群平台與我們聯繫。下方地圖為住宿的實際位置。",
        map_cta="在 Google 地圖中開啟",
    ),
}

ROOM_NAMES = {
    "ko": ("헤윰", "오롯"),
    "en": ("Heyum", "Orot"),
    "ja": ("ヘユム", "オロッ"),
    "zhcn": ("Heyum", "Orot"),
    "zhtw": ("Heyum", "Orot"),
}


def migrate(path: Path, key: str) -> None:
    d = LANG[key]
    s = path.read_text()

    # 1) nav
    s2, n = re.subn(r'"nav": \{.*?\n    \},', lambda m: NAV % (d["book"], d["faq"]), s, count=1, flags=re.S)
    assert n == 1, f"{path}: nav not replaced"

    # 2) hero
    def repl(field, value):
        nonlocal s2
        s2, m = re.subn(r'("' + field + r'": )"[^"]*"', lambda mm: mm.group(1) + '"' + value + '"', s2, count=1)
        assert m == 1, f"{path}: {field} not replaced"

    repl("hero_h1", "A PRIVATE STAY BY GWANGALLI BEACH")
    s2, m = re.subn(r'"hero_h1":', '"hero_latin":', s2, count=1)
    assert m == 1
    repl("hero_sub", d["hero_sub"])
    repl("hero_cta1", d["cta_stays"])
    repl("hero_cta2", d["cta_book"])
    s2 = s2.replace('"hero_cta1":', '"hero_cta_stays":').replace('"hero_cta2":', '"hero_cta_book":')

    # 3) card book labels
    hname, oname = ROOM_NAMES[key]
    for name, label in ((hname, d["book_heyum"]), (oname, d["book_orot"])):
        pat = r'("tag": "[^"]*",\n\s+"name": "' + re.escape(name) + r'",\n)'
        s2, m = re.subn(pat, lambda mm: mm.group(1) + f'                "book_label": "{label}",\n', s2, count=1)
        assert m == 1, f"{path}: book_label for {name}"

    # 4) contact section copy
    contact = (
        f'        "contact_kicker": "Contact",\n'
        f'        "contact_h2": "{d["contact_h2"]}",\n'
        f'        "contact_lede": "{d["contact_lede"]}",\n'
        f'        "map_cta": "{d["map_cta"]}",\n'
    )
    s2, m = re.subn(r'\n(\s+)"cta_kicker":', lambda mm: "\n" + contact + mm.group(1) + '"cta_kicker":', s2, count=1)
    assert m == 1, f"{path}: contact keys"

    path.write_text(s2)
    print("migrated", path.name)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent / "content"
    for key in ("ko", "en", "ja", "zhcn", "zhtw"):
        migrate(base / f"{key}.py", key)
