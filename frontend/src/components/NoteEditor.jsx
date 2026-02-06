import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import './NoteEditor.css'
import { API_BASE, encodePath } from '../config'

const AUTO_SAVE_DELAY = 2000 // 2 seconds

function NoteEditor({ folder, filename }) {
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
  const [folderTree, setFolderTree] = useState([])
  const [loadingTree, setLoadingTree] = useState(false)
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
      const res = await fetch(`${API_BASE}/notes/content/${encodePath(folder)}/${encodeURIComponent(filename)}`, {
        credentials: 'include',
      })

      if (res.ok) {
        const data = await res.json()
        setContent(data.content || '')
        setOriginalContent(data.content || '')
      } else if (res.status === 404) {
        const data = await res.json().catch(() => ({}))
        const msg = typeof data?.detail === 'object' ? data.detail.message : 'Note not found'
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
      const res = await fetch(`${API_BASE}/notes/update/${encodePath(folder)}/${encodeURIComponent(filename)}`, {
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
      const res = await fetch(`${API_BASE}/notes/delete/${encodePath(folder)}/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (res.ok) {
        navigate(`/notes/${encodePath(folder)}`)
      } else {
        throw new Error('Failed to delete note')
      }
    } catch (error) {
      console.error('Failed to delete note:', error)
      alert('Failed to delete note')
    }
  }

  const loadFolderTree = async () => {
    setLoadingTree(true)
    try {
      const res = await fetch(`${API_BASE}/notes/folder-tree`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setFolderTree(data.tree || [])
      }
    } catch (err) {
      console.error('Failed to load folder tree:', err)
    } finally {
      setLoadingTree(false)
    }
  }

  const openMoveModal = () => {
    setShowMoveModal(true)
    loadFolderTree()
  }

  const moveNote = async (targetFolder) => {
    if (targetFolder === folder) return

    setMoving(true)
    try {
      const res = await fetch(`${API_BASE}/notes/move/${encodePath(folder)}/${encodeURIComponent(filename)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ target_folder: targetFolder }),
      })

      if (res.ok) {
        navigate(`/notes/${encodePath(targetFolder)}/${encodeURIComponent(filename)}`)
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

  // Breadcrumb segments for the folder path
  const folderSegments = folder.split('/')

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
            <button className="btn btn-primary" onClick={() => navigate(`/notes/${encodePath(folder)}`)}>
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
            <button className="btn btn-secondary" onClick={() => navigate(`/notes/${encodePath(folder)}`)}>
              &#8592; Back
            </button>
            <h2>{filename.replace('.md', '')}</h2>
            <span className="folder-badge">{folderSegments[folderSegments.length - 1]}</span>
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
            <button className="btn btn-secondary" onClick={openMoveModal}>
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
            <div style={{ marginTop: '16px', maxHeight: '400px', overflowY: 'auto' }}>
              {loadingTree ? (
                <div className="loading">
                  <div className="loading-spinner"></div>
                </div>
              ) : (
                <FolderTreeView
                  nodes={folderTree}
                  currentFolder={folder}
                  onSelect={moveNote}
                  moving={moving}
                  depth={0}
                />
              )}
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

function FolderTreeView({ nodes, currentFolder, onSelect, moving, depth }) {
  const [expanded, setExpanded] = useState({})

  const toggle = (path) => {
    setExpanded(prev => ({ ...prev, [path]: !prev[path] }))
  }

  return (
    <div className="folder-tree">
      {nodes.map((node) => {
        const isCurrent = node.path === currentFolder
        const hasChildren = node.children && node.children.length > 0
        const isExpanded = expanded[node.path]

        return (
          <div key={node.path}>
            <div className="folder-tree-row" style={{ paddingLeft: `${depth * 20}px` }}>
              {hasChildren ? (
                <button
                  className={`folder-tree-toggle ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => toggle(node.path)}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </button>
              ) : (
                <span className="folder-tree-spacer" />
              )}
              <button
                className={`btn btn-secondary folder-tree-btn ${isCurrent ? 'current' : ''}`}
                onClick={() => onSelect(node.path)}
                disabled={moving || isCurrent}
              >
                {node.name}{isCurrent ? ' (current)' : ''}
              </button>
            </div>
            {hasChildren && isExpanded && (
              <FolderTreeView
                nodes={node.children}
                currentFolder={currentFolder}
                onSelect={onSelect}
                moving={moving}
                depth={depth + 1}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default NoteEditor
