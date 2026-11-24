#!/usr/bin/env python3
"""
NEUNGNOL STAY · 네이버 예약 달력 동기화 (헤윰 3F · 오롯 6F)
------------------------------------------------------------------
네이버 예약(m.booking.naver.com)의 공개 GraphQL(schedule)을 로그인 없이
조회해 객실별 날짜의 '1박 요금 + 판매/마감 상태'를 naver-sync.json 으로 저장한다.

  python3 naver-sync.py                 # 오늘부터 180일, 두 객실
  python3 naver-sync.py --days 200
  python3 naver-sync.py --print
  python3 naver-sync.py --merge downloads/neungnol_stay/calendar.json
                                        # GraphQL 이 비어 있는 날짜를 수집본으로 보충

응답 필드 해석 (네이버 예약 달력과 동일)
  isBusinessDay false            -> 영업일 아님(마감)               => "sold"
  isSaleDay false                -> 판매중지(호스트가 닫음)          => "closed"
  stock <= bookingCount          -> 재고 소진(이미 예약됨)          => "sold"
  그 외                          -> 예약 가능                       => "open"
"""
import json, sys, time, urllib.request, datetime, argparse, os

BUSINESS_ID = '839642'
ROOMS = [
    {'key': 'hewyum', 'name': '능놀스테이: 헤윰', 'floor': '3층', 'item': '4848181'},
    {'key': 'orot',   'name': '능놀스테이: 오롯', 'floor': '6층', 'item': '4881823'},
]
GRAPHQL = 'https://m.booking.naver.com/graphql?opName=schedule'
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
QUERY = """query schedule($scheduleParams: ScheduleParams) {
  schedule(input: $scheduleParams) {
    bizItemSchedule { daily { date summary {
      dateKey minBookingCount maxBookingCount bookingCount stock
      isBusinessDay hasBusinessDays isSaleDay startTime endTime
      todayDealRate hasBookableSlots
      prices { groupName isDefault price priceId name normalPrice desc order }
    } } }
  }
}"""
KST = datetime.timezone(datetime.timedelta(hours=9))


def page_url(item):
    return f'https://m.booking.naver.com/booking/3/bizes/{BUSINESS_ID}/items/{item}'


def fetch(item, start, end):
    body = {
        "operationName": "schedule",
        "variables": {"scheduleParams": {
            "businessId": BUSINESS_ID, "bizItemId": item, "businessTypeId": 3,
            "startDateTime": start.strftime('%Y-%m-%d') + 'T00:00:00+09:00',
            "endDateTime": end.strftime('%Y-%m-%d') + 'T23:59:59+09:00',
            "partitionDays": 15,
        }},
        "query": QUERY,
    }
    req = urllib.request.Request(
        GRAPHQL, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'Referer': page_url(item), 'User-Agent': UA},
        method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def state_of(s):
    if not s.get('isBusinessDay'):
        return 'sold'
    if not s.get('isSaleDay'):
        return 'closed'
    stock = s.get('stock') or 0
    booked = s.get('bookingCount') or 0
    if stock and booked < stock:
        return 'open'
    return 'sold'


def scrape_room(room, days=180, verbose=False):
    today = datetime.datetime.now(KST).date()
    days_map = {}
    cur = today
    end_all = today + datetime.timedelta(days=days)
    while cur <= end_all:
        chunk_end = min(cur + datetime.timedelta(days=14), end_all)
        try:
            data = fetch(room['item'], cur, chunk_end)
        except Exception as e:
            print('WARN request failed', room['key'], cur, chunk_end, type(e).__name__, e, file=sys.stderr)
            cur = chunk_end + datetime.timedelta(days=1)
            time.sleep(1.0)
            continue
        daily = (((data or {}).get('data') or {}).get('schedule') or {}) \
            .get('bizItemSchedule', {}).get('daily', {}).get('date', {})
        for k, s in daily.items():
            prices = s.get('prices') or []
            price = prices[0].get('price') if prices else None
            days_map[k] = [price, state_of(s)]
            if verbose:
                print(room['key'], k, days_map[k], 'sale', s.get('isSaleDay'),
                      'biz', s.get('isBusinessDay'), 'stock', s.get('stock'), 'booked', s.get('bookingCount'))
        cur = chunk_end + datetime.timedelta(days=1)
        time.sleep(0.3)
    return dict(sorted(days_map.items()))


def merge_collected(days_map, path, key):
    """GraphQL 응답이 비어 있거나 요금이 없는 날짜를 수집본(calendar.json)으로 보충."""
    if not path or not os.path.exists(path):
        return 0
    try:
        cal = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        print('WARN merge read failed', e, file=sys.stderr)
        return 0
    rooms = cal.get('rooms') or cal
    src = None
    if isinstance(rooms, dict):
        src = rooms.get(key) or rooms.get(key.replace('orot', 'orot')) or None
    if isinstance(src, dict):
        src = src.get('days')
    if not isinstance(src, dict):
        return 0
    added = 0
    for d, v in src.items():
        if not isinstance(v, dict):
            continue
        price = v.get('price')
        state = v.get('status') or v.get('state')
        if state in ('open', 'closed', 'sold'):
            st = state
        elif v.get('available') is True:
            st = 'open'
        elif v.get('available') is False:
            st = 'sold'
        else:
            continue
        cur = days_map.get(d)
        if cur is None or cur[0] is None:
            if cur is not None and cur[1] == 'open' and st != 'open':
                continue
            days_map[d] = [price if price is not None else (cur[0] if cur else None), st]
            added += 1
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=180)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'naver-sync.json'))
    ap.add_argument('--print', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--merge', default='', help='fallback calendar.json path')
    a = ap.parse_args()

    out = {
        'source': f'https://m.booking.naver.com/booking/3/bizes/{BUSINESS_ID}/search',
        'api': 'm.booking.naver.com/graphql opName=schedule',
        'businessId': BUSINESS_ID,
        'updatedAt': datetime.datetime.now(KST).isoformat(timespec='seconds'),
        'timezone': 'Asia/Seoul',
        'rooms': {},
    }
    for room in ROOMS:
        days_map = scrape_room(room, a.days, a.verbose)
        if a.merge:
            n = merge_collected(days_map, a.merge, room['key'])
            if n:
                print(f'merged {n} days from calendar.json for {room["key"]}')
        open_days = [d for d, v in days_map.items() if v[1] == 'open']
        out['rooms'][room['key']] = {
            'name': room['name'], 'floor': room['floor'], 'item': room['item'],
            'bookingUrl': page_url(room['item']),
            'openUntil': max(open_days, default=None),
            'openCount': len(open_days),
            'days': days_map,
        }
        print(f'{room["key"]}: {len(days_map)} days · open {len(open_days)} · openUntil {max(open_days, default=None)}')

    if a.print:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f'saved {a.out} · updatedAt {out["updatedAt"]}')


if __name__ == '__main__':
    main()
