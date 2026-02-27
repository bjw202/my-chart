import React from 'react'

interface ChartPaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function ChartPagination({
  currentPage,
  totalPages,
  onPageChange,
}: ChartPaginationProps): React.ReactElement {
  return (
    <div className="chart-pagination" role="navigation" aria-label="Chart page navigation">
      <button
        type="button"
        className="pagination-btn"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 0}
        aria-label="Previous page"
      >
        ‹
      </button>

      <span className="pagination-info">
        {currentPage + 1} / {totalPages}
      </span>

      <button
        type="button"
        className="pagination-btn"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages - 1}
        aria-label="Next page"
      >
        ›
      </button>
    </div>
  )
}
