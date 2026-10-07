# wcomp 축소 fixture (SPEC-FNGUIDE-WCOMP-001)

FnGuide 신사이트(`https://wcomp.fnguide.com/`)의 실제 응답을 테스트가 쓰는 범위로 줄인 오프라인 fixture다. 기본 테스트 스위트는 이 파일만 읽으며 실제 HTTP를 보내지 않는다(REQ-WC-016). 모든 행은 실제 응답에서 온 것이고, 지어낸 값은 없다. 조작본·합성본이 필요한 테스트는 이 파일을 테스트 안에서 복사해 고친다.

## 출처 구분

- **plan 표본**: plan 단계 조사 때 받은 원본(세션 임시 디렉터리 `scratchpad/raw`, `scratchpad/html`, `scratchpad/fs.html`). 캡처 시각은 원본 파일의 수정 시각(mtime)이다 — 파일을 쓴 시각이므로 실제 요청 시각과 수 초 차이가 날 수 있다.
- **M1 라이브**: run 단계 M1에서 표본에 없던 응답을 한 번씩 받은 것. 캡처 시각은 요청 직전에 기록한 시각이다. 요청은 `requests.Session().get(url, params={...}, headers=H, timeout=10)`로 보냈고, `H`는 `User-Agent: Mozilla/5.0`, `X-Requested-With: XMLHttpRequest`, `Referer: https://wcomp.fnguide.com/`(REQ-WC-001과 같은 헤더)이다. 요청 사이에 0.5초를 쉬었다. 16건 모두 HTTP 200이었고 재무제표는 `application/json; charset=utf-8`, 스냅샷은 `text/html; charset=utf-8`, 스냅샷 리디렉션은 없었다.

`robots.txt`는 `Disallow: /`다. 사용자가 현행 수집 자세(요청 시에만 받고 대량 수집하지 않음)를 알고 수용했다. 이 fixture는 1회 캡처본이며 갱신 크롤러는 두지 않는다.

## 축소 방법

| 종류 | 방법 |
|---|---|
| 재무제표 JSON (`getFin*_<code>_<Y|Q>_<C|B>.json`) | `dataset.header`는 그대로 둔다(VAL1~VAL6 머리글, `LINE` 포함). `dataset.data`는 **행을 하나도 빼지 않고** 각 행에서 `AC_CODE`, `P_AC_CODE`, `NAME`, `LVL`, `VAL1`~`VAL5` 키만 남긴다(`SEQ`, `DIGIT`, `UNIT`, `VAL6` 제거). 행을 빼지 않는 이유는 정합성 가드(REQ-WC-011)와 접기가 대차대조표의 모든 행을 더하기 때문이다. `NAME`의 공백·`\xa0`과 값 문자열은 원문 그대로다. 한 행을 한 줄로 직렬화했다. 축소 후 다시 읽어 머리글·남긴 키 값·행 수가 원본과 같음을 확인했다 |
| 스냅샷 HTML (`Snapshot_<code>.html`, `snapshot_005935_served_as_005930.html`) | 모든 `<script>…</script>` 요소(외부·인라인·템플릿), HTML 주석, `id="snpFinancial"` 표(재무 하이라이트 — REQ-WC-013이 쓰지 않음)를 지우고 빈 줄을 줄였다. 줄바꿈은 LF로 바뀌었다. 나머지 마크업은 원문 그대로다. 남은 요소: hidden `#cmp_cd`, `#giName`, `#master_chk`, PER·PER(Fwd.12M)·업종 PER·PBR·현금배당수익률 영역, 시세 표(`시가총액(상장예정포함)`, `52주베타`, `발행주식수`), 주주 표(`자사주`, `자사주(자사주+자사주신탁)`), 기업 개요(`bizSummaryContent`) |
| 원본 그대로 (바이트가 판정에 쓰임) | `legacy_stub_1829.html`(1,829바이트, 표 1개), `getFinIncome_999999_Y_C.html`(1,668바이트, 본문이 `\r\n\n<!DOCTYPE`로 시작), `getFinIncome_005935_Y_C.json`(263바이트, `data=[]`), `snapshot_999999_object_moved.html`(193바이트, 302 응답 본문) |
| 응답 헤더 (`HEADERS_*.txt`) | `curl -s -D - -o /dev/null`의 출력 그대로(plan.md §F.1 V-1). `HEADERS_999999_follow.txt`만 `curl -sL`(리디렉션 추종)로 받았다 |

표본에 있었으나 이 SPEC의 테스트가 쓰지 않는 종목(000220 등 17종목의 Income, `consol_typ=P|I` 응답, `page_*.html`, 컨센서스·재무비율 페이지)은 넣지 않았다.

## 파일 목록 (원본 URL · 출처 · 캡처 시각, KST)

| 파일 | 원본 URL | 출처 | 캡처 시각 |
|---|---|---|---|
| `getFinBalance_001750_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=001750&freq_typ=Q&consol_typ=B | M1 라이브 | 2026-10-07T23:15:53+09:00 |
| `getFinBalance_001750_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=001750&freq_typ=Q&consol_typ=C | M1 라이브 | 2026-10-07T23:15:52+09:00 |
| `getFinBalance_001750_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=001750&freq_typ=Y&consol_typ=B | M1 라이브 | 2026-10-07T23:15:51+09:00 |
| `getFinBalance_001750_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=001750&freq_typ=Y&consol_typ=C | M1 라이브 | 2026-10-07T23:15:51+09:00 |
| `getFinBalance_005930_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=005930&freq_typ=Q&consol_typ=C | plan 표본 | 2026-10-07T00:04:55+09:00 |
| `getFinBalance_005930_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=005930&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:04:59+09:00 |
| `getFinBalance_105560_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=105560&freq_typ=Q&consol_typ=C | M1 라이브 | 2026-10-07T23:15:56+09:00 |
| `getFinBalance_105560_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=105560&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:06:39+09:00 |
| `getFinBalance_330590_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=330590&freq_typ=Q&consol_typ=B | M1 라이브 | 2026-10-07T23:15:55+09:00 |
| `getFinBalance_330590_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=330590&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:43:47+09:00 |
| `getFinBalance_403870_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=403870&freq_typ=Q&consol_typ=B | plan 표본 | 2026-10-07T00:06:12+09:00 |
| `getFinBalance_403870_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinBalance?cmp_cd=403870&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:06:10+09:00 |
| `getFinCashFlow_001750_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=001750&freq_typ=Q&consol_typ=B | M1 라이브 | 2026-10-07T23:15:55+09:00 |
| `getFinCashFlow_001750_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=001750&freq_typ=Q&consol_typ=C | M1 라이브 | 2026-10-07T23:15:54+09:00 |
| `getFinCashFlow_001750_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=001750&freq_typ=Y&consol_typ=B | M1 라이브 | 2026-10-07T23:15:54+09:00 |
| `getFinCashFlow_001750_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=001750&freq_typ=Y&consol_typ=C | M1 라이브 | 2026-10-07T23:15:53+09:00 |
| `getFinCashFlow_005930_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=005930&freq_typ=Q&consol_typ=C | plan 표본 | 2026-10-07T00:04:57+09:00 |
| `getFinCashFlow_005930_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=005930&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:05:02+09:00 |
| `getFinCashFlow_105560_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=105560&freq_typ=Q&consol_typ=C | M1 라이브 | 2026-10-07T23:15:57+09:00 |
| `getFinCashFlow_105560_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=105560&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:06:40+09:00 |
| `getFinCashFlow_330590_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=330590&freq_typ=Q&consol_typ=B | M1 라이브 | 2026-10-07T23:15:56+09:00 |
| `getFinCashFlow_330590_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=330590&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:43:49+09:00 |
| `getFinCashFlow_403870_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=403870&freq_typ=Q&consol_typ=B | plan 표본 | 2026-10-07T00:06:16+09:00 |
| `getFinCashFlow_403870_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinCashFlow?cmp_cd=403870&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:06:14+09:00 |
| `getFinIncome_001750_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=001750&freq_typ=Q&consol_typ=B | M1 라이브 | 2026-10-07T23:15:50+09:00 |
| `getFinIncome_001750_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=001750&freq_typ=Q&consol_typ=C | M1 라이브 | 2026-10-07T23:15:50+09:00 |
| `getFinIncome_001750_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=001750&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:10:10+09:00 |
| `getFinIncome_001750_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=001750&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:09:33+09:00 |
| `getFinIncome_005930_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=005930&freq_typ=Q&consol_typ=C | plan 표본 | 2026-10-07T00:04:52+09:00 |
| `getFinIncome_005930_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=005930&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:04:44+09:00 |
| `getFinIncome_005930_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=005930&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:04:43+09:00 |
| `getFinIncome_105560_Q_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=105560&freq_typ=Q&consol_typ=C | plan 표본 | 2026-10-07T00:06:38+09:00 |
| `getFinIncome_105560_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=105560&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:06:37+09:00 |
| `getFinIncome_105560_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=105560&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:06:36+09:00 |
| `getFinIncome_330590_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=330590&freq_typ=Q&consol_typ=B | plan 표본 | 2026-10-07T00:43:46+09:00 |
| `getFinIncome_330590_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=330590&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:10:12+09:00 |
| `getFinIncome_330590_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=330590&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:10:11+09:00 |
| `getFinIncome_403870_Q_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=403870&freq_typ=Q&consol_typ=B | plan 표본 | 2026-10-07T00:06:08+09:00 |
| `getFinIncome_403870_Y_B.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=403870&freq_typ=Y&consol_typ=B | plan 표본 | 2026-10-07T00:06:05+09:00 |
| `getFinIncome_403870_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=403870&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:06:04+09:00 |
| `getFinIncome_005935_Y_C.json` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=005935&freq_typ=Y&consol_typ=C | plan 표본 | 2026-10-07T00:09:10+09:00 |
| `getFinIncome_999999_Y_C.html` | https://wcomp.fnguide.com/CompanyInfo/getFinIncome?cmp_cd=999999&freq_typ=Y&consol_typ=C (302 → `/Error/InvalidCompany` 추종 후 본문) | plan 표본 | 2026-10-07T00:09:16+09:00 |
| `legacy_stub_1829.html` | 옛 호스트 `http://comp.fnguide.com/SVO2/asp/SVD_Finance.asp?…&gicode=A005930`로 추정(표본 이름 `fs.html`; 옛 URL 세 개가 같은 안내 페이지를 돌려준다는 관측은 research.md·spec.md §1.2) | plan 표본 | 2026-10-06T23:59:35+09:00 |
| `Snapshot_005930.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=005930 | plan 표본 | 2026-10-07T00:05:35+09:00 |
| `Snapshot_403870.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=403870 | plan 표본 | 2026-10-07T00:05:28+09:00 |
| `Snapshot_105560.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=105560 | plan 표본 | 2026-10-07T00:05:31+09:00 |
| `Snapshot_001750.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=001750 | M1 라이브 | 2026-10-07T23:15:57+09:00 |
| `Snapshot_330590.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=330590 | M1 라이브 | 2026-10-07T23:15:58+09:00 |
| `snapshot_005935_served_as_005930.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=005935 (사이트가 005930 페이지를 내줌) | plan 표본 | 2026-10-07T00:09:20+09:00 |
| `snapshot_999999_object_moved.html` | https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=999999 (리디렉션을 따라가지 않은 302 본문) | plan 표본 | 2026-10-07T00:09:19+09:00 |
| `HEADERS_005930.txt` | 세 엔드포인트, `cmp_cd=005930&freq_typ=Y&consol_typ=C` | M1 라이브(V-1) | 2026-10-07T23:16:20+09:00 |
| `HEADERS_005935.txt` | 세 엔드포인트, `cmp_cd=005935&freq_typ=Y&consol_typ=C` | M1 라이브(V-1) | 2026-10-07T23:16:20+09:00 |
| `HEADERS_999999.txt` | 세 엔드포인트, `cmp_cd=999999&freq_typ=Y&consol_typ=C` | M1 라이브(V-1) | 2026-10-07T23:16:20+09:00 |
| `HEADERS_999999_follow.txt` | 위와 같음, 리디렉션 추종(`curl -sL`) | M1 라이브(V-1) | 2026-10-07T23:16:41+09:00 |

## 같은 날 두 시점이 섞인 점

001750·330590·105560은 연간 Income(plan 표본, 2026-10-07 00시대)과 일부 재무제표(M1 라이브, 2026-10-07 23시대)가 같은 날 다른 시각에 받은 것이다. 받은 직후 머리글을 대조해 세 재무제표의 기간(연간 `2023/12…2026/06`, 분기 `2025/09…2026/06`, 330590 연간 `2024/12, 2025/06, 2025/12, 2026/06`)이 일치함을 확인했다. 그 사이 사이트의 수치 정정이 있었는지는 확인하지 않았다.
