# 보고서 구조화 입력 v1

`scripts/render_report.py`는 Python 3 표준 라이브러리만 사용합니다. 외부 요청을 하거나 스크립트를 내려받지 않습니다. HTML에 CSS·승인된 글자 로고·SVG 차트를 내장하며, Pretendard와 Gowun Batang 서체만 CDN에서 읽습니다. 폰트 서버에 접근하지 못하면 시스템 대체 글꼴로 표시됩니다. 작성자는 한국어 존대 평서체로 원문을 작성하고 독립 검토를 마친 뒤 입력 상태를 선언합니다. 렌더러는 내용의 진실성이나 계산식을 검증했다고 주장하지 않습니다.

## 실행

```sh
python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --input runs/<job_id>/company-input.json --validate-only
python3 .claude/skills/goose/workflows/stock-report/scripts/render_report.py --input runs/<job_id>/company-input.json --output-dir runs/<job_id>/draft
```

개발용 회귀 테스트는 소스 저장소에만 있고 사용자 ZIP에는 없습니다. ZIP 실행에서 해당 테스트가 있다고 가정하지 않습니다. 입력·출력 경로는 호출 환경에 맞게 지정합니다. 출력은 `report.html`, 입력 바이트를 보존한 `report-input.json`, `source-ledger.json`, `render-validation.json`입니다. 같은 종목의 개정본은 새 출력 디렉터리에 만들어 이전 보고서를 보존합니다. 입력 파일은 출력 파일 중 하나와 같은 경로일 수 없습니다. 오류 시 종료 코드는 2이며 렌더링 전에 검증합니다. 검증 JSON에는 원본 SHA-256과 문단별 출처 연결·문장 수가 포함됩니다. 이 해시는 원문 보존 확인용이며 내용의 진실성을 증명하지 않습니다.

## 루트 객체

필수 키:

| 키 | 형식·의미 |
|---|---|
| `schema_version` | 정수 `1` |
| `document_type` | 선택: `deep_report`(기본), `comparison`, `earnings`, `event`, `portfolio`, `fact_check`, `briefing` |
| `company` | 심층 보고서 필수. `{name, ticker, market}` 문자열. 다른 유형에서는 선택이며 가상 회사 식별자를 넣지 않음 |
| `document` | `{title, subtitle, context_label}` 문자열. 일반 문서에서 회사가 없으면 필수. 있으면 표지에 사용 |
| `as_of`, `subtitle` | 기준일 필수. 루트 부제는 `document`가 없을 때 필수 |
| `status` | `draft`(미검증 초안), `limited`(조사 한계를 명시한 검토본), `verified`(작성자가 원문 대조를 완료했다고 선언한 검토본) |
| `limitations` | 문자열 배열. `limited`는 하나 이상 필수. 비어 있어도 전수 조사·완전성을 의미하지 않음 |
| `sources` | 아래의 출처 객체 배열. 한 개 이상 |
| `kpis` | 선택적 KPI 배열. 필요 없을 때 생략 또는 빈 배열 |
| `summary` | 문단 객체 배열. 심층 보고서는 한 개 이상, 일반 문서는 선택 |
| `sections` | 심층 보고서 **정확히 9개**, 일반 문서 **1~12개**. 각 `{title, blocks:[...]}`. 제목에 번호를 넣지 않음 |
| `opinion` | 심층 보고서 필수(열 번째 섹션), 일반 문서는 선택(일반 섹션 뒤에 추가) |

권장 일반 섹션: 사업 구조 / 실적 추이 / 이익의 질 / 현금·재무 여력 / 산업·경쟁사 / 뉴스·후속 사건 / 팩트체크 / 시나리오 / 조사 근거와 판단 연결. 보고서 목적에 맞게 제목·블록을 바꿀 수 있습니다. 자료 장부는 부록으로 자동 표시됩니다.

## 출처와 주장 연결

각 source는 다음 문자열을 모두 갖습니다: `id`, `title`, `publisher`, `published_at`, `period`, `accessed_at`, `read_scope`, `findings`, `status`, `verification`. `url`은 외부 출처에서는 HTTP(S) 문자열이며, 아래 로컬 출처에서는 명시적 `null`입니다.

- `id`: 영문·숫자로 시작하며 영문·숫자·밑줄·점·하이픈만 허용, 최대 80자, 중복 금지.
- `url`: 절대 HTTP(S) 원문 URL. 자바스크립트·data·상대 URL, 자격증명, 공백·제어문자·역슬래시 금지.
- 로컬 예외: `source_type:user_input` 또는 `source_type:local_calculation`은 `url:null`과 `artifact_ref`가 필수입니다. 사용자 제공 내용이나 로컬 계산에 가짜 웹 주소를 만들지 않습니다. `artifact_ref`는 `holdings-input-01`처럼 작업 내에서 근거를 식별하는 이식 가능한 별칭입니다. 첫 글자는 문자·숫자, 이후에는 문자·숫자·밑줄·점·하이픈만 허용하며 최대 120자입니다. 절대경로·상대경로·URL은 거부하고 HTML에는 링크가 아닌 자료 식별명으로 표시합니다. 실제 파일 경로와 별칭의 대응은 사용자 작업 공간에 따로 관리하며 외부 제공 보고서에 개인 경로를 노출하지 않습니다.
- `published_at`, `accessed_at`: ISO 날짜 또는 날짜가 불명확한 사유를 명시한 문자열. `period`는 실제 대상 기간/사건일을 구분해 기입합니다.
- `read_scope`: 직접 읽은 본문·표·주석·첨부 구간을 구체적으로 적습니다. 본문과 첨부 검토보고서를 별도로 읽었는지 식별합니다.
- `verification`: 공통 조사 장부와 동일한 `direct_read` / `prior_record` / `blocked` / `not_published` 필수. 이번 실행 직접 열람, 기존 열람 기록 대조, 접근 제한, 미공개를 각각 구분하여 표시합니다. 기존 기록을 가져온 자료는 `prior_record`이며 `direct_read`로 올리지 않습니다. `blocked`·`not_published`는 반드시 `status:unverified`여야 합니다.
- `status`: `read`(열람 기록을 확보함; 이번 실행/기존 기록 여부는 `verification`으로 구분) 또는 `unverified`. 후자는 `attempts`(시도한 대체 경로와 실패 이유), `impact`(판단에 미치는 영향) 문자열도 필수입니다.
- `findings`: 해당 구간에서 확인한 사실/불일치/가정과 출처 성격을 기록합니다. `source_type`, `event_date`, `document_id`, `independence_group` 등 추가 메타데이터는 원본·자료 장부에 보존할 수 있습니다.

로컬 근거도 `verification`과 `read_scope` 등 모든 열람·분석 메타데이터가 필요합니다. 사용자 입력을 실제 읽었다면 `direct_read`, 예전 입력 기록만 대조했다면 `prior_record`로 구분합니다. 실제 계산을 확인한 `local_calculation`에는 읽은 계산식·입력 범위를 적고, 가능하면 추가 메타데이터에 원래 입력 출처 ID·계산식을 보존합니다. 자체 계산이라는 이유로 그 입력 자료까지 직접 검증했다고 처리하지 않습니다.

```json
{"id":"holdings-input","source_type":"user_input","title":"사용자 제공 보유 항목",
 "publisher":"사용자","published_at":"사용자 제공일","period":"사용자가 명시한 기준일",
 "accessed_at":"실제 읽은 날짜","url":null,"artifact_ref":"holdings-input-01",
 "read_scope":"제공된 보유 항목과 비중 열","findings":"관심 자산과 비중을 확인했습니다.",
 "status":"read","verification":"direct_read"}
```

모든 주장 문단, 표, 차트, KPI, 오피니언 카드의 세 문단은 `source_ids`(존재하는 출처 ID의 중복 없는 비어 있지 않은 배열)와 `status`가 필수입니다. 주장 상태는 `verified`(원문 대조 기록), `qualified`(조건부 근거, `qualification` 설명 문자열 필수), `inference`(분석·추론), `unverified`(미확인)입니다. 본문에는 작은 근거 캡션과 자료 장부 번호 링크를 표시합니다. 조건부·미확인 상태를 숨기지 않습니다. `verified` 주장은 `read` 출처만 연결할 수 있습니다. 보고서 전체 `verified`에는 미확인 주장이나 미열람 출처를 넣을 수 없습니다. `inference`는 사실의 복제가 아니라 근거를 종합한 판단임을 표시합니다. `limited`의 한계는 본문 주장 상태까지 정직하게 반영합니다.

## 공통 원장 → 렌더러 입력 어댑터 규칙

공통 `sources.json`의 `verification`, `source_type`, 사건일·한계·시도 기록을 삭제하지 않습니다. `direct_read`·`prior_record`는 해당 기록의 실제 내용이 뒷받침되면 renderer `status:read`로, `blocked`·`not_published`는 `status:unverified`로 연결합니다. 과거 기록의 `accessed_at`은 실제 과거 열람일을 유지하고 현재 대조일은 별도 메타데이터 `record_checked_at`로 보관합니다. 기존 기록의 내용을 이번 실행 직접 읽은 사실로 바꾸지 않습니다. `attempts`가 공통 원장에서 배열이면 본문 표시용 설명 문자열로 정리하고 원래 배열은 `original_source`에 보존합니다. 미확인 출처의 `impact`는 공통 장부의 판단 영향·한계 설명에서 가져옵니다.

공통 주장 원장은 `original_claim` 추가 필드에 그대로 보존하고 다음과 같이 표시용 필드를 만듭니다.

| 공통 주장 | 렌더러 상태·조건 |
|---|---|
| `supported` + `fact` | `verified`. 실제 연결 출처가 `read`여야 함 |
| `supported` + `inference` | `inference`. 전제·반대 근거·변경 조건을 본문에 보존 |
| `supported` + `forecast` | `qualified`와 `qualification`에 전망이라는 사실·발표기관·전제 표시 |
| `qualified` | `qualified`와 `qualification`에 원장의 `reason`·제약을 명시 |
| `unresolved` | `unverified`. 미해결 수치는 `null`, 설명은 본문/한계에 표시 |
| `contradicted` | `unverified`. 원래 주장을 결론으로 채택하지 않고 반증 결과를 명시하거나 제거. 원장은 보존 |

원장 `id`, `kind`, `status`, `reason`, 반대 출처·계산 연결 등의 필드는 삭제하지 않습니다. 원문 JSON에 추가한 메타데이터는 그대로 출력 입력 파일에 남습니다. 이 어댑터는 작성자가 수행하며 렌더러가 `supported`를 무조건 자동 승격하지 않습니다.

## 콘텐츠 객체

**문단**: `{type:"paragraph", text:"존대 서술입니다.", source_ids:["dart"], status:"verified"}`. 요약과 오피니언 카드 문단에서는 `type`을 생략할 수 있습니다. HTML·Markdown을 해석하지 않으므로 문자열에 태그를 넣지 않습니다. 모든 동적 문자열은 이스케이프됩니다.

**소제목**: `{type:"heading", text:"현금흐름을 읽는 기준"}`. h3로 표시하며 사실 주장을 담기 위한 블록이 아닙니다. 근거가 필요한 서술은 출처 연결 문단으로 작성합니다.

**KPI**: `{label:"영업현금흐름", value:12.3, unit:"조 원", period:"2026 H1", basis:"연결", definition:"배당 수취 포함", source_ids:["dart"], status:"verified"}`. `value`는 유한 숫자 또는 명시적 `null`입니다. 누락은 오류, `null`은 **미확인**, `0`은 실제 0으로 구분합니다. 숫자는 입력 단위 그대로 표시하며 자동 통화 변환이나 연율화를 하지 않습니다.

**표**:

```json
{"type":"table","title":"재무 비교","period":"2026 H1","unit":"조 원","basis":"연결",
 "headers":["항목","회사 A","회사 B"],"rows":[["영업현금흐름",12.3,null]],
 "source_ids":["dart"],"status":"verified"}
```

모든 행 길이는 머리글과 같아야 하며 셀은 문자열·유한 숫자·`null`입니다. 비교 기간·통화·연결 범위가 다르면 동일 비교로 오인하지 않도록 작성자가 설명합니다. 행별 출처가 다르면 별도 표/문단으로 연결하거나 셀 텍스트에 ID를 표시하고 표 `source_ids`에 모두 포함합니다.

**재무 차트**:

```json
{"type":"chart","kind":"bar","title":"영업이익 추이","period":"2025–2026 분기",
 "unit":"조 원","basis":"연결","categories":["2025 Q4","2026 Q1","2026 Q2"],
 "series":[{"label":"영업이익","values":[-2.1,null,4.5]}],
 "source_ids":["dart"],"status":"verified"}
```

`kind`는 `bar` 또는 `line`입니다. 최대 40개 구분, 6개 계열이며 각 계열 값 길이는 구분 수와 같습니다. 데이터에 맞춰 영점 포함 축을 계산하고 음수는 영점 아래에 표시합니다. 결측값은 막대/점을 그리지 않으며 선도 연결하지 않습니다. 정확한 수치 표가 함께 제공됩니다. OHLC·봉차트·기술적 주가 분석 입력은 지원하지 않습니다. 차트 제목·기간·단위·연결/별도 등의 범위·출처는 모두 필수입니다.

**오피니언**:

```json
{"decision":"관망","confidence":"중간",
 "lead":{"text":"...","source_ids":["dart"],"status":"inference"},
 "grounds":{"text":"...","source_ids":["dart"],"status":"inference"},
 "conditions":{"text":"...","source_ids":["dart"],"status":"inference"},
 "paragraphs":[{"sentences":["첫 문장입니다.","둘째 문장입니다.","셋째 문장입니다.","넷째 문장입니다.","다섯째 문장입니다."],"source_ids":["dart"],"status":"inference"}]}
```

위 예시는 구조만 보여줍니다. 심층 보고서의 `paragraphs`는 **정확히 12개**, 각 `sentences`는 **5개 이상의 완결 문장**이어야 합니다. 일반 문서는 오피니언 자체를 생략할 수 있고, 카드를 넣으면 `paragraphs`는 생략 또는 0~12개입니다. 일반 문서의 추가 산문에는 문단당 1개 이상의 완결 문장을 씁니다. 소수점·URL 때문에 문장 수를 잘못 나누지 않도록 작성자가 문장 배열을 직접 제공합니다. 각 항목은 하나의 문장을 담고 문장부호로 끝내야 합니다. 렌더러는 배열 길이와 종결부호를 검사하며 언어학적 완결성은 편집자가 검토합니다. 결론 카드를 먼저 배치하고 뒤에 연결된 산문으로 출력합니다. `decision`은 `관심종목 편입` / `관망` / `편입 보류`, `confidence`는 `낮음` / `중간` / `높음` 중 하나입니다. `conditions`에는 판단을 바꿀 관찰 조건을 제시합니다. 근거가 부족하면 `decision:null`과 비어 있지 않은 `decision_reason`을 넣습니다. 이때 카드는 **판단 유보 — 근거 부족**, 세 판단 칩은 모두 비선택 상태로 표시되어 억지 등급을 만들지 않습니다.

## 검토 경계

단위·기간·출처 누락과 알 수 없는 출처 ID, 잘못된 URL, NaN/무한대, JSON 중복 키는 거부합니다. 대조 완료 상태는 외부 감사 인증이 아닙니다. 재계산, 긍정·반대 근거 충실성, 최신 정정·후속 공시, 권리·접근 한계, 출처 읽기 여부는 별도 에이전트 검토 책임입니다. 생성 후 실제 브라우저에서 글꼴·잘림·차트·모바일 크기를 검토합니다. 인쇄 스타일은 제공하지만 PDF 결과의 페이지 나눔은 별도 검증합니다.


## 일반 리포트·페이지 템플릿

승인된 로고·전자잉크 배경·제목 고운바탕·본문 Pretendard·행간 1.6을 모든 문서 유형이 공유합니다. 제목·요약·KPI·표·재무 SVG·출처 장부를 조합해 비교 리포트, 실적 리뷰, 사건 분석, 포트폴리오 점검, 팩트체크, 브리핑 페이지를 만들 수 있습니다. 이는 파일을 생성하는 공통 템플릿이며 배포된 웹 앱을 뜻하지 않습니다. 포트폴리오에 가상 `company`를 넣지 말고 다음처럼 문서 헤더를 씁니다.

```json
{"schema_version":1,"document_type":"portfolio",
 "document":{"title":"포트폴리오 점검","subtitle":"사업 노출과 위험 요인","context_label":"사용자가 제공한 보유 항목 기준"},
 "as_of":"2026-10-16","status":"limited","limitations":["확인된 한계를 구체적으로 기재합니다."],
 "sources":["실제 출처 객체로 대체"],
 "sections":[{"title":"사업 노출","blocks":["실제 문단·표 객체로 대체"]}]}
```

위 예시는 루트 구조 설명용입니다. 문자열 자리표시자를 실제 객체로 대체해야 실행됩니다. 일반 문서는 최소 한 섹션이 필요하며 `opinion`을 넣지 않으면 판단 카드도 생성하지 않습니다. 생성기의 구조 검사 설명은 표지가 아닌 자료 장부의 **검증 범위 안내**에 표시합니다.

## 편집 품질과 독립 파일 전달

문단 객체에는 선택적으로 `highlights:["원문에 있는 핵심 수치", "판단"]`를 넣습니다. 최대 3개·각 100자 이내이며 실제 문단의 정확한 부분 문자열이어야 합니다. HTML은 계속 이스케이프합니다. `opinion.decision_scope:"research_priority"`로 관심목록 판단의 범위를 명시합니다.

선택 메타데이터 `editorial_review`는 argument_depth, decision_scope, material_coverage, visual_review의 상태와 실제 근거를 담습니다. 생성기의 `editorial_quality`는 문단 밀도·최소 문장수 패턴과 누락 검토를 경고할 뿐 내용 품질을 인증하지 않습니다. 기준 미달을 임의로 숨기지 않습니다. 수익성·시장 전망 등 사실의 검증은 별도입니다.

단일 report.html에 입력 JSON·출처 JSON·구조검증 JSON을 다운로드 데이터로 내장합니다. CLI 출력의 입력 원본 바이트와 SHA-256을 보존합니다. 다른 조사 메모까지 한 HTML에 포함되는 것은 아니므로 전체 기록은 별도 ZIP으로 제공합니다.

## 제출 감사용 기록

조사 마감 시각, 최신 검색, DART 열람 범위, 분기·연간 원장과 생성 후 감수 기록은 [최종 감사 계약](../../fact-check/references/delivery-audit.md)을 따릅니다. 일반 렌더는 감사 대기 초안이며 `--final`은 현재 초안과 연결된 감수 기록이 통과해야 생성됩니다.
