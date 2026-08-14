// RED: AC-SUX-055 (§10.2 / LD-7) — 상세 fetch 실패 시 오류 상태 + [다시 시도].
//      조용한 catch 삭제 + 거짓 안내 문구(X4) 제거.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import type { SectorRankItem } from '../../../types/market'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { fetchSectorDetail } from '../../../api/sectors'
import { SectorDetailPanel } from '../SectorDetailPanel'

vi.mock('../../../api/sectors', () => ({ fetchSectorDetail: vi.fn() }))

const sector: SectorRankItem = {
  name: '반도체',
  stock_count: 10,
  returns: { w1: 1, m1: 2, m3: 3 },
  excess_returns: { w1: 1, m1: 2, m3: 3 },
  rs_avg: 60, rs_top_pct: 20, nh_pct: 10, stage2_pct: 30,
  composite_score: 70, rank: 1, rank_change: 0,
}

function renderPanel() {
  return render(
    <AnalysisParamsProvider>
      <DataLoadProvider><SectorDetailPanel sector={sector} /></DataLoadProvider>
    </AnalysisParamsProvider>,
  )
}

beforeEach(() => { vi.mocked(fetchSectorDetail).mockReset() })
afterEach(() => cleanup())

describe('AC-SUX-055 — 섹터 상세 오류 표시', () => {
  it('상세 fetch 가 실패하면 오류 상태와 [다시 시도] 가 렌더된다', async () => {
    vi.mocked(fetchSectorDetail).mockRejectedValue(new Error('detail down'))
    renderPanel()
    await waitFor(
      () => expect(screen.getByTestId('sector-detail-error')).toBeInTheDocument(),
      { timeout: 25000 },
    )
    expect(screen.getByTestId('sector-detail-error').textContent).toContain('detail down')
    expect(screen.getByTestId('sector-detail-retry').textContent).toBe('[다시 시도]')
  }, 30000)

  it('[다시 시도] 클릭 시 재조회하고 성공하면 오류가 사라진다', async () => {
    vi.mocked(fetchSectorDetail).mockRejectedValue(new Error('detail down'))
    renderPanel()
    await waitFor(
      () => expect(screen.getByTestId('sector-detail-error')).toBeInTheDocument(),
      { timeout: 25000 },
    )
    vi.mocked(fetchSectorDetail).mockResolvedValue({
      sector_name: '반도체',
      sub_sectors: [{ name: '반도체장비', stock_count: 3, rs_avg: 70, stage2_pct: 50 }],
      top_stocks: [],
    } as never)
    fireEvent.click(screen.getByTestId('sector-detail-retry'))
    await waitFor(() => expect(screen.getByText('반도체장비')).toBeInTheDocument())
    expect(screen.queryByTestId('sector-detail-error')).not.toBeInTheDocument()
  }, 30000)

  it('성공했지만 내용이 비면 "세부 구성이 없습니다" 를 렌더한다 (거짓 안내 아님)', async () => {
    vi.mocked(fetchSectorDetail).mockResolvedValue({
      sector_name: '반도체', sub_sectors: [], top_stocks: [],
    } as never)
    renderPanel()
    await waitFor(() => expect(screen.getByTestId('sector-detail-empty')).toBeInTheDocument())
    expect(screen.getByTestId('sector-detail-empty').textContent)
      .toBe('이 섹터에는 표시할 세부 구성이 없습니다')
  })
})

// AC-SUX-055 정적 스캔 2건(`catch(() => {})` 0행 / 거짓 안내 문자열 소멸)은 vitest 가 아니라
// grep 명령으로 검증한다 — acceptance.md 가 grep 명령을 그대로 판정 기준으로 적고 있고,
// node:fs 를 테스트에서 import 하면 tsc 게이트(b) 에 NEW 오류 4건이 추가되기 때문이다.
// 실행 명령과 출력은 progress.md §E.2 M6 증거에 verbatim 기록한다.
