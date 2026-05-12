// @MX:NOTE: [AUTO] PresetChips — 프리셋 칩 바 프리젠테이션 컴포넌트
// @MX:REASON: 상태를 직접 보유하지 않는 순수 프리젠테이션. 활성 ID 판정과 상태 변이는 FilterBar가 담당한다.
// @MX:SPEC: SPEC-PRESET-001 REQ-PST-002/003/004/005/010/012
import React, { useState } from 'react'
import type { Preset, PresetId } from '../../types/filter'
import { formatPresetConditions } from '../../presets/utils'

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
 *
 * 호버 동작:
 * - native `title` attribute 는 SPEC REQ-PST-012 / B6 테스트 보호 영역이므로 그대로 유지.
 * - 그 위에 커스텀 호버 패널을 얹어 patch 조건을 사람이 읽기 쉬운 문장으로 표시.
 * - 키보드 사용자도 focus/blur 로 동일한 패널을 노출 (접근성).
 */
export function PresetChips({
  presets,
  activePresetId,
  onApply,
  onClear,
}: PresetChipsProps): React.ReactElement {
  const [hoveredId, setHoveredId] = useState<PresetId | null>(null)

  return (
    // REQ-PST-010: 컨테이너 접근성 속성
    <div role="group" aria-label="필터 프리셋" className="preset-chips">
      {presets.map((preset) => {
        const isActive = preset.id === activePresetId
        // REQ-PST-012: tooltip이 있으면 우선, 없으면 description fallback
        const tooltip = preset.tooltip ?? preset.description
        const isHovered = preset.id === hoveredId
        const tooltipId = `preset-tooltip-${preset.id}`
        const conditions = isHovered ? formatPresetConditions(preset.patch) : []

        return (
          <div key={preset.id} className="preset-chip-wrapper">
            <button
              type="button"
              className={`preset-chip${isActive ? ' preset-chip--active' : ''}`}
              aria-pressed={isActive ? 'true' : 'false'}
              aria-describedby={isHovered ? tooltipId : undefined}
              title={tooltip}
              onMouseEnter={() => setHoveredId(preset.id)}
              onMouseLeave={() => setHoveredId(null)}
              onFocus={() => setHoveredId(preset.id)}
              onBlur={() => setHoveredId(null)}
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

            {isHovered && (
              <div id={tooltipId} role="tooltip" className="preset-tooltip">
                <div className="preset-tooltip-title">{preset.label}</div>
                <div className="preset-tooltip-desc">{preset.description}</div>
                {conditions.length > 0 && (
                  <div className="preset-tooltip-conditions">
                    <div className="preset-tooltip-conditions-label">조건</div>
                    {conditions.map((line, i) => (
                      <div key={i} className="preset-tooltip-condition-line">
                        {line}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
