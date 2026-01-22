import { useState, useEffect } from 'react'
import './Actions.css'
import { API_BASE } from '../config'

function Actions() {
  const [pendingActions, setPendingActions] = useState([])
  const [historyActions, setHistoryActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(null)
  const [activeTab, setActiveTab] = useState('pending')

  useEffect(() => {
    loadActions()
  }, [])

  const loadActions = async () => {
    setLoading(true)
    try {
      const [pendingRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/actions/pending`, { credentials: 'include' }),
        fetch(`${API_BASE}/actions/history?limit=20`, { credentials: 'include' }),
      ])

      if (pendingRes.ok) {
        const data = await pendingRes.json()
        setPendingActions(data.actions || [])
      }

      if (historyRes.ok) {
        const data = await historyRes.json()
        setHistoryActions(data.actions || [])
      }
    } catch (error) {
      console.error('Failed to load actions:', error)
    } finally {
      setLoading(false)
    }
  }

  const approveAction = async (actionId) => {
    setProcessing(actionId)
    try {
      const res = await fetch(`${API_BASE}/actions/${actionId}/approve`, {
        method: 'POST',
        credentials: 'include',
      })

      if (res.ok) {
        await loadActions()
      } else {
        const error = await res.json()
        alert(`Failed to approve: ${error.detail}`)
      }
    } catch (error) {
      console.error('Failed to approve action:', error)
    } finally {
      setProcessing(null)
    }
  }

  const rejectAction = async (actionId) => {
    setProcessing(actionId)
    try {
      const res = await fetch(`${API_BASE}/actions/${actionId}/reject`, {
        method: 'POST',
        credentials: 'include',
      })

      if (res.ok) {
        await loadActions()
      } else {
        const error = await res.json()
        alert(`Failed to reject: ${error.detail}`)
      }
    } catch (error) {
      console.error('Failed to reject action:', error)
    } finally {
      setProcessing(null)
    }
  }

  const getActionIcon = (type) => {
    switch (type) {
      case 'create_task':
        return '✓'
      case 'create_event':
        return '📅'
      case 'create_note':
      case 'edit_note':
        return '📝'
      case 'draft_email':
        return '✉️'
      default:
        return '⚡'
    }
  }

  const getActionTitle = (action) => {
    const { type, data } = action
    switch (type) {
      case 'create_task':
        return `Create Task: ${data.title}`
      case 'create_event':
        return `Create Event: ${data.subject}`
      case 'create_note':
        return `Create Note: ${data.filename}`
      case 'edit_note':
        return `Edit Note: ${data.filename}`
      case 'draft_email':
        return `Draft Email: ${data.subject}`
      default:
        return `Action: ${type}`
    }
  }

  const getStatusBadge = (status) => {
    const classes = {
      pending: 'badge-pending',
      approved: 'badge-approved',
      rejected: 'badge-rejected',
      executed: 'badge-executed',
      failed: 'badge-failed',
    }
    return <span className={`badge ${classes[status] || ''}`}>{status}</span>
  }

  const renderActionDetails = (action) => {
    const { type, data } = action

    switch (type) {
      case 'create_task':
        return (
          <div className="action-details">
            <div><strong>Title:</strong> {data.title}</div>
            {data.body && <div><strong>Description:</strong> {data.body}</div>}
            {data.due_date && <div><strong>Due:</strong> {data.due_date}</div>}
            {data.importance !== 'normal' && <div><strong>Priority:</strong> {data.importance}</div>}
          </div>
        )

      case 'create_event':
        return (
          <div className="action-details">
            <div><strong>Subject:</strong> {data.subject}</div>
            <div><strong>Start:</strong> {new Date(data.start_datetime).toLocaleString()}</div>
            <div><strong>End:</strong> {new Date(data.end_datetime).toLocaleString()}</div>
            {data.location && <div><strong>Location:</strong> {data.location}</div>}
            {data.attendees?.length > 0 && (
              <div><strong>Attendees:</strong> {data.attendees.join(', ')}</div>
            )}
          </div>
        )

      case 'create_note':
      case 'edit_note':
        return (
          <div className="action-details">
            <div><strong>Folder:</strong> {data.folder}</div>
            <div><strong>Filename:</strong> {data.filename}</div>
            <div><strong>Content Preview:</strong></div>
            <pre className="content-preview">{data.content?.substring(0, 500)}...</pre>
          </div>
        )

      case 'draft_email':
        return (
          <div className="action-details">
            <div><strong>To:</strong> {data.to?.join(', ')}</div>
            <div><strong>Subject:</strong> {data.subject}</div>
            <div><strong>Body:</strong></div>
            <pre className="content-preview">{data.body}</pre>
          </div>
        )

      default:
        return (
          <div className="action-details">
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </div>
        )
    }
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString()
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>AI Actions</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {pendingActions.length > 0 && (
              <span className="pending-count">{pendingActions.length} pending</span>
            )}
            <button className="btn btn-secondary" onClick={loadActions}>
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="actions-tabs">
        <button
          className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          Pending ({pendingActions.length})
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
      </div>

      <div className="actions-container">
        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
          </div>
        ) : activeTab === 'pending' ? (
          pendingActions.length === 0 ? (
            <div className="empty-state">
              <h3>No pending actions</h3>
              <p>When the AI proposes actions, they will appear here for your approval.</p>
            </div>
          ) : (
            pendingActions.map((action) => (
              <div key={action.id} className="action-card pending">
                <div className="action-header">
                  <span className="action-icon">{getActionIcon(action.type)}</span>
                  <span className="action-title">{getActionTitle(action)}</span>
                  {getStatusBadge(action.status)}
                </div>

                <div className="action-reason">
                  <strong>AI Reason:</strong> {action.reason}
                </div>

                {renderActionDetails(action)}

                <div className="action-footer">
                  <span className="action-time">Created: {formatDate(action.created_at)}</span>
                  <div className="action-buttons">
                    <button
                      className="btn btn-danger"
                      onClick={() => rejectAction(action.id)}
                      disabled={processing === action.id}
                    >
                      Reject
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={() => approveAction(action.id)}
                      disabled={processing === action.id}
                    >
                      {processing === action.id ? 'Processing...' : 'Approve'}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )
        ) : (
          historyActions.length === 0 ? (
            <div className="empty-state">
              <h3>No action history</h3>
              <p>Approved and rejected actions will appear here.</p>
            </div>
          ) : (
            historyActions.map((action) => (
              <div key={action.id} className={`action-card ${action.status}`}>
                <div className="action-header">
                  <span className="action-icon">{getActionIcon(action.type)}</span>
                  <span className="action-title">{getActionTitle(action)}</span>
                  {getStatusBadge(action.status)}
                </div>

                <div className="action-reason">
                  <strong>AI Reason:</strong> {action.reason}
                </div>

                {action.error && (
                  <div className="action-error">
                    <strong>Error:</strong> {action.error}
                  </div>
                )}

                <div className="action-footer">
                  <span className="action-time">
                    Created: {formatDate(action.created_at)}
                  </span>
                </div>
              </div>
            ))
          )
        )}
      </div>
    </>
  )
}

export default Actions
