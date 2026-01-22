import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock fetch globally
global.fetch = vi.fn()

// Mock window.location
delete window.location
window.location = {
  href: 'http://localhost:5173',
  origin: 'http://localhost:5173',
  pathname: '/',
  search: '',
  hash: '',
  assign: vi.fn(),
  replace: vi.fn(),
  reload: vi.fn(),
}

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

// Reset mocks after each test
afterEach(() => {
  vi.clearAllMocks()
})
