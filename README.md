# NEUNGNOL STAY · 능놀스테이 홈페이지

## 글로벌 다국어 SEO 사이트 (`docs/`) — 현재 배포 대상

부산 광안리 **능놀스테이**의 공식 글로벌 사이트입니다. 한국어 · English · 日本語 · 简体中文 · 繁體中文
5개 언어, 객실별(헤윰 3층 / 오롯 6층) 독립 페이지, 검색엔진 크롤링이 가능한 정적 멀티페이지 구조입니다.

- 생성기·문구·검증 스크립트: [`i18n_build/`](i18n_build/README.md)
- 결과물: `docs/` (직접 수정 금지 — 빌드로 생성)
- 배포: GitHub Pages 소스 **main / docs** (`./deploy.sh`)

```bash
python3 i18n_build/build.py       # docs/ 재생성
python3 i18n_build/check.py       # 16페이지 + /admin/ 전수 검증(사진·버튼·SEO·렌더링·예약)
```

### 객실 사진 갤러리·직접 예약·관리 화면

| 기능 | 위치 | 설명 |
|---|---|---|
| 사진 갤러리 | `/{lang}/{room}/#gallery` | 에어비앤비 두 리스팅의 사진을 큐레이션(헤윰 38장·오롯 33장). 분류 필터 + 풀스크린 라이트박스(좌우 넘김·키보드·스와이프) |
| 직접 예약 | `/{lang}/{room}/#reserve`, `/{lang}/#reserve` | 2개월 실시간 달력(예약·차단 날짜 자동 비활성), 인원(기준 8·최대 12), 일별 요금 합계, 예약 신청 폼 |
| 관리 화면 | `/admin/` | PIN 잠금(초기 `0000`) · 예약 달력 · 예약 신청 관리 · 요금 설정 |
| 데이터 | Firebase RTDB `/neungnol_booking_v1` | 직원 체크리스트(`/neungnol_v1`)와 완전히 분리 |

- 예약 데이터 구조: `settings`(요금·PIN 해시·인원 기준) · `blocks/{room}/{date}`(외부예약 차단) · `settings/overrides/{room}/{date}`(특정일 요금) · `bookings/{id}`(신청·확정·취소, 메모)
- 게스트 신청은 `pending`으로 저장되고, 사장님이 관리 화면에서 `확정`하면 해당 날짜가 자동 마감됩니다. `취소`하면 날짜가 다시 열립니다.
- 사진 재생성: `python3 i18n_build/make_gallery.py` (큐레이션 목록은 `i18n_build/gallery_map.py`)

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
| `/llms-full.txt` | 5개 언어 전체 상세(객실 사양·시설·이용 안내·FAQ·에어비앤비 후기·키워드) |
| `/robots.txt` | GPTBot·OAI-SearchBot·ChatGPT-User·Google-Extended·PerplexityBot·ClaudeBot·anthropic-ai·Applebot-Extended·Bingbot 등 명시적 Allow |

- 16페이지 JSON-LD에 `LodgingBusiness`/`HotelRoom` + `FAQPage`(홈 10문항)를 넣고, `knowsLanguage`(ko·en·ja·zh-Hans·zh-Hant), `amenityFeature`(오션뷰·자쿠지·키즈룸·100인치 프로젝터·유아 하이체어·주차·세탁기 등), `sameAs`(에어비앤비 두 객실·인스타그램·네이버 플레이스·톡톡), `petsAllowed`/`smokingAllowed`(false), `floorSize`를 채웁니다.
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
