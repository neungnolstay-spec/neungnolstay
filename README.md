# NEUNGNOL STAY · 능놀스테이 홈페이지

## 글로벌 다국어 SEO 사이트 (`docs/`) — 현재 배포 대상

부산 광안리 **능놀스테이**의 공식 글로벌 사이트입니다. 한국어 · English · 日本語 · 简体中文 · 繁體中文
5개 언어, 객실별(헤윰 3층 / 오롯 6층) 독립 페이지, 검색엔진 크롤링이 가능한 정적 멀티페이지 구조입니다.

- 생성기·문구·검증 스크립트: [`i18n_build/`](i18n_build/README.md)
- 결과물: `docs/` (직접 수정 금지 — 빌드로 생성)
- 배포: GitHub Pages 소스 **main / docs** (`./deploy.sh`)

```bash
python3 i18n_build/build.py       # docs/ 재생성
python3 i18n_build/check.py       # 16페이지 + /admin/ 전수 검증(SEO·렌더링·예약·리뷰·문의·번역·출처 색상)
python3 i18n_build/check.py --phase 1   # (느린 환경) 단계별 실행: 1 정적 / 2 렌더링 / 3 관리자·e2e
```

### 전용 홈페이지 기능 (외부 플랫폼 링크 없음)

능놀스테이만의 홈페이지로 운영합니다. 에어비앤비·네이버 플레이스/톡톡 링크와 문구는 사이트 어디에도 없고,
예약·리뷰·문의가 모두 이 사이트 안에서 끝납니다.

| 기능 | 위치 | 설명 |
|---|---|---|
| 사진 갤러리 | `/{lang}/{room}/#gallery` | 실제 객실 사진을 큐레이션(헤윰 38장·오롯 33장). 분류 필터 + 풀스크린 라이트박스 |
| 직접 예약 | `/{lang}/{room}/#reserve`, `/{lang}/#reserve` | 2개월 실시간 달력(확정·차단 날짜 비활성), 인원, 날짜별 실제 요금 합계, **무료 비품·유아용품 요청 7종**, 예약 신청 |
| 예약 승인제 | `/admin/` 예약 탭 | 신청은 `pending`(승인 대기)으로 저장 → 사장님이 `예약 확정`을 눌러야 `confirmed`가 되고 달력이 마감됩니다 |
| 게스트 후기 | `/{lang}/{room}/#reviews` | Firebase 실시간 목록 + 고객이 직접 쓰는 후기 폼(이름·별점·내용). 관리자가 지우면 홈페이지에서 즉시 사라집니다 |
| 문의 게시판 | `/{lang}/#inquiry`, `/{lang}/{room}/#inquiry` | 고객이 이름·연락처(선택)·내용을 남기면 공개 목록에 표시, 관리자 답변 표시. **양방향 자동 번역**(외국어 문의→한국어, 한국어 답변→고객 언어) |
| 관리 화면 | `/admin/` | PIN 잠금(초기 `0000`) · 예약 달력 · 예약 · 리뷰 · 문의 · 요금 · 설정 |
| 데이터 | Firebase RTDB `/neungnol_booking_v1` | 직원 체크리스트(`/neungnol_v1`)와 완전히 분리 |

- 예약 데이터: `settings`(요금·PIN) · `settings/naverRates/{room}/{date}`(네이버 실판매 요금) ·
  `settings/overrides/{room}/{date}`(관리자가 달력에서 지정한 날짜 요금) · `settings/bank`(입금 계좌) ·
  `settings/checkinTemplates`(입실 안내문) · `blocks/{room}/{date}`(외부 예약·차단, `source`: naver·airbnb·other) ·
  `bookings/{id}`(신청·확정·취소, `amenitiesRequested` 비품 요청) · `reviews/{room}` · `inquiries`
- 요금 우선순위: 관리자 지정(`overrides`) → 네이버 실판매(`naverRates`) → 기본 평일/금/토.
  관리자 달력에서 날짜를 탭/드래그하면 그 날(구간)의 1박 요금을 바로 수정할 수 있고, 달력 칸과 고객 예약 합계에 즉시 반영됩니다.
- 예약 출처 색상: **네이버 초록 `#03C75A`** · **에어비앤비 파랑 `#0077FF`** · 직접 예약 차콜(확정)/앰버(대기) · 기타 차단 회색.

### 자동 동기화 스크립트

| 스크립트 | 역할 |
|---|---|
| `python3 i18n_build/sync_ical.py` | 에어비앤비 iCal(두 객실) → `blocks/{room}/{date}` 에 `source:"airbnb"`. 확정된 직접·네이버 예약 날짜는 건드리지 않고, 이 스크립트가 만든 airbnb 항목만 갱신·삭제. `--dry-run`·`--days N` 지원 |
| `python3 i18n_build/seed_firebase.py` | 초기 시드: 게스트 후기 6+6(비어 있을 때만) + 네이버 180일 실판매 요금(`settings/naverRates`) |
| `python3 naver-sync.py` | 네이버 예약 달력 180일 요금·마감 수집(→ `naver-sync.json`) |

- iCal 주소에는 비공개 토큰이 들어 있어 **공개 사이트(HTML/JS)와 Firebase에 넣지 않습니다.**
  `sync_ical.py` 안에만 두고, 관리자 화면에는 토큰을 뺀 주소와 마지막 동기화 시각만 표시합니다.
- 에어비앤비는 iCal을 서버/로컬에서 내려받아 반영합니다(브라우저에서 airbnb.com 직접 호출은 CORS로 막힘).
  GitHub Pages는 정적 호스팅이라 자체 실행이 불가하므로, 로컬 cron·예약 작업 또는 GitHub Actions로 하루 1~2회 `sync_ical.py`를 돌리면 됩니다.

URL 구조

```
/                  언어 선택(브라우저 언어 자동 감지)
/ko/ /en/ /ja/ /zh-cn/ /zh-tw/
/ko/heyum/  /ko/orot/   (각 언어 동일)
```

`BASE_URL`·GA4·GTM·Search Console·네이버 서치어드바이저 값은 `i18n_build/build.py` 상단 한 곳에서 관리합니다.
자체 도메인으로 옮길 때는 `BASE_URL` 한 줄만 바꾸면 canonical·hreflang·OG·sitemap이 함께 바뀝니다.

### AI 검색 최적화 (GEO/AEO)

ChatGPT·Perplexity·Gemini·Claude 같은 AI 검색이 능놀스테이를 정확히 찾아 인용하도록 아래 파일을 `build.py`가 함께 생성합니다.

| URL | 내용 |
|---|---|
| `/llms.txt` | AI용 짧은 사실 요약(주소·객실·특징·규정·평점·16페이지 목록·예약 링크·5개 언어 질문·키워드) |
| `/llms-full.txt` | 5개 언어 전체 상세(객실 사양·시설·이용 안내·FAQ·게스트 후기·키워드) |
| `/robots.txt` | GPTBot·OAI-SearchBot·ChatGPT-User·Google-Extended·PerplexityBot·ClaudeBot·anthropic-ai·Applebot-Extended·Bingbot 등 명시적 Allow |

- 16페이지 JSON-LD에 `LodgingBusiness`/`HotelRoom` + `FAQPage`(홈 10문항)를 넣고, `knowsLanguage`(ko·en·ja·zh-Hans·zh-Hant), `amenityFeature`(오션뷰·자쿠지·키즈룸·100인치 프로젝터·유아 하이체어·주차·세탁기 등), `sameAs`(인스타그램·구글 지도), `petsAllowed`/`smokingAllowed`(false), `floorSize`를 채웁니다.
- AI 검색용 자연어 질문·키워드는 `i18n_build/content/geo.py` 한 곳에 5개 언어로 모여 있습니다.
- 연박 할인·소음·건물 주차처럼 사이트에서 삭제된 항목은 `check.py`가 금지어로 검사합니다.

---

## 기존 1페이지 SPA (루트 · 보존)

아래는 이전 버전(네이버 예약 달력 연동) 설명입니다. 루트 파일은 삭제하지 않고 그대로 두었습니다.

부산 광안리 **능놀스테이 풀빌라** 공식 소개·요금 안내 페이지입니다.
GitHub Pages로 정적 배포되며, 날짜별 요금과 예약 가능 여부는 **네이버 예약 달력**을 그대로 읽어옵니다.

- 사이트: https://neungnolstay-spec.github.io/neungnolstay/
- 네이버 플레이스: https://m.place.naver.com/accommodation/1967720454
- 네이버 예약(사업장 839642): 3층 헤윰 `items/4848181` · 6층 오롯 `items/4881823`

## 구성

| 파일 | 역할 |
|---|---|
| `index.html` | 페이지 본문(객실 전환 탭, 예약 달력, 갤러리, 요금표, 후기, 위치·FAQ) |
| `styles.css` | 디자인 시스템(네이비·골드·아이보리) |
| `app.js` | 달력·견적 계산, 객실 전환, 갤러리 라이트박스, 다국어(한/영/중) |
| `site-data.js` | `naver-sync.json` + `assets/photos.json`에서 생성한 내장 데이터 |
| `naver-sync.py` | 네이버 예약 GraphQL에서 두 객실 180일치 요금·마감 상태 수집 |
| `build_data_js.py` | `naver-sync.json` → `site-data.js` |
| `build_assets.py` | 원본 사진 선별 → `assets/*.webp`(긴 변 1600px, q85) + 앱 아이콘 |
| `assets/` | 사진 26장(webp), 앱 아이콘, 사진 메타데이터 |

## 요금 동기화

```bash
python3 naver-sync.py            # 오늘부터 180일, 헤윰·오롯 두 객실
python3 build_data_js.py         # 사이트에 내장할 데이터 갱신
```

브라우저는 페이지를 열 때 `naver-sync.json`을 캐시 없이 다시 읽어(15분 주기) 최신 상태를 반영합니다.
`naver-sync.json`을 갱신해 푸시하면 사이트에 반영됩니다.

## 요금 규칙 (네이버 예약 기준)

- 기준 8인 / 최대 12인 · 24개월 미만 영유아 무료
- 기준 인원 초과 1인당 30,000원
- 2박 이상 예약 시 추가 1박당 50,000원 할인
- 3층 헤윰 입실 15:00 / 퇴실 11:00 · 6층 오롯 입실 16:00 / 퇴실 12:00

## 예약

이 페이지에서는 결제가 이루어지지 않습니다. 견적을 확인한 뒤 **네이버 예약**으로 이동해 예약·결제합니다.
네이버 톡톡(https://talk.naver.com/w4hhwm) · 전화 0507-1429-2309 · 인스타그램 @neungnol_stay
