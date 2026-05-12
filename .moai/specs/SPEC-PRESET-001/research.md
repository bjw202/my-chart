# 프리셋 필터 시스템 리서치 (Frontend)

- SPEC-ID: SPEC-PRESET-001
- 작성일: 2026-04-21
- 상태: 리서치 완료
- 목적: 미너비니·스테이지 기반 원클릭 필터 프리셋 UX 를 React + TypeScript + Vite 프런트엔드에 도입하기 위한 기초 조사
- 범위: 프런트엔드 UI/UX, 상태 관리, URL 동기화, 드리프트 감지. 백엔드 엔진 로직은 SPEC-MINERVINI-001 의 책임이다.

---

## 1. 배경과 문제 정의

### 1.1 현재 상태 (2026-04-21 기준)

`frontend/src/components/FilterBar/FilterBar.tsx` 는 다음 구성 요소를 단일 폼으로 노출한다:

- `MarketCapFilter` (시가총액 최소값)
- `ReturnFilter` (1주 / 1개월 / 3개월 수익률)
- `PatternBuilder` (이동평균 패턴 조건, 최대 **3개**)
- `RSFilter` (상대강도 최소값)
- `DbUpdateButton`

사용자가 "미너비니 풀 세팅", "스테이지 1 매집 구간" 과 같은 재사용 빈도가 높은 조합을 적용하려면 매번 개별 입력을 반복해야 한다. 또한 "Stage 2 돌파" 프리셋은 패턴 3조건을 모두 소모해 다른 조건을 추가할 여유가 없다.

### 1.2 페인 포인트

| 페인 포인트 | 영향 | 근거 |
|--------------|------|------|
| 필터 조합 재현성 부족 | 사용자가 동일 조합을 세션마다 재입력 | `ScreenContext` 에 초기값만 존재, 북마크 불가 |
| 패턴 3개 제약 | 스테이지 판정을 위한 다중 조건 구성 불가 | `PatternBuilder.tsx:38` (`< 3`), `backend/schemas/screen.py` (`max_length=3`) |
| 공유/복원 경로 부재 | URL 로 필터 상태를 공유할 수 없음 | URL 쿼리 동기화 미구현 |
| 실수 복구 비용 | 프리셋 적용 후 드리프트 인지 수단 없음 | 활성 프리셋 표시 UI 부재 |

---

## 2. 경쟁 서비스 UX 패턴 참고

본 리서치는 외부 웹 조회 없이, 설계 경험에 기반한 금융 스크리너 프리셋 UX 패턴을 정리한다.

### 2.1 TradingView Screener - 프리셋 저장/불러오기

- 패턴: 드롭다운 리스트 + 즐겨찾기 아이콘
- 장점: 개인 프리셋 무제한 저장
- 단점: v1 요건 (사용자 저장 프리셋 없음) 에는 과도한 복잡도

### 2.2 Koyfin Screener - 칩 바 + 템플릿 토글

- 패턴: 상단 가로형 칩 버튼 바, 클릭 시 현재 폼이 해당 템플릿으로 치환
- 장점: 1클릭 적용, 시각적 스캔 효율 우수, 활성 상태 명시
- 단점: 칩 수가 많으면 가로 스크롤 필요

### 2.3 Finviz Screener - 탭 기반 프리셋

- 패턴: 페이지 상단의 탭 전환
- 장점: 탭 간 명확한 구분
- 단점: 드리프트 개념이 약함 (탭 이동 시 리셋)

### 2.4 결론: 칩 버튼 바 (Koyfin 스타일) 채택

제품 결정 사항 (사전 확정) 과 일치한다. 칩 버튼 바는 다음 이점을 제공한다:

- 시각적 활성 상태 (`aria-pressed`) 로 드리프트 감지와 자연스럽게 결합
- 프리셋 수가 3 ~ 10개 범위일 때 가장 효율적
- 모바일에서 `overflow-x: auto` 로 수평 스크롤 대응이 용이

드롭다운은 프리셋 수가 20+ 개로 늘어날 때 재검토한다 (현재는 과도한 클릭 비용).

---

## 3. 드리프트 감지 설계 비교

사용자가 프리셋을 적용한 후 개별 필드를 수정하면 "현재 표시되는 필터 값 집합" 이 프리셋 정의와 더 이상 일치하지 않는다. 이때 활성 칩 하이라이트를 해제해야 사용자가 현재 상태를 오해하지 않는다.

### 3.1 접근 1 — 깊은 동등 비교 (Deep Equality)

매번 현재 `local` 상태와 `applyPatch(DEFAULT, preset.patch)` 결과를 깊이 비교하여 일치하는 프리셋 ID 를 파생한다.

- **장점**
  - 상태 추가 불필요, 순수 함수로 드리프트 판정 가능
  - 프리셋 전환 후 사용자가 우연히 원래 값으로 되돌려도 정확히 복귀 인식
- **단점**
  - 매 렌더마다 `presets.length × fieldsPerPatch` 만큼 비교 필요
- **비용**
  - v1 기준 프리셋 3개, 필드 < 10개 → 비교는 렌더당 ~30 필드 비교, `useMemo` 로 최적화 가능

### 3.2 접근 2 — 더티 플래그 (Dirty Flag)

`activePresetId` 를 상태로 유지하고, `updateFilters` 가 호출될 때마다 플래그를 null 로 초기화한다.

- **장점**
  - 비교 비용 0 (플래그 토글만)
- **단점**
  - 사용자가 수동으로 프리셋 정의 그대로 되돌려도 하이라이트가 복귀하지 않음
  - `applyFilters` vs `updateFilters` 호출 경로를 엄격히 구분해야 함

### 3.3 접근 3 — 반응형 추적 (Reactive Tracking)

각 필드마다 "프리셋 적용 이후 변경 여부" 를 플래그로 관리.

- **장점**: 세밀한 필드 단위 드리프트 노출 가능
- **단점**: 상태 복잡도 급증, v1 요건 초과

### 3.4 권장: **깊은 동등 비교 (접근 1)**

근거:

- 프리셋 수와 필드 수가 작아 성능 부담이 미미
- 사용자가 값만 정확히 되돌려도 활성화가 복구되는 UX 가 직관적
- 상태를 추가하지 않으므로 `ScreenContext` 변경이 최소화됨

구현: `useMemo` 로 `activePresetId` 를 `filters` 와 `presets` 의 파생값으로 계산한다. 동등 비교는 얕은 비교로 충분하지만 `patterns` 배열 때문에 커스텀 헬퍼 `isEqualScreenRequest` 를 사용한다.

---

## 4. URL 동기화 패턴 비교

### 4.1 접근 A — React Router `useSearchParams`

- 장점: 라우팅 프레임워크 표준 API
- 단점: 프로젝트는 현재 필터 상태용 라우터를 도입하지 않았다. 도입 시 라우터 전체 의존성 추가

### 4.2 접근 B — History API (`window.history.replaceState`) + `popstate`

- 장점: 라이트웨이트, 라우터 불필요
- 단점: 수동 이벤트 처리

### 4.3 접근 C — Hash 기반 (`#preset=...`)

- 장점: 서버 라우팅과 완전 격리
- 단점: 관습적으로 앱 라우트와 구분이 어려움

### 4.4 권장: **History API (접근 B)**

근거:

- 프로젝트가 현재 React Router 를 필터에 사용하지 않음 (`frontend/package.json` 기준 확인 필요)
- `replaceState` 로 히스토리를 오염시키지 않고 URL 만 갱신 가능
- 초기 마운트 시 `window.location.search` 읽기 1회 + 프리셋 변경 시 `replaceState` 호출만으로 충분

구현: `URLSearchParams` 로 `preset` 키를 관리. 적용/토글 off 시 `replaceState`, 드리프트 시 `preset` 키를 삭제하고 동일 URL 로 갱신. 키 네이밍 충돌 방지를 위해 `preset` 은 예약어로 명시한다.

---

## 5. 코드베이스 기존 구현 조사

`frontend/src/` 내 프리셋 시스템에 유사한 선례는 없다. 따라서 본 SPEC 은 신규 패턴을 도입한다.

| 항목 | 현황 |
|------|------|
| 프리셋 레지스트리 | **없음** (신규 도입) |
| URL 쿼리 동기화 | **없음** (신규 도입) |
| 드리프트 감지 | **없음** (신규 도입) |
| 칩 바 UI | **없음** (신규 도입) |
| 유사 패턴 | `DEFAULT_SCREEN_REQUEST` 가 `frontend/src/types/filter.ts` 에 상수로 선언된 사례 하나 |

결론: SPEC 은 **새로운 프런트엔드 패턴** 을 안전하게 도입하되, 기존 `ScreenContext` API 표면을 유지하여 다른 컴포넌트의 영향을 최소화해야 한다.

---

## 6. 프리셋 정의 vs `ScreenRequest` 필드 매핑

v1 초기 프리셋 3종의 `patch` 필드가 `ScreenRequest` 의 기존 필드와 충돌하지 않는지 검증한다.

| 프리셋 | 사용 필드 | 충돌 여부 | 비고 |
|--------|-----------|----------|------|
| `minervini_full` | `minervini_trend_template`, `rs_min`, `market_cap_min` | 없음 | `minervini_trend_template` 는 SPEC-MINERVINI-001 에서 신설 |
| `breakout_init` | `market_cap_min`, `rs_min`, `chg_1w_min`, `pattern_logic`, `patterns` (3개) | 없음 | patterns 3개, max 5 이내 |
| `stage1_accumulation` | `market_cap_min`, `chg_1m_min`, `pattern_logic`, `patterns` (3개) | 없음 | patterns 3개, max 5 이내 |

결론: v1 프리셋은 모두 `ScreenRequest` 필드 집합 내에서 표현 가능하다.

---

## 7. 백엔드 접점 최소화

v1 은 프런트엔드 중심 SPEC 이다. 백엔드 변경은 다음 1건으로 제한한다.

- `backend/schemas/screen.py` 의 `ScreenRequest.patterns` Pydantic 제약: `max_length=3 → 5`

이 변경은 **완화 (relaxation)** 이므로 기존 3개 이하 요청은 영향이 없다. 회귀 리스크는 낮다 (SPEC-MINERVINI-001 R6 참조).

---

## 8. 접근성 (A11y) 고려

- 칩 컨테이너: `role="group"` + `aria-label="필터 프리셋"`
- 각 칩: `<button>` 엘리먼트 + `aria-pressed` 속성
- 키보드: Tab 순회, Enter/Space 로 활성화, 포커스 링 시각적 유지
- 스크린리더: 활성 프리셋은 "선택됨" 으로 읽히며, 드리프트 시 "선택 해제됨" 알림 제공 (브라우저 기본)

구현 시 `@testing-library/react` 의 `getByRole('button', { pressed: true })` 로 테스트 가능하다.

---

## 9. 모바일 반응형 고려

- 칩 바 너비가 뷰포트를 초과하는 경우 `overflow-x: auto` + `scroll-snap` 으로 가로 스크롤
- 칩 최소 터치 영역 44×44 px (Apple HIG 기준)
- 작은 화면에서도 칩 라벨이 잘리지 않도록 `white-space: nowrap`

---

## 10. 성능 고려

- 드리프트 감지 `useMemo` 의존성: `filters`, `presets` 두 값만
- `presets` 는 모듈 스코프 상수이므로 참조가 변하지 않음 → `useMemo` 는 `filters` 변경 시에만 재계산
- URL 업데이트는 `useEffect` 내부에서 `activePresetId` 변화 시에만 실행
- 프리셋 3개 × 필드 ~10개 → 렌더당 ~30회 필드 비교는 무시할 수 있는 비용

---

## 11. 개방 질문 (사전 확정 범위 밖)

다음 사항은 v1 범위 밖이며 후속 SPEC 에서 다룬다:

- 사용자 정의 프리셋 저장/편집 (localStorage 또는 백엔드)
- 프리셋 간 전환 애니메이션
- 프리셋 사용 빈도 분석 (텔레메트리)
- i18n (영어 라벨 추가)
- 프리셋 그룹핑 (카테고리 탭)

---

## 12. 결론 및 설계 방향

| 결정 사항 | 채택 값 | 근거 |
|-----------|---------|------|
| UI 형태 | 칩 버튼 바 (상단 배치) | Koyfin 스타일, 활성 상태 시각화 용이 |
| 드리프트 감지 | 깊은 동등 비교 (`useMemo` 파생) | v1 비용 미미, UX 자연스러움 |
| URL 동기화 | History API `replaceState` | 라우터 의존성 불필요 |
| 프리셋 레지스트리 위치 | `frontend/src/presets/filter-presets.ts` | 단일 진실 원천 (SSOT) |
| 패턴 한도 | 3 → 5 (프런트 + 백엔드) | `breakout_init`, `stage1_accumulation` 3조건 + 미래 확장 여지 |
| 초기 프리셋 | `minervini_full`, `breakout_init`, `stage1_accumulation` | 제품 요구 |
| 의존 SPEC | SPEC-MINERVINI-001 (데이터/엔진) | `minervini_trend_template` 필드, `patterns.max_length=5` 확장 |

이 리서치 결과는 `spec.md` 의 전제 (§2 Assumptions), 기술 접근 (§6 Technical Approach), 리스크 (§8 Risk Register) 에 반영된다.

---

문서 버전: 1.0.0
작성일: 2026-04-21
작성자: MoAI (manager-spec)
