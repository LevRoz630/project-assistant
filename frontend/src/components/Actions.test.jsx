import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Actions from './Actions'
import { mockFetchResponse } from '../test/utils'

describe('Actions Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockPendingActions = {
    count: 1,
    actions: [
      {
        id: 'action-1',
        type: 'create_task',
        status: 'pending',
        data: { title: 'Test Task', body: 'Description' },
        reason: 'AI suggested creating this task',
        created_at: '2024-01-15T10:00:00Z',
      },
    ],
  }

  const mockHistoryActions = {
    count: 2,
    actions: [
      {
        id: 'action-2',
        type: 'create_event',
        status: 'executed',
        data: { subject: 'Meeting' },
        reason: 'Scheduled meeting',
        created_at: '2024-01-14T09:00:00Z',
      },
      {
        id: 'action-3',
        type: 'create_task',
        status: 'rejected',
        data: { title: 'Rejected Task' },
        reason: 'Reason',
        created_at: '2024-01-13T08:00:00Z',
      },
    ],
  }

  it('renders loading state initially', () => {
    global.fetch = vi.fn(() => new Promise(() => {}))

    render(<Actions />)

    expect(screen.getByRole('heading', { name: /ai actions/i })).toBeInTheDocument()
  })

  it('renders empty state when no pending actions', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      expect(screen.getByText(/no pending actions/i)).toBeInTheDocument()
    })
  })

  it('renders pending actions', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse(mockHistoryActions)
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      expect(screen.getByText(/Create Task: Test Task/i)).toBeInTheDocument()
      expect(screen.getByText(/AI suggested creating this task/i)).toBeInTheDocument()
    })
  })

  it('shows approve and reject buttons for pending actions', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
    })
  })

  it('approves action when approve button clicked', async () => {
    global.fetch = vi.fn((url, options) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      if (url.includes('/approve')) {
        return mockFetchResponse({ status: 'executed' })
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /approve/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/approve'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  it('rejects action when reject button clicked', async () => {
    global.fetch = vi.fn((url, options) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      if (url.includes('/reject')) {
        return mockFetchResponse({ status: 'rejected' })
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /reject/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/reject'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  it('switches between pending and history tabs', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse(mockHistoryActions)
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    // Initially on pending tab - use the action title which is unique
    await waitFor(() => {
      expect(screen.getByText(/Create Task: Test Task/i)).toBeInTheDocument()
    })

    // Switch to history tab
    await userEvent.click(screen.getByRole('button', { name: /history/i }))

    await waitFor(() => {
      expect(screen.getByText(/Create Event: Meeting/i)).toBeInTheDocument()
    })
  })

  it('displays action type icons correctly', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      // Task icon should be present (checkmark)
      expect(screen.getByText('✓')).toBeInTheDocument()
    })
  })

  it('shows pending count badge', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/actions/pending')) {
        return mockFetchResponse(mockPendingActions)
      }
      if (url.includes('/actions/history')) {
        return mockFetchResponse({ count: 0, actions: [] })
      }
      return mockFetchResponse({})
    })

    render(<Actions />)

    await waitFor(() => {
      expect(screen.getByText(/1 pending/i)).toBeInTheDocument()
    })
  })
})
