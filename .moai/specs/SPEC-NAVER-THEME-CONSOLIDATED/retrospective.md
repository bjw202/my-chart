# SPEC-NAVER-THEME 시리즈 회고 (Retrospective)

본 회고는 SPEC-NAVER-THEME-001/002/003에 걸친 7일간의 작업과 5건의 amendment를 통해 학습한 내용을 정리한다. 본 SPEC 시리즈는 결과적으로 사용자에게 의도한 기능을 전달했지만, "전달까지 5번 다시 작업해야 했다"는 사실 자체가 SPEC 작성 단계의 빈틈을 지목한다. 회고의 목적은 다음 SPEC에서 동일 비용을 반복하지 않도록 lessons.md 체크리스트로 변환하는 데 있다.

---

## 1. 시리즈 개요

| 항목 | 값 |
| --- | --- |
| 기간 | 2026-05-01 ~ 2026-05-07 (7일) |
| SPEC 수 | 3 (001 V1 / 002 V2 backend / 003 V2 frontend) |
| Amendment 수 | 5 (v1.0.1 ~ v1.0.5, 모두 SPEC-003) |
| Amendment 발생 시점 | v1.0.0 ship(2026-05-06) 후 1일 내 v1.0.1~v1.0.4, 다음 날 v1.0.5 |
| 최초 ship | V2 frontend v1.0.0 commit `6284280` (2026-05-06) |
| 최종 ship | v1.0.5 commit `4e75f14` (2026-05-07, 다음 날) |
| 전체 frontend 변경 LOC | +3050 / -19 (16 files) |
| 최종 AC 수 | 24 (SPEC-003 기준), 통합 SPEC 25 AC |
| evaluator-active 점수 | Func 100 / Sec 90 / Craft 92 / Cons 95 (v1.0.0 ship 시점) |

특이사항: SPEC-002는 frontmatter `status: Draft`로 남았으나 commits `888e2eb~b1c24eb`로 실제 ship 완료. 본 통합 작업 시점에 발견되어 SPEC-002 frontmatter를 `Implemented`로 보정하는 HISTORY 라인 추가.

---

## 2. Timeline

| 날짜 | SPEC / Amendment | 핵심 변경 | 트리거 |
| --- | --- | --- | --- |
| 2026-05-01 | SPEC-001 v1.0.0 Implemented (`12d81b1`) | V1 desktop EUC-KR HTML 크롤러 ship. 5종 DataFrame, 14 AC, 51 단위 테스트, 99% 커버리지 | 신규 기능 요청 |
| 2026-05-01 | SPEC-002 v1.0.0 ship (`888e2eb~b1c24eb`) | V2 mobile JSON API 추가, Cohabitation Option γ, theme_description/stock_description 신규 컬럼, bare except 금지 신규 명문화 | V1 EUC-KR 안정성·신규 컬럼 필요성 |
| 2026-05-06 | SPEC-003 v1.0.0 ship (`6284280`) | V2 frontend 채택. endpoint URL swap, theme_name hover Tooltip, 503 error+retry, V1 alias metadata | V2 backend ship 완료 후속 |
| 2026-05-06 | v1.0.1 amendment | hover-only → 본문 표시 reverse. theme_description 본문 박스 + stock inclusion_reason 본문 노출 | 사용자 라이브 검증 — hover undiscoverable |
| 2026-05-06 | v1.0.2 amendment (`3ecd97c`) | 주도주 섹션 제거 + theme_description prominent 강화 | 네이버 모바일 UX의 "테마 설명 우선" prominence와 mismatch |
| 2026-05-06 | v1.0.3 amendment (`2a43dc3`) | default mode 'quick' → 'full' + quick advisory | "본문 박스 추가했는데 화면에 안 보인다" — quick 응답 sectorDescription=null |
| 2026-05-06 | v1.0.4 amendment (`07de0bd`) | strong_themes_df theme_description post-loop 머지 | full 모드에서도 description hidden — themes_df ↔ strong_themes_df 컬럼 전파 결함 |
| 2026-05-07 | v1.0.5 amendment (`4e75f14`, `4c2d7bb`) | localStorage 캐시 + 🔄 갱신 버튼 | "탭 전환 시 30초 재크롤링 왜?" — 사용 패턴 가정 미수립 |

---

## 3. 5개 Amendment의 발생 사유 분석

### v1.0.1 — hover-only Tooltip의 발견성 부족

**표면 증상**: 사용자가 V2 frontend 채택 후 화면을 확인했을 때 theme_description이 hover로만 보여 "한눈에 들어오지 않는다"고 신고. 네이버 모바일 UX는 description을 본문으로 prominent하게 노출.

**Root cause (코드)**: `ThemeRankingTable.tsx`의 `title={theme.theme_description ?? undefined}` 한 줄(D-2). hover tooltip은 desktop에서 사용자가 마우스를 1초간 hold해야 발견되며, 화면 진입 직후에는 아무 표시가 없다.

**Root cause (SPEC)**: D-3 결정에서 "hover tooltip + ThemeDetailPanel 무수정"을 v1.0.0에 잠금. `ThemeDetailPanel.tsx` 무수정을 LOC 0으로 자랑한 결과, 화면에 description이 본문으로 나타나는 경로 자체가 막혔다.

**SPEC에 들어있어야 했던 항목**:
- AC: "default 진입 화면에서 theme_description이 보이는가" (hover 의존 검증 금지)
- "라이브 화면 검증 후 D-3 잠금" 또는 "프로토타입 스크린샷으로 D-3 사전 검증" 단계

**비용**: REQ-NT3-009/010 신규 추가, ThemeDetailPanel.tsx 본문 박스 + 종목 inclusion_reason 본문 컨테이너 추가, AC 15→17 (2개 신규), vitest 케이스 추가.

### v1.0.2 — 시각 우선순위 미정의

**표면 증상**: v1.0.1 적용 후 사용자 스크린샷 비교 신고. v1.0.1의 본문 박스는 추가됐으나 화면에 "주도주" 섹션이 테마명 직후 가장 위에 위치하여, 네이버 모바일의 "테마 설명 우선" prominence와 정반대 순서가 됐다.

**Root cause (코드)**: `ThemeDetailPanel.tsx`의 섹션 순서가 `[테마 헤더] → [주도주 카드 섹션] → [종목 테이블] → [theme_description 본문 박스]`. theme_description이 가장 마지막에 배치되어 스크롤 없이 안 보임.

**Root cause (SPEC)**: SPEC-003 v1.0.0/v1.0.1 어느 곳에도 "시각 우선순위(prominence priority)"가 명시되지 않음. 컴포넌트 레이아웃의 "어떤 정보가 가장 prominent해야 하는가"에 대한 결정이 없어서, 구현자는 코드 추가가 쉬운 위치에 본문 박스를 넣었다.

**SPEC에 들어있어야 했던 항목**:
- §3 Functional 또는 별도 "Visual Hierarchy" 섹션에 prominence priority 명시: "theme_description > stock list > [optional] leaders"
- AC: "ThemeDetailPanel 첫 visible 영역(스크롤 0)에 theme_description 본문 박스가 포함되어 있는가"

**비용**: REQ-NT3-011 신규 (주도주 섹션 제거), REQ-NT3-009 styling 강화 (font 12→13, text-secondary→text-primary, padding 8/12→12/14, border-radius 6→8, border-left 3→4px), AC 17→18 (1개 신규).

### v1.0.3 — default 모드와 데이터 가시성 관계 누락

**표면 증상**: v1.0.2까지 본문 박스 코드는 추가됐는데 사용자 화면에 "여전히 안 보인다" 신고. 코드는 존재하지만 컨테이너 렌더 조건(`theme.theme_description이 non-null/non-empty`)이 만족되지 않음.

**Root cause (코드)**: `ThemeAnalysis.tsx`의 `useState<LoadMode>('quick')` 초기값. quick 모드는 `/api/themes/v2/quick` endpoint를 호출하고, 이 endpoint는 list endpoint만 사용하며 list 응답의 `sectorDescription`은 항상 null. 따라서 quick 모드 사용자는 detail loop 없이 description=null 응답만 받게 된다.

**Root cause (SPEC)**: "default 모드는 무엇이며, default 모드 진입 시 신규 기능(theme_description)이 보이는가?"라는 질문이 SPEC-003 어느 곳에도 없음. v1.0.0/v1.0.1/v1.0.2 모두 default 모드를 변경할 이유가 없었으므로 'quick'을 유지했고, 이는 사용자 진입 시점에 theme_description이 영원히 안 보이는 결과를 초래.

**SPEC에 들어있어야 했던 항목**:
- §2 Assumptions: "list 응답 sectorDescription은 항상 null이므로 description 표시는 detail 호출에 의존" (parser.py 주석에는 명시되어 있었으나 SPEC body 외부)
- AC: "default 모드 진입 시 신규 기능 가시성 검증" — 어떤 모드든 default가 신규 기능 표시를 막지 않는가?

**비용**: REQ-NT3-012 (default 'full', 코드 1줄 변경), REQ-NT3-013 (quick advisory 박스 신규), AC 18→20 (2개 신규). 사용자 입장에서는 1일 동안 v1.0.0/v1.0.1/v1.0.2 모두 "안 보인다" 상태.

### v1.0.4 — 백엔드 데이터 흐름 추적 부재

**표면 증상**: v1.0.3로 default 'full'을 적용해 detail loop가 호출되는데도 사용자가 클릭한 테마의 ThemeDetailPanel에 description이 여전히 hidden. 라이브 응답 직접 확인 결과 `themes` 배열에는 description=274자(예: "유리 기판") 채워지나 `strong_themes` 배열에는 description=0자(empty).

**Root cause (코드)**: `backend/services/naver_theme_v2/service.py:73`이 `strong_themes_df = build_strong_themes(themes_df, ...)`를 detail 호출 전에 빌드. 라인 92-95의 detail 머지가 `themes_df`에만 적용됨. 결과적으로 `strong_themes_df["theme_description"]`은 None 상태로 머무름. frontend `ThemeAnalysis.tsx:80`의 `data?.strong_themes ?? data?.themes` 패턴이 strong_themes 우선이라 사용자가 클릭한 selectedTheme은 description=null인 strong_themes에서 매핑됨 → ThemeDetailPanel의 D-4 hidden 정책 발동.

**Root cause (SPEC)**: SPEC-002와 SPEC-003 어디에도 "themes_df → strong_themes_df 컬럼 전파"가 도식 또는 본문 텍스트로 추적되지 않음. 같은 schema의 dataframe이 다수 존재하고 detail loop가 한쪽에만 머지되는 구조는 SPEC body에서 시각화되지 않으면 발견하기 어렵다. 이 결함은 v1.0.0 RUN 시점부터 존재했으나, v1.0.3에서 default 'full'을 켜기 전까지는 사용자 경로에 도달하지 않아 발견되지 않았다.

**SPEC에 들어있어야 했던 항목**:
- §1 Environment에 데이터 흐름 도식(`list → themes_df → build_strong_themes → strong_themes_df → detail merge → post-loop merge`) 추가
- AC: "snapshot (full) 응답의 `strong_themes` 배열이 `themes` 배열과 동일한 description을 보유하는가" — themes_df ↔ strong_themes_df 컬럼 일관성 통합 테스트

**비용**: REQ-NT3-014 신규 (post-loop 머지 1줄 코드, 그러나 backend pytest 신규 AC 1개), AC 20→21 (1개 신규). 사용자 입장에서는 v1.0.3 적용 후에도 "안 보인다"가 유지되어 추가 1라운드 디버깅.

### v1.0.5 — 사용 패턴 가정 미수립

**표면 증상**: 사용자 신고 — "한 번 크롤링 했는데 다른 메뉴 갔다오면 왜 다시 크롤링을 하느라 시간을 쓰지?" 탭 전환/페이지 새로고침/모드 토글 모든 시점에 30초 fetch 재발생.

**Root cause (코드)**: backend stateless (REQ-NT-C-004) + frontend `ThemeAnalysis` 컴포넌트가 `useEffect`로 mount 시점에 자동 fetch. 캐시는 backend·frontend 양쪽에 0.

**Root cause (SPEC)**: SPEC-001의 §2 Assumptions [A-8]에 "호출자(라우터 레벨)에서 메모리 dict 기반 TTL 캐싱을 수행한다"고 명시되어 있으나 실제로는 라우터에 캐싱 미구현. 더 본질적으로는 "이 기능을 누가, 얼마나 자주, 어떤 freshness 기대치로 사용하는가"라는 사용 패턴 가정이 SPEC-001/002/003 어디에도 명시되지 않음. 다인 협업 환경이라면 backend TTL 캐시가 적합하지만, 단일 사용자 환경(이 프로젝트 실제)이라면 frontend localStorage가 더 단순하고 효과적이다. SPEC이 사용 패턴을 가정하지 않은 결과, 자동 fetch 모델로 ship되었다가 1일 후 수동 갱신 모델로 전환됐다.

**SPEC에 들어있어야 했던 항목**:
- §2 Assumptions: "단일 사용자 + Chart Grid DB 수동 업데이트 패턴과 일관된 freshness 기대치"
- §3 Functional 또는 §4 AC: "캐시 모델 결정 — 자동 TTL vs 수동 갱신, 어느 layer에서 보관"

**비용**: REQ-NT3-015/016 신규 (localStorage 캐시 + 🔄 갱신 버튼), `ThemeAnalysis.tsx`만 수정 + frontend 단위 테스트 1 파일에 케이스 3개 추가, AC 21→24 (3개 신규).

---

## 4. SPEC 빈틈 카테고리화

5개 amendment의 root cause를 일반화하면 다음 5개 카테고리가 추출된다. 각 카테고리는 lessons.md의 LESSON-NTC-NNN 항목으로 1:1 매핑된다.

### 4.1 UX 발견성 검증 누락 (v1.0.1 근거)

UX 정책이 "코드 변경 0"으로 잠긴 상태에서 라이브 화면 검증 없이 ship 됨. hover tooltip / placeholder hidden / 본문 표시 등 발견성(discoverability)에 영향을 주는 결정은 화면을 직접 보지 않으면 평가가 불가능하다. SPEC 단계에서 "결정 사항을 잠그기 전에 라이브 화면 또는 충실한 프로토타입으로 검증" 단계를 명시할 것.

### 4.2 시각 우선순위 미정의 (v1.0.2 근거)

여러 정보 영역이 한 화면에 공존할 때 "어떤 정보가 가장 prominent해야 하는가"의 우선순위 결정이 SPEC body에 없으면, 구현자는 코드 작성이 쉬운 순서대로 배치한다. SPEC이 visual hierarchy를 명시하지 않으면 화면 결과는 임의가 된다. SPEC body에 prominence priority(또는 reading order, layout zone)를 명시할 것.

### 4.3 default 모드와 데이터 가시성 관계 누락 (v1.0.3 근거)

신규 기능을 화면에 표시하는 코드를 작성했더라도, 그 기능이 default 모드 진입 시 보이지 않으면 사용자는 영원히 인지하지 못한다. "어떤 모드가 default인가" + "default 모드의 데이터 응답이 신규 기능을 포함하는가"는 별개 질문이며 둘 다 SPEC AC로 검증해야 한다.

### 4.4 백엔드 데이터 흐름 추적 부재 (v1.0.4 근거)

같은 schema의 dataframe(또는 동일 데이터 객체의 변형)이 다수 존재하고 그 사이에 detail merge / aggregation / projection이 발생하는 구조는 SPEC body에 도식 또는 본문 추적이 없으면 누락이 발생한다. v1.0.4의 themes_df → strong_themes_df 전파 누락은 코드 1줄로 해결 가능했지만, SPEC에 도식이 있었다면 v1.0.0 RUN 시점에 발견됐을 것이다.

### 4.5 사용 패턴 가정 미수립 (v1.0.5 근거)

"누가, 얼마나 자주, 어떤 freshness 기대치로 사용하는가"가 SPEC §2 Assumptions에 없으면, 캐시·자동 fetch·refresh 모델 등 운영 정책 결정이 임의가 된다. 단일 사용자 / 다인 협업 / 외부 사용자 / 자동화 호출 등 사용 패턴 가정을 SPEC §2에 명시할 것.

---

## 5. 잘 됐던 것 (계속 유지할 패턴)

### 5.1 결정 사항 D-1~D-7 사전 잠금

SPEC-003 v1.0.0이 D-1(에러 처리), D-2(tooltip), D-3(자리 재사용), D-4(null hidden) 4개를 annotation cycle에서 사전 잠근 결과, RUN phase에서 추가 라운드트립 없이 ship 가능했다. v1.0.2 이후의 D-5~D-7도 amendment 시점에 명시적으로 추가되어 후속 작업에서 일관성을 유지함. **결정 사항을 SPEC에 명문화하는 패턴은 유지한다.**

### 5.2 Cohabitation Option γ — V1 byte-identical 보존

V2 ship 후에도 V1 endpoint·모듈을 무수정 보존하는 정책 덕분에, V2 endpoint URL 변경 risk(R-1) 또는 V2 backend regression 시 즉시 rollback 경로가 항상 열려 있었다. SPEC-002 REQ-NT2-C-002 / SPEC-003 REQ-NT3-C-001/C-002로 byte-identical 보존이 명문화된 것이 안전망 역할을 함. **Cohabitation 정책은 다른 시리즈에도 채택할 가치가 있다.**

### 5.3 bare except 금지를 SPEC-002에서 신규 명문화

SPEC-001 RUN phase에서 일부 모듈이 `except Exception`을 사용해 진단성이 떨어진 교훈을, SPEC-002 REQ-NT2-C-005로 신규 constraint 추가. SPEC-003 REQ-NT3-C-005로 계승. 결과적으로 v1.0.5 ship 시점까지 bare except 0건 유지. **이전 SPEC의 RUN phase 교훈을 다음 SPEC의 constraint로 명문화하는 패턴은 효과 입증.**

### 5.4 AC를 amendment마다 누적 추가

v1.0.0 → v1.0.1 (15→17) → v1.0.2 (17→18) → v1.0.3 (18→20) → v1.0.4 (20→21) → v1.0.5 (21→24)로 AC가 단조 증가. amendment마다 새 검증 수단이 함께 추가되어, 회귀 보호망이 점점 두꺼워짐. **AC 누적은 다음 amendment의 회귀를 막는다.**

### 5.5 라이브 검증 commits로 빠른 피드백 루프

v1.0.4의 root cause는 "라이브 응답 직접 확인 결과 `themes`에는 description=274자, `strong_themes`에는 0자"라는 명확한 증거에서 나옴. v1.0.3의 root cause도 라이브 list endpoint 응답 직접 확인. **라이브 검증 → 정확한 root cause → 최소 코드 변경의 사이클은 효율적이었다.**

---

## 6. 비싸게 배운 것

### 6.1 v1.0.1 reverse — D-3 hover-only 정책 잠금

SPEC-003 v1.0.0이 "ThemeDetailPanel.tsx 무수정 = LOC 0 = elegant"로 D-3를 잠갔다. 화면 검증 없이 잠근 결과 1일 후 reverse. **결정의 elegance(코드 변경 0)와 결과의 effectiveness(사용자가 기능을 발견)는 분리된 차원이다.**

### 6.2 v1.0.3 default 모드 — 가시성 질문 부재

"default 진입에서 핵심 컬럼이 보이는가?"라는 1개 질문이 SPEC AC에 있었다면 v1.0.0 RUN phase에서 잡혔을 결함. 코드 변경 1줄로 해결 가능했지만, 사용자 입장에서는 v1.0.0/v1.0.1/v1.0.2 1일 동안 "안 보인다" 상태가 누적됨.

### 6.3 v1.0.4 데이터 흐름 — themes_df → strong_themes_df 전파 누락

코드 1줄 추가로 해결됐지만, SPEC body에 데이터 흐름 도식이 없어서 v1.0.0 RUN 시점에 발견되지 않음. v1.0.3 default 'full' 적용 후에야 사용자 경로에 도달. **"같은 데이터의 변형이 여러 개 존재하는 구조"는 도식 없이 정확히 구현하기 어렵다.**

### 6.4 v1.0.5 캐시 모델 — 사용 패턴 가정 미수립

SPEC-001 §2 Assumptions [A-8]은 라우터 레벨 캐싱을 가정했으나 실제 라우터에는 캐싱 미구현. 더 근본적으로 "단일 사용자 vs 협업"이라는 사용 패턴 결정이 없어서 backend TTL vs frontend localStorage vs 수동 갱신 모델 중 어느 것을 채택할지 임의가 됨. 1일 후 frontend localStorage + 수동 갱신 모델로 정착.

---

## 7. 권장 후속 액션

### 7.1 다음 SPEC 작성 시 lessons.md 체크리스트 사용

본 회고에서 도출된 5개 anti-pattern은 `lessons.md`의 LESSON-NTC-001~005에 체크리스트 형태로 정리됨. 다음 SPEC 작성자는 SPEC §3 Functional / §4 AC 작성 직전에 체크리스트를 review.

### 7.2 EARS template 보강 검토 (선택)

회고 §4의 5개 카테고리는 현재 EARS template에 명시적 슬롯이 없다. 향후 EARS template 진화 시 다음 슬롯 추가를 검토:
- "Visual hierarchy" 섹션 (4.2 카테고리 대응)
- "Default mode visibility check" AC 자동 생성 (4.3 카테고리 대응)
- "Data flow diagram" 슬롯 in §1 Environment (4.4 카테고리 대응)
- "Usage pattern assumptions" 슬롯 in §2 Assumptions (4.5 카테고리 대응)
- "Live UX verification step" pre-D-lock 단계 (4.1 카테고리 대응)

### 7.3 SPEC-002 status 보정

SPEC-002 frontmatter의 `status: Draft`는 실제 ship 상태와 불일치. 본 통합 작업의 SPEC-002 HISTORY append 시점에 `status: Implemented`로 보정. 향후 SPEC ship 직후 frontmatter 업데이트를 RUN phase 종료 절차에 포함하는 것을 검토.

---

Version: 1.0.0
Last Updated: 2026-05-07
Source: SPEC-NAVER-THEME-001/002/003 시리즈 (2026-05-01 ~ 2026-05-07)
