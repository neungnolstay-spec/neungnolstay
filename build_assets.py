#!/usr/bin/env python3
"""능놀스테이 홈페이지 이미지 선별·최적화 (2024년 이후 실제 촬영·등록 사진만)"""
import os, json
from PIL import Image, ImageDraw, ImageFont

SRC = '/workspace/downloads/neungnol_stay/photos'
OUT = '/workspace/neungnolstay-site/assets'
os.makedirs(OUT, exist_ok=True)

# (출력이름, 원본경로, 객실, 공간, 캡션[ko,en,zh])
SEL = [
    ('hero',        'hewyum/hewyum_015.jpg', 'hewyum', 'living',  ['야경이 들어오는 3층 거실', 'The third-floor living room at night', '三樓客廳夜景']),

    ('h01', 'hewyum/hewyum_020.jpg', 'hewyum', 'living',  ['거실 · 다이닝 전경', 'Living room & dining, wide view', '客廳與餐桌全景']),
    ('h02', 'hewyum/hewyum_051.jpg', 'hewyum', 'jacuzzi', ['자쿠지에서 바라보는 광안대교', 'Gwangandaegyo bridge seen from the jacuzzi', '從按摩浴缸眺望廣安大橋']),
    ('h03', 'hewyum/hewyum_052.jpg', 'hewyum', 'jacuzzi', ['비치뷰 자쿠지', 'Beach-view jacuzzi', '海景按摩浴缸']),
    ('h04', 'hewyum/hewyum_050.jpg', 'hewyum', 'jacuzzi', ['자쿠지 · 오션뷰', 'Jacuzzi with an ocean view', '按摩浴缸・海景']),
    ('h05', 'hewyum/hewyum_018.jpg', 'hewyum', 'living',  ['밤바다가 보이는 거실', 'Living room with the night sea', '可看夜景的客廳']),
    ('h06', 'hewyum/hewyum_063.jpg', 'hewyum', 'kids',    ['키즈룸 · 붕붕카와 게임기', 'Kids’ room · ride-on cars & console', '兒童房・玩具車與遊戲機']),
    ('h07', 'hewyum/hewyum_064.jpg', 'hewyum', 'living',  ['100인치 빔 프로젝터', '100-inch projection screen', '100 吋投影螢幕']),
    ('h08', 'hewyum/hewyum_074.jpg', 'hewyum', 'bath',    ['욕실 · 세면대', 'Bathroom vanity', '衛浴・洗手台']),
    ('h09', 'hewyum/hewyum_081.jpg', 'hewyum', 'bed',     ['침실', 'Bedroom', '臥室']),
    ('h10', 'hewyum/hewyum_043.jpg', 'hewyum', 'detail',  ['수건 · 어메니티', 'Towels & amenities', '毛巾與備品']),
    ('h11', 'hewyum/hewyum_068.jpg', 'hewyum', 'detail',  ['광안리 해변 포토존', 'The beach photo spot in Gwangalli', '廣安里海灘拍照點']),

    ('o01', 'orot/orot_047.jpg', 'orot', 'jacuzzi', ['노을 진 6층 자쿠지', 'Sixth-floor jacuzzi at sunset', '夕陽下的六樓按摩浴缸']),
    ('o02', 'orot/orot_051.jpg', 'orot', 'jacuzzi', ['자쿠지 · 오션뷰', 'Jacuzzi with an ocean view', '按摩浴缸・海景']),
    ('o03', 'orot/orot_055.jpg', 'orot', 'jacuzzi', ['자쿠지와 바다', 'The jacuzzi and the sea', '按摩浴缸與海']),
    ('o04', 'orot/orot_058.jpg', 'orot', 'living',  ['거실에서 이어지는 자쿠지', 'The jacuzzi off the living room', '與客廳相連的按摩浴缸']),
    ('o05', 'orot/orot_061.jpg', 'orot', 'living',  ['거실 · 좌식공간', 'Living room · floor seating', '客廳・和室座位']),
    ('o06', 'orot/orot_035.jpg', 'orot', 'living',  ['거실 전경', 'Living room, wide view', '客廳全景']),
    ('o07', 'orot/orot_082.jpg', 'orot', 'kitchen', ['다이닝 · 오션뷰', 'Dining with an ocean view', '餐桌・海景']),
    ('o08', 'orot/orot_087.jpg', 'orot', 'living',  ['빔 프로젝터 · 야경', 'Projection screen at night', '投影螢幕・夜景']),
    ('o09', 'orot/orot_012.jpg', 'orot', 'bath',    ['욕실 · 세면대', 'Bathroom vanity', '衛浴・洗手台']),
    ('o10', 'orot/orot_096.jpg', 'orot', 'bed',     ['침실', 'Bedroom', '臥室']),
    ('o11', 'orot/orot_089.jpg', 'orot', 'bed',     ['침실 · 퀸베드', 'Bedroom · queen beds', '臥室・加大雙人床']),
    ('o12', 'orot/orot_109.jpg', 'orot', 'kids',    ['키즈룸', 'Kids’ room', '兒童房']),

    ('plan-hewyum', 'business/business_006.jpg', 'hewyum', 'plan', ['3층 헤윰 도면', 'Heyum 3F floor plan', '三樓 헤윰 平面圖']),
    ('plan-orot',   'business/business_005.jpg', 'orot',   'plan', ['6층 오롯 도면', 'Orot 6F floor plan', '六樓 오롯 平面圖']),
]

MAX = 1600
meta = []
for name, rel, room, space, cap in SEL:
    p = os.path.join(SRC, rel)
    if not os.path.exists(p):
        stem = os.path.splitext(p)[0]
        for ext in ('.png', '.jpg', '.jpeg', '.PNG', '.JPG'):
            if os.path.exists(stem + ext):
                p = stem + ext
                break
    im = Image.open(p)
    im = im.convert('RGB')
    w, h = im.size
    if max(w, h) > MAX:
        s = MAX / max(w, h)
        im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    out = os.path.join(OUT, name + '.webp')
    q = 85
    im.save(out, 'WEBP', quality=q, method=6)
    while os.path.getsize(out) > 320 * 1024 and q > 62:
        q -= 6
        im.save(out, 'WEBP', quality=q, method=6)
    meta.append({'file': name + '.webp', 'room': room, 'space': space, 'cap': cap,
                 'src': rel, 'w': im.width, 'h': im.height,
                 'kb': round(os.path.getsize(out) / 1024)})
    print(f'{name:12s} {rel:22s} {w}x{h} -> {im.width}x{im.height} {os.path.getsize(out)//1024}KB')

# 앱 아이콘 512x512 — 네이비 바탕 + 골드 이니셜
def icon(path):
    S = 512
    im = Image.new('RGB', (S, S), '#0A1926')
    d = ImageDraw.Draw(im)
    for y in range(S):
        t = y / S
        d.line([(0, y), (S, y)], fill=(int(10 + 8 * (1 - t)), int(25 + 17 * (1 - t)), int(38 + 24 * (1 - t))))
    d.rectangle([18, 18, S - 19, S - 19], outline='#C2A15C', width=3)
    kr = ImageFont.truetype('/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Regular.otf', 200)
    en = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf', 52)
    t1 = '능놀'
    bb = d.textbbox((0, 0), t1, font=kr)
    d.text(((S - (bb[2] - bb[0])) / 2 - bb[0], 120), t1, font=kr, fill='#C2A15C')
    t2 = 'NEUNGNOL STAY'
    bb2 = d.textbbox((0, 0), t2, font=en)
    d.text(((S - (bb2[2] - bb2[0])) / 2 - bb2[0], 345), t2, font=en, fill='#E3D9C6')
    im.save(path)
    print('icon', path)

icon(os.path.join(OUT, 'app-icon.png'))
json.dump(meta, open('/workspace/neungnolstay-site/assets/photos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('total', len(meta), 'images,', round(sum(m['kb'] for m in meta) / 1024, 1), 'MB')
