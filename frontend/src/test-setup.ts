import '@testing-library/jest-dom'

// ResizeObserver polyfill for jsdom (not available in test environment)
global.ResizeObserver = class ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
