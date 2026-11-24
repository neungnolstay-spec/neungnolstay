#!/usr/bin/env python3
"""에어비앤비 원본에서 사이트 갤러리용 webp 를 만든다.

    python3 i18n_build/make_gallery.py

원본: downloads/neungnol_stay/airbnb_raw/{heyum,orot}_media_dl.json + {heyum,orot}_img/
출력: assets/gallery/{room}/{slug}.webp  (긴 변 최대 1600px)
      assets/gallery/{room}/{slug}-t.webp (긴 변 최대 900px, 그리드용)
      assets/gallery/manifest.json (파일별 실제 픽셀 크기)
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import gallery_map

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT.parent / "downloads" / "neungnol_stay" / "airbnb_raw"
OUT = ROOT / "assets" / "gallery"

FULL_MAX = 1600
THUMB_MAX = 900


def src_path(room: str, idx: int) -> Path:
    items = json.loads((RAW / f"{room}_media_dl.json").read_text(encoding="utf-8"))
    it = items[idx]
    ext = it["file"].split(".")[-1]
    return RAW / f"{room}_img" / f"{idx:03d}_{it['file'].split('.')[0][:8]}.{ext}"


def fit(im: Image.Image, max_side: int) -> Image.Image:
    w, h = im.size
    scale = min(1.0, max_side / max(w, h))
    if scale >= 1.0:
        return im
    return im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


def main() -> None:
    manifest: dict[str, list[dict]] = {}
    for room, entries in gallery_map.ROOMS.items():
        outdir = OUT / room
        outdir.mkdir(parents=True, exist_ok=True)
        rows = []
        for ent in entries:
            src = src_path(room, ent["src"])
            im = Image.open(src).convert("RGB")
            full = fit(im, FULL_MAX)
            full.save(outdir / f"{ent['slug']}.webp", "WEBP", quality=84, method=6)
            thumb = fit(im, THUMB_MAX)
            thumb.save(outdir / f"{ent['slug']}-t.webp", "WEBP", quality=78, method=6)
            rows.append({
                "slug": ent["slug"], "cat": ent["cat"], "tone": ent["tone"],
                "ko": ent["ko"], "en": ent["en"],
                "w": full.size[0], "h": full.size[1],
                "tw": thumb.size[0], "th": thumb.size[1],
            })
            print(f"{room:6s} {ent['slug']:22s} {full.size[0]}x{full.size[1]}")
        manifest[room] = rows

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in manifest.values())
    size = sum(p.stat().st_size for p in OUT.rglob("*.webp")) / 1024 / 1024
    print(f"\n{total}장 → {OUT} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
