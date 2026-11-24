# NEUNGNOL STAY · 능놀스테이 홈페이지

## 글로벌 다국어 SEO 사이트 (`docs/`) — 현재 배포 대상

부산 광안리 **능놀스테이**의 공식 글로벌 사이트입니다. 한국어 · English · 日本語 · 简体中文 · 繁體中文
5개 언어, 객실별(헤윰 3층 / 오롯 6층) 독립 페이지, 검색엔진 크롤링이 가능한 정적 멀티페이지 구조입니다.

- 생성기·문구·검증 스크립트: [`i18n_build/`](i18n_build/README.md)
- 결과물: `docs/` (직접 수정 금지 — 빌드로 생성)
- 배포: GitHub Pages 소스 **main / docs** (`./deploy.sh`)

```bash
python3 i18n_build/build.py       # docs/ 재생성
python3 i18n_build/check.py       # 16페이지 전수 검증(사진·버튼·SEO·렌더링)
```

URL 구조

```
/                  언어 선택(브라우저 언어 자동 감지)
/ko/ /en/ /ja/ /zh-cn/ /zh-tw/
/ko/heyum/  /ko/orot/   (각 언어 동일)
```

`BASE_URL`·GA4·GTM·Search Console·네이버 서치어드바이저 값은 `i18n_build/build.py` 상단 한 곳에서 관리합니다.
자체 도메인으로 옮길 때는 `BASE_URL` 한 줄만 바꾸면 canonical·hreflang·OG·sitemap이 함께 바뀝니다.

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
