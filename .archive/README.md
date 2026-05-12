# .archive — 보존용 비활성 자산

본 디렉토리는 product code가 아닌 **transition / ad-hoc / planning 자산을 보존**하기 위한 격리 공간이다.

`git mv`로 이동하여 git history는 온전히 보존되며, working tree에서는 product 영역과 분리된다. 어떤 backend / frontend 코드도 이 디렉토리를 import하지 않는다 (`grep -rE "\.archive" backend frontend my_chart` 검증 가능).

## 디렉토리 구성

### `scripts/` — SPEC-AI-REPORT-002/003 작업 중 ad-hoc 검증 스크립트 7개

원래 위치: `/scripts/test_*.py`
이동일: 2026-05-12

| 파일 | 용도 |
| --- | --- |
| `test_perplexity.py` | Perplexity API 직접 호출 검증 (SPEC-AI-REPORT-001 시절) |
| `test_sonar_reasoning.py` | sonar reasoning model 응답 비교 |
| `test_v11_live.py` | SPEC-AI-REPORT-002 v1.1 라이브 검증 |
| `test_v113_service.py` | v1.1.3 service layer 검증 |
| `test_v116_sktelecom.py` | v1.1.6 SK텔레콤 종목 회귀 검증 |
| `test_domain_filter.py` | Brave search domain filter param 검증 |
| `test_domain_limit.py` | Brave search domain limit 검증 |

특징:
- 모두 root에서 `python scripts/test_*.py`로 실행하던 ad-hoc CLI 스크립트
- `backend/tests/` 위치가 아니므로 pytest 대상 아님
- 다른 모듈에서 import 0건 (격리됨)
- SPEC-AI-REPORT-003 (Codex 전환) 후 실효성 상실

복원 방법:
```bash
git mv .archive/scripts/test_perplexity.py scripts/test_perplexity.py
```

### `codex-transform-plan/` — Perplexity → Codex 전환 plan 자산 11개

원래 위치: `/codex-transform-plan/`
이동일: 2026-05-12

| 파일 | 용도 |
| --- | --- |
| `README.md` | 전환 plan overview |
| `plan.md` | 마스터 plan |
| `plan-v2-perplexity-migration.md` | v2 migration approach |
| `plan-v3-complete-codex-replacement.md` | v3 완전 교체 path (실제 채택) |
| `codex-cli-reference.md` | Codex CLI 사용법 reference |
| `perplexity-usage-analysis.md` | 기존 Perplexity 사용 패턴 분석 |
| `comparison-samsungsdi-2026-04-23.md` | 삼성SDI 종목 응답 품질 비교 |
| `samples/codex_sample_006400.md` | Codex 응답 sample |
| `samples/perplexity_enhanced_citations_006400.json` | Perplexity 인용 sample |
| `samples/perplexity_enhanced_sample_006400.md` | Perplexity 응답 sample |
| `samples/perplexity_sample_006400.json` | Perplexity 원본 응답 |

특징:
- SPEC-AI-REPORT-003 (v3 complete codex replacement, 2026-04-23 ship) 이후 transition 완료 → 악세서리 가치만 남음
- 외부 코드 / 문서에서 참조 0건 (검증 완료)
- history는 git log에 영구 보존

복원 방법:
```bash
git mv .archive/codex-transform-plan codex-transform-plan
```

## 운영 원칙

- archive는 **삭제가 아닌 격리**. git history는 항상 보존되며 언제든 복원 가능
- product code에서 import 금지. `.archive/` 경로 참조가 발견되면 product 회귀로 간주
- 향후 SPEC ship 후 transition 산출물도 본 패턴으로 archive 권장 (예: SPEC-X-001 도입 후 SPEC-X-002로 대체된 plan 문서들)
- 영구 삭제가 필요한 경우 별도 PR로 처리 (git history는 prune 전까지 보존)

---

Last Updated: 2026-05-12
