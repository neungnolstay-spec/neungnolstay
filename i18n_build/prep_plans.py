#!/usr/bin/env python3
"""도면(평면도) 이미지 전처리: 원본에서 빈 여백을 잘라내고 웹용 webp로 만든다.

네이버 플레이스 '업체' 사진의 도면 원본은 4687×4687 정사각형이지만, 실제 도면은
가운데 가로 띠(약 1288×959 / 1600 기준)에만 그려져 있고 위아래는 빈 회색 여백이다.
그대로 쓰면 페이지에서 도면이 작게 보이므로, 내용 경계만 남기고 잘라
`assets/plan-hewyum.webp` · `assets/plan-orot.webp` 를 다시 만든다.

    python3 i18n_build/prep_plans.py

원본: /workspace/downloads/neungnol_stay/photos/business/business_006.jpg (헤윰 3층)
      /workspace/downloads/neungnol_stay/photos/business/business_005.jpg (오롯 6층)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = Path("/workspace/downloads/neungnol_stay/photos/business")
OUT_DIR = ROOT / "assets"

JOBS = {
    "plan-hewyum.webp": "business_006.jpg",   # 헤윰 3층
    "plan-orot.webp": "business_005.jpg",     # 오롯 6층
}

TARGET_W = 2200        # 웹 표시·확대용 가로 픽셀
PAD_RATIO = 0.02       # 내용 경계 바깥으로 남길 여백(가로 기준 비율)
BACKGROUND_CUT = 220   # 이 밝기보다 어두운 픽셀을 내용으로 본다


def content_box(im: Image.Image) -> tuple[int, int, int, int]:
    g = im.convert("L")
    w, h = g.size
    px = g.load()
    # 빠르게 훑기 위해 4픽셀 간격으로 표본을 본다.
    step = max(1, w // 900)
    rows = [y for y in range(0, h, step) if any(px[x, y] < BACKGROUND_CUT for x in range(0, w, step))]
    cols = [x for x in range(0, w, step) if any(px[x, y] < BACKGROUND_CUT for y in range(0, h, step))]
    if not rows or not cols:
        return 0, 0, w, h
    return cols[0], rows[0], cols[-1] + 1, rows[-1] + 1


def main() -> None:
    for out_name, src_name in JOBS.items():
        src = SRC_DIR / src_name
        if not src.exists():
            sys.exit(f"missing source: {src}")
        im = Image.open(src).convert("RGB")
        orig_size = im.size
        box = content_box(im)
        pad = round((box[2] - box[0]) * PAD_RATIO)
        x0 = max(0, box[0] - pad)
        y0 = max(0, box[1] - pad)
        x1 = min(im.width, box[2] + pad)
        y1 = min(im.height, box[3] + pad)
        crop = im.crop((x0, y0, x1, y1))
        if crop.width > TARGET_W:
            crop = crop.resize((TARGET_W, round(crop.height * TARGET_W / crop.width)), Image.LANCZOS)
        out = OUT_DIR / out_name
        crop.save(out, "WEBP", quality=86, method=6)
        print(f"{out_name}: {orig_size} -> crop {x1 - x0}x{y1 - y0} -> {crop.size} "
              f"({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
