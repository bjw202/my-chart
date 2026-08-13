# SPEC-MARKET-BREADTH-001 — 구현 계획

> Tier **S** / Route **A**(Hybrid Trunk main-direct — PR·브랜치 없음) / 산출물 2종(`spec.md` + `plan.md`, AC는 spec.md §3 인라인)

## A. 맥락

`SPEC-SECTOR-GRID-001`(v0.3.0 `completed`)이 7개 기준일 소비자를 정규 주간 격자로 수렴시키면서 **범위 판정**으로 남긴 8번째 소비자 `market_breadth.py:472`를 전환한다. 이는 가설이 아니라 **현재 출하 중인 사용자 가시 오계산**이다(spec.md §1.3 — 1년 차트가 실제로는 약 20주).

기존 자산을 **소비만 한다** — `weekly_grid.compute_weekly_grid()` / `history()` / `anchor()` / `_get_latest_valid_date()`. 새 날짜 해석 헬퍼를 만들지 않는다.

## B. 알려진 이슈

| # | 이슈 | 대응 |
| --- | --- | --- |
| B1 | 작업 트리에 약 390건의 무관한 변경/미추적 항목 | `git add`는 **경로 지정만**. `git add -A`/`.` 금지. `.moai/state`, `.moai/harness`, `.moai/cache`, `.moai/logs` 미접촉 |
| B2 | 선행 SPEC이 `completed` 상태 | REQ-MBR-006의 allowlist 정리는 완료된 SPEC 본문 수정 = in-place amendment. M5에서 별도 취급(위험 R2) |
| B3 | venv 경로가 프로젝트 루트 밖 | `source /Users/byunjungwon/Dev/my_chart/.venv/bin/activate` |
| B4 | 프로즌 스냅샷은 `/api/db/update`로 갱신되지 않는 고정 사본 | 게이팅 AC는 전부 프로즌 위에서만. 라이브 실행은 비게이팅 스모크(선행 §3 규약 3) |

## C. 사전 확인 (M1 착수 전)

```bash
source /Users/byunjungwon/Dev/my_chart/.venv/bin/activate
git rev-parse --abbrev-ref HEAD                              # main
ls tests/fixtures/frozen/weekly-2026-08-12/weekly.db         # 프로즌 스냅샷 존재
python -m pytest tests/test_market_breadth.py -q             # 20건 baseline GREEN
```

## D. 제약

1. `compute_breadth_history`의 **반환 타입·정렬 순서**를 바꾸지 않는다(spec.md §4).
2. `compute_breadth`(`:85`)와 `compute_breadth_composite`를 건드리지 않는다.
3. `market_service.py:132`의 `weeks=52`를 바꾸지 않는다.
4. 새 날짜 해석 헬퍼를 만들지 않는다 — `weekly_grid` API 재사용.
5. spec.md §3.0 금지 형태 **F1~F4**에 해당하는 단언을 작성하지 않는다.
6. spec.md §8 O-M1~O-M3의 답을 발명하지 않는다.

## E. 자체 검증

각 마일스톤 종료 시 5-섹션 증거 형식(Claim / Evidence 축자 출력 / Baseline-attribution / Gaps / Residual-risk)으로 보고한다. 관측하지 않은 출력을 요약하지 않는다.

## F. 마일스톤 (되돌리기 어려운 순)

### M1 — baseline 리터럴 캡처 + 변형 하네스 [HARD · 코드 변경 전 진입 게이트]

가장 먼저다. AC-MBR-008(PRESERVE)의 우변과 변형 대조의 기준값이 **코드 변경 전에** 캡처되어야만 의미를 갖는다. **M1 미완 상태로 M2 착수 금지.**

- 프로즌 스냅샷에서 `compute_breadth(db, "KOSPI", "2026-07-31")` + `compute_breadth_composite` 전 필드를 캡처해 테스트 상수로 고정 → AC-MBR-008
- spec.md §3.0 변형표 V0/V1/V2/V3의 리터럴(n / 첫 날짜 / 마지막 날짜 / span)을 테스트 상수로 등재
- 변형 되돌림 하네스: 각 변형의 날짜 집합을 테스트 안에서 **직접 구성**(구현을 호출하지 않는다)하고, AC-MBR-001/002/003의 단언에 넣었을 때 실패함을 확인 — **AC가 실제로 잡는지 먼저 증명한다**
- 산출: `tests/test_market_breadth_grid.py`(신규) RED 상태

### M2 — 격자 전환 (REQ-MBR-001/002/003) [데이터 형태 결정 — 가장 되돌리기 어렵다]

- `compute_breadth_history`의 `:472` 쿼리를 `compute_weekly_grid(db_path)` → `history(grid, weeks)`로 교체
- `grid.history`를 쓴다 — `grid.dates`를 쓰면 CG-2가 죽는다(변형 V1)
- 게이트: AC-MBR-001 / 002 / 003 GREEN, AC-MBR-008 불변, 기존 20건 통과

### M3 — 이력 부족 공개 (REQ-MBR-004)

- 10 ISO 주 합성 픽스처 신규 작성(진행 중인 주 없음 — `as_of` 고정)
- `returned < requested` 시 요청값과 반환 개수를 **둘 다 담은** WARNING 로그
- 게이트: AC-MBR-005 GREEN

### M4 — 기간 표기 일치 (REQ-MBR-005) [사용자 가시 UI 변경]

- `backend/routers/market.py:20` docstring, `frontend/src/components/MarketOverview/BreadthChart.tsx:156` 차트 제목을 1년 기준으로 정정
- 최종 문구는 spec.md §8 **O-M3** — run 단계에서 확정하고 테스트 상수와 바이트 동등으로 고정
- `market_service.py:132`는 **미변경**(AC-MBR-007 셋째 조건)
- 게이트: AC-MBR-007 GREEN, 프론트 기존 테스트(`BreadthChart.test.tsx`) 통과

### M5 — 정적 스캔 + 선행 allowlist 정리 (REQ-MBR-006) [교차 SPEC 결합]

- AC-MBR-006 스캔 + 되돌림 대조 단언
- `SPEC-SECTOR-GRID-001/acceptance.md`의 allowlist L5 제거 + 상한 **5 → 4** 동기화, HISTORY에 amendment 행 추가
- **위험 R2 발동 지점** — 완료된 SPEC 본문 수정이므로 아래 R2 대응을 따른다
- 게이트: AC-MBR-006 GREEN, 선행 SPEC의 AC-SGR-005 테스트가 여전히 통과

### M6 — 회귀 게이트 + 릴리스 노트 (기계적)

- AC-MBR-004(비게이팅 리포트), AC-MBR-009(단언 승격 `<= 4` → `== 4`), AC-MBR-010
- **[HARD · plan-audit iter-1 이월] 리뷰는 "잡는 잘못된 구현" 열을 읽지 않고 실행한다.** SPEC v0.1.0의 AC-MBR-010은 그 열에 거짓 반증 주장(`history[:8]`을 잡는다)을 담고 있었고 실측으로 반증됐다(D1). 열 자체가 거짓일 수 있으므로, **열에 이름 붙은 변형을 실제로 구성해 단언에 투입하고 실패를 관측한 축자 출력**만이 증거로 인정된다
- 변형 되돌림 대조 전량 **실행** 기록: V0 / V1 / V2 / V3 / `history[:8]` / `history[-16:]` / AC-MBR-006 스캔 되돌림
- spec.md §5 C1~C6을 릴리스 노트에 반영
- §8 O-M1~O-M3을 `progress.md`에 사용자 확인 대기로 등재

## G. PRESERVE 목록 (건드리지 않는다)

- `compute_breadth` (`market_breadth.py:85` 및 시그니처)
- `compute_breadth_composite`, `determine_cycle`, `detect_choppy` 산식과 임계값
- `BreadthResult` 필드 구성, `backend/schemas/market.py`, `frontend/src/types/market.ts`
- `compute_breadth_history`의 반환 타입 `list[BreadthResult]`, 오름차순 정렬, `weeks` 기본값 12
- `market_service.py:132`의 `weeks=52`
- `weekly_grid.py` 전체 (소비만 한다)
- `meta_service.py:136` (O-G7 — 범위 밖)
- `docs/sector-ux/*`, CHANGELOG, README

## H. 위험

| # | 위험 | 대응 |
| --- | --- | --- |
| **R1** | **항진명제 AC 재발** — 선행 SPEC은 plan 단계에서 4건을 잡고도 테스트 작성 단계에서 3건이 재발했다. 본 SPEC은 개수가 판별자가 아니라는 함정(spec.md §1.4)까지 안고 있어 재발 확률이 높다 | M1을 **변형 하네스 우선**으로 배치해 "AC가 실제로 잡는지"를 구현 전에 증명한다. 리뷰 체크리스트에 F1~F4 대조를 명시 |
| **R2** | **완료 SPEC 본문 수정**(M5) — `SPEC-SECTOR-GRID-001`은 `completed`이며 allowlist 상한은 기계 단언 대상이다. 잘못 건드리면 선행 SPEC의 AC-SGR-005가 붉어진다 | M5를 **마지막 직전**에 두어 본 SPEC의 변경이 GREEN으로 확정된 뒤 수행. 선행 SPEC 테스트를 함께 돌려 회귀 확인. 실패 시 allowlist를 되돌리고 미수행 사유를 progress.md에 기록(품질 게이트가 이를 허용한다) |
| **R3** | **`detect_choppy` 판정 변화**(spec.md §5 C6 / O-M2) — 임계값이 원시 행 창 전제로 튜닝됐을 수 있어 사용자가 phase 표시 변화를 회귀로 신고할 수 있다 | M6에서 프로즌 기준 변경 전/후 phase·choppy를 실측해 기록하고 O-M2를 사용자 확인 대기로 승격. **임계값을 재튜닝하지 않는다** |
| **R4** | **프로즌 스냅샷 리터럴 노후화** — 스냅샷이 갱신되면 아래 **전체 목록**이 이동한다. plan-audit iter-1에서 AC-MBR-010의 span 경계가 이 목록에 누락되어 갱신 체크리스트를 빠져나갈 뻔했다(D6) | 선행 §3 규약 4·5를 따른다. 본 SPEC의 리터럴을 한 곳(테스트 상수 모듈)에 모아 갱신 지점을 단일화. **갱신 시 재도출 대상 전량**:<br>① AC-MBR-001 — `358` / `2025-08-14` / `2026-08-07`<br>② AC-MBR-002 — 진행 중인 주 `2026-08-11`<br>③ AC-MBR-003 — 고유 ISO 주 `52`<br>④ **AC-MBR-010 — 창 앵커 `2026-06-19` / `2026-08-07` 및 span 경계 `47–56`**(하한 47은 8바 창 45개 전수 실측 분포 48–50의 바닥 48에서 1일 여유를 뺀 값이므로, 갱신 후 **분포를 재측정해 재도출**한다)<br>⑤ AC-MBR-008 — `2026-07-31` 및 M1 캡처 baseline 전 필드<br>⑥ §3.0 변형표 V0/V1/V2/V3의 n·첫 날짜·마지막 날짜·span |
| **R5** | **범위 이탈** — O-M1(`market` 미사용 필터)이 눈에 띄어 함께 고치고 싶은 유혹 | spec.md §7.2로 명시 제외. 발견 시 progress.md에 기록만 하고 코드는 건드리지 않는다 |

## I. 교차 참조

- `.moai/specs/SPEC-SECTOR-GRID-001/spec.md` §1.2.1 / §1.2.2 / §7 O-G6, `acceptance.md` AC-SGR-005 / 007 / 008 / 020 / §3
- `.moai/reports/sync-audit-SPEC-SECTOR-GRID-001-20260812.md`
- `docs/sector-ux/00-overview.md` §4(범위 밖 행), `01-data-contract.md` §3
- `tests/fixtures/frozen/weekly-2026-08-12/MANIFEST.md`
