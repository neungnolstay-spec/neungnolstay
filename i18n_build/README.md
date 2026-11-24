# NEUNGNOL STAY — 글로벌 다국어 SEO 사이트 (i18n_build)

부산 광안리 **능놀스테이** 공식 사이트의 정적 멀티페이지 버전입니다.
루트의 기존 1페이지 SPA(`index.html`, `app.js` 등)는 그대로 보존되어 있고,
새 사이트는 `docs/` 에 생성되어 GitHub Pages 의 **/docs** 소스로 배포됩니다.

```
https://neungnolstay-spec.github.io/neungnolstay/          ← 언어 선택 (docs/index.html)
https://neungnolstay-spec.github.io/neungnolstay/ko/       ← 한국어
                               …/en/  …/ja/  …/zh-cn/  …/zh-tw/
                               …/{lang}/heyum/  …/{lang}/orot/
```

## 빌드

```bash
python3 i18n_build/build.py          # → docs/
python3 i18n_build/build.py --out docs
```

`docs/` 는 생성물이므로 직접 수정하지 말고 `i18n_build/` 소스를 고친 뒤 다시 빌드합니다.

| 파일 | 역할 |
|---|---|
| `i18n_build/build.py` | 페이지 생성기. **BASE_URL·GA4·GTM·GSC·네이버 인증값은 이 파일 상단 한 곳** |
| `i18n_build/content/ko.py` … `zhtw.py` | 언어별 문구(5개). 키 집합이 다르면 빌드가 중단됩니다. 객실별 에어비앤비 리뷰 본문(`rooms.*.reviews`)도 여기에 있고, 평점·후기 수는 `build.py` 의 `AIRBNB_STATS` |
| `i18n_build/content/geo.py` | AI 검색(GEO/AEO)용 5개 언어 요약·자연어 질문·키워드·FAQ. `llms.txt`·`llms-full.txt` 와 홈 FAQ·meta keywords 에 쓰입니다 |
| `i18n_build/photos.py` | 사진 크기·언어별 alt·갤러리 순서·객실 대표 사진 |
| `i18n_build/prep_plans.py` | 도면 원본(네이버 플레이스 `business_005/006.jpg`)에서 빈 여백을 잘라 `assets/plan-hewyum.webp`·`plan-orot.webp` 재생성 (2200px, 비율 유지) |
| `i18n_build/static/style.css` | 부티크 호텔 스타일 디자인 시스템 |
| `i18n_build/static/app.js` | GA4 이벤트(`heyum_airbnb_click`, `orot_airbnb_click`, `language_switch`, `room_detail_view`, `floor_plan_zoom`) + 도면 확대 보기(라이트박스) |
| `i18n_build/check.py` | 16페이지 전수 검증(HTTP·SEO·JSON-LD·링크·에어비앤비 사진/버튼·PC/모바일 렌더링) |
| `i18n_build/shots.py` | 검수용 스크린샷 → `i18n_build/screenshots/review/` |
| `i18n_build/setup_browser_deps.py` | (샌드박스 전용) Playwright chromium 실행에 필요한 라이브러리를 사용자 공간에 설치 |

## 검증

```bash
export LD_LIBRARY_PATH="$PWD/.cache/chromedeps/usr/lib/x86_64-linux-gnu"   # 이 환경에서만 필요
python3 i18n_build/check.py
```

검사 항목

1. 16개 페이지 HTTP 200
2. `<html lang>` · `hreflang`(ko/en/ja/zh-Hans/zh-Hant/x-default) · `canonical` · OG
3. `LodgingBusiness` / `HotelRoom` / `BreadcrumbList` / `FAQPage` JSON-LD 파싱
4. 모든 내부 링크 200, 외부 링크 `target=_blank` + `rel=noopener`
5. `sitemap.xml`(xhtml:link 포함) · `robots.txt`
6. **에어비앤비 대표 사진이 원본 `01_living.jpg` 와 동일한지 픽셀 비교**
7. **헤윰/오롯 카드가 PC·모바일에서 동일 크기인지**
8. **각 카드 사진 아래 예약 버튼, 정확한 에어비앤비 URL 연결**
9. PC(1440)·모바일(390) 가로 넘침·콘솔 오류·하단 고정 예약 바
10. 상세 페이지 상단 사진도 동일한 에어비앤비 대표 사진인지
11. **객실 페이지 상단·하단의 `← 전체 객실로 돌아가기` / `다른 객실 보기` 버튼** (클릭 시 실제 이동까지)
12. **객실별 에어비앤비 리뷰 섹션** — 카드 6개·별점·게스트 이름·리뷰 더 보기 링크, 그리고 **리뷰 영역에 날짜 표기(연도·월·`~ 전`)가 없는지**
13. **AI 검색 자산** — `llms.txt`·`llms-full.txt` HTTP 200·필수 항목(주소·두 에어비앤비 링크·5개 언어 URL), `robots.txt` 의 AI 크롤러 Allow, 홈 `FAQPage` 문항 수 = 화면 문항 수, `LodgingBusiness` 의 `knowsLanguage`·`sameAs`·`amenityFeature`
14. **금지 표기** — `nungnol`·`NUNG NOL`·`누놀` 0건, 삭제된 연박 할인·소음·건물 주차 문구 0건

## 배포

1. GitHub `neungnolstay-spec/neungnolstay` 저장소를 만들고 Pages 소스를 **main / docs** 로 설정
2. `docs/`, `i18n_build/` 를 push (`./deploy.sh` 가 push + Pages 설정까지 수행)

자체 도메인으로 옮길 때는 `build.py` 의 `BASE_URL` 한 줄만 바꾸고 다시 빌드하면
canonical · hreflang · OG · sitemap 이 모두 함께 바뀝니다.

## GA4 / Search Console / 네이버 서치어드바이저

`build.py` 상단의 빈 값을 채우고 다시 빌드하면 16페이지 전체에 반영됩니다.

```python
GA4_MEASUREMENT_ID = "G-XXXXXXXXXX"
GTM_ID = "GTM-XXXXXXX"
GSC_VERIFICATION = "..."      # google-site-verification content
NAVER_VERIFICATION = "..."    # naver-site-verification content
```

값이 비어 있어도 GA4 커스텀 이벤트는 `dataLayer` 에 쌓이므로, 나중에 GTM에서 그대로 받아 쓸 수 있습니다.
