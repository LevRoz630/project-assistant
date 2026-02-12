import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithRouter, mockFetchResponse } from './utils'
import NoteEditor from '../components/NoteEditor'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('NoteEditor Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Loading and Display', () => {
    it('loads and displays note content', async () => {
      global.fetch = vi.fn(() =>
        mockFetchResponse({
          content: '# Test Note\n\nContent here',
          folder: 'Diary',
          filename: 'test-note.md',
        })
      )

      renderWithRouter(<NoteEditor folder="Diary" filename="test-note.md" />)

      await waitFor(() => {
        expect(screen.getByDisplayValue(/# Test Note/)).toBeInTheDocument()
      })
    })

    it('handles 404 not found with structured error', async () => {
      global.fetch = vi.fn(() =>
        mockFetchResponse(
          { detail: { code: 'note_not_found', message: 'Note not found in Diary' } },
          404
        )
      )

      renderWithRouter(<NoteEditor folder="Diary" filename="test-note.md" />)

      await waitFor(() => {
        expect(screen.getByText(/Note not found/i)).toBeInTheDocument()
        expect(screen.getByText(/Back to Notes/i)).toBeInTheDocument()
      })
    })

    it('handles malformed 404 error safely', async () => {
      global.fetch = vi.fn(() =>
        mockFetchResponse(
          { detail: { code: 'error', message: { nested: 'object' } } },
          404
        )
      )

      renderWithRouter(<NoteEditor folder="Diary" filename="test-note.md" />)

      await waitFor(() => {
        // Should show fallback message, not crash
        expect(screen.getByText(/Note not found|error occurred/i)).toBeInTheDocument()
      })
    })
  })

  describe('Save Status Indicator', () => {
    it('shows Saved when content matches original', async () => {
      global.fetch = vi.fn(() =>
        mockFetchResponse({
          content: '# Test',
          folder: 'Diary',
          filename: 'test.md',
        })
      )

      renderWithRouter(<NoteEditor folder="Diary" filename="test.md" />)

      await waitFor(() => {
        expect(screen.getByText('Saved')).toBeInTheDocument()
      })
    })

    it('shows Save button when content is modified', async () => {
      global.fetch = vi.fn(() =>
        mockFetchResponse({
          content: '# Test',
          folder: 'Diary',
          filename: 'test.md',
        })
      )

      renderWithRouter(<NoteEditor folder="Diary" filename="test.md" />)

      await waitFor(() => {
        expect(screen.getByDisplayValue(/# Test/)).toBeInTheDocument()
      })

      const textarea = screen.getByDisplayValue(/# Test/)
      fireEvent.change(textarea, { target: { value: '# Modified' } })

      await waitFor(() => {
        expect(screen.getByText('Save')).toBeInTheDocument()
      })
    })
  })

  describe('Manual Save', () => {
    it('allows manual save via button', async () => {
      let savedContent = null
      global.fetch = vi.fn((url, options) => {
        if (options?.method === 'PUT') {
          savedContent = JSON.parse(options.body).content
          return mockFetchResponse({ success: true })
        }
        return mockFetchResponse({
          content: '# Original',
          folder: 'Diary',
          filename: 'test.md',
        })
      })

      renderWithRouter(<NoteEditor folder="Diary" filename="test.md" />)

      await waitFor(() => {
        expect(screen.getByDisplayValue(/# Original/)).toBeInTheDocument()
      })

      const textarea = screen.getByDisplayValue(/# Original/)
      fireEvent.change(textarea, { target: { value: '# Manual Save Test' } })

      // Wait for Save button to appear
      await waitFor(() => {
        expect(screen.getByText('Save')).toBeInTheDocument()
      })

      // Click save button
      const saveBtn = screen.getByText('Save')
      fireEvent.click(saveBtn)

      await waitFor(() => {
        expect(savedContent).toBe('# Manual Save Test')
      })
    })

    it('shows Save failed when save fails', async () => {
      global.fetch = vi.fn((url, options) => {
        if (options?.method === 'PUT') {
          return mockFetchResponse({ detail: 'Failed' }, 500)
        }
        return mockFetchResponse({
          content: '# Test',
          folder: 'Diary',
          filename: 'test.md',
        })
      })

      renderWithRouter(<NoteEditor folder="Diary" filename="test.md" />)

      await waitFor(() => {
        expect(screen.getByDisplayValue(/# Test/)).toBeInTheDocument()
      })

      const textarea = screen.getByDisplayValue(/# Test/)
      fireEvent.change(textarea, { target: { value: '# Modified' } })

      await waitFor(() => {
        expect(screen.getByText('Save')).toBeInTheDocument()
      })

      // Click save
      fireEvent.click(screen.getByText('Save'))

      await waitFor(() => {
        expect(screen.getByText(/Save failed/i)).toBeInTheDocument()
      })
    })
  })

  describe('Preview Mode', () => {
    it('toggles between edit and preview mode', async () => {
      global.fetch = vi.fn(() =>
        mockFetchResponse({
          content: '# Test Header',
          folder: 'Diary',
          filename: 'test.md',
        })
      )

      renderWithRouter(<NoteEditor folder="Diary" filename="test.md" />)

      await waitFor(() => {
        expect(screen.getByDisplayValue(/# Test Header/)).toBeInTheDocument()
      })

      // Click preview button
      fireEvent.click(screen.getByText('Preview'))

      await waitFor(() => {
        // Textarea should be replaced by preview pane
        expect(screen.queryByDisplayValue(/# Test Header/)).not.toBeInTheDocument()
        // Edit button should appear
        expect(screen.getByText('Edit')).toBeInTheDocument()
      })
    })
  })
})
