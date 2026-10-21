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
| `orch-m2` ~ `orch-m5` | `t18-m*-orch` | 오케스트레이터 독립 재실행(pytest, vitest, 하네스 전후, 기준 상태 e2e) |

## 제외

- 1MB를 넘는 파일 3개는 복사하지 않았다(`EXCLUDED-over-1MB.txt`): `t18-plan/cdp_desktop.png`, `cdp_mobile.png`, `t18-m1/timing-stream.jsonl`.
- 임시 `HOME`·하네스 설치 사본(`home/`)은 증거가 아니라서 지웠다.

## 비밀 문자열 검색 (2026-10-21)

- 키워드: `crtfc_key|api[_-]?key|secret|password|bearer|authorization:|sk-ant|serviceKey|access_token|refresh_token|OPENDART|ANTHROPIC_API_KEY|AIza…|ghp_…|xox[bp]-|PRIVATE KEY` — 일치는 스트림 초기화 줄의 필드 이름 `"apiKeySource":"none"` 3건뿐(값 아님).
- 40자리 16진 문자열(DART 키 형태): 0건. 64자리 16진 172건은 SHA-256 해시(매니페스트·하네스 해시).
- base64 이미지 안의 우연한 일치는 없었다(`AIza…`, `ghp_…` 0건).
