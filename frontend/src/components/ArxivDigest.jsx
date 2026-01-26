import { useState, useEffect } from 'react'
import './ArxivDigest.css'
import { API_BASE } from '../config'

function ArxivDigest() {
  const [digest, setDigest] = useState(null)
  const [availableDates, setAvailableDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [status, setStatus] = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [editedConfig, setEditedConfig] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [digestRes, datesRes, statusRes, configRes] = await Promise.all([
        fetch(`${API_BASE}/arxiv/digest`, { credentials: 'include' }),
        fetch(`${API_BASE}/arxiv/digests`, { credentials: 'include' }),
        fetch(`${API_BASE}/arxiv/status`, { credentials: 'include' }),
        fetch(`${API_BASE}/arxiv/config`, { credentials: 'include' }),
      ])

      if (digestRes.ok) {
        const data = await digestRes.json()
        if (data.status !== 'no_digest') {
          setDigest(data)
          setSelectedDate(data.date)
        }
      }

      if (datesRes.ok) {
        const data = await datesRes.json()
        setAvailableDates(data.dates || [])
      }

      if (statusRes.ok) {
        const data = await statusRes.json()
        setStatus(data)
        setGenerating(data.is_generating)
      }

      if (configRes.ok) {
        const data = await configRes.json()
        setConfig(data)
        setEditedConfig(data)
      }
    } catch (error) {
      console.error('Failed to load arxiv data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadDigestByDate = async (date) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/arxiv/digest/${date}`, { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        setDigest(data)
        setSelectedDate(date)
      }
    } catch (error) {
      console.error('Failed to load digest:', error)
    } finally {
      setLoading(false)
    }
  }

  const triggerGeneration = async () => {
    setGenerating(true)
    try {
      const res = await fetch(`${API_BASE}/arxiv/run-now`, {
        method: 'POST',
        credentials: 'include',
      })
      if (res.ok) {
        // Poll for completion
        pollStatus()
      }
    } catch (error) {
      console.error('Failed to trigger generation:', error)
      setGenerating(false)
    }
  }

  const pollStatus = () => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/arxiv/status`, { credentials: 'include' })
        if (res.ok) {
          const data = await res.json()
          setStatus(data)
          if (!data.is_generating) {
            clearInterval(interval)
            setGenerating(false)
            loadData()
          }
        }
      } catch (error) {
        clearInterval(interval)
        setGenerating(false)
      }
    }, 3000)
  }

  const saveConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/arxiv/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(editedConfig),
      })
      if (res.ok) {
        const data = await res.json()
        setConfig(data.config)
        setShowSettings(false)
      }
    } catch (error) {
      console.error('Failed to save config:', error)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 8) return 'score-high'
    if (score >= 5) return 'score-medium'
    return 'score-low'
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  if (loading && !digest) {
    return (
      <div className="loading" style={{ height: '100%' }}>
        <div className="loading-spinner"></div>
      </div>
    )
  }

  return (
    <>
      <div className="content-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>ArXiv Digest</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {status?.scheduler_running && (
              <span className="scheduler-badge">Scheduler Active</span>
            )}
            <button
              className="btn btn-secondary"
              onClick={() => setShowSettings(!showSettings)}
            >
              Settings
            </button>
            <button
              className="btn btn-primary"
              onClick={triggerGeneration}
              disabled={generating}
            >
              {generating ? 'Generating...' : 'Generate Now'}
            </button>
          </div>
        </div>
      </div>

      {showSettings && (
        <div className="settings-panel">
          <h3>Digest Settings</h3>

          <div className="setting-group">
            <label>Categories (comma-separated)</label>
            <input
              type="text"
              value={editedConfig?.categories?.join(', ') || ''}
              onChange={(e) =>
                setEditedConfig({
                  ...editedConfig,
                  categories: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              placeholder="cs.AI, cs.CL, cs.LG"
            />
          </div>

          <div className="setting-group">
            <label>Research Interests</label>
            <textarea
              value={editedConfig?.interests || ''}
              onChange={(e) => setEditedConfig({ ...editedConfig, interests: e.target.value })}
              placeholder="AI agents, LLMs, NLP..."
              rows={3}
            />
          </div>

          <div className="setting-row">
            <div className="setting-group">
              <label>Schedule Hour (UTC)</label>
              <input
                type="number"
                min="0"
                max="23"
                value={editedConfig?.schedule_hour || 6}
                onChange={(e) =>
                  setEditedConfig({ ...editedConfig, schedule_hour: parseInt(e.target.value) })
                }
              />
            </div>

            <div className="setting-group">
              <label>Top N Papers</label>
              <input
                type="number"
                min="5"
                max="50"
                value={editedConfig?.top_n || 10}
                onChange={(e) =>
                  setEditedConfig({ ...editedConfig, top_n: parseInt(e.target.value) })
                }
              />
            </div>

            <div className="setting-group">
              <label>LLM Provider</label>
              <select
                value={editedConfig?.llm_provider || 'anthropic'}
                onChange={(e) => setEditedConfig({ ...editedConfig, llm_provider: e.target.value })}
              >
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="openai">OpenAI (GPT)</option>
                <option value="google">Google (Gemini)</option>
              </select>
            </div>
          </div>

          <div className="setting-actions">
            <button className="btn btn-secondary" onClick={() => setShowSettings(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={saveConfig}>
              Save Settings
            </button>
          </div>
        </div>
      )}

      <div className="content-body">
        {availableDates.length > 0 && (
          <div className="date-selector">
            <label>View digest for:</label>
            <select
              value={selectedDate || ''}
              onChange={(e) => loadDigestByDate(e.target.value)}
            >
              {availableDates.map((date) => (
                <option key={date} value={date}>
                  {formatDate(date)}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="digest-container">
        {!digest ? (
          <div className="empty-state">
            <h3>No digest available</h3>
            <p>Click &ldquo;Generate Now&rdquo; to create your first arXiv paper digest.</p>
            {config && (
              <div className="config-summary">
                <p>
                  <strong>Categories:</strong> {config.categories?.join(', ')}
                </p>
                <p>
                  <strong>Interests:</strong> {config.interests}
                </p>
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="digest-header">
              <h3>{formatDate(digest.date)}</h3>
              <p className="digest-meta">
                {digest.papers?.length} papers from {digest.total_papers_fetched} reviewed
              </p>
            </div>

            <div className="papers-list">
              {digest.papers?.map((paper, index) => (
                <div key={paper.arxiv_id} className="paper-card">
                  <div className="paper-rank">#{index + 1}</div>

                  <div className="paper-content">
                    <div className="paper-header">
                      <a
                        href={paper.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="paper-title"
                      >
                        {paper.title}
                      </a>
                      <span className={`relevance-score ${getScoreColor(paper.relevance_score)}`}>
                        {paper.relevance_score.toFixed(1)}
                      </span>
                    </div>

                    <div className="paper-authors">
                      {paper.authors?.slice(0, 5).join(', ')}
                      {paper.authors?.length > 5 && ` +${paper.authors.length - 5} more`}
                    </div>

                    <div className="paper-categories">
                      {paper.categories?.map((cat) => (
                        <span key={cat} className="category-tag">
                          {cat}
                        </span>
                      ))}
                    </div>

                    {paper.relevance_reason && (
                      <div className="paper-reason">
                        <strong>Why relevant:</strong> {paper.relevance_reason}
                      </div>
                    )}

                    <p className="paper-abstract">{paper.abstract}</p>

                    <div className="paper-footer">
                      <span className="paper-date">
                        Published: {new Date(paper.published).toLocaleDateString()}
                      </span>
                      <a
                        href={`https://arxiv.org/pdf/${paper.arxiv_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="pdf-link"
                      >
                        PDF
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        </div>
      </div>
    </>
  )
}

export default ArxivDigest
