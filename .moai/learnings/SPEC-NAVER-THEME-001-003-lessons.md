# 네이버 테마 분석 SPEC-NAVER-THEME-001~003 시리즈 회고

> 본 문서는 SPEC-001 V1 ship → SPEC-002 V2 backend → SPEC-003 V2 frontend 채택까지 진행하면서 얻은 교훈을 정리합니다. 다음 비슷한 작업(예: 다른 데이터 소스 도입)에서 즉시 활용할 수 있도록 구체적인 패턴 위주로 기록.

비개발자용 종합 가이드는 `docs/theme-analysis-guide.md`를 먼저 읽어주세요. 본 문서는 그 다음 단계, "다음 SPEC을 만들 때 무엇을 그대로 가져갈지 / 무엇을 피할지"에 초점을 둡니다.

---

## 시리즈 한눈에

| SPEC | 시점 | 핵심 작업 | 결과 |
|---|---|---|---|
| SPEC-NAVER-THEME-001 | 2026-04 | 데스크탑 HTML 기반 테마 분석 V1 신규 | 14 AC PASS, 51 tests, 커버리지 99% |
| SPEC-NAVER-THEME-002 | 2026-04 | 모바일 JSON API 기반 V2 backend 신규 (V1 무수정) | V2 24 + 라이브 1 PASS, V1 51 회귀 0 |
| SPEC-NAVER-THEME-003 | 2026-05-06 | 화면이 V2 통로 사용 + V2 metadata V1 alias | AC 15/15 PASS, V2 29 PASS, frontend 271 PASS, evaluator-active 4/4 PASS |

ship branch: `chore/integrated-main-merge-2026-04-25`. PR #4 (통합 머지)에 누적.

---

## 잘 된 점 (다음에도 그대로 적용)

### 1. V1 무수정 정책 (REQ-NT*-C-002)

V2 작업 시작부터 끝까지 V1 모듈(`backend/services/naver_theme/`)을 한 줄도 수정하지 않음. 결과적으로 V1 단위 테스트 51개가 매 단계 자동으로 회귀 검증 역할을 수행했고, V2 작업이 V1을 깨트리지 않았다는 보장이 즉시 확인됐습니다.

**교훈**: "기존 코드 무수정"을 명시적 정책으로 정하면, 회귀 risk가 사실상 0이 된다. 큰 변경 시 가장 먼저 SPEC에 박아두자.

### 2. Additive only 정책 (REQ-NT3-C-003)

V2 backend metadata에 V1 alias 4 필드(`collected_at`, `theme_count`, `stock_count`, `elapsed_sec`)를 추가할 때, 기존 4 필드(`data_source`, `generated_at`, `total_themes_seen`, `errors`)를 절대 제거/이름변경/dtype변경 안 함. 결과: 기존 V2 24 테스트 모두 그대로 PASS.

**교훈**: 기존 데이터 구조에 새 필드를 추가하는 건 안전. 기존 필드를 손대면 회귀가 폭발한다. SPEC에서 "additive only" 명시하고 acceptance에서 "기존 N 필드 보존" 검증.

### 3. Cohabitation (V1+V2 동시 등록)

V1 endpoint(`/api/themes/snapshot`, `/api/themes/quick`)를 즉시 rollback 경로로 보존. V2 변경이 잘못되어도 frontend `themes.ts` URL을 한 줄 되돌리면 즉시 V1 복귀 가능.

**교훈**: 새 데이터 소스 도입 시 "기존 소스를 죽이지 말고 등록만 유지"가 안전망. 정리(cleanup)는 충분히 안정된 후 별도 SPEC.

### 4. 사용자 결정 사전 잠금 (D-1 ~ D-4)

SPEC-003 plan 시점에 D-1(에러 처리 방식), D-2(tooltip 위치), D-3(description 표시 자리), D-4(null 처리) 4가지를 미리 결정. RUN phase에서 추가 결정 0회, annotation cycle 회피.

**교훈**: "어떻게 만들지" 결정을 plan 시점에 명시하면 RUN이 빠르고 단순해진다. 다중 옵션이 가능한 결정(에러 처리 방식, UI 위치 등)은 plan에서 잠그자. "옵션 A/B/C/D + rationale" 형식 권장.

### 5. 신규 의존성 0건 (REQ-NT*-C-004)

V1과 V2 모두 기존 라이브러리만 사용 (backend: `requests`/`pandas`/`numpy`/`pydantic`/`fastapi`, frontend: `react`/`axios`/`vitest`). D-2 tooltip은 native HTML `title` 속성으로 구현 (Radix Tooltip 미도입). package.json/requirements.txt git diff empty.

**교훈**: 새 기능에 라이브러리 추가는 마지막 수단. 표준 HTML/CSS/JS API로 가능한지 먼저 검토. "신규 의존성 0건"을 명시 정책으로 박으면 자연스럽게 절제된다.

### 6. bare except 금지 (REQ-NT*-C-005)

`except:` 또는 `except Exception:` 사용 금지. specific exception(`requests.RequestException`, `Timeout`, `JSONDecodeError`, `ValidationError` 등)만 catch.

**교훈**: 예외 처리는 "내가 무엇을 catch하는지" 명시. 광범위 catch는 예상 못한 예외를 silently 무시 → 디버깅 지옥.

### 7. 핸드오프 문서 (handoff-frontend-v2.md, 488 lines)

SPEC-002 ship 직후 V2 frontend 채택(SPEC-003)을 위한 self-contained 컨텍스트 문서 작성. SPEC-003 plan 시점에 zero-context에서 시작 가능 → 빠른 plan 작성.

**교훈**: "다음 단계 작업자(사람 또는 AI)가 처음부터 다시 read해도 이해 가능한" 핸드오프 문서가 시간을 절약한다. 큰 변경의 중간 단계마다 작성 권장.

### 8. evaluator-active final-pass

SPEC-003 RUN phase 종료 직전 evaluator-active로 4-dimension 독립 평가 (Functionality 100, Security 90, Craft 92, Consistency 95). Critical 0건. Warning 1건(error 메시지 raw 노출), Suggestion 1건(coverage gap)은 별도 SPEC 후보로 분리.

**교훈**: agent가 "구현 + 자가 검증"으로 PASS라고 선언한 결과를 다른 agent가 skeptical하게 재평가하면 놓친 issue를 발견할 가능성이 있다. Standard harness 이상에서 권장.

---

## 어려웠던 점 (다음에 주의할 것)

### 1. 비공식 endpoint risk

네이버 모바일 API(`m.stock.naver.com/front-api/...`)는 공식 문서가 없는 endpoint. Sentry release tag `stock-web@`이 활발히 변경되어 데이터 구조가 갑자기 바뀔 수 있음.

**대응**:
- D-1 (수동 retry 버튼)으로 사용자가 일시 장애를 인지 가능
- endpoint URL을 `config.py`로 격리(REQ-NT2-NF-005), 변경 시 한 곳만 수정

**교훈**: 비공식 데이터 소스 사용 시 (1) URL을 코드에 inline 박지 말고 config 분리, (2) 실패 시 사용자가 인지할 수 있는 명확한 에러 + retry path를 마련.

### 2. inclusion_reason과 description의 동일 source (D-3 fragility)

V2 mobile parser가 `item.description`을 두 컬럼(`inclusion_reason`, `stock_description`)에 동일하게 채움. 발견 후 → ThemeDetailPanel.tsx 무수정으로 D-3 결정 (변경 0줄).

**Risk**: 미래에 V2 parser 정책이 바뀌면 (두 컬럼이 다른 source를 가지면) ThemeDetailPanel 수정 필요.

**교훈**: "변경 0줄" 결정은 강력하지만 fragile. 의존성을 명확히 SPEC에 명시(REQ-NT3-008 + research §2.3)해서 미래 작업자가 "왜 이 정책에 의존하는지" 알 수 있게 해두자.

### 3. 데스크탑 vs 모바일 인코딩 차이

V1: EUC-KR 강제 처리 필요. V2: UTF-8 (default).

**대응**: V1 코드의 EUC-KR 처리를 그대로 살려둠 (cohabitation), V2는 UTF-8 그대로.

**교훈**: 새 소스로 갈아탈 때 인코딩이 다른 경우, 기존 처리 코드를 무수정으로 두고 새 소스만 깔끔하게 만들면 두 통로가 각자 책임을 갖는다.

### 4. frontend baseline의 e2e/ChartGrid pre-existing fail

본 SPEC와 무관한 1 test fail이 baseline에 있음 (ChartGrid). e2e/*.spec.ts files도 vitest scope에서 setup error.

**대응**: AC-15 (baseline diff 0)을 검증할 때 "신규 fail 0"으로 측정 → 1 fail 그대로 유지.

**교훈**: baseline에 known-fail이 있으면 SPEC AC를 "신규 fail 0" + "기존 fail 그대로 유지"로 명시. "전체 fail 0"으로 잡으면 무관한 기존 fail이 본 SPEC을 막는다.

### 5. SPEC-002 ship 시 CHANGELOG entry 누락

SPEC-002 V2 backend ship(commits `888e2eb`~`b1c24eb`) 시점에 CHANGELOG에 SPEC-002 entry 추가 안됨. SPEC-003 sync에서 함께 보강.

**교훈**: ship phase 직전 sync에서 CHANGELOG entry 추가가 누락되기 쉽다. sync workflow의 명시 checklist에 "CHANGELOG entry 신규 SPEC 추가됐는지" 항목을 두자.

### 6. D-2/D-3 hover tooltip-only 결정의 발견성 함정 (v1.0.1 amendment 사유)

SPEC-003 plan에서 D-2(테마 설명 hover tooltip) + D-3(편입설명 hover tooltip 자리 재사용)을 결정한 이유는 "최소 변경 + 레이아웃 0 영향"이었음. 그러나 사용자 라이브 검증에서 "한눈에 description이 안 보여 데이터가 없어 보인다"는 신고. 네이버 모바일 사이트는 동일 데이터를 본문 텍스트로 항상 표시하고 있어 사용자 기대와 어긋남.

**즉시 대응** (v1.0.1 amendment): ThemeDetailPanel.tsx에 본문 노출 추가, hover tooltip은 보존하여 중복 노출. data-testid 기반 vitest 추가 (AC-16/17). SPEC-003 spec.md HISTORY에 D-3 reverse 명시.

**교훈**:
- "최소 변경" 결정이 항상 좋은 UX는 아님. 데이터의 발견성(discoverability)을 사용자 기준으로 평가해야 함.
- 비교 reference(네이버 모바일 사이트 등)가 있으면 plan 단계에서 reference UX 분석을 명시 — "참조 사이트가 X 위치에 표시한다면 우리도 X 위치에 표시" 정책을 plan에서 잠그면 reverse를 피할 수 있음.
- hover-only UX는 mobile touch 미동작뿐 아니라 desktop에서도 hover 행동이 필요해 발견성이 낮음. **본문 표시 + hover 중복**이 가장 안전.
- amendment(v1.0.x)는 SPEC version만 올리면 되므로 큰 부담은 아님. plan에서 너무 보수적으로 잡는 것보다 라이브 검증 후 amend가 효율적인 경우도 있음.

**적용**: 다음 frontend SPEC에서 hover-only 결정을 할 때, "본문 표시 추가 가능성"을 옵션으로 plan에 함께 기록 → amendment 발동 임계치 낮춤.

### 7. v1.0.2 amendment — 정보 우선순위(IA)는 라이브 화면에서 다시 잡기 (주도주 섹션 제거)

v1.0.1에서 본문 표시를 추가했음에도 사용자는 후속 신고를 함: "주도주" 섹션이 테마명 바로 아래에 자리 잡고 있어서 사용자 시선이 테마 설명보다 먼저 도달함. 네이버 모바일 사이트는 테마 설명을 가장 위에 prominent하게 두고 종목/주도주는 그다음에 배치. v1.0.2 amendment에서 주도주(themeLeaders) 섹션을 완전 제거하고 theme_description 본문 박스를 prominent style(font-size 13, padding 강화, border-left 4px)로 강화.

**핵심 통찰**:
- "코드는 데이터를 노출했다" ≠ "사용자가 데이터를 발견했다". 화면의 자리(IA — Information Architecture)와 비주얼 prominence가 발견성의 절반 이상을 좌우.
- v1.0.1처럼 "데이터를 화면에 추가" 작업이 끝나도, 라이브 화면에서 우선순위(어느 영역이 가장 먼저 시선을 받는가)를 다시 검증해야 함.
- "기존 섹션을 그대로 두고 추가" 패턴은 IA를 변경하지 않는 안전한 변경 같지만, 정작 "새로 추가한 정보가 가장 prominent하지 않은" 결과를 낳을 수 있음.

**교훈**:
- frontend SPEC에서 새 정보를 추가할 때 "가장 위에 둘 것인가, 기존 섹션 다음에 둘 것인가"는 plan 단계 결정 항목으로 명시. 단순 "표시할지 여부"만이 아니라 "어느 위치에 어느 비중으로"까지 기록.
- reference 사이트 비교 시 "어떤 데이터를 노출하느냐"뿐 아니라 "어떤 순서로 어떤 비중으로"도 기록 — 정보 우선순위가 reference 그대로 따라가도록.
- Amendment를 두려워하지 말기. v1.0.1 → v1.0.2처럼 작은 단계로 라이브 검증 후 잡으면 큰 위험 없음. 한 번에 완벽한 plan보다 빠른 iteration이 낫다 (사용자 라이브 신고 기반).

**적용**: SPEC-003 amendment chain (v1.0.0 → v1.0.1 → v1.0.2)을 다른 SPEC에서도 패턴화. 각 amendment는 spec.md HISTORY entry + acceptance.md AC 신규 + 작은 commit으로 정리.

### 8. v1.0.3 amendment — data availability ≠ data display (default mode 함정)

v1.0.2까지 코드에 본문 박스가 추가됐고 vitest도 PASS했음에도 사용자 화면에 description이 안 보임. 원인 추적:
- backend `service.py:92-95`가 detail endpoint 호출 결과로만 `theme_description`을 머지. parser.py 주석에 "list 응답 sectorDescription은 항상 null" 명시.
- frontend ThemeAnalysis.tsx의 default mode가 `'quick'` (list-only) → backend가 description=null 반환 → D-4 hidden 정책으로 본문 박스 미표시.
- 사용자가 "빠른 조회"가 default라 항상 quick 응답만 봤기 때문에 description을 영원히 못 봄.

**핵심 통찰**:
- "코드가 description을 표시할 수 있다" ≠ "사용자 default 화면에 description이 노출된다". data availability와 data display는 default 진입 path에서 만나야 함.
- 빠른 조회/전체 조회 같은 mode 분기가 있을 때 default가 어떤 mode인지가 사용자 첫 인상을 결정.
- backend가 lazy-fill하는 데이터 (detail endpoint에서만 채워지는 필드)는 frontend default mode가 lazy-fill을 트리거하지 않으면 사용자에겐 영원히 안 보임.

**교훈**:
- Frontend SPEC에서 default mode/state는 plan 단계 결정 항목으로 명시. "어느 데이터가 어느 mode에서만 채워지는지" 매트릭스를 plan에 박아두면 default mode 함정을 피할 수 있음.
- Backend의 lazy-fill 정책 (예: detail 호출 시에만 필드 채움)을 frontend SPEC에서도 추적. 둘이 맞물려야 사용자에게 보임.
- "AC PASS = 사용자에게 보임"이 아님. AC는 코드의 정합성 검증이고, 사용자 default path 검증은 별도. plan 단계에서 "default 진입 시 사용자가 보는 정보 매트릭스"를 만들어두면 좋음.
- amendment chain은 두려워하지 말기 (v1.0.0 → v1.0.1 → v1.0.2 → v1.0.3). 사용자 라이브 신고가 amendment 발동 임계치 — 첫 amendment는 코드 추가, 두 번째는 IA 조정, 세 번째는 default path 조정 — 각 단계가 학습 cycle.

**적용**: 다음 frontend SPEC에서 (1) default mode/state를 명시 결정 항목으로, (2) backend lazy-fill 필드 매트릭스를 plan §환경 섹션에 기록, (3) "default 진입 시 사용자가 보는 정보" sanity check를 plan annotation cycle에 포함.

---

## 시리즈 전반 적용 가능 패턴

### 패턴 1 — 데이터 소스 마이그레이션

```
1. 기존 모듈 무수정 정책 명시 (REQ-X-C-002 형태)
2. 새 모듈을 별도 디렉토리/이름공간에 신규 (예: `naver_theme_v2/`)
3. 기존 endpoint와 새 endpoint를 모두 등록 (cohabitation)
4. frontend swap 직전까지 새 모듈 단독 검증 (단위 + 라이브)
5. frontend swap = URL 한 줄 변경 + 타입 확장 (additive)
6. metadata alias 등 frontend 호환 layer는 별도 SPEC 또는 v1.x amendment
7. 충분히 안정 후 V1 cleanup SPEC 별도 진행
```

### 패턴 2 — 사용자 결정 사전 잠금

```
plan 시점에:
  D-N: <결정 항목>
    선택지 A/B/C/D
    각 선택지의 trade-off
    rationale (왜 이걸 선택했나)
  → SPEC plan에 명시 잠금
  → RUN/SYNC phase에서 추가 질문 없이 진행
```

### 패턴 3 — Cohabitation rollback path

```
- 새 endpoint/모듈 도입 시 기존을 즉시 삭제하지 말 것
- routes에 V1+V2 모두 등록 유지
- frontend는 V2만 호출, V1은 dormant
- rollback 명령: `frontend/.../themes.ts` URL 한 줄 V1으로 되돌림
- cleanup은 별도 SPEC (충분히 안정 후)
```

---

## 미해결 / 후속 작업 (별도 SPEC 후보)

| 후보 | 동기 | 선행 조건 |
|---|---|---|
| SPEC-NAVER-THEME-CACHE | 30s API 호출 캐시 정책 (TTL, lru_cache) | SPEC-003 ship 후 권장 |
| SPEC-NAVER-THEME-V1-CLEANUP | V1 endpoint/모듈 dead code 제거 | V2 충분히 안정 후 |
| SPEC-NAVER-THEME-MOBILE-UX | mobile touch에서도 theme_description 표시 | Radix/custom Tooltip 도입 검토 |
| SPEC-NAVER-THEME-STOCK-DESC | stock_description 별도 컬럼 표시 (D-3 옵션 A) | desktop 가로 폭 여유 검토 |
| SPEC-NAVER-THEME-LENGTH-LIMIT | description 길이 제한 (line-clamp 등) | 라이브 데이터에서 가독성 검토 |
| SPEC-NAVER-THEME-ERR-MASKING | ThemeAnalysis.tsx raw e.message 마스킹 (evaluator hardening) | 작은 SPEC, 즉시 가능 |
| SPEC-NAVER-THEME-AC12-COVER | AC-12 success-transition 추가 검증 (evaluator suggestion) | 작은 SPEC, 즉시 가능 |

---

## 환경 메모

- branch: `chore/integrated-main-merge-2026-04-25` (SPEC-001 V1 ship부터 SPEC-003 V2 frontend ship까지 누적)
- PR: PR #4 (통합 머지) — head=`chore/integrated-main-merge-2026-04-25`, base=`main`
- git author 자동 설정: `byunjungwon@JW.local` (사용자가 explicit user.name/email 설정 안함)
- `.moai/learnings/` 디렉토리: 본 SPEC 시리즈에서 신규 생성 (이전에는 부재)
- 비개발자용 종합 가이드: `docs/theme-analysis-guide.md` (본 문서와 함께 작성됨)

---

Version: 1.0.0
Created: 2026-05-06
Source: SPEC-NAVER-THEME-003 sync phase 직후 시리즈 회고
