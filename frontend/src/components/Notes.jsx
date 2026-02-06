import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './Notes.css'
import { API_BASE, encodePath } from '../config'

// Validate note name before sending to server
const validateNoteName = (name) => {
  if (!name.trim()) return null // Empty is handled separately
  if (name.length > 100) return 'Name is too long (max 100 characters)'
  if (/[\\/:*?"<>|]/.test(name)) return 'Name contains invalid characters (\\/:*?"<>|)'
  if (name.startsWith('.')) return 'Name cannot start with a dot'
  if (name.includes('..')) return 'Name cannot contain ".."'
  return null
}

// Validate folder name
const validateFolderName = (name) => {
  if (!name.trim()) return null
  if (name.length > 100) return 'Name is too long (max 100 characters)'
  if (/[\\/:*?"<>|]/.test(name)) return 'Name contains invalid characters'
  if (name.startsWith('.') || name.startsWith('_')) return 'Name cannot start with "." or "_"'
  if (name.includes('..')) return 'Name cannot contain ".."'
  return null
}

// Parse structured error from backend - always returns string message
const parseError = (data, status) => {
  if (typeof data?.detail === 'object') {
    const msg = data.detail.message
    return {
      code: data.detail.code || 'unknown',
      // Ensure message is always a string
      message: typeof msg === 'string' ? msg : (msg ? JSON.stringify(msg) : 'An error occurred')
    }
  }
  if (typeof data?.detail === 'string') {
    return { code: 'unknown', message: data.detail }
  }
  return { code: 'unknown', message: `Failed to create note (${status})` }
}

function Notes({ folderPath }) {
  const [folders, setFolders] = useState([])
  const [notes, setNotes] = useState([])
  const [subfolders, setSubfolders] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNewNote, setShowNewNote] = useState(false)
  const [newNoteName, setNewNoteName] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)
  const [validationError, setValidationError] = useState(null)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [folderError, setFolderError] = useState(null)
  const [folderValidationError, setFolderValidationError] = useState(null)
  const navigate = useNavigate()

  // Determine the current path from prop (URL-driven)
  const currentPath = folderPath || null

  useEffect(() => {
    if (!currentPath) {
      loadFolders()
    }
  }, [])

  useEffect(() => {
    if (currentPath) {
      loadNotes(currentPath)
    } else {
      setNotes([])
      setSubfolders([])
      setLoading(false)
    }
  }, [currentPath])

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
    } finally {
      setLoading(false)
    }
  }

  const loadNotes = async (folderToLoad) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/notes/list/${encodePath(folderToLoad)}`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setNotes(data.notes || [])
        setSubfolders(data.subfolders || [])
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
    setError(null)
  }

  const handleFolderNameChange = (e) => {
    const name = e.target.value
    setNewFolderName(name)
    setFolderValidationError(validateFolderName(name))
    setFolderError(null)
  }

  const createNote = async () => {
    if (!newNoteName.trim() || !currentPath) return

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
          folder: currentPath,
          filename,
          content: `# ${newNoteName.replace('.md', '')}\n\n`,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        setShowNewNote(false)
        setNewNoteName('')
        setValidationError(null)
        navigate(`/notes/${encodePath(currentPath)}/${encodeURIComponent(data.filename || filename)}`)
      } else {
        const data = await res.json().catch(() => ({}))
        const { code, message } = parseError(data, res.status)

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
    navigate(`/notes/${encodePath(currentPath)}/${encodeURIComponent(filename)}`)
  }

  const createFolder = async () => {
    if (!newFolderName.trim() || !currentPath) return

    const validation = validateFolderName(newFolderName)
    if (validation) {
      setFolderValidationError(validation)
      return
    }

    setCreatingFolder(true)
    setFolderError(null)

    try {
      const res = await fetch(`${API_BASE}/notes/create-folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          parent_path: currentPath,
          name: newFolderName,
        }),
      })

      if (res.ok) {
        setShowNewFolder(false)
        setNewFolderName('')
        setFolderValidationError(null)
        loadNotes(currentPath)
      } else {
        const data = await res.json().catch(() => ({}))
        const { message } = parseError(data, res.status)
        setFolderError({ type: 'error', message })
      }
    } catch (err) {
      console.error('Failed to create folder:', err)
      setFolderError({ type: 'error', message: 'Network error - please try again' })
    } finally {
      setCreatingFolder(false)
    }
  }

  const createTodayDiary = async () => {
    try {
      const res = await fetch(`${API_BASE}/notes/diary/today`, {
        method: 'POST',
        credentials: 'include',
      })

      if (res.ok) {
        const data = await res.json()
        navigate(`/notes/Diary/${encodeURIComponent(data.filename)}`)
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

  // Build breadcrumb segments from currentPath
  const breadcrumbs = currentPath ? currentPath.split('/') : []

  // Top-level folder view (no path selected)
  if (!currentPath) {
    return (
      <>
        <div className="content-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Notes</h2>
          </div>
        </div>

        <div className="content-body">
          <div className="notes-layout">
            <div className="folders-list">
              {loading ? (
                <div className="loading">
                  <div className="loading-spinner"></div>
                </div>
              ) : (
                (Array.isArray(folders) ? folders : ['Diary', 'Projects', 'Study', 'Inbox']).map((folder) => {
                  const name = typeof folder === 'string' ? folder : folder.name
                  return (
                    <button
                      key={name}
                      className="folder-item"
                      onClick={() => navigate(`/notes/${encodePath(name)}`)}
                    >
                      <FolderIcon />
                      {name}
                    </button>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </>
    )
  }

  // Folder contents view (inside a folder)
  const topFolder = breadcrumbs[0]

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2>Notes</h2>
            <div className="breadcrumbs">
              <span
                className="breadcrumb-item"
                onClick={() => navigate('/notes')}
              >
                All
              </span>
              {breadcrumbs.map((segment, i) => {
                const path = breadcrumbs.slice(0, i + 1).join('/')
                const isLast = i === breadcrumbs.length - 1
                return (
                  <span key={path}>
                    <span className="breadcrumb-separator">/</span>
                    <span
                      className={`breadcrumb-item ${isLast ? 'breadcrumb-active' : ''}`}
                      onClick={() => !isLast && navigate(`/notes/${encodePath(path)}`)}
                    >
                      {segment}
                    </span>
                  </span>
                )
              })}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            {topFolder === 'Diary' && breadcrumbs.length === 1 && (
              <button className="btn btn-secondary" onClick={createTodayDiary}>
                {"Today's Diary"}
              </button>
            )}
            <button className="btn btn-secondary" onClick={() => { setShowNewFolder(true); setFolderError(null); }}>
              New Folder
            </button>
            <button className="btn btn-primary" onClick={() => { setShowNewNote(true); setError(null); }}>
              New Note
            </button>
          </div>
        </div>
      </div>

      <div className="content-body">
        <div className="notes-layout">
          <div className="notes-list">
            {loading ? (
              <div className="loading">
                <div className="loading-spinner"></div>
              </div>
            ) : (
              <>
                {subfolders.map((sf) => (
                  <div
                    key={sf.path}
                    className="note-item subfolder-item"
                    onClick={() => navigate(`/notes/${encodePath(sf.path)}`)}
                  >
                    <div className="note-icon">
                      <FolderIcon />
                    </div>
                    <div className="note-info">
                      <div className="note-name">{sf.name}</div>
                      <div className="note-meta">
                        {sf.childCount} {sf.childCount === 1 ? 'item' : 'items'}
                      </div>
                    </div>
                    <div className="subfolder-chevron">
                      <ChevronIcon />
                    </div>
                  </div>
                ))}

                {notes.length === 0 && subfolders.length === 0 ? (
                  <div className="empty-state">
                    <h3>No notes in {breadcrumbs[breadcrumbs.length - 1]}</h3>
                    <p>Create your first note or subfolder to get started</p>
                  </div>
                ) : (
                  notes.map((note) => (
                    <div
                      key={note.id || note.name}
                      className="note-item"
                      onClick={() => navigate(`/notes/${encodePath(currentPath)}/${encodeURIComponent(note.name)}`)}
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
              </>
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
                  <div>{typeof error.message === 'string' ? error.message : 'Note already exists'}</div>
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
                  {typeof error.message === 'string' ? error.message : 'An error occurred'}
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

        {showNewFolder && (
          <div className="modal-overlay" onClick={() => !creatingFolder && setShowNewFolder(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h3>New Folder</h3>
              {folderError && folderError.type === 'error' && (
                <div style={{
                  padding: '10px 12px',
                  background: 'var(--error)',
                  color: 'white',
                  borderRadius: '6px',
                  marginBottom: '16px',
                  fontSize: '14px'
                }}>
                  {typeof folderError.message === 'string' ? folderError.message : 'An error occurred'}
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Folder Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="my-folder"
                  value={newFolderName}
                  onChange={handleFolderNameChange}
                  onKeyDown={(e) => e.key === 'Enter' && !creatingFolder && !folderValidationError && createFolder()}
                  disabled={creatingFolder}
                  autoFocus
                  style={folderValidationError ? { borderColor: 'var(--error)' } : {}}
                />
                {folderValidationError && (
                  <div style={{ color: 'var(--error)', fontSize: '13px', marginTop: '6px' }}>
                    {folderValidationError}
                  </div>
                )}
              </div>
              <div className="modal-actions">
                <button
                  className="btn btn-secondary"
                  onClick={() => { setShowNewFolder(false); setFolderValidationError(null); setFolderError(null); }}
                  disabled={creatingFolder}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={createFolder}
                  disabled={creatingFolder || !newFolderName.trim() || !!folderValidationError}
                >
                  {creatingFolder ? 'Creating...' : 'Create'}
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

function ChevronIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  )
}

export default Notes
