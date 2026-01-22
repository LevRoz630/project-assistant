import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'

// Custom render function that includes providers
export function renderWithRouter(ui, options = {}) {
  return render(ui, {
    wrapper: ({ children }) => <BrowserRouter>{children}</BrowserRouter>,
    ...options,
  })
}

// Mock authenticated user
export const mockUser = {
  name: 'Test User',
  email: 'test@example.com',
  authenticated: true,
}

// Mock accounts data
export const mockAccounts = {
  authenticated: true,
  accounts: [
    {
      purpose: 'primary',
      label: 'Primary (All Services)',
      name: 'Test User',
      email: 'test@example.com',
    },
  ],
  has_email_account: true,
  has_storage_account: true,
}

// Mock fetch response helper
export function mockFetchResponse(data, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

// Mock fetch error
export function mockFetchError(message = 'Network error') {
  return Promise.reject(new Error(message))
}

// Setup authenticated fetch mock
export function setupAuthenticatedFetch(mockResponses = {}) {
  global.fetch = vi.fn((url) => {
    const path = new URL(url, 'http://localhost:8000').pathname

    if (mockResponses[path]) {
      return mockFetchResponse(mockResponses[path])
    }

    // Default responses
    if (path === '/auth/me') {
      return mockFetchResponse(mockUser)
    }
    if (path === '/auth/accounts') {
      return mockFetchResponse(mockAccounts)
    }

    return mockFetchResponse({ error: 'Not found' }, 404)
  })
}
