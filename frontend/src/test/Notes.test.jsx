import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithRouter, mockFetchResponse, mockFetchError } from './utils'
import Notes from '../components/Notes'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('Notes Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
  })

  describe('Folder List View', () => {
    it('shows folders when API returns 200', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ folders: [{ name: 'Diary' }, { name: 'Inbox' }] })
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes />)

      await waitFor(() => {
        expect(screen.getByText('Diary')).toBeInTheDocument()
        expect(screen.getByText('Inbox')).toBeInTheDocument()
      })
    })

    it('shows session expired message on 401', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ detail: 'Not authenticated' }, 401)
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes />)

      await waitFor(() => {
        expect(screen.getByText('Session expired')).toBeInTheDocument()
        expect(screen.getByText(/sign in again/i)).toBeInTheDocument()
        expect(screen.getByText('Sign in')).toBeInTheDocument()
      })
    })

    it('shows session expired on 401 inside a folder', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/notes/list/')) {
          return mockFetchResponse({ detail: 'Not authenticated' }, 401)
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes folderPath="Diary" />)

      await waitFor(() => {
        expect(screen.getByText('Session expired')).toBeInTheDocument()
      })
    })
  })

  describe('Note Creation Validation', () => {
    beforeEach(() => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ folders: ['Diary', 'Inbox'] })
        }
        if (url.includes('/notes/list/')) {
          return mockFetchResponse({ notes: [], subfolders: [] })
        }
        return mockFetchResponse({})
      })
    })

    it('shows error for invalid characters in name', async () => {
      renderWithRouter(<Notes folderPath="Diary" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: 'bad:name' } })

      await waitFor(() => {
        expect(screen.getByText(/invalid characters/i)).toBeInTheDocument()
      })
    })

    it('shows error for name too long', async () => {
      renderWithRouter(<Notes folderPath="Diary" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      const longName = 'a'.repeat(101)
      fireEvent.change(input, { target: { value: longName } })

      await waitFor(() => {
        expect(screen.getByText(/too long/i)).toBeInTheDocument()
      })
    })

    it('shows error for name starting with dot', async () => {
      renderWithRouter(<Notes folderPath="Diary" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: '.hidden' } })

      await waitFor(() => {
        expect(screen.getByText(/cannot start with a dot/i)).toBeInTheDocument()
      })
    })

    it('disables create button when validation fails', async () => {
      renderWithRouter(<Notes folderPath="Diary" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: 'bad:name' } })

      await waitFor(() => {
        const createBtn = screen.getByRole('button', { name: /^create$/i })
        expect(createBtn).toBeDisabled()
      })
    })
  })

  describe('Error Handling', () => {
    it('handles 409 already exists with open option', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ folders: ['Inbox'] })
        }
        if (url.includes('/notes/list/')) {
          return mockFetchResponse({ notes: [], subfolders: [] })
        }
        if (options?.method === 'POST' && url.includes('/notes/create')) {
          return mockFetchResponse(
            { detail: { code: 'already_exists', message: 'Note exists in Inbox' } },
            409
          )
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes folderPath="Inbox" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: 'existing' } })
      fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

      await waitFor(() => {
        expect(screen.getByText(/Note exists/i)).toBeInTheDocument()
        expect(screen.getByText(/Open existing note/i)).toBeInTheDocument()
      })
    })

    it('handles network errors gracefully', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ folders: ['Inbox'] })
        }
        if (url.includes('/notes/list/')) {
          return mockFetchResponse({ notes: [], subfolders: [] })
        }
        if (options?.method === 'POST') {
          return mockFetchError('Network failed')
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes folderPath="Inbox" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: 'test-note' } })
      fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

      await waitFor(() => {
        expect(screen.getByText(/Network error/i)).toBeInTheDocument()
      })
    })

    it('handles malformed error responses safely', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ folders: ['Inbox'] })
        }
        if (url.includes('/notes/list/')) {
          return mockFetchResponse({ notes: [], subfolders: [] })
        }
        if (options?.method === 'POST') {
          return mockFetchResponse(
            { detail: { code: 'error', message: { nested: 'object' } } },
            500
          )
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes folderPath="Inbox" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: 'test' } })
      fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

      await waitFor(() => {
        const errorDiv = screen.queryByText(/nested|error occurred/i)
        expect(errorDiv).toBeInTheDocument()
      })
    })
  })

  describe('Successful Creation', () => {
    it('navigates to new note on successful creation', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url.includes('/notes/folders')) {
          return mockFetchResponse({ folders: ['Diary'] })
        }
        if (url.includes('/notes/list/')) {
          return mockFetchResponse({ notes: [], subfolders: [] })
        }
        if (options?.method === 'POST') {
          return mockFetchResponse({ success: true, filename: 'mynote.md' })
        }
        return mockFetchResponse({})
      })

      renderWithRouter(<Notes folderPath="Diary" />)

      await waitFor(() => {
        expect(screen.getByText('New Note')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('New Note'))

      const input = screen.getByPlaceholderText('my-note')
      fireEvent.change(input, { target: { value: 'mynote' } })
      fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/notes/Diary/mynote.md')
      })
    })
  })
})
