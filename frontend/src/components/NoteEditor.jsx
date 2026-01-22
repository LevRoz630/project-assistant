import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import './NoteEditor.css'

const API_BASE = 'http://localhost:8000'

function NoteEditor() {
  const { folder, filename } = useParams()
  const navigate = useNavigate()
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadNote()
  }, [folder, filename])

  const loadNote = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/notes/content/${folder}/${filename}`, {
        credentials: 'include',
      })

      if (res.ok) {
        const data = await res.json()
        setContent(data.content || '')
        setOriginalContent(data.content || '')
      } else if (res.status === 404) {
        setError('Note not found')
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

  const saveNote = async () => {
    setSaving(true)
    try {
      const res = await fetch(`${API_BASE}/notes/update/${folder}/${filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ content }),
      })

      if (res.ok) {
        setOriginalContent(content)
      } else {
        throw new Error('Failed to save note')
      }
    } catch (error) {
      console.error('Failed to save note:', error)
      alert('Failed to save note')
    } finally {
      setSaving(false)
    }
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

  const hasChanges = content !== originalContent

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
            <h3>{error}</h3>
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
              className="btn btn-primary"
              onClick={saveNote}
              disabled={!hasChanges || saving}
            >
              {saving ? 'Saving...' : hasChanges ? 'Save' : 'Saved'}
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
            onChange={(e) => setContent(e.target.value)}
            placeholder="Start writing..."
            spellCheck="false"
          />
        )}
      </div>
    </>
  )
}

export default NoteEditor
