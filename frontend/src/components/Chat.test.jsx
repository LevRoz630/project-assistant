import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Chat from './Chat'
import { mockFetchResponse } from '../test/utils'

describe('Chat Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock the history API call that happens on mount
    global.fetch = vi.fn((url) => {
      if (url.includes('/chat/history')) {
        return mockFetchResponse({ conversations: [] })
      }
      return mockFetchResponse({
        response: 'AI response',
        context_used: false,
        sources: null,
      })
    })
  })

  it('renders empty chat state', () => {
    render(<Chat />)

    expect(screen.getByText('Start a conversation')).toBeInTheDocument()
    expect(screen.getByText(/Ask me anything/)).toBeInTheDocument()
  })

  it('renders suggestion buttons', () => {
    render(<Chat />)

    expect(screen.getByText(/What did I write in my diary/)).toBeInTheDocument()
    expect(screen.getByText(/What tasks do I have/)).toBeInTheDocument()
  })

  it('clicking suggestion fills input', async () => {
    render(<Chat />)

    const suggestion = screen.getByText(/What did I write in my diary/)
    await userEvent.click(suggestion)

    const input = screen.getByPlaceholderText('Type your message...')
    expect(input.value).toContain('diary')
  })

  it('sends message on form submit', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        response: 'AI response here',
        context_used: false,
        sources: null,
      })
    )

    render(<Chat />)

    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Hello AI')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/chat/send'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('Hello AI'),
        })
      )
    })
  })

  it('displays user message after sending', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        response: 'Hello!',
        context_used: false,
        sources: null,
      })
    )

    render(<Chat />)

    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Test message')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    expect(screen.getByText('Test message')).toBeInTheDocument()
  })

  it('displays AI response after receiving', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        response: 'This is the AI response',
        context_used: false,
        sources: null,
      })
    )

    render(<Chat />)

    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Hello')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('This is the AI response')).toBeInTheDocument()
    })
  })

  it('displays sources when context is used', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        response: 'Based on your notes...',
        context_used: true,
        sources: ['PersonalAI/Diary/2024-01-15.md'],
      })
    )

    render(<Chat />)

    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'What did I write?')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('Sources:')).toBeInTheDocument()
      expect(screen.getByText('PersonalAI/Diary/2024-01-15.md')).toBeInTheDocument()
    })
  })

  it('clears chat when clear button is clicked', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        response: 'Response',
        context_used: false,
        sources: null,
      })
    )

    render(<Chat />)

    // Send a message first
    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Hello')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument()
    })

    // Clear chat
    const clearButton = screen.getByRole('button', { name: /clear chat/i })
    await userEvent.click(clearButton)

    expect(screen.queryByText('Hello')).not.toBeInTheDocument()
    expect(screen.getByText('Start a conversation')).toBeInTheDocument()
  })

  it('shows loading state while sending', async () => {
    // Make fetch hang
    global.fetch = vi.fn(() => new Promise(() => {}))

    render(<Chat />)

    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Hello')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    // Send button should be disabled
    expect(sendButton).toBeDisabled()
  })

  it('toggles context settings panel', async () => {
    render(<Chat />)

    // Settings panel should not be visible initially
    expect(screen.queryByText('Notes (RAG)')).not.toBeInTheDocument()

    // Click settings button
    const settingsButton = screen.getByRole('button', { name: /context settings/i })
    await userEvent.click(settingsButton)

    // Settings should now be visible
    expect(screen.getByText('Notes (RAG)')).toBeInTheDocument()
    expect(screen.getByText('Tasks')).toBeInTheDocument()
    expect(screen.getByText('Calendar')).toBeInTheDocument()
    expect(screen.getByText('Email')).toBeInTheDocument()
  })

  it('handles API error gracefully', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/chat/history')) {
        return mockFetchResponse({ conversations: [] })
      }
      return Promise.reject(new Error('Network error'))
    })

    render(<Chat />)

    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Hello')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })
})

describe('Conversation History', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows history button with count', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        conversations: [
          { id: '1', title: 'Test', messages: [], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
          { id: '2', title: 'Test 2', messages: [], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
        ],
      })
    )

    render(<Chat />)

    await waitFor(() => {
      expect(screen.getByText(/History \(2\)/)).toBeInTheDocument()
    })
  })

  it('shows history panel when history button is clicked', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({ conversations: [] })
    )

    render(<Chat />)

    await waitFor(() => {
      expect(screen.getByText(/History/)).toBeInTheDocument()
    })

    const historyButton = screen.getByRole('button', { name: /history/i })
    await userEvent.click(historyButton)

    expect(screen.getByText('Conversation History')).toBeInTheDocument()
  })

  it('shows empty state when no conversations', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({ conversations: [] })
    )

    render(<Chat />)

    const historyButton = screen.getByRole('button', { name: /history/i })
    await userEvent.click(historyButton)

    await waitFor(() => {
      expect(screen.getByText('No saved conversations')).toBeInTheDocument()
    })
  })

  it('loads conversations from API on mount', async () => {
    const mockConversations = [
      {
        id: 'conv-1',
        title: 'Previous chat',
        messages: [{ role: 'user', content: 'Hello' }],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ]

    global.fetch = vi.fn(() =>
      mockFetchResponse({ conversations: mockConversations })
    )

    render(<Chat />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/chat/history'),
        expect.objectContaining({ credentials: 'include' })
      )
    })
  })

  it('displays conversation list in history panel', async () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({
        conversations: [
          {
            id: '1',
            title: 'Chat about tasks',
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        ],
      })
    )

    render(<Chat />)

    const historyButton = screen.getByRole('button', { name: /history/i })
    await userEvent.click(historyButton)

    await waitFor(() => {
      expect(screen.getByText('Chat about tasks')).toBeInTheDocument()
    })
  })

  it('shows new chat button', () => {
    global.fetch = vi.fn(() =>
      mockFetchResponse({ conversations: [] })
    )

    render(<Chat />)

    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument()
  })

  it('clears messages when new chat is clicked', async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/chat/history')) {
        return mockFetchResponse({ conversations: [] })
      }
      return mockFetchResponse({
        response: 'Hello!',
        context_used: false,
        sources: null,
      })
    })

    render(<Chat />)

    // Send a message first
    const input = screen.getByPlaceholderText('Type your message...')
    await userEvent.type(input, 'Hello')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await userEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument()
    })

    // Click new chat
    const newChatButton = screen.getByRole('button', { name: /new chat/i })
    await userEvent.click(newChatButton)

    expect(screen.queryByText('Hello')).not.toBeInTheDocument()
    expect(screen.getByText('Start a conversation')).toBeInTheDocument()
  })
})
