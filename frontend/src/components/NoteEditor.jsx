import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import './NoteEditor.css'
import { API_BASE } from '../config'

const AUTO_SAVE_DELAY = 2000 // 2 seconds

function NoteEditor() {
  const { folder, filename } = useParams()
  const navigate = useNavigate()
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState('saved') // 'saved' | 'saving' | 'failed' | 'unsaved'
  const [showPreview, setShowPreview] = useState(false)
  const [showMoveModal, setShowMoveModal] = useState(false)
  const [moving, setMoving] = useState(false)
  const [error, setError] = useState(null)
  const autoSaveTimer = useRef(null)
  const isMounted = useRef(true)

  // Cleanup on unmount
  useEffect(() => {
    isMounted.current = true
    return () => {
      isMounted.current = false
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current)
      }
    }
  }, [])

  useEffect(() => {
    loadNote()
  }, [folder, filename])

  const loadNote = async () => {
    setLoading(true)
    setError(null)
    setSaveStatus('saved')
    try {
      const res = await fetch(`${API_BASE}/notes/content/${folder}/${filename}`, {
        credentials: 'include',
      })

      if (res.ok) {
        const data = await res.json()
        setContent(data.content || '')
        setOriginalContent(data.content || '')
      } else if (res.status === 404) {
        const data = await res.json().catch(() => ({}))
        const msg = typeof data?.detail === 'object' ? data.detail.message : 'Note not found'
        // Ensure error message is always a string
        setError(typeof msg === 'string' ? msg : 'Note not found')
      } else {
        throw new Error('Failed to load note')
      }
    } catch (error) {
      console.error('Failed to load note:', error)
      setError('Failed to load note')
    } finally {
      setLoading(false)
    }
  }

  const saveNote = useCallback(async (contentToSave) => {
    if (!isMounted.current) return

    setSaving(true)
    setSaveStatus('saving')
    try {
      const res = await fetch(`${API_BASE}/notes/update/${folder}/${filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ content: contentToSave }),
      })

      if (!isMounted.current) return

      if (res.ok) {
        setOriginalContent(contentToSave)
        setSaveStatus('saved')
      } else {
        const data = await res.json().catch(() => ({}))
        const message = typeof data?.detail === 'object' ? data.detail.message : 'Failed to save note'
        console.error('Save failed:', message)
        setSaveStatus('failed')
      }
    } catch (error) {
      console.error('Failed to save note:', error)
      if (isMounted.current) {
        setSaveStatus('failed')
      }
    } finally {
      if (isMounted.current) {
        setSaving(false)
      }
    }
  }, [folder, filename])

  // Auto-save with debounce
  useEffect(() => {
    if (content === originalContent) {
      setSaveStatus('saved')
      return
    }

    setSaveStatus('unsaved')

    // Clear previous timer
    if (autoSaveTimer.current) {
      clearTimeout(autoSaveTimer.current)
    }

    // Set new timer for auto-save
    autoSaveTimer.current = setTimeout(() => {
      saveNote(content)
    }, AUTO_SAVE_DELAY)

    return () => {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current)
      }
    }
  }, [content, originalContent, saveNote])

  const handleContentChange = (e) => {
    setContent(e.target.value)
  }

  const handleManualSave = () => {
    if (autoSaveTimer.current) {
      clearTimeout(autoSaveTimer.current)
    }
    saveNote(content)
  }

  const deleteNote = async () => {
    if (!confirm('Are you sure you want to delete this note?')) return

    try {
      const res = await fetch(`${API_BASE}/notes/delete/${folder}/${filename}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (res.ok) {
        navigate('/notes')
      } else {
        throw new Error('Failed to delete note')
      }
    } catch (error) {
      console.error('Failed to delete note:', error)
      alert('Failed to delete note')
    }
  }

  const moveNote = async (targetFolder) => {
    if (targetFolder === folder) return

    setMoving(true)
    try {
      const res = await fetch(`${API_BASE}/notes/move/${folder}/${filename}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ target_folder: targetFolder }),
      })

      if (res.ok) {
        navigate(`/notes/${targetFolder}/${filename}`)
      } else {
        const data = await res.json().catch(() => ({}))
        const msg = typeof data?.detail === 'object' ? data.detail.message : 'Failed to move note'
        alert(typeof msg === 'string' ? msg : 'Failed to move note')
      }
    } catch (err) {
      console.error('Failed to move note:', err)
      alert('Failed to move note')
    } finally {
      setMoving(false)
      setShowMoveModal(false)
    }
  }

  const hasChanges = content !== originalContent

  const getSaveButtonText = () => {
    switch (saveStatus) {
      case 'saving': return 'Saving...'
      case 'failed': return 'Save failed - retry'
      case 'unsaved': return 'Save'
      default: return 'Saved'
    }
  }

  if (loading) {
    return (
      <>
        <div className="content-header">
          <h2>Loading...</h2>
        </div>
        <div className="content-body">
          <div className="loading">
            <div className="loading-spinner"></div>
          </div>
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <div className="content-header">
          <h2>Error</h2>
        </div>
        <div className="content-body">
          <div className="empty-state">
            <h3>{typeof error === 'string' ? error : 'An error occurred'}</h3>
            <button className="btn btn-primary" onClick={() => navigate('/notes')}>
              Back to Notes
            </button>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn btn-secondary" onClick={() => navigate('/notes')}>
              ← Back
            </button>
            <h2>{filename.replace('.md', '')}</h2>
            <span className="folder-badge">{folder}</span>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className={`btn ${showPreview ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setShowPreview(!showPreview)}
            >
              {showPreview ? 'Edit' : 'Preview'}
            </button>
            <button
              className={`btn ${saveStatus === 'failed' ? 'btn-danger' : 'btn-primary'}`}
              onClick={handleManualSave}
              disabled={(!hasChanges && saveStatus !== 'failed') || saving}
            >
              {getSaveButtonText()}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowMoveModal(true)}>
              Move
            </button>
            <button className="btn btn-danger" onClick={deleteNote}>
              Delete
            </button>
          </div>
        </div>
      </div>

      <div className="editor-container">
        {showPreview ? (
          <div className="preview-pane">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : (
          <textarea
            className="editor-textarea"
            value={content}
            onChange={handleContentChange}
            placeholder="Start writing..."
            spellCheck="false"
          />
        )}
      </div>

      {showMoveModal && (
        <div className="modal-overlay" onClick={() => !moving && setShowMoveModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Move to folder</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
              {['Diary', 'Projects', 'Study', 'Inbox']
                .filter((f) => f !== folder)
                .map((f) => (
                  <button
                    key={f}
                    className="btn btn-secondary"
                    onClick={() => moveNote(f)}
                    disabled={moving}
                    style={{ width: '100%', justifyContent: 'center' }}
                  >
                    {moving ? 'Moving...' : f}
                  </button>
                ))}
            </div>
            <div className="modal-actions" style={{ marginTop: '16px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowMoveModal(false)}
                disabled={moving}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default NoteEditor
