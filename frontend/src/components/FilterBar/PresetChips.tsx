// @MX:NOTE: [AUTO] PresetChips — 프리셋 칩 바 프리젠테이션 컴포넌트
// @MX:REASON: 상태를 직접 보유하지 않는 순수 프리젠테이션. 활성 ID 판정과 상태 변이는 FilterBar가 담당한다.
// @MX:SPEC: SPEC-PRESET-001 REQ-PST-002/003/004/005/010/012
import React from 'react'
import type { Preset, PresetId } from '../../types/filter'

interface PresetChipsProps {
  presets: readonly Preset[]
  activePresetId: PresetId | null
  /** 비활성 칩 클릭 시 호출 */
  onApply: (preset: Preset) => void
  /** 활성 칩 재클릭 (토글 오프) 시 호출 */
  onClear: () => void
}

/**
 * 프리셋 칩 바 — 각 프리셋에 대한 버튼을 가로로 나열한다.
 * 활성 상태, 클릭 처리는 모두 부모 컴포넌트(FilterBar)에 위임한다.
 */
export function PresetChips({
  presets,
  activePresetId,
  onApply,
  onClear,
}: PresetChipsProps): React.ReactElement {
  return (
    // REQ-PST-010: 컨테이너 접근성 속성
    <div role="group" aria-label="필터 프리셋" className="preset-chips">
      {presets.map((preset) => {
        const isActive = preset.id === activePresetId
        // REQ-PST-012: tooltip이 있으면 우선, 없으면 description fallback
        const tooltip = preset.tooltip ?? preset.description

        return (
          <button
            key={preset.id}
            type="button"
            className={`preset-chip${isActive ? ' preset-chip--active' : ''}`}
            aria-pressed={isActive ? 'true' : 'false'}
            title={tooltip}
            onClick={() => {
              if (isActive) {
                onClear()
              } else {
                onApply(preset)
              }
            }}
          >
            {preset.label}
          </button>
        )
      })}
    </div>
  )
}
