// @MX:NOTE: [AUTO] ThemeDetailPanel은 선택된 테마의 주도주 + 전체 종목을 렌더링; inclusion_reason은 호버 툴팁으로 표시
// @MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-008
import type { ReactElement } from 'react'
import type { ThemeItem, ThemeStockItem } from '../../api/themes'

interface ThemeDetailPanelProps {
  theme: ThemeItem
  stocks: ThemeStockItem[]
  leaders: ThemeStockItem[]
}

function RankBadge({ rank }: { rank: number }): ReactElement {
  const colors: Record<number, string> = {
    1: 'var(--positive)',
    2: 'var(--text-secondary)',
    3: '#cd7f32',
  }
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 18,
      height: 18,
      borderRadius: '50%',
      background: colors[rank] ?? 'var(--bg-surface)',
      color: 'var(--bg-primary)',
      fontSize: 10,
      fontWeight: 700,
      marginRight: 4,
      flexShrink: 0,
    }}>
      {rank}
    </span>
  )
}

function formatChangePct(value: number): ReactElement {
  if (!isFinite(value)) return <span style={{ color: 'var(--text-muted)' }}>-</span>
  const color = value > 0 ? 'var(--positive)' : value < 0 ? 'var(--negative)' : 'var(--text-secondary)'
  const sign = value > 0 ? '+' : ''
  return <span style={{ color }}>{sign}{value.toFixed(2)}%</span>
}

export function ThemeDetailPanel({ theme, stocks, leaders }: ThemeDetailPanelProps): ReactElement {
  const themeStocks = stocks.filter(s => s.theme_id === theme.theme_id)
  const themeLeaders = leaders.filter(s => s.theme_id === theme.theme_id)

  return (
    <div className="sector-detail-panel">
      <div className="sector-detail-panel-title">{theme.theme_name}</div>

      {/* 주도주 Top 3 */}
      {themeLeaders.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
            주도주
          </div>
          {themeLeaders.map(stock => (
            <div
              key={stock.stock_code}
              title={stock.inclusion_reason}
              style={{ display: 'flex', alignItems: 'center', padding: '5px 0', fontSize: 12, cursor: 'default', gap: 4 }}
            >
              {stock.rank != null && <RankBadge rank={stock.rank} />}
              <span style={{ fontWeight: 500, color: 'var(--text-primary)', flex: 1 }}>{stock.stock_name}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: 11, marginRight: 8 }}>{stock.stock_code}</span>
              {formatChangePct(stock.change_pct)}
            </div>
          ))}
        </div>
      )}

      {/* 전체 종목 테이블 */}
      {themeStocks.length > 0 && (
        <div style={{ background: 'var(--bg-surface)', borderRadius: 6, padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
            종목 ({themeStocks.length}개)
          </div>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                <th style={{ textAlign: 'left', padding: '4px 0' }}>종목명</th>
                <th style={{ textAlign: 'right', padding: '4px 6px', width: 60 }}>등락률</th>
                <th style={{ textAlign: 'right', padding: '4px 0', width: 60 }}>현재가</th>
              </tr>
            </thead>
            <tbody>
              {themeStocks.map((stock, idx) => (
                <tr
                  key={stock.stock_code}
                  title={stock.inclusion_reason || undefined}
                  style={{ background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)', cursor: 'default' }}
                >
                  <td style={{ padding: '5px 0' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{stock.stock_name}</span>
                    <span style={{ color: 'var(--text-muted)', marginLeft: 4, fontSize: 11 }}>{stock.stock_code}</span>
                  </td>
                  <td style={{ textAlign: 'right', padding: '5px 6px' }}>
                    {formatChangePct(stock.change_pct)}
                  </td>
                  <td style={{ textAlign: 'right', padding: '5px 0', color: 'var(--text-secondary)' }}>
                    {isFinite(stock.price) ? stock.price.toLocaleString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {themeStocks.length === 0 && (
        <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
          종목 데이터 없음 (빠른 모드에서는 상세 크롤링을 생략합니다)
        </div>
      )}
    </div>
  )
}
