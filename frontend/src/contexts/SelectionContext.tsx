// SelectionContext — 02-screen-flow.md §3.3 상태 소유권 표.
// selectedSector (단일 전역 슬롯, 마지막 쓰기 우선) + sectorScopeFollow (스코프 추종 토글, SM-5/SM-6).
import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'

export interface SelectionValue {
  // 단일 선택 슬롯 — 사용자 명시 해제(clearSector) 시에만 소멸 (§3.3 / SM-5)
  selectedSector: string | null
  // 스코프 추종 — 종목 탐색 칩 × → false, 새 섹터 선택 → true 강제 (SM-6)
  sectorScopeFollow: boolean
  // 섹터 선택 — selectedSector 설정 + sectorScopeFollow 를 true 로 강제 (SM-6)
  selectSector: (name: string) => void
  // 명시 해제 — selectedSector = null (사용자 의도적 해제만 소멸시킨다)
  clearSector: () => void
  setSectorScopeFollow: (v: boolean) => void
}

const SelectionContext = createContext<SelectionValue | null>(null)

export function SelectionProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [selectedSector, setSelectedSector] = useState<string | null>(null)
  const [sectorScopeFollow, setSectorScopeFollow] = useState(true)

  // SM-6: 어디서든 섹터를 선택하면 sectorScopeFollow 가 true 로 강제된다.
  const selectSector = useCallback((name: string) => {
    setSelectedSector(name)
    setSectorScopeFollow(true)
  }, [])

  const clearSector = useCallback(() => {
    setSelectedSector(null)
  }, [])

  const value = useMemo<SelectionValue>(
    () => ({
      selectedSector,
      sectorScopeFollow,
      selectSector,
      clearSector,
      setSectorScopeFollow,
    }),
    [selectedSector, sectorScopeFollow, selectSector, clearSector],
  )

  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>
}

export function useSelection(): SelectionValue {
  const ctx = useContext(SelectionContext)
  if (!ctx) throw new Error('useSelection must be used within SelectionProvider')
  return ctx
}
