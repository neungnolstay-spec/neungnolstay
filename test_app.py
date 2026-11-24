#!/usr/bin/env python3
"""app.js 런타임 점검 — 최소 DOM 스텁으로 실제 함수를 그대로 실행해 본다.
(레이아웃 검증이 아니라, 로드 시 예외·계산 결과·객실 전환 동작을 확인하는 용도)"""
import json, os, re, sys
import quickjs

BASE = os.path.dirname(os.path.abspath(__file__))

PRELUDE = r"""
var __els = {};
function El(id){
  this.id = id; this._html=''; this._text=''; this.value=''; this.min=''; this.max='';
  this.style={}; this.dataset={}; this.attrs={};
  this.classList={ _s:new Set(), add:function(){for(var i=0;i<arguments.length;i++)this._s.add(arguments[i]);},
    remove:function(){for(var i=0;i<arguments.length;i++)this._s.delete(arguments[i]);},
    contains:function(c){return this._s.has(c);},
    toggle:function(c,f){ if(f===undefined) f=!this._s.has(c); if(f) this._s.add(c); else this._s.delete(c); } };
}
El.prototype.__defineGetter__('innerHTML', function(){ return this._html; });
El.prototype.__defineSetter__('innerHTML', function(v){ this._html = String(v); });
El.prototype.__defineSetter__('textContent', function(v){ this._text = String(v); });
El.prototype.__defineGetter__('textContent', function(){ return this._text; });
El.prototype.insertAdjacentHTML = function(pos, html){ this._html = html + this._html; };
El.prototype.closest = function(){ return null; };
El.prototype.querySelector = function(){ return null; };
El.prototype.querySelectorAll = function(){ return []; };
El.prototype.setAttribute = function(k,v){ this.attrs[k]=v; };
El.prototype.getAttribute = function(k){ return this.attrs[k]; };
El.prototype.scrollIntoView = function(){};
El.prototype.remove = function(){};
El.prototype.focus = function(){};

var NodeFilter = { SHOW_TEXT: 4 };
var document = {
  body: new El('body'),
  documentElement: {},
  title: '',
  getElementById: function(id){ if(!__els[id]) __els[id]=new El(id); return __els[id]; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; },
  createTreeWalker: function(){ return { nextNode: function(){ return false; } }; },
  addEventListener: function(){},
  createElement: function(){ return new El('tmp'); }
};
var localStorage = { getItem: function(){ return null; }, setItem: function(){} };
var history = { state:null, pushState:function(){}, replaceState:function(){}, go:function(){} };
var location = { href:'https://example.test/' };
var navigator = {};
function fetch(){ return Promise.reject(new Error('no network in test')); }
var __intervals = [];
function setInterval(fn, ms){ __intervals.push(ms); return 1; }
function clearInterval(){}
function setTimeout(fn, ms){ if (ms === 0) { try{ fn(); }catch(e){} } return 1; }
function clearTimeout(){}
var window = this;
window.addEventListener = function(){};
window.__setIntervalCount = function(){ return __intervals.length; };
"""

def run():
    q = quickjs.Context()
    q.eval(PRELUDE)
    q.eval(open(os.path.join(BASE, 'site-data.js'), encoding='utf-8').read())
    q.eval(open(os.path.join(BASE, 'app.js'), encoding='utf-8').read())

    def ev(expr):
        return q.eval(expr)

    checks = []
    def check(name, got, want=None, contains=None):
        ok = (got == want) if want is not None else (contains in str(got))
        checks.append((ok, name, got))

    # 초기 렌더
    
    cal1 = ev("document.getElementById('cal1').innerHTML")
    checks.append((len(cal1) > 500, '달력 HTML 길이', len(cal1)))
    checks.append(("open" in cal1, '달력에 예약가능 클래스', cal1.count('class="d open')))
    check('오늘(TODAY)', ev("TODAY"), '2026-11-22')
    check('초기 객실', ev("ST.room"), 'hewyum')
    check('히어로 체크인 표기', ev("document.getElementById('heroCheck').textContent"), '3층 헤윰 15:00 / 11:00')

    # 요금/상태
    check('헤윰 12/01 상태', ev("stateOf('2026-12-01')"), 'open')
    check('헤윰 12/01 요금', ev("priceOf('2026-12-01')"), 500000)
    check('헤윰 12/11 마감', ev("stateOf('2026-12-11')"), 'closed')
    check('오롯 12/12 sold', ev("stateOf('2026-12-12','orot')"), 'sold')
    check('오롯 12/11 open', ev("stateOf('2026-12-11','orot')"), 'open')
    check('지난 날짜', ev("stateOf('2026-11-01')"), 'past')

    # 견적: 12/1~12/3 2박
    ev("setRoom('hewyum')")
    ev("pickDate('2026-12-01')")
    ev("pickDate('2026-12-03')")
    check('2박 합계', ev("document.getElementById('qTotal').textContent").replace(',',''), '950000원')
    check('숙박 라벨', ev("document.getElementById('selNights').textContent"), '2박')
    check('예약 버튼 활성', ev("document.getElementById('qBtn').disabled"), False)

    # 인원 추가 (9인 · 2박 → 1×30000×2 = 60,000)
    ev("stepGuest('adults',1)")
    check('9인 2박 합계', ev("document.getElementById('qTotal').textContent").replace(',',''), '1010000원')
    ev("stepGuest('adults',-1)")

    # 객실 전환
    ev("setRoom('orot')")
    check('오롯 전환 후 히어로', ev("document.getElementById('heroCheck').textContent"), '6층 오롯 16:00 / 12:00')
    check('오롯 전환 후 달력 요금', ev("priceOf('2026-12-01')"), 500000)
    panel = ev("document.getElementById('roomPanel').innerHTML")
    checks.append(('오롯 6F' in panel or '오롯' in panel, '객실 패널 렌더', len(panel)))
    checks.append(('4881823' in panel or 'booking.naver.com' in panel, '객실 패널 예약 링크', 'ok'))

    # 다국어
    ev("setLang('en')")
    check('영어 히어로', ev("document.getElementById('heroCheck').textContent"), '6th floor Orot 16:00 / 12:00')
    check('영어 합계 표기', ev("document.getElementById('qTotal').textContent").replace(',',''), '₩950000')
    ev("setLang('ko')")

    # 갤러리 · 후기 · 하단 바
    gal = ev("document.getElementById('galMosaic').innerHTML")
    checks.append((gal.count('<img') == 5, '갤러리 모자이크 5장', gal.count('<img')))
    rev = ev("document.getElementById('revGrid').innerHTML")
    checks.append((rev.count('class="rev"') == 3, '후기 카드 3개', rev.count('class="rev"')))
    check('하단 바 금액', ev("document.getElementById('bbPrice').textContent").replace(',',''), '950000원')

    # 예약 안내 모달
    ev("startBooking()")
    pane = ev("document.getElementById('bkPane').innerHTML")
    checks.append(('4881823' in pane, '모달에 오롯 네이버 예약 링크', 'booking' in pane))
    checks.append(('talk.naver.com' in pane and 'tel:050714292309' in pane, '톡톡·전화 링크', 'ok'))

    # 예약 불가 날짜가 낀 구간
    ev("ST.in='2026-11-24'; ST.out='2026-11-26'; renderQuote()")
    check('차단 구간 버튼 비활성', ev("document.getElementById('qBtn').disabled"), True)
    body = ev("document.getElementById('qBody').innerHTML")
    checks.append(('11월 24일' in body, '차단 안내 문구', body[:80]))


    # 중국어 전환
    ev("setLang('zh')")
    check('중국어 히어로', ev("document.getElementById('heroCheck').textContent"), '6樓 오롯 16:00 / 12:00')
    ev("setLang('ko')")

    # 라이트박스 · 카테고리
    ev("openLightbox('hewyum')")
    lb = ev("document.getElementById('lbGrid').innerHTML")
    checks.append((lb.count('<img') == 13, '헤윰 필터 13장(히어로·도면 포함)', lb.count('<img')))
    ev("openLightbox('plan')")
    lb2 = ev("document.getElementById('lbGrid').innerHTML")
    checks.append((lb2.count('<img') == 2, '도면 필터 2장', lb2.count('<img')))
    ev("openLightbox('all')")
    lb3 = ev("document.getElementById('lbGrid').innerHTML")
    checks.append((lb3.count('<img') == 26, '전체 26장', lb3.count('<img')))
    ev("openViewer(0)")
    cap = ev("document.getElementById('viewerCap').textContent")
    checks.append((len(cap) > 3, '뷰어 캡션', cap))

    # 실시간 동기화 적용 경로
    sample = '{"updatedAt":"2026-11-22T11:00:00+09:00","rooms":{"hewyum":{"openUntil":"2027-02-28","days":{"2026-12-01":[520000,"open"]}}}}'
    check('applySync 변경 수', ev("applySync(" + sample + ")"), 1)
    check('동기화 후 요금 반영', ev("priceOf('2026-12-01','hewyum')"), 520000)

    ok = True
    for good, name, got in checks:
        print(('PASS' if good else 'FAIL'), name, '::', got)
        ok = ok and good
    print('\n결과:', 'ALL PASS' if ok else 'FAIL 있음')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(run())
