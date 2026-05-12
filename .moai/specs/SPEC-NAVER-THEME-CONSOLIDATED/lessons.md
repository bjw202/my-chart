# SPEC-NAVER-THEME 시리즈 Lessons (다음 SPEC 체크리스트)

본 문서는 SPEC-NAVER-THEME-001/002/003 시리즈에서 발생한 5건의 amendment 분석(`retrospective.md`)을 다음 SPEC 작성 단계에서 체크리스트로 활용하기 위한 anti-pattern 모음이다. 각 LESSON-NTC-NNN은 SPEC §3 Functional / §4 AC 작성 직전에 review해야 한다.

---

## LESSON-NTC-001: UX 정책은 라이브 화면 검증 후에만 잠근다

**카테고리**: UX 검증

**잘못된 패턴**:
SPEC-003 v1.0.0이 D-3 결정 사항을 "ThemeDetailPanel.tsx 무수정 = LOC 0"의 elegance로 잠갔다. hover tooltip 단독 노출이 사용자에게 발견(discoverable) 가능한지 라이브 화면 검증 없이 잠근 결과, ship 1일 후 v1.0.1에서 본문 표시로 reverse하는 비용 발생.

**올바른 접근**:
사용자에게 보이는 UX 결정(hover vs 본문, placeholder hidden vs 표시, 컴포넌트 위치 등 발견성/가시성에 영향을 주는 결정)은 SPEC annotation cycle에서 잠그기 전에 다음 중 하나로 검증한다:
1. 동등 화면의 라이브 스크린샷 (참조 사이트가 있는 경우 — 본 시리즈에서는 네이버 모바일)
2. 충실한 프로토타입(static HTML 또는 Figma)
3. 결정 직후 1차 ship 후 즉시 라이브 검증 → 결과에 따라 결정 재검토

코드 변경 0(elegance)과 사용자가 기능을 발견함(effectiveness)은 분리된 차원임을 SPEC 작성자가 인지한다.

**SPEC 작성 시 체크 항목**:
- [ ] D-N 결정 사항 중 사용자에게 보이는 UX 정책은 라이브 화면 또는 프로토타입 검증을 거쳤는가?
- [ ] 결정의 elegance 메트릭(LOC, 컴포넌트 무수정 등)이 결정의 effectiveness 평가를 대체하지 않는가?
- [ ] hover-only / tooltip-only / placeholder-hidden 정책은 발견성을 별도 AC로 검증하는가?

**근거 amendment**: v1.0.1 (SPEC-NAVER-THEME-003)

---

## LESSON-NTC-002: 시각 우선순위(prominence priority)를 SPEC body에 명시한다

**카테고리**: SPEC 작성

**잘못된 패턴**:
SPEC-003 v1.0.0/v1.0.1 어디에도 ThemeDetailPanel 내부의 시각 우선순위 결정이 없었다. 결과적으로 v1.0.1 본문 박스 추가 시 구현자가 코드 추가가 쉬운 위치(맨 아래)에 본문 박스를 넣었고, "주도주" 섹션이 가장 위에 위치해 네이버 모바일의 "테마 설명 우선" prominence와 정반대 순서가 됐다. v1.0.2에서 주도주 섹션 제거 + theme_description prominent 강화로 reverse.

**올바른 접근**:
한 화면에 여러 정보 영역이 공존할 때, SPEC §3 Functional 또는 별도 "Visual Hierarchy" 섹션에 prominence priority(또는 reading order, layout zone)를 명시한다:
- "theme_description > stock list > leaders" 같은 순서 정의
- "default 화면 진입 시 스크롤 0 위치에서 보여야 하는 영역"
- 참조 사이트가 있는 경우 "X 사이트의 prominence 순서를 그대로 따른다" 명시

**SPEC 작성 시 체크 항목**:
- [ ] 화면에 여러 정보 영역이 공존하는가? Yes → Visual hierarchy 명시 필수
- [ ] AC에 "ThemeDetailPanel 첫 visible 영역(스크롤 0)에 X가 포함되어 있는가" 같은 위치 검증 항목이 있는가?
- [ ] 참조 사이트가 있는 경우 SPEC body에서 prominence 순서를 1:1 인용했는가?

**근거 amendment**: v1.0.2 (SPEC-NAVER-THEME-003)

---

## LESSON-NTC-003: default 모드 진입 시 신규 기능이 보이는지 별도 AC로 검증한다

**카테고리**: SPEC 작성

**잘못된 패턴**:
SPEC-003 v1.0.0~v1.0.2가 theme_description 표시 코드를 추가하면서 default 모드(`useState<LoadMode>('quick')`)는 변경하지 않았다. quick 모드는 list endpoint만 호출하고 list 응답의 `sectorDescription`은 항상 null이라, default로 진입한 사용자는 description 본문 박스를 영원히 볼 수 없었다. v1.0.3에서 default 'full'로 변경 + advisory 추가로 해결.

**올바른 접근**:
신규 기능 또는 신규 컬럼을 SPEC에 추가할 때, "default 모드 진입 시 해당 기능이 사용자 화면에 표시되는가"를 별도 AC로 명시한다. 이는 다음 두 질문이 결합된 것이다:
1. 어떤 모드가 default인가?
2. default 모드의 backend 응답이 신규 기능 데이터를 포함하는가?

backend assumption(예: "list 응답은 description=null")이 SPEC §2에 명시되어 있더라도, "default 진입 가시성"은 별도 AC가 필요하다. Assumption은 데이터 형태를 기술할 뿐, 사용자 경로를 검증하지 않는다.

**SPEC 작성 시 체크 항목**:
- [ ] 신규 기능 / 신규 컬럼이 표시되는 코드 경로는 default 모드 진입 시 활성화되는가?
- [ ] AC에 "default 진입 후 신규 기능이 화면에 보이는가" 항목이 있는가?
- [ ] backend assumption(예: "X 응답은 null")이 frontend 가시성에 미치는 영향이 SPEC body에서 추적되는가?
- [ ] 사용자가 default 외 모드를 선택했을 때 기능 부재를 인지할 수 있는 advisory가 있는가?

**근거 amendment**: v1.0.3 (SPEC-NAVER-THEME-003)

---

## LESSON-NTC-004: 같은 schema dataframe 다수가 존재할 때 컬럼 전파 도식을 §1 Environment에 포함한다

**카테고리**: 데이터 흐름

**잘못된 패턴**:
SPEC-002와 SPEC-003 어디에도 backend의 `themes_df → strong_themes_df → detail merge → response` 데이터 흐름 도식이 없었다. `service.py:73`이 `strong_themes_df = build_strong_themes(themes_df, ...)`를 detail 호출 전에 빌드하고, 라인 92-95의 detail 머지가 `themes_df`에만 적용되는 구조가 SPEC body에서 시각화되지 않아, v1.0.0 RUN 시점에 누락이 발견되지 않음. v1.0.4에서 post-loop 머지 1줄로 해결.

**올바른 접근**:
같은 schema의 dataframe(또는 동일 데이터 객체의 여러 변형)이 다수 존재하고 그 사이에 detail merge / aggregation / projection이 발생하는 구조는 SPEC §1 Environment에 도식으로 명시한다:
```
list endpoint
   ↓
themes_df (X=null)
   ↓
build_strong_themes(themes_df)
   ↓
strong_themes_df (X=null, here be dragons)
   ↓
for each: detail merge into themes_df (X populated)
   ↓
post-loop: themes_df → strong_themes_df mapping (X populated everywhere)
```

또한 §4 AC에 통합 테스트 항목으로 "themes_df ↔ strong_themes_df 컬럼 일관성 검증"을 포함한다.

**SPEC 작성 시 체크 항목**:
- [ ] 같은 schema dataframe(또는 데이터 객체 변형)이 2개 이상인가? Yes → §1 Environment에 데이터 흐름 도식 추가 필수
- [ ] frontend가 backend 응답의 어느 배열/key를 우선 사용하는가? 그 우선순위에 대해 SPEC body에 명시되어 있는가?
- [ ] AC에 "응답 내 동일 의미 컬럼이 모든 배열에서 일관된 값을 갖는가" 검증이 있는가?
- [ ] detail merge / aggregation 함수의 호출 순서가 SPEC body에서 추적 가능한가?

**근거 amendment**: v1.0.4 (SPEC-NAVER-THEME-003)

---

## LESSON-NTC-005: 사용 패턴 가정을 SPEC §2 Assumptions에 명시하고 캐시 모델 결정을 도출한다

**카테고리**: 사용 패턴 가정

**잘못된 패턴**:
SPEC-001 §2 Assumptions [A-8]에 "호출자(라우터 레벨)에서 메모리 dict 기반 TTL 캐싱을 수행한다"고 가정만 명시되어 있고 실제 라우터에는 캐싱 미구현. 더 근본적으로 "이 기능을 누가, 얼마나 자주, 어떤 freshness 기대치로 사용하는가"라는 사용 패턴 결정이 SPEC-001/002/003 어디에도 없어서, 자동 fetch 모델로 ship 후 1일 만에 사용자 신고("탭 전환 시 30초 재크롤링 왜?"). v1.0.5에서 frontend localStorage + 수동 갱신 모델로 전환.

**올바른 접근**:
SPEC §2 Assumptions에 다음 항목을 명시한다:
- 사용자 수: 단일 사용자 / 다인 협업 / 외부 사용자 / 자동화 호출
- 호출 빈도 기대치: "1일 1회" / "장중 5분 단위" / "사용자 트리거 only"
- Freshness 기대치: "실시간" / "분 단위 신선" / "수동 갱신" / "stale 허용"
- 일관 모델 references: "Chart Grid DB 수동 업데이트 패턴과 동일" 같은 프로젝트 내 기존 모델 참조

이로부터 캐시·자동 fetch·refresh UI 결정을 도출한다:
- 단일 사용자 + 수동 갱신 → frontend localStorage + 명시적 버튼
- 다인 협업 + 분 단위 신선 → backend TTL 캐시 + 자동 refresh
- 외부 사용자 + 실시간 → backend stateless + 매 요청 fresh

**SPEC 작성 시 체크 항목**:
- [ ] §2 Assumptions에 사용자 수 / 호출 빈도 / freshness 기대치가 명시되어 있는가?
- [ ] 캐시 layer(none / backend TTL / frontend localStorage / 둘 다)가 결정되어 있는가?
- [ ] 자동 fetch 트리거(mount, mode 변경, 페이지 새로고침)별 동작이 명시되어 있는가?
- [ ] 프로젝트 내 기존 동등 기능의 fetch 모델(예: Chart Grid)과 일관성이 있는가? 다르다면 그 이유가 §2에 있는가?

**근거 amendment**: v1.0.5 (SPEC-NAVER-THEME-003)

---

## LESSON-NTC-006 (보너스): SPEC ship 직후 frontmatter status를 보정한다

**카테고리**: SPEC 작성

**잘못된 패턴**:
SPEC-002가 commits `888e2eb~b1c24eb`로 실제 ship 완료됐으나 frontmatter `status: Draft`로 남았다. 본 통합 작업 시점에 발견되어 보정 대상이 됨. ship 시점에 frontmatter 갱신이 RUN phase 종료 절차에 포함되지 않은 결과.

**올바른 접근**:
RUN phase 종료 직후(또는 ship commit과 같은 PR 안에서) frontmatter status를 `Implemented`로 갱신한다. HISTORY 라인에도 "ship 완료" 항목을 추가한다.

**SPEC 작성 시 체크 항목**:
- [ ] RUN phase 종료 직후 frontmatter `status` 갱신을 ship checklist에 포함했는가?
- [ ] HISTORY 라인이 ship commit hash와 함께 추가되었는가?

**근거 사례**: SPEC-NAVER-THEME-002 (frontmatter Draft, 실제 Implemented — 본 통합 시점에 발견)

---

Version: 1.0.0
Last Updated: 2026-05-07
Source: `retrospective.md` §4 카테고리화에서 1:1 매핑
Usage: 다음 SPEC의 §3 Functional / §4 AC 작성 직전에 본 체크리스트 review
