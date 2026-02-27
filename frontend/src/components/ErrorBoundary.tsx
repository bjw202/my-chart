import React from 'react'

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  override componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  override render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="error-boundary">
            <h2>오류가 발생했습니다</h2>
            <pre className="error-details">{this.state.error?.message}</pre>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              다시 시도
            </button>
          </div>
        )
      )
    }
    return this.props.children
  }
}
