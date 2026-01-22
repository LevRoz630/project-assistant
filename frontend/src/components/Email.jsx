import { useState, useEffect } from 'react'
import './Email.css'
import { API_BASE } from '../config'

function Email() {
  const [emails, setEmails] = useState([])
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingEmail, setLoadingEmail] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [folders, setFolders] = useState([])
  const [selectedFolder, setSelectedFolder] = useState('inbox')

  useEffect(() => {
    loadFolders()
    loadEmails()
  }, [])

  const loadFolders = async () => {
    try {
      const res = await fetch(`${API_BASE}/email/folders`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setFolders(data.folders || [])
      }
    } catch (error) {
      console.error('Failed to load folders:', error)
    }
  }

  const loadEmails = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/email/inbox`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setEmails(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to load emails:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadEmail = async (emailId) => {
    setLoadingEmail(true)
    try {
      const res = await fetch(`${API_BASE}/email/message/${emailId}`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setSelectedEmail(data)
      }
    } catch (error) {
      console.error('Failed to load email:', error)
    } finally {
      setLoadingEmail(false)
    }
  }

  const searchEmails = async () => {
    if (!searchQuery.trim()) {
      loadEmails()
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/email/search?query=${encodeURIComponent(searchQuery)}`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setEmails(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to search emails:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Email</h2>
          <button className="btn btn-secondary" onClick={loadEmails}>
            Refresh
          </button>
        </div>
      </div>

      <div className="email-container">
        <div className="email-sidebar">
          <div className="email-search">
            <input
              type="text"
              placeholder="Search emails..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchEmails()}
            />
            <button onClick={searchEmails}>Search</button>
          </div>

          <div className="email-folders">
            {folders.map((folder) => (
              <div
                key={folder.id}
                className={`email-folder ${selectedFolder === folder.id ? 'active' : ''}`}
                onClick={() => setSelectedFolder(folder.id)}
              >
                <span className="folder-name">{folder.name}</span>
                {folder.unread_count > 0 && (
                  <span className="folder-badge">{folder.unread_count}</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="email-list">
          {loading ? (
            <div className="loading">
              <div className="loading-spinner"></div>
            </div>
          ) : emails.length === 0 ? (
            <div className="empty-state">
              <p>No emails found</p>
            </div>
          ) : (
            emails.map((email) => (
              <div
                key={email.id}
                className={`email-item ${!email.is_read ? 'unread' : ''} ${selectedEmail?.id === email.id ? 'selected' : ''}`}
                onClick={() => loadEmail(email.id)}
              >
                <div className="email-sender">{email.from_name}</div>
                <div className="email-subject">{email.subject}</div>
                <div className="email-preview">{email.preview}</div>
                <div className="email-date">{formatDate(email.received)}</div>
              </div>
            ))
          )}
        </div>

        <div className="email-content">
          {loadingEmail ? (
            <div className="loading">
              <div className="loading-spinner"></div>
            </div>
          ) : selectedEmail ? (
            <div className="email-detail">
              <div className="email-header">
                <h3>{selectedEmail.subject}</h3>
                <div className="email-meta">
                  <div>
                    <strong>From:</strong> {selectedEmail.from_name} &lt;{selectedEmail.from_email}&gt;
                  </div>
                  <div>
                    <strong>To:</strong> {selectedEmail.to?.join(', ')}
                  </div>
                  <div>
                    <strong>Date:</strong> {new Date(selectedEmail.received).toLocaleString()}
                  </div>
                </div>
              </div>
              <div
                className="email-body"
                dangerouslySetInnerHTML={{
                  __html: selectedEmail.body_type === 'html'
                    ? selectedEmail.body
                    : `<pre>${selectedEmail.body}</pre>`
                }}
              />
            </div>
          ) : (
            <div className="empty-state">
              <p>Select an email to view</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default Email
