# SPEC-UI-001 Acceptance Criteria

## Scenario 1: Stock Check via StockItem

**Given** 필터 적용 후 종목 목록이 표시된 상태에서
**When** StockItem의 체크박스 영역을 클릭하면
**Then** 해당 종목이 체크 상태로 전환되고, 체크박스에 체크 표시가 나타나며, 좌측에 초록 accent border가 표시된다
**And** 차트 선택(navigation)은 동작하지 않는다

## Scenario 2: Stock Check via ChartCell

**Given** ChartGrid에 종목 차트가 표시된 상태에서
**When** ChartCell 헤더의 체크 버튼을 클릭하면
**Then** 해당 종목이 체크 상태로 전환되고, 버튼이 초록 강조 상태로 변경된다
**And** StockList의 동일 종목 체크박스도 동기화된다

## Scenario 3: Watchlist Tab View

**Given** 3개 종목이 체크된 상태에서
**When** StockList 헤더의 "체크(3)" 탭을 클릭하면
**Then** 체크된 3개 종목만 flat list로 표시된다
**And** 각 종목에 해제(x) 버튼이 표시된다

## Scenario 4: Uncheck from Watchlist

**Given** "체크" 탭에서 체크된 종목 목록이 표시된 상태에서
**When** 특정 종목의 해제 버튼을 클릭하면
**Then** 해당 종목이 목록에서 제거되고, 탭 카운트가 감소한다
**And** "전체" 탭으로 돌아가면 해당 종목의 체크가 해제되어 있다

## Scenario 5: TradingView Export

**Given** 종목 코드 448900, 234590이 체크된 상태에서
**When** Export 버튼을 클릭하면
**Then** 클립보드에 `KRX:448900,KRX:234590` 형식의 텍스트가 복사된다
**And** Export 버튼이 1.5초간 "Copied!" 텍스트로 변경된다

## Scenario 6: Cross-filter Persistence

**Given** 필터 A로 검색하여 종목 3개를 체크한 상태에서
**When** 필터 B로 새로운 검색을 실행하면
**Then** 이전에 체크한 3개 종목이 체크 목록에 유지된다
**And** "체크(3)" 탭에서 확인할 수 있다

## Scenario 7: Navigation Independence

**Given** StockList에 체크박스가 표시된 상태에서
**When** 체크박스 외 영역(종목 이름, 코드, 등락률 등)을 클릭하면
**Then** 기존과 동일하게 차트가 해당 종목으로 이동(navigate)한다
**And** 체크 상태는 변경되지 않는다

## Edge Cases

- 체크된 종목이 0개일 때 Export 버튼은 disabled 상태
- "체크" 탭에서 모든 종목을 해제하면 빈 상태 메시지 표시
- StatusBar에 checkedCount > 0일 때만 "관심 N개" 표시
