#!/usr/bin/env python3
"""naver-sync.json + assets/photos.json -> site-data.js (사이트가 바로 읽는 내장 데이터)"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
sync = json.load(open(os.path.join(BASE, 'naver-sync.json'), encoding='utf-8'))
photos = json.load(open(os.path.join(BASE, 'assets', 'photos.json'), encoding='utf-8'))

days = {}
for key, room in sync['rooms'].items():
    days[key] = {
        'openUntil': room.get('openUntil'),
        'days': room['days'],
    }

out = [
    '/* 능놀스테이 사이트 데이터 — naver-sync.py 가 만든 naver-sync.json 에서 자동 생성 */',
    'window.NAVER_DATA = ' + json.dumps({
        'updatedAt': sync.get('updatedAt'),
        'businessId': sync.get('businessId'),
        'rooms': days,
    }, ensure_ascii=False, separators=(',', ':')) + ';',
    '',
    'window.PHOTOS = ' + json.dumps([
        {'f': p['file'], 'room': p['room'], 'space': p['space'], 'cap': p['cap']} for p in photos
    ], ensure_ascii=False, separators=(',', ':')) + ';',
    '',
]
path = os.path.join(BASE, 'site-data.js')
open(path, 'w', encoding='utf-8').write('\n'.join(out))
print('wrote', path, round(os.path.getsize(path) / 1024, 1), 'KB')
