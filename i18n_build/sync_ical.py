#!/usr/bin/env python3
"""에어비앤비 iCal 캘린더 → Firebase RTDB 예약 차단(blocks) 동기화.

두 객실의 에어비앤비 iCal(비공개 주소)에서 예약·차단 기간을 읽어
`/neungnol_booking_v1/blocks/{heyum|orot}/{YYYY-MM-DD}` 에 `source: "airbnb"` 로 기록한다.
관리자 화면(/admin/) 달력에서 에어비앤비 예약은 파란색(#0077FF)으로 표시된다.

규칙
  · 이미 확정된 예약(홈페이지 직접 예약·네이버 예약 등)이 덮는 날짜는 건드리지 않는다.
  · 이 스크립트가 만든 `source: "airbnb"` 항목만 갱신·삭제한다.
    (관리자가 넣은 네이버/기타 차단은 그대로 둔다.)
  · iCal 주소에는 비공개 토큰이 들어 있으므로 공개 사이트(HTML/JS)에 넣지 않는다.
    이 파일과 로컬 설정에만 둔다.

사용
    python3 i18n_build/sync_ical.py                 # 내려받아 Firebase 에 반영
    python3 i18n_build/sync_ical.py --dry-run       # 반영 없이 결과만 확인
    python3 i18n_build/sync_ical.py --days 365      # 오늘부터 이 기간만 반영/정리
    python3 i18n_build/sync_ical.py --print-ics     # iCal 주소 확인(토큰 포함, 화면에만)

정기 실행은 이 스크립트를 하루 1~2회 돌리면 된다(로컬 cron·예약 작업·GitHub Actions).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DB = "https://neungnol-checklist-default-rtdb.asia-southeast1.firebasedatabase.app"
PATH = "/neungnol_booking_v1"
ROOMS = ("heyum", "orot")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; neungnolstay-ical-sync/1.0)"

# 비공개 iCal 주소 — 여기(와 로컬 실행 환경)에만 둔다. 사이트 코드에는 절대 넣지 않는다.
ICAL = {
    "heyum": "https://www.airbnb.com/calendar/ical/827083520643586714.ics"
             "?t=e8d5e792d4164015a9f5eb5538c90678&locale=ko",
    "orot": "https://www.airbnb.com/calendar/ical/842458938331176391.ics"
            "?t=7b065a2418a840c7b22e73b1abda2ed9&locale=ko",
}
# 관리자 화면에는 토큰을 뺀 주소만 보여 준다.
ICAL_PUBLIC = {
    "heyum": "airbnb.com/calendar/ical/827083520643586714.ics",
    "orot": "airbnb.com/calendar/ical/842458938331176391.ics",
}


# ---------------------------------------------------------------------------
# iCal
# ---------------------------------------------------------------------------
def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/calendar,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def unfold(text: str) -> str:
    """RFC5545 줄바꿈(CRLF + 공백) 이어붙이기."""
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n"))


def parse_ymd(value: str) -> date | None:
    v = value.strip()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", v)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def parse_events(ics: str) -> list[dict]:
    text = unfold(ics)
    events = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        ds = re.search(r"DTSTART[^:\n]*:([^\n]+)", block)
        de = re.search(r"DTEND[^:\n]*:([^\n]+)", block)
        if not ds:
            continue
        start = parse_ymd(ds.group(1))
        end = parse_ymd(de.group(1)) if de else None
        if not start:
            continue
        if not end or end <= start:
            end = start + timedelta(days=1)
        summary = ""
        m = re.search(r"SUMMARY:(.*)", block)
        if m:
            summary += m.group(1).strip()
        uid = ""
        m = re.search(r"UID:(.*)", block)
        if m:
            uid += m.group(1).strip()
        # 숙박일 = DTSTART ~ DTEND 전날
        nights = []
        d = start
        while d < end:
            nights.append(d)
            d += timedelta(days=1)
        events.append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "nights": [n.isoformat() for n in nights],
            "summary": summary,
            "uid": uid,
        })
    return events


# ---------------------------------------------------------------------------
# Firebase (RTDB REST)
# ---------------------------------------------------------------------------
def db_get(path: str = ""):
    url = f"{DB}{PATH}{path}.json"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as ex:  # noqa: PERF203
        raise SystemExit(f"[firebase] GET {path} → HTTP {ex.code}") from ex


def db_patch(payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{DB}{PATH}.json", data=data, method="PATCH",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


# ---------------------------------------------------------------------------
# 동기화
# ---------------------------------------------------------------------------
def protected_dates(bookings: dict) -> dict[str, set[str]]:
    """확정된 예약이 덮는 날짜 — 어떤 경우에도 차단을 지우거나 바꾸지 않는다."""
    out: dict[str, set[str]] = {r: set() for r in ROOMS}
    for bk in (bookings or {}).values():
        if not isinstance(bk, dict):
            continue
        room = bk.get("room")
        if room not in out:
            continue
        if bk.get("status") != "confirmed":
            continue
        d = parse_ymd(str(bk.get("checkin", "")))
        end = parse_ymd(str(bk.get("checkout", "")))
        if not d or not end:
            continue
        while d < end:
            out[room].add(d.isoformat())
            d += timedelta(days=1)
    return out


def sync(dry_run: bool = False, days: int = 0) -> dict:
    blocks = db_get("/blocks") or {}
    bookings = db_get("/bookings") or {}
    guard = protected_dates(bookings)
    today = datetime.now(KST).date()
    limit = today + timedelta(days=days) if days else None
    now_ms = int(datetime.now(KST).timestamp() * 1000)

    updates: dict[str, object] = {}
    report = {"syncedAt": now_ms, "rooms": {}}

    for room in ROOMS:
        try:
            ics = fetch(ICAL[room])
        except Exception as ex:  # noqa: BLE001
            report["rooms"][room] = {"error": f"{type(ex).__name__}: {ex}"}
            continue
        events = parse_events(ics)

        wanted: dict[str, dict] = {}
        for ev in events:
            for ds in ev["nights"]:
                d = parse_ymd(ds)
                if d and limit and (d > limit or d < today - timedelta(days=1)):
                    continue
                if ds in guard[room]:
                    continue
                wanted[ds] = {
                    "source": "airbnb",
                    "reason": "ical",
                    "summary": ev["summary"][:60],
                    "updatedAt": now_ms,
                }

        existing = blocks.get(room) or {}
        removed = []
        for ds, entry in existing.items():
            src = (entry or {}).get("source") if isinstance(entry, dict) else None
            auto = isinstance(entry, dict) and entry.get("reason") == "ical"
            if src != "airbnb" and not auto:
                continue  # 네이버·기타·수동 차단은 보존
            if ds in wanted:
                continue
            if limit and parse_ymd(ds) and parse_ymd(ds) > limit:
                continue
            removed.append(ds)
            updates[f"/blocks/{room}/{ds}"] = None

        added = []
        for ds, payload in wanted.items():
            cur = existing.get(ds)
            if isinstance(cur, dict) and cur.get("source") == payload["source"] \
                    and cur.get("reason") == payload["reason"] \
                    and cur.get("summary") == payload["summary"]:
                continue  # 이미 최신
            added.append(ds)
            updates[f"/blocks/{room}/{ds}"] = payload

        report["rooms"][room] = {
            "events": len(events),
            "nights": len(wanted),
            "added": len(added),
            "removed": len(removed),
            "keptExisting": len([ds for ds in wanted if ds in existing and ds not in added]),
            "first": min(wanted) if wanted else None,
            "last": max(wanted) if wanted else None,
            "ical": ICAL_PUBLIC[room],
        }

    settings = db_get("/settings") or {}
    prev = (settings.get("icalSync") or {}) if isinstance(settings, dict) else {}
    report["note"] = ("에어비앤비 iCal 자동 동기화. 확정된 직접·네이버 예약 날짜는 건드리지 않는다. "
                      "iCal 주소(토큰 포함)는 공개 사이트에 넣지 않는다.")
    report["icalPublic"] = ICAL_PUBLIC
    report["prevSyncedAt"] = (prev or {}).get("syncedAt")

    payload = dict(updates)
    payload["/settings/icalSync"] = {
        "syncedAt": now_ms,
        "syncedAtText": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "rooms": {r: {k: v for k, v in (report["rooms"][r] or {}).items()} for r in ROOMS},
        "icalPublic": ICAL_PUBLIC,
        "note": report["note"],
    }
    if dry_run:
        report["dryRun"] = True
        report["changes"] = {k: v for k, v in updates.items()}
        return report
    db_patch(payload)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="에어비앤비 iCal → Firebase 예약 차단 동기화")
    ap.add_argument("--dry-run", action="store_true", help="Firebase 에 쓰지 않고 결과만 출력")
    ap.add_argument("--days", type=int, default=0, help="오늘부터 N일까지만 반영/정리 (기본: 전체)")
    ap.add_argument("--print-ics", action="store_true", help="iCal 주소(토큰 포함) 출력")
    args = ap.parse_args()

    if args.print_ics:
        for room, url in ICAL.items():
            print(f"{room}: {url}")
        return

    report = sync(dry_run=args.dry_run, days=args.days)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any((report["rooms"].get(r) or {}).get("error") for r in ROOMS):
        sys.exit(1)


if __name__ == "__main__":
    main()
