# 최종 제출 감사와 수정 반환

초기 종목 분석 요청은 짧아도 전체 기업 보고서를 기본으로 합니다. 후속 질문만 범위를 줄입니다. 이 계약은 HTML 보고서의 최종 제출에 적용합니다. 단순 질문 답변을 불필요하게 보고서로 만들지 않습니다.

## 실제 조사와 최신성

실행 환경의 현재 날짜·시간대를 먼저 확인합니다. 사용자가 과거 기준일을 지정하지 않았다면 오늘을 기준으로 조사합니다. 조사 마감 시각까지 공개된 최신 공시·기사·정정·후속 사건을 다시 검색합니다. 최근 24~72시간의 새 정보와 주요 쟁점의 30~90일 전후 맥락을 함께 읽으며, 개수 채우기로 끝내지 않습니다. 발행일·사건일·수치 대상기간·열람시각을 구분합니다. 미래 실적·미공개 자료를 확정값으로 넣지 않습니다. 모든 인터넷 자료를 빠짐없이 수집했다고 주장하지 않습니다.

한국 기업의 전체 보고서는 DART 정기보고서 본문, 관련 주석, 첨부 검토·감사보고서를 직접 읽습니다. IR은 보완 자료입니다. IR만 읽고 DART 열람 완료로 처리하지 않습니다. DART 뷰어·첨부·정정·원 발행처 등 대체 경로를 조사하되 끝내 접근하지 못하면 초안으로 남깁니다.

최근 8개 분기를 목표로 최소 6개 연속 공시 분기와 최근 3개 연도를 비교합니다. 매출·영업이익의 기간·단위·연결 범위를 통일하고 누적 차감으로 분기를 구한 경우 산식을 남깁니다. 잠정 실적은 별도 표시하며 공시 분기 수를 채우는 데 쓰지 않습니다. 실적 추이, 이익률, 현금흐름 도해에 검증된 값을 사용합니다. 신규상장·자료 미공개는 실제 제한으로 기록하고 사용자에게 범위 조정을 설명합니다. 부족한 보고서를 통과시키려고 brief 유형으로 바꾸지 않습니다.

## 입력 JSON에 남길 기록

- `research_window`: `mode`는 current 또는 사용자가 요청한 historical, `cutoff`는 시간대가 포함된 ISO 시각. historical에는 `user_requested_as_of`를 남깁니다. `as_of`는 cutoff 날짜로 시작합니다.
- `research_window.searches`: `{channel, searched_at, query, result, source_ids, note}` 배열. 전체 기업 보고서 channel은 dart(한국 기업), company_ir, naver, original_news, industry입니다. 기타 보고서도 original_news 최신 검색은 포함합니다. `result=read`이면 직접 읽은 원문 출처로 연결합니다. `no_results`는 실제 검색 조건·확인 결과를 note에 남긴 경우만 씁니다. 차단은 결과 없음이 아닙니다. cutoff 전 24시간 이내의 실제 검색 기록이어야 합니다. 미완료 조사 기록의 날짜만 바꾸지 않습니다.
- `filing_coverage`: body, notes, review_or_audit 각각 `{status:"read", read_scope, source_ids}`. DART 원문 URL과 직접 열람 구간을 가리킵니다.
- `financial_history.quarters`: `{period:"2026-Q2", status:"filed"|"derived", revenue, operating_profit, source_ids, basis, unit, calculation}`. 실제 값만 사용하며 분기별 검토·공시 상태를 보존합니다.
- `financial_history.annual`: `{year, revenue, operating_profit, source_ids, basis, unit}`. 이 원장은 본문 표·차트와 수치가 일치해야 합니다.
- 재무 chart 블록의 `purpose`는 revenue_profit, margins, cashflow. revenue_profit의 categories는 YYYY-Qn 표기로 수집한 전체 기간을 보여줍니다.

## 감수 → 수정 → 재감수

1. stock-report가 일반 렌더 명령으로 **감사 대기 초안**을 만듭니다. HTML·원장·계산·본문을 팩트체크 담당에게 넘깁니다.
2. 팩트체크 담당은 실제 원문에 주요 수치와 결론을 대조하고, 누락·반론·기간·기준일·문체·수치 강조·12문단의 논리 연결을 확인합니다. 실제 브라우저로 표·차트·모바일 넘침·문단·다운로드를 확인합니다. 도구가 없으면 화면 검토 미완료이며 pass로 꾸미지 않습니다. 독립 에이전트가 없으면 작성 후 별도 검토로 수행하고 그 한계를 명시합니다.
3. `audit-review.json`에는 현재 입력 바이트의 `input_sha256`, 실제 확인한 초안 HTML의 `preview_sha256`, 시간대 포함 `reviewed_at`, `mode=independent_agent|separate_review_pass`를 기록합니다. `checks`의 source_accuracy, calculations, coverage, opinion, visual 각각 `{status:"pass"|"revise", evidence:"실제 대조·관찰 기록"}`를 남깁니다. 오피니언 없는 문서는 그 이유와 해당 결론 검토 결과를 opinion에 기록합니다. `issues`에는 `{owner, description, status:"resolved"|"open"}`를 남깁니다.
4. 감사기는 아래 명령으로 누락·최신성·기간·버전·감수 기록을 검사합니다. 결정 revise이면 findings.owner에게 정확한 결함을 돌려보냅니다. 자료를 추가하거나 문장을 고치면 입력 버전을 올리고 초안을 새로 만든 뒤 재감수합니다. 반복은 최대 3회이며 같은 접근 차단이 그대로면 중지하고 미완료 사유를 보고합니다. 중지했다고 통과시키지 않습니다.
5. 최종 제출은 `--final`로만 생성합니다. 입력·템플릿이 달라진 초안, 미완료 감수, 누락 조사로는 최종본이 생성되지 않습니다. 이전 최종본과 혼동하지 않도록 매번 새 실행 디렉터리를 사용합니다. 검사 결과는 사실의 진실성 자체를 증명하지 않으며 감수 선언을 실제 실행 증거로 위장하지 않습니다.

스킬 루트 기준 실행:

```sh
python3 workflows/stock-report/scripts/render_report.py --input input.json --output-dir run/draft
python3 workflows/fact-check/scripts/audit_report.py --input input.json --preview run/draft/report.html --review audit-review.json --output run/delivery-audit.json
python3 workflows/stock-report/scripts/render_report.py --input input.json --preview run/draft/report.html --audit-review audit-review.json --final --output-dir run/final
```

감사기는 소스 내용의 사실 여부나 독립 에이전트 실행을 자동으로 증명하지 않습니다. 형식 검사를 통과시키기 위해 가짜 열람·감수 기록을 작성하지 않습니다. 최종 HTML, 입력 JSON, 출처 장부, 구조 검사, 최종 감사 기록을 함께 전달하고 실제 실행 범위를 설명합니다.
