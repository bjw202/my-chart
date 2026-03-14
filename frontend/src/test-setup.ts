import '@testing-library/jest-dom'

// ResizeObserver polyfill for jsdom (not available in test environment)
globalThis.ResizeObserver = class ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
