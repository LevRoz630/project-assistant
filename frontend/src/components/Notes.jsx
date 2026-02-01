import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './Notes.css'
import { API_BASE } from '../config'

// Validate note name before sending to server
const validateNoteName = (name) => {
  if (!name.trim()) return null // Empty is handled separately
  if (name.length > 100) return 'Name is too long (max 100 characters)'
  if (/[\\/:*?"<>|]/.test(name)) return 'Name contains invalid characters (\\/:*?"<>|)'
  if (name.startsWith('.')) return 'Name cannot start with a dot'
  if (name.includes('..')) return 'Name cannot contain ".."'
  return null
}

// Parse structured error from backend
const parseError = (data, status) => {
  if (typeof data?.detail === 'object') {
    return { code: data.detail.code, message: data.detail.message }
  }
  if (typeof data?.detail === 'string') {
    return { code: 'unknown', message: data.detail }
  }
  return { code: 'unknown', message: `Failed to create note (${status})` }
}

function Notes() {
  const [folders, setFolders] = useState([])
  const [activeFolder, setActiveFolder] = useState('Diary')
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNewNote, setShowNewNote] = useState(false)
  const [newNoteName, setNewNoteName] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)
  const [validationError, setValidationError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadFolders()
  }, [])

  useEffect(() => {
    if (activeFolder) {
      loadNotes(activeFolder)
    }
  }, [activeFolder])

  const loadFolders = async () => {
    try {
      const res = await fetch(`${API_BASE}/notes/folders`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setFolders(data.folders || ['Diary', 'Projects', 'Study', 'Inbox'])
      }
    } catch (error) {
      console.error('Failed to load folders:', error)
      setFolders(['Diary', 'Projects', 'Study', 'Inbox'])
    }
  }

  const loadNotes = async (folder) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/notes/list/${folder}`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setNotes(data.notes || [])
      }
    } catch (error) {
      console.error('Failed to load notes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleNameChange = (e) => {
    const name = e.target.value
    setNewNoteName(name)
    setValidationError(validateNoteName(name))
    setError(null) // Clear server error when user starts typing
  }

  const createNote = async () => {
    if (!newNoteName.trim()) return

    // Check validation before sending
    const validation = validateNoteName(newNoteName)
    if (validation) {
      setValidationError(validation)
      return
    }

    const filename = newNoteName.endsWith('.md') ? newNoteName : `${newNoteName}.md`

    setCreating(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/notes/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          folder: activeFolder,
          filename,
          content: `# ${newNoteName.replace('.md', '')}\n\n`,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        setShowNewNote(false)
        setNewNoteName('')
        setValidationError(null)
        // Use the filename from response (backend may have normalized it)
        navigate(`/notes/${activeFolder}/${data.filename || filename}`)
      } else {
        const data = await res.json().catch(() => ({}))
        const { code, message } = parseError(data, res.status)

        // Handle "already exists" with option to open
        if (code === 'already_exists') {
          setError({ type: 'exists', message, filename })
        } else {
          setError({ type: 'error', message })
        }
      }
    } catch (err) {
      console.error('Failed to create note:', err)
      setError({ type: 'error', message: 'Network error - please try again' })
    } finally {
      setCreating(false)
    }
  }

  const openExistingNote = () => {
    const filename = newNoteName.endsWith('.md') ? newNoteName : `${newNoteName}.md`
    setShowNewNote(false)
    setNewNoteName('')
    setError(null)
    navigate(`/notes/${activeFolder}/${filename}`)
  }

  const createTodayDiary = async () => {
    try {
      const res = await fetch(`${API_BASE}/notes/diary/today`, {
        method: 'POST',
        credentials: 'include',
      })

      if (res.ok) {
        const data = await res.json()
        navigate(`/notes/Diary/${data.filename}`)
      }
    } catch (error) {
      console.error('Failed to create diary:', error)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Notes</h2>
          <div style={{ display: 'flex', gap: '12px' }}>
            {activeFolder === 'Diary' && (
              <button className="btn btn-secondary" onClick={createTodayDiary}>
                {"Today's Diary"}
              </button>
            )}
            <button className="btn btn-primary" onClick={() => { setShowNewNote(true); setError(null); }}>
              New Note
            </button>
          </div>
        </div>
      </div>

      <div className="content-body">
        <div className="notes-layout">
          <div className="folders-list">
            {(Array.isArray(folders) ? folders : ['Diary', 'Projects', 'Study', 'Inbox']).map((folder) => {
              const name = typeof folder === 'string' ? folder : folder.name
              return (
                <button
                  key={name}
                  className={`folder-item ${activeFolder === name ? 'active' : ''}`}
                  onClick={() => setActiveFolder(name)}
                >
                  <FolderIcon />
                  {name}
                </button>
              )
            })}
          </div>

          <div className="notes-list">
            {loading ? (
              <div className="loading">
                <div className="loading-spinner"></div>
              </div>
            ) : notes.length === 0 ? (
              <div className="empty-state">
                <h3>No notes in {activeFolder}</h3>
                <p>Create your first note to get started</p>
              </div>
            ) : (
              notes.map((note) => (
                <div
                  key={note.id || note.name}
                  className="note-item"
                  onClick={() => navigate(`/notes/${activeFolder}/${note.name}`)}
                >
                  <div className="note-icon">
                    <NoteIcon />
                  </div>
                  <div className="note-info">
                    <div className="note-name">{note.name.replace('.md', '')}</div>
                    <div className="note-meta">
                      Modified {formatDate(note.modified)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {showNewNote && (
          <div className="modal-overlay" onClick={() => !creating && setShowNewNote(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h3>New Note</h3>
              {error && error.type === 'exists' && (
                <div style={{
                  padding: '10px 12px',
                  background: 'var(--warning, #e67e22)',
                  color: 'white',
                  borderRadius: '6px',
                  marginBottom: '16px',
                  fontSize: '14px'
                }}>
                  <div>{error.message}</div>
                  <button
                    onClick={openExistingNote}
                    style={{
                      marginTop: '8px',
                      padding: '6px 12px',
                      background: 'rgba(255,255,255,0.2)',
                      border: 'none',
                      borderRadius: '4px',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '13px'
                    }}
                  >
                    Open existing note
                  </button>
                </div>
              )}
              {error && error.type === 'error' && (
                <div style={{
                  padding: '10px 12px',
                  background: 'var(--error)',
                  color: 'white',
                  borderRadius: '6px',
                  marginBottom: '16px',
                  fontSize: '14px'
                }}>
                  {error.message}
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Note Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="my-note"
                  value={newNoteName}
                  onChange={handleNameChange}
                  onKeyDown={(e) => e.key === 'Enter' && !creating && !validationError && createNote()}
                  disabled={creating}
                  autoFocus
                  style={validationError ? { borderColor: 'var(--error)' } : {}}
                />
                {validationError && (
                  <div style={{ color: 'var(--error)', fontSize: '13px', marginTop: '6px' }}>
                    {validationError}
                  </div>
                )}
              </div>
              <div className="modal-actions">
                <button
                  className="btn btn-secondary"
                  onClick={() => { setShowNewNote(false); setValidationError(null); setError(null); }}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={createNote}
                  disabled={creating || !newNoteName.trim() || !!validationError}
                >
                  {creating ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

function FolderIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
    </svg>
  )
}

function NoteIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  )
}

export default Notes
