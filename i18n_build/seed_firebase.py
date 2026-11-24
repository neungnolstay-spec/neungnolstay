#!/usr/bin/env python3
"""Firebase 초기 시드: 게스트 후기 + 네이버 플레이스 실판매 요금.

    python3 i18n_build/seed_firebase.py              # 후기(비어 있을 때만) + 요금(항상 최신)
    python3 i18n_build/seed_firebase.py --reviews    # 후기만
    python3 i18n_build/seed_firebase.py --rates      # 요금만
    python3 i18n_build/seed_firebase.py --dry-run    # 쓰지 않고 확인

- 후기: content/ko.py 의 객실별 게스트 후기 6건씩 → /neungnol_booking_v1/reviews/{room}
        이미 리뷰가 하나라도 있으면 건너뛴다(중복 시드 방지).
- 요금: naver-sync.json(네이버 예약 180일 실판매 요금) → /neungnol_booking_v1/settings/naverRates
        홈페이지·관리자 달력에서 기본 요금보다 우선 적용된다. (예약 마감은 반영하지 않는다.)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB = "https://neungnol-checklist-default-rtdb.asia-southeast1.firebasedatabase.app"
PATH = "/neungnol_booking_v1"
ROOMS = ("heyum", "orot")
KST = timezone(timedelta(hours=9))

sys.path.insert(0, str(HERE))
from content import ko  # noqa: E402


def db_get(path: str):
    import urllib.request
    with urllib.request.urlopen(f"{DB}{PATH}{path}.json", timeout=30) as r:
        return json.load(r)


def db_patch(payload: dict) -> None:
    import urllib.request
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{DB}{PATH}.json", data=data, method="PATCH",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def seed_reviews(dry: bool) -> dict:
    existing = db_get("/reviews") or {}
    out = {}
    for room in ROOMS:
        if existing.get(room):
            out[room] = {"skipped": True, "existing": len(existing[room])}
            continue
        reviews = ko.T["rooms"][room]["reviews"]
        base = int(datetime.now(KST).timestamp() * 1000)
        payload = {}
        for i, rv in enumerate(reviews):
            payload[f"seed{i + 1:02d}"] = {
                "name": rv["name"],
                "rating": int(rv["rating"]),
                "text": rv["text"],
                "textKo": rv["text"],
                "lang": "ko",
                "source": "seed",
                "createdAt": base - (len(reviews) - i) * 86400000,
            }
        out[room] = {"seeded": len(payload)}
        if not dry:
            db_patch({f"/reviews/{room}": payload})
    return out


def seed_rates(dry: bool) -> dict:
    src = ROOT / "naver-sync.json"
    if not src.exists():
        raise SystemExit("naver-sync.json 이 없습니다. 먼저 naver-sync.py 를 실행해 주세요.")
    data = json.loads(src.read_text(encoding="utf-8"))
    today = datetime.now(KST).date()
    rates: dict[str, dict[str, int]] = {r: {} for r in ROOMS}
    for room, key in (("heyum", "hewyum"), ("orot", "orot")):
        for ds, pair in (data["rooms"][key].get("days") or {}).items():
            price = pair[0] if isinstance(pair, list) and pair else None
            if not price:
                continue
            try:
                d = datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                continue
            if d < today:
                continue
            rates[room][ds] = int(price)
    stamp = str(data.get("updatedAt", ""))[:16].replace("T", " ")
    out = {r: {"dates": len(rates[r]), "updatedAt": stamp} for r in ROOMS}
    if not dry:
        db_patch({
            "/settings/naverRates": rates,
            "/settings/naverRatesUpdatedAt": (stamp + " 기준") if stamp else "",
            "/settings/naverRatesSource": "네이버 예약 180일 실판매 요금",
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews", action="store_true")
    ap.add_argument("--rates", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    both = not args.reviews and not args.rates
    if args.reviews or both:
        print("reviews:", json.dumps(seed_reviews(args.dry_run), ensure_ascii=False))
    if args.rates or both:
        print("rates:", json.dumps(seed_rates(args.dry_run), ensure_ascii=False))


if __name__ == "__main__":
    main()
