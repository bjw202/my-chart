// @MX:ANCHOR: [AUTO] FilterBar — 필터 UI 진입점
// @MX:REASON: 필터 UI 진입점. fan_in >= 3 (Dashboard, PresetChips, URL effect). 상태 파생과 URL 동기화를 모두 담당한다.
// @MX:SPEC: SPEC-PRESET-001 REQ-PST-002/003/004/006/007
import React, { useState, useMemo, useEffect, useRef } from 'react'
import { useScreen } from '../../contexts/ScreenContext'
import type { Preset, PresetId, ScreenRequest } from '../../types/filter'
import { DEFAULT_SCREEN_REQUEST } from '../../types/filter'
import { FILTER_PRESETS } from '../../presets/filter-presets'
import { applyPatch, isEqualScreenRequest } from '../../presets/utils'
import { PresetChips } from './PresetChips'
import { DbUpdateButton } from './DbUpdateButton'
import { MarketCapFilter } from './MarketCapFilter'
import { PatternBuilder } from './PatternBuilder'
import { RSFilter } from './RSFilter'
import { ReturnFilter } from './ReturnFilter'

// 초기 URL에서 프리셋 id를 미리 읽어 초기 상태를 설정한다.
// URL 동기화 effect가 실행되기 전에 초기 상태를 올바르게 설정하기 위함 (타이밍 문제 방어).
function getInitialStateFromUrl(): ScreenRequest {
  const params = new URLSearchParams(window.location.search)
  const id = params.get('preset')
  if (id) {
    const preset = FILTER_PRESETS.find((p) => p.id === id)
    if (preset) {
      return applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)
    }
  }
  return DEFAULT_SCREEN_REQUEST
}

export function FilterBar(): React.ReactElement {
  const { applyFilters, clearResults } = useScreen()
  // URL에서 초기 프리셋을 읽어 local 초기 상태 설정
  const [local, setLocal] = useState<ScreenRequest>(getInitialStateFromUrl)
  // 초기 마운트 시 applyFilters 1회 호출을 추적하는 ref
  const hasAppliedInitialPreset = useRef(false)

  // REQ-PST-006: 드리프트 감지 — local 상태에서 activePresetId 파생 (useMemo)
  // local 변경 시에만 재계산. FILTER_PRESETS는 모듈 상수라 참조 불변.
  const activePresetId = useMemo<PresetId | null>(() => {
    for (const preset of FILTER_PRESETS) {
      const expected = applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)
      if (isEqualScreenRequest(local, expected)) {
        return preset.id
      }
    }
    return null
  }, [local])

  // REQ-PST-007: URL 동기화 — activePresetId 변화 시 history.replaceState
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (activePresetId) {
      params.set('preset', activePresetId)
    } else {
      params.delete('preset')
    }
    const nextQuery = params.toString()
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}`
    const currentUrl = `${window.location.pathname}${window.location.search}`
    // 불필요한 replaceState 방지 (무한 루프 방어)
    if (nextUrl !== currentUrl) {
      window.history.replaceState(null, '', nextUrl)
    }
  }, [activePresetId])

  // REQ-PST-007: 초기 마운트 시 ?preset=<id> 자동 적용 (1회만)
  // getInitialStateFromUrl이 local을 이미 병합 상태로 설정했으므로,
  // 유효한 preset이 감지된 경우에만 applyFilters로 네트워크 요청을 트리거한다.
  // A9: 레지스트리에 없는 id는 getInitialStateFromUrl에서 DEFAULT 반환 → activePresetId=null → 자동 무시.
  useEffect(() => {
    if (hasAppliedInitialPreset.current) return
    hasAppliedInitialPreset.current = true
    if (activePresetId) {
      void applyFilters(local)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const update = <K extends keyof ScreenRequest>(key: K, value: ScreenRequest[K]): void => {
    setLocal((prev) => ({ ...prev, [key]: value }))
  }

  const handleApply = (e: React.SyntheticEvent): void => {
    e.preventDefault()
    void applyFilters(local)
  }

  const handleReset = (): void => {
    setLocal(DEFAULT_SCREEN_REQUEST)
    clearResults()
  }

  // REQ-PST-003: 비활성 칩 클릭 — merged 상태로 applyFilters 1회 호출
  const handlePresetApply = (preset: Preset): void => {
    const merged = applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)
    setLocal(merged)
    void applyFilters(merged)
  }

  // REQ-PST-004: 활성 칩 재클릭 — 초기화 버튼과 동일하게 DEFAULT로 리셋 (applyFilters 호출 안 함)
  const handlePresetClear = handleReset

  return (
    <header className="filter-bar">
      <form className="filter-bar-form" onSubmit={handleApply}>
        {/* REQ-PST-002: PresetChips를 필터 바 첫 자리에 — 다른 필터와 동일 flex 라인 공유 */}
        <PresetChips
          presets={FILTER_PRESETS}
          activePresetId={activePresetId}
          onApply={handlePresetApply}
          onClear={handlePresetClear}
        />

        <MarketCapFilter
          value={local.market_cap_min}
          onChange={(v) => update('market_cap_min', v)}
        />

        <ReturnFilter
          filters={local}
          onChange={(key, v) => update(key, v)}
        />

        <PatternBuilder
          patterns={local.patterns}
          patternLogic={local.pattern_logic}
          onPatternsChange={(p) => update('patterns', p)}
          onLogicChange={(l) => update('pattern_logic', l)}
        />

        <RSFilter
          value={local.rs_min}
          onChange={(v) => update('rs_min', v)}
        />

        <div className="filter-actions">
          <button type="submit" className="btn btn--primary">검색</button>
          <button type="button" className="btn btn--secondary" onClick={handleReset}>초기화</button>
        </div>

        <DbUpdateButton />
      </form>
    </header>
  )
}
