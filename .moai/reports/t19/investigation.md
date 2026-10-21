# t19 — 네이버 최신 검색 막힘 원인 조사 (읽기 전용)

card: t19 · base: 7abdcac · 조사일: 2026-10-21 · 방법: 이 머신에서 curl GET (UA=Chrome), 코드 읽기

## 감사 규칙 (코드에서 읽음)

`backend/goose_harness_src/skills/goose/workflows/fact-check/scripts/audit_report.py:41-52`
- `document_type == deep_report`이면 channels에 `naver`가 들어간다.
- 채널마다 `research_window.searches`에 (channel 일치, cutoff 24시간 이내, query·note 비어 있지 않음, `result=read`+직접 읽은 source_ids 또는 `result=no_results`) 항목이 있어야 통과.
- 없으면 `LATEST_SEARCH_NAVER` 실패. 메시지에 "차단은 완료가 아닙니다"가 박혀 있어 `blocked`는 통과 수단이 아니다.

## 네이버 엔드포인트 관측 (이 머신, curl)

| 주소 | 결과 |
|---|---|
| `finance.naver.com/item/news_news.naver?code=020150` | HTTP 410, 2476B (EUC-KR, "Npay" 안내 페이지) |
| `finance.naver.com/item/news_notice.naver?code=020150` | HTTP 410, 1840B (같은 안내 페이지) |
| `m.stock.naver.com/api/news/stock/020150?pageSize=5&page=1` | HTTP 200 JSON, 최신 기사(제목·본문·datetime·officeName·articleId) 반환 |
| `search.naver.com/search.naver?where=news&query=…&sort=1` | HTTP 200 HTML 328KB, 뉴스검색 결과 페이지 |
| `openapi.naver.com/v1/search/news.json` | HTTP 401 (키 없음 — 공식 검색 API는 클라이언트 ID 필요) |

## 해석 (가설, 아직 검증 전)

- 데스크톱 금융 뉴스·공시 페이지는 폐기(410)되었다. goose가 이 주소로 갔다면 "막힘"으로 기록했을 가능성이 높다.
- 모바일 뉴스 JSON은 서버에서 키 없이 열린다. DART처럼 서버 사전 수집 후보가 된다.
- 단, goose 쪽 WebFetch/샌드박스가 별도로 막히는지는 이 조사로는 알 수 없다.

## Gaps (미관측)

- G1: 라이브 실행 a5becbb9의 `research_window.searches`에서 naver 채널이 어떤 주소·어떤 사유로 `blocked`가 됐는지 원문을 못 봤다. `find`로 `a5becbb9*` 디렉터리를 찾았으나 없음(보존 위치 미확인).
- G2: goose 샌드박스에서의 WebFetch 거동은 관측하지 않았다 (이 머신 curl과 다를 수 있다).
- G3: 모바일 API의 반복 호출 제한·약관·안정성은 확인하지 않았다 (1회 호출만).
- G4: search.naver.com HTML의 기사 목록 추출 가능성(스크립트 렌더 여부)은 파싱해 보지 않았다 — 328KB 응답 수신만 확인.

## Residual risk

- 비공식 모바일 API라 예고 없이 바뀔 수 있다 (같은 계열 naver_theme_v2도 스키마가 바뀐 전례, t14 참조).
