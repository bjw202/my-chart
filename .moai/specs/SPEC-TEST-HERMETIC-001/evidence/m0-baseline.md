# M0 — 정상 환경 기준선 실측 (plan §C-2 / REQ-009 비교 기준선)

## 측정 조건

- 환경: 주 체크아웃(`/Users/byunjungwon/Dev/my-project-01/my_chart`) — `Output/` 프로덕션 DB 존재 정상 환경
- 측정 성격: 읽기 전용 관측. 파일 편집·서버 재시작 없음.
- 측정 시각: 2026-10-21 (run-phase M0)

## 명령과 verbatim 출력

명령 (plan §C-2 그대로):

```
cd /Users/byunjungwon/Dev/my-project-01/my_chart && /Users/byunjungwon/Dev/my-project-01/my_chart/.venv/bin/pytest tests/ -q
```

출력 말미 (verbatim):

```
1087 passed, 1 skipped, 95 deselected, 1 xpassed in 88.15s (0:01:28)
```

종료 코드: 0 (직접 확인 — 백그라운드 태스크 exit code 0)

## 기준선 수치 (AC-009 비교 대상 — 본 실측값을 인용, 상수 아님)

| 항목 | 실측값 |
|------|--------|
| passed | 1087 |
| skipped | 1 |
| deselected (live/slow 마커) | 95 |
| xpassed | 1 |
| failed | 0 |
| 종료 코드 | 0 |

## 프로덕션 DB 부작용 감시 (BASELINE-SIDE-EFFECT 점검)

측정 전후로 `Output/*.db` mtime을 stat으로 대조:

- 측정 전: `stock_data_weekly.db` mtime=1792502962 / `stock_data_daily.db` mtime=1792503020
- 측정 후: `stock_data_weekly.db` mtime=1792502962 / `stock_data_daily.db` mtime=1792503020

변화 없음 → 기준선 실행은 읽기 전용이었음을 실측으로 확인. `BASELINE-SIDE-EFFECT` 중단 조건 미발동.

## LSP baseline (plan §C-1)

- 프로젝트 Python LSP/타입체커: `pyproject.toml`에 `[tool.mypy]`(python_version=3.13)와 `[tool.ruff]` 설정 존재. venv에는 `pyright`가 설치되어 있고 ruff 바이너리는 없음(`.venv/bin`에 부재 실측).
- 측정 명령: `.venv/bin/pyright tests/conftest.py tests/test_market_api.py tests/test_response_contract.py tests/test_m6_gap_closure.py tests/test_ac_sag_045_r1_r4_r5a.py`
- 출력 (verbatim): `0 errors, 0 warnings, 0 informations`
- 비고: pyright가 `Config contains unrecognized setting "pythonPath"` 경고와 워크트리 `.venv` 부재 안내를 출력했으나 진단 자체는 정상 완료. 이 0건이 변경 전 baseline이며, M4 최종 검증에서 동일 명령을 재실행해 신규 진단 0을 확인한다.
