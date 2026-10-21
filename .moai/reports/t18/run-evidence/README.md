# t18 run 증거 사본

SPEC-AI-REPORT-006(카드 t18)의 `progress.md`가 인용하는 비추적 증거(`.moai/state/verify/t18-*`)를 작업공간 정리 전에 옮긴 사본이다. 원본은 git이 추적하지 않는 경로라서 원격 병합 뒤 워크트리를 지우면 사라진다.

| 폴더 | 원본 | 내용 |
|---|---|---|
| `plan`, `plan2`, `plan3` | `t18-plan*` | plan 단계 프로브(감사기 응답, CDP 캡처, 재렌더, 매니페스트 재생성 기준선) |
| `audit`, `audit2` | `t18-audit*` | plan 감사관 재실행 프로브 |
| `m1` | `t18-m1` | M1 스파이크: 캐너리 실험 `attempt1/`, 지오메트리 측정, 쓰기 프로브 |
| `m2` | `t18-m2` | M2 캡처 모듈: 되돌림 변형 출력(`mutations.out`), 실제 브라우저 1회 실행 |
| `m3` | `t18-m3` | M3: 0단계 쓰기 허용·거부 관측(`step0-*`), 되돌림 변형 |
| `m4` | `t18-m4` | M4: 되돌림 변형(`mutations*.out`), 하네스 전후 |
| `m5` | `t18-m5` | M5: 규칙 번호 검사, 매니페스트 재생성, 변형 |
| `merge` | `t18-merge` | main 병합 해결 기록과 시험 출력 |
| `orch-m2` ~ `orch-m6` | `t18-m*-orch` | 오케스트레이터 독립 재실행(pytest, vitest, 하네스 전후, 기준 상태 e2e, M6 라이브 JSON 읽기 요약) |
| `live-m6` | 런 `0ffb8f9e…`(~/.goose-harness/runs), 리드 `3313cef6-lead` | M6 라이브(AC-AIR6-018) 인용용 JSON 4개(`screens-index`, `review-receipt`, `review-delivery-audit`, `audit-review`), `job.json`, 리드 판정 파일 `lead-*`(`ac018.txt`, `ac018_check.py`, 감수 포함/제외 감사 출력, `events.sse`). PNG·html은 복사하지 않았다. `review-delivery-audit.json`과 `lead-audit018_with_review.json`은 크기는 같고 내용은 검사 시각 등에서 다르다 |

## sync 단계 추가분 (2026-10-21)

| 폴더 | 원본 | 내용 |
|---|---|---|
| `sync` | `t18-sync` | sync 보안 검토(`--security --deep`)의 PoC1·PoC2(`sec/poc1.py`, `poc2.py`), 수정 전 재현 출력, 의도적 가짜 비밀 `sec/secret.txt` |
| `m7` | 구현 에이전트 작업공간의 `t18-m7` | M7 보안 강화: 층 행렬(`matrix.out`), 되돌림 변형(`mutations-*.out`), 수정 전후 PoC, 규칙 번호 검사, 매니페스트 재생성 비교, 설정 sha, pytest 전후, 하네스 전후 |
| `resec` | `t18-resec` | 독립 보안 재검토(약 60개 우회 시도) PoC·출력, `jobs/<변형>/`. 판정 보고서는 `../security-rereview.md` |

- 이 추가분에서 PNG, `h/`(임시 하네스 사본), `pt/`, `.pyc`, 900KB 초과 파일(`resec/jobs/big_40mb`, `jobs/deep_nest`의 `report.html`)은 복사하지 않았다.
- 비밀 문자열 검색: 실제 키 형태(`crtfc_key|sk-ant|serviceKey|access_token|…|PRIVATE KEY|AIza…`) 0건. 가짜 비밀 `TOP-SECRET-LOCAL-FILE-CONTENT-12345`는 의도적으로 심은 시험용 문자열이며 `sync/sec/poc1.py`, `sync/sec/secret.txt`, `m7/poc.py`, `m7/poc-baseline/secret.txt`, `m7/poc-new/secret.txt`, `resec/jobs/hardlink_secret/draft/report.html`에만 있다.

## 제외

- 1MB를 넘는 파일 3개는 복사하지 않았다(`EXCLUDED-over-1MB.txt`): `t18-plan/cdp_desktop.png`, `cdp_mobile.png`, `t18-m1/timing-stream.jsonl`.
- 임시 `HOME`·하네스 설치 사본(`home/`)은 증거가 아니라서 지웠다.

## 비밀 문자열 검색 (2026-10-21)

- 키워드: `crtfc_key|api[_-]?key|secret|password|bearer|authorization:|sk-ant|serviceKey|access_token|refresh_token|OPENDART|ANTHROPIC_API_KEY|AIza…|ghp_…|xox[bp]-|PRIVATE KEY` — 일치는 스트림 초기화 줄의 필드 이름 `"apiKeySource":"none"` 3건뿐(값 아님).
- 40자리 16진 문자열(DART 키 형태): 0건. 64자리 16진 172건은 SHA-256 해시(매니페스트·하네스 해시).
- base64 이미지 안의 우연한 일치는 없었다(`AIza…`, `ghp_…` 0건).
