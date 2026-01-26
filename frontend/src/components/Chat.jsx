import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './Chat.css'
import { API_BASE } from '../config'

function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useContext, setUseContext] = useState(true)
  const [includeTasks, setIncludeTasks] = useState(true)
  const [includeCalendar, setIncludeCalendar] = useState(true)
  const [includeEmail, setIncludeEmail] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [conversations, setConversations] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [savingHistory, setSavingHistory] = useState(false)
  const messagesEndRef = useRef(null)
  const saveTimeoutRef = useRef(null)

  // Load conversations from OneDrive on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await fetch(`${API_BASE}/chat/history`, {
          credentials: 'include',
        })
        if (res.ok) {
          const data = await res.json()
          setConversations(data.conversations || [])
        }
      } catch (e) {
        console.error('Failed to load chat history:', e)
      } finally {
        setHistoryLoaded(true)
      }
    }
    loadHistory()
  }, [])

  // Debounced save to OneDrive when conversations change
  const saveHistoryToCloud = async (convs) => {
    if (!historyLoaded || savingHistory) return

    setSavingHistory(true)
    try {
      await fetch(`${API_BASE}/chat/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ conversations: convs }),
      })
    } catch (e) {
      console.error('Failed to save chat history:', e)
    } finally {
      setSavingHistory(false)
    }
  }

  // Debounce saves to avoid too many API calls
  useEffect(() => {
    if (!historyLoaded || conversations.length === 0) return

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    saveTimeoutRef.current = setTimeout(() => {
      saveHistoryToCloud(conversations)
    }, 2000) // Save 2 seconds after last change

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [conversations, historyLoaded])

  // Auto-save current conversation after each message
  useEffect(() => {
    if (messages.length > 0) {
      saveCurrentConversation()
    }
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const generateTitle = (msgs) => {
    const firstUserMsg = msgs.find(m => m.role === 'user')
    if (firstUserMsg) {
      const title = firstUserMsg.content.slice(0, 50)
      return title.length < firstUserMsg.content.length ? title + '...' : title
    }
    return 'New conversation'
  }

  const saveCurrentConversation = () => {
    if (messages.length === 0) return

    const now = new Date().toISOString()

    if (currentConversationId) {
      // Update existing conversation
      setConversations(prev => prev.map(conv =>
        conv.id === currentConversationId
          ? { ...conv, messages, updatedAt: now, title: generateTitle(messages) }
          : conv
      ))
    } else {
      // Create new conversation
      const newId = Date.now().toString()
      setCurrentConversationId(newId)
      setConversations(prev => [{
        id: newId,
        title: generateTitle(messages),
        messages,
        createdAt: now,
        updatedAt: now,
      }, ...prev])
    }
  }

  const loadConversation = (conv) => {
    setMessages(conv.messages)
    setCurrentConversationId(conv.id)
    setShowHistory(false)
  }

  const deleteConversation = async (convId, e) => {
    e.stopPropagation()
    setConversations(prev => prev.filter(c => c.id !== convId))
    if (currentConversationId === convId) {
      setMessages([])
      setCurrentConversationId(null)
    }

    // Delete from OneDrive
    try {
      await fetch(`${API_BASE}/chat/history/${convId}`, {
        method: 'DELETE',
        credentials: 'include',
      })
    } catch (e) {
      console.error('Failed to delete conversation from cloud:', e)
    }
  }

  const startNewConversation = () => {
    setMessages([])
    setCurrentConversationId(null)
    setShowHistory(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    // Create abort controller for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 120000) // 2 minute timeout

    try {
      const res = await fetch(`${API_BASE}/chat/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: controller.signal,
        body: JSON.stringify({
          message: userMessage,
          history: messages,
          use_context: useContext,
          include_tasks: includeTasks,
          include_calendar: includeCalendar,
          include_email: includeEmail,
        }),
      })

      clearTimeout(timeoutId)

      if (res.status === 401) {
        // Session expired - redirect to login
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: 'Your session has expired. Please refresh the page and log in again.',
            error: true,
          },
        ])
        return
      }

      if (res.status === 429) {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: 'Too many requests. Please wait a moment before trying again.',
            error: true,
          },
        ])
        return
      }

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server error (${res.status})`)
      }

      const data = await res.json()
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          sources: data.sources,
          proposed_actions: data.proposed_actions,
        },
      ])
    } catch (error) {
      clearTimeout(timeoutId)
      console.error('Chat error:', error)

      let errorMessage = 'Sorry, something went wrong. Please try again.'
      if (error.name === 'AbortError') {
        errorMessage = 'The request took too long. The AI might be busy - please try again.'
      } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
        errorMessage = 'Network error. Please check your connection and try again.'
      } else if (error.message) {
        errorMessage = `Error: ${error.message}`
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: errorMessage,
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
    setCurrentConversationId(null)
  }

  const handleApproveAction = async (actionId, msgIndex) => {
    try {
      const res = await fetch(`${API_BASE}/actions/${actionId}/approve`, {
        method: 'POST',
        credentials: 'include',
      })
      if (res.ok) {
        setMessages(prev => prev.map((msg, idx) => {
          if (idx === msgIndex && msg.proposed_actions) {
            return {
              ...msg,
              proposed_actions: msg.proposed_actions.map(a =>
                a.id === actionId ? { ...a, status: 'executed' } : a
              ),
            }
          }
          return msg
        }))
      }
    } catch (error) {
      console.error('Failed to approve action:', error)
    }
  }

  const handleRejectAction = async (actionId, msgIndex) => {
    try {
      const res = await fetch(`${API_BASE}/actions/${actionId}/reject`, {
        method: 'POST',
        credentials: 'include',
      })
      if (res.ok) {
        setMessages(prev => prev.map((msg, idx) => {
          if (idx === msgIndex && msg.proposed_actions) {
            return {
              ...msg,
              proposed_actions: msg.proposed_actions.map(a =>
                a.id === actionId ? { ...a, status: 'rejected' } : a
              ),
            }
          }
          return msg
        }))
      }
    } catch (error) {
      console.error('Failed to reject action:', error)
    }
  }

  const formatActionData = (action) => {
    const { type, data } = action
    if (type === 'create_event') {
      return `Event: ${data.subject} (${data.start_datetime?.slice(0, 16)} - ${data.end_datetime?.slice(11, 16)})`
    }
    if (type === 'create_task') {
      return `Task: ${data.title}${data.due_date ? ` (due: ${data.due_date.slice(0, 10)})` : ''}`
    }
    if (type === 'create_note') {
      return `Note: ${data.filename} in ${data.folder}`
    }
    return JSON.stringify(data)
  }

  const formatDate = (isoString) => {
    const date = new Date(isoString)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === today.toDateString()) {
      return 'Today ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>AI Chat</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowHistory(!showHistory)}
            >
              History ({conversations.length})
              {savingHistory && <span className="sync-indicator" title="Syncing to OneDrive...">●</span>}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => setShowSettings(!showSettings)}
            >
              Context Settings
            </button>
            <button className="btn btn-secondary" onClick={startNewConversation}>
              New Chat
            </button>
          </div>
        </div>

        {showSettings && (
          <div className="context-settings">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={useContext}
                onChange={(e) => setUseContext(e.target.checked)}
              />
              <span>Notes (RAG)</span>
            </label>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={includeTasks}
                onChange={(e) => setIncludeTasks(e.target.checked)}
              />
              <span>Tasks</span>
            </label>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={includeCalendar}
                onChange={(e) => setIncludeCalendar(e.target.checked)}
              />
              <span>Calendar</span>
            </label>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={includeEmail}
                onChange={(e) => setIncludeEmail(e.target.checked)}
              />
              <span>Email</span>
            </label>
          </div>
        )}

        {showHistory && (
          <div className="history-panel">
            <div className="history-header">
              <span>Conversation History</span>
              {conversations.length > 0 && (
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={async () => {
                    if (confirm('Delete all conversations?')) {
                      setConversations([])
                      setMessages([])
                      setCurrentConversationId(null)
                      // Clear from OneDrive
                      try {
                        await fetch(`${API_BASE}/chat/history`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          credentials: 'include',
                          body: JSON.stringify({ conversations: [] }),
                        })
                      } catch (e) {
                        console.error('Failed to clear history from cloud:', e)
                      }
                    }
                  }}
                >
                  Clear All
                </button>
              )}
            </div>
            {conversations.length === 0 ? (
              <p className="history-empty">No saved conversations</p>
            ) : (
              <div className="history-list">
                {conversations.map(conv => (
                  <div
                    key={conv.id}
                    className={`history-item ${conv.id === currentConversationId ? 'active' : ''}`}
                    onClick={() => loadConversation(conv)}
                  >
                    <div className="history-item-content">
                      <span className="history-title">{conv.title}</span>
                      <span className="history-date">{formatDate(conv.updatedAt)}</span>
                    </div>
                    <button
                      className="history-delete"
                      onClick={(e) => deleteConversation(conv.id, e)}
                      title="Delete conversation"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <h3>Start a conversation</h3>
              <p>Ask me anything about your notes, tasks, or schedule.</p>
              <div className="suggestions">
                <button onClick={() => setInput("What did I write in my diary recently?")}>
                  What did I write in my diary recently?
                </button>
                <button onClick={() => setInput("What tasks do I have today?")}>
                  What tasks do I have today?
                </button>
                <button onClick={() => setInput("Summarize my notes about")}>
                  Summarize my notes about...
                </button>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-content">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources">
                    <span>Sources:</span>
                    {msg.sources.map((src, i) => (
                      <span key={i} className="source-tag">{src}</span>
                    ))}
                  </div>
                )}
                {msg.proposed_actions && msg.proposed_actions.length > 0 && (
                  <div className="proposed-actions">
                    {msg.proposed_actions.map((action) => (
                      <div key={action.id} className={`action-card ${action.status || 'pending'}`}>
                        <div className="action-info">
                          <span className="action-type">{action.type.replace('_', ' ')}</span>
                          <span className="action-data">{formatActionData(action)}</span>
                        </div>
                        {!action.status && (
                          <div className="action-buttons">
                            <button
                              className="btn btn-sm btn-primary"
                              onClick={() => handleApproveAction(action.id, idx)}
                            >
                              Approve
                            </button>
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={() => handleRejectAction(action.id, idx)}
                            >
                              Reject
                            </button>
                          </div>
                        )}
                        {action.status && (
                          <span className={`action-status ${action.status}`}>
                            {action.status}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
          {loading && (
            <div className="message assistant">
              <div className="message-content loading-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            className="chat-input"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </>
  )
}

export default Chat
