# SPEC-AI-REPORT-005 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_complete_at: 2026-10-21T00:00:00+09:00
- plan_status: audit-ready (v0.3.1, plan-audit PASS)
- plan_audit:
  - 1회차 FAIL 0.77 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-1.md` (B1~B7·S1~S6·M1~M5 → v0.2.0에서 반영)
  - 2회차 FAIL 0.88 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-2.md` (N1~N5 → v0.3.0에서 반영)
  - 3회차 PASS 0.92 — `.moai/reports/plan-audit/SPEC-AI-REPORT-005-review-3.md` (R3-1 → v0.3.1에서 반영, R3-2·R3-3은 아래 부채)
- plan_debt (사용자 승인 2026-10-21, run 단계 처리):
  - R3-2: AC-AIR5-014 되돌림 (r3)이 대상 테스트를 지정하지 않아 결과가 비결정적이다. → run 단계는 (r1)·(r3)에 쓸 테스트 이름을 정확히 정해 `progress.md §E.2`에 적고, 수집 성공 여부와 무관한 단언(실행기 호출·작업 진행)만 가진 테스트를 고르거나 (r2)의 작업 서비스 변형으로 (r3)를 수행한다.
  - R3-3: 첨부 항목이 `section == "auditor_report"`·`document == "attachment"`를 갖는지 단언하는 AC가 없다. → run 단계는 새 AC를 만들지 말고 AC-AIR5-008 테스트 안에 eleId 1·2 항목에 대한 두 단언을 추가한다.
- R3-1 run 단계 주의: 네트워크 가드 범위는 테스트 파일 이름으로 판정하고, AC-AIR5-014 #4를 되돌림 관측보다 먼저 실행한다.
- artifacts: spec.md, plan.md, acceptance.md, research.md, progress.md
- counts: REQ 16개(REQ-AIR5-001~016), AC 16개(AC-AIR5-001~016) — Tier M 상한(각 16) 이내
- needs_clarification: 0건 (미확인 DART 사실 F4·F8은 run 단계 M1 관측 항목, research.md §3)
- baseline: 이전 실행 2건에서 대상 감사 결함 6종 모두 발생(research.md §2, P14), 매니페스트 = 원본 재생성 결과(P7)

## §F Phase 4 Mode Selection

- 입력: Tier M · 범위 약 10~12개 파일(백엔드 모듈·테스트·conftest·하네스 지침·매니페스트·프론트 3개) · 도메인 3(백엔드, 하네스, 프론트) · 코딩 중심 · 동시성 이점 낮음
- direct: 미선택 — 다중 파일 구현
- serial: **선택** — 코딩 중심 작업, 마일스톤 순서 의존(M1 픽스처 → M2 모듈 → M3 연결 → M4 지침 → M5 라이브)
- fanout: 미선택 — 연구 중심이 아님
- sweep: 미선택 — 기계적 대량 변환 아님
- Decision: serial
- 근거: 코딩 작업은 병렬화 이점이 작고 마일스톤이 앞 단계 산출물(픽스처·모듈)에 의존한다. 사용자 선택에 따라 마일스톤마다 보고 후 다음으로 진행한다(2026-10-21 Implementation Kickoff Approval). 실행자는 공용 체크아웃에서 작업하는 manager-develop 역할의 general-purpose 에이전트(SPEC-AI-REPORT-004와 같은 방식; manager-develop 정의는 자동으로 별도 작업 공간에 격리됨).

## §E.2 Run-phase Evidence

### M1 — 픽스처와 데이터 모양 확정 (2026-10-21, HEAD 9f9e09e 기준)

산출물: `backend/tests/fixtures/dart/` — `recorded/`(녹화 9개 + `request_log.json`), `synthetic/`(합성 6개), `capture_dart.py`(수집), `build_synthetic.py`(합성 생성), `index_keys.json`(색인 키 집합), `README.md`(수집 시각·명령·요청 수·출처). 운영 코드·conftest 없음(M2·M3 몫).

#### 요청 기록

- 명령: `/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I backend/tests/fixtures/dart/capture_dart.py backend/tests/fixtures/dart/recorded`
- 1차(11:45 KST): 첫 POST가 httpx 폼 직렬화 오류(`TypeError: sequence item 1: expected a bytes-like object, tuple found`)로 본문 전송 중 중단 — 응답·파일 없음. 상한 계산에 1건으로 포함.
- 2차: 9회, 모두 HTTP 200, 시작 시각 `2026-10-21T11:46:27.901+09:00` ~ `11:46:36.758+09:00`, 간격 1.1초 이상, 응답 0.057~0.155초. 합계 10회(중단 1 포함).
- 상한 때문에 받지 않은 것: 사업보고서 감사보고서 본문 구간 1건(위임 범위의 9번째 항목). M2의 `auditor_report` 본문은 합성 바이트로 대신한다 — Gap G-M1-1.

#### F4·F8 관측표

| 사실 | 가정(research §3) | 관측 | 근거 | 판정 |
|---|---|---|---|---|
| F4 `finalReport=recent` 목록에서 정정 전 원본이 빠지는가 | 미확인 | 하나기술(299030) `finalReport=recent` 정기보고서 12행에 `[기재정정] 사업보고서 (2025.12)`(`20260814003680`), `[기재정정] 사업보고서 (2024.12)`(`20250814004212`), `[기재정정] 사업보고서 (2023.12)`(`20240422000338`)만 있고 같은 기간 원본 사업보고서 행은 0개. 같은 기간 행이 둘 이상인 경우 0건 | `recorded/list_299030_recent.html` (요청 9) | 가정과 일치: `recent` 조회는 기간당 최신 제출본 하나만 보여 준다. REQ-AIR5-006의 "같은 기간이면 최신 접수" 규칙은 안전장치로 유지(합성 `list_020150_correction.html`이 검사) — SPEC 변경 불필요 |
| F4 보조 | — | `finalReport` 없이 받은 목록은 관측하지 않았다(요청 상한). 원본 사업보고서들이 3년 창 안에 실제로 있다는 것은 추론(정정은 원본을 전제) | — | Gap G-M1-2 |
| F8 사업보고서 첨부 감사보고서 목차 순서 | "감사인 보고서 본문 → `(첨부)` 재무제표"인지 미확인 | 연결감사보고서(`dcmNo=11105314`) 노드: 1 `감   사   보   고   서`, 2 `독립된 감사인의 감사보고서`, 3 `(첨부)연 결 재 무 제 표`, 4 `주석`, 5 `외부감사 실시내용` | `recorded/main_20260310002974_11105314.html` (요청 8) | 가정과 일치: 감사인 보고서(1·2)가 `(첨부)` 앞에 온다. 반기 검토보고서와 달리 `주석` 뒤에 5번 노드가 더 있으나 REQ-AIR5-008("`(첨부)` 앞 텍스트만")·plan T5("`(첨부)` 앞 노드")로 자동 제외 — SPEC 변경 불필요 |
| F8 보조: 첨부 선택 | — | 사업보고서 첨부 7종: `감사보고서` 11105293, `감사의감사보고서` 11105318, `내부감시장치에대한감사의의견서` 11105320, `내부회계관리제도운영보고서` 11105321, `연결감사보고서` 11105314, `영업보고서` 11105319, `정관` 11105317 | `recorded/main_20260310002974.html` | M2 주의: `감사보고서` 부분 일치는 `감사의감사보고서`를 잡는다 |

#### research §5 기댓값 대조

- `recorded/list_020150_recent.html`: 12행, 고유번호 집합 `{'00113997'}`, 접수번호·순서가 research §5 12행과 같다(`20260814000373` … `20231114000877`). 2026.09 분기보고서 없음 → **§5 기댓값 변경 없음**, AC-AIR5-006 리터럴 그대로.
- 반기 목차 노드가 research P11과 같다: 요약재무정보 `11527102/18/233941/25639`, 연결재무제표 `19/259834/178344`, 연결재무제표 주석 `24/438182/1703030`, 재무제표 `58/2141216/124954`, 재무제표 주석 `63/2266174/1375036`. 첨부 `11527104` 반기검토보고서, `11527105` 반기연결검토보고서. 첨부 목차 노드 4개(P12와 같음). 본문 바이트 53,931·492,989(P13과 같음).
- 새 측정값(최신 사업보고서 `20260310002974`, 본문 `dcmNo=11105315`): 요약재무정보 `eleId=18 offset=250218 length=25415`(제39·38·37기 3개 회계연도), 연결재무제표 `19/275884/278976`, 연결재무제표 주석 `24/554864/2182152`, 재무제표 `65/2737020/188752`, 재무제표 주석 `70/2925776/1946506`.
- 관측(SPEC 변경 불필요, M2 참고): 목록 순서는 접수 순이다. 하나기술은 정정 사업보고서(2025.12)와 반기보고서(2026.06)가 같은 날 접수되어 정정본이 첫 행이다. 020150에는 해당 없음.

#### index.json 키 집합

`backend/tests/fixtures/dart/index_keys.json` = acceptance.md §B. 대조 명령(이번 실행): §B 줄의 백틱 토큰과 JSON을 집합 비교 → `top True 9`, `company True 2`, `search True 6`, `files_item True 17`, `outcome True`, `status True`. 각 키의 값은 녹화 데이터에서 얻을 수 있다: `company.name`·`corp_code`(목록 행 회사명·`openCorpInfoNew`), `rcp_no`·`report_name`·`period`(목록 행), `section_title`·`viewer_url` 인자 6개(목차 노드), `attachment_name`(첨부 선택 목록 이름). 변경 없음.

#### 합성 픽스처

`build_synthetic.py` 실행 후 독립 파서로 확인: `list_020150_mixed_corp.html` 12행·고유번호 `{00113997, 00999999}`; `list_020150_correction.html` 13행, `20250902000123 [기재정정] 반기보고서 (2025.06)`이 `20250814003923` 앞; `list_empty.html` 0행; `no_consolidated` 재무제표 `eleId 58`·주석 `63`만; `reordered` 순서 주석(24) → 연결재무제표(19); `polluted` 연결재무제표 노드 `dcmNo ../1, offset 1&x=y, dtd a/b`(원본과 `diff` 3줄만 다름). CRLF 보존(`mixed_corp` 17,715바이트 = 원본, `cmp` 차이 4바이트).

#### TDD 메모

M1은 픽스처만 만든다(운영 코드 없음). RED 출력(E8)은 해당 없음 — M2의 첫 테스트가 RED를 남긴다.

#### Gaps

- G-M1-1: 감사·검토보고서 본문 구간 녹화 없음(요청 상한).
- G-M1-2: `finalReport` 없는 목록 미관측 — F4의 "원본이 존재한다" 쪽은 추론.
- G-M1-3: 실제 DART "결과 없음" 목록 마크업 미관측 — `list_empty.html`은 행만 지운 합성본.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
