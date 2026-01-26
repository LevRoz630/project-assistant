import { useState, useEffect } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import Chat from './components/Chat'
import Notes from './components/Notes'
import NoteEditor from './components/NoteEditor'
import Tasks from './components/Tasks'
import Calendar from './components/Calendar'
import Email from './components/Email'
import Actions from './components/Actions'
import ArxivDigest from './components/ArxivDigest'
import Accounts from './components/Accounts'
import { API_BASE } from './config'

function App() {
  const [user, setUser] = useState(null)
  const [accounts, setAccounts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
        // Also fetch accounts info
        loadAccounts()
      }
    } catch (error) {
      console.error('Auth check failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadAccounts = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/accounts`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setAccounts(data)
      }
    } catch (error) {
      console.error('Failed to load accounts:', error)
    }
  }

  const handleLogin = (type = '') => {
    const endpoint = type ? `/auth/login/${type}` : '/auth/login'
    window.location.href = `${API_BASE}${endpoint}`
  }

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        credentials: 'include',
      })
      setUser(null)
      setAccounts(null)
      navigate('/')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  if (loading) {
    return (
      <div className="loading" style={{ height: '100vh' }}>
        <div className="loading-spinner"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="login-container">
        <h1>Personal AI Assistant</h1>
        <p>Your unified productivity hub with AI-powered insights</p>

        <div className="login-options">
          <button className="login-btn" onClick={() => handleLogin()}>
            <MicrosoftIcon />
            Sign in with Microsoft
          </button>
          <p className="login-hint">
            Use a single account for all services, or add separate accounts after signing in.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="app-container">
      {/* Mobile header */}
      <header className="mobile-header">
        <h1>AI Assistant</h1>
        <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          <MenuIcon />
        </button>
      </header>

      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <nav className="mobile-menu" onClick={(e) => e.stopPropagation()}>
            <NavLink to="/" onClick={() => setMobileMenuOpen(false)}>
              <ChatIcon /> Chat
            </NavLink>
            <NavLink to="/notes" onClick={() => setMobileMenuOpen(false)}>
              <NotesIcon /> Notes
            </NavLink>
            <NavLink to="/tasks" onClick={() => setMobileMenuOpen(false)}>
              <TasksIcon /> Tasks
            </NavLink>
            <NavLink to="/calendar" onClick={() => setMobileMenuOpen(false)}>
              <CalendarIcon /> Calendar
            </NavLink>
            <NavLink to="/email" onClick={() => setMobileMenuOpen(false)}>
              <EmailIcon /> Email
            </NavLink>
            <NavLink to="/arxiv" onClick={() => setMobileMenuOpen(false)}>
              <ArxivIcon /> ArXiv
            </NavLink>
            <div className="mobile-menu-divider"></div>
            <NavLink to="/actions" onClick={() => setMobileMenuOpen(false)}>
              <ActionsIcon /> Actions
            </NavLink>
            <NavLink to="/accounts" onClick={() => setMobileMenuOpen(false)}>
              <SettingsIcon /> Accounts
            </NavLink>
            <div className="mobile-menu-divider"></div>
            <button className="mobile-logout" onClick={handleLogout}>
              Sign Out
            </button>
          </nav>
        </div>
      )}

      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>AI Assistant</h1>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
            <ChatIcon />
            Chat
          </NavLink>
          <NavLink to="/notes" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <NotesIcon />
            Notes
          </NavLink>
          <NavLink to="/tasks" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <TasksIcon />
            Tasks
          </NavLink>
          <NavLink to="/calendar" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <CalendarIcon />
            Calendar
          </NavLink>
          <NavLink to="/email" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <EmailIcon />
            Email
          </NavLink>
          <NavLink to="/arxiv" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <ArxivIcon />
            ArXiv
          </NavLink>

          <div className="nav-divider"></div>

          <NavLink to="/actions" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <ActionsIcon />
            Actions
          </NavLink>
          <NavLink to="/accounts" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <SettingsIcon />
            Accounts
            {accounts && accounts.accounts?.length > 1 && (
              <span className="badge">{accounts.accounts.length}</span>
            )}
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">
              {user.name?.charAt(0) || '?'}
            </div>
            <div>
              <div className="user-name">{user.name}</div>
              <div className="user-email">{user.email}</div>
            </div>
          </div>
          <button
            className="btn btn-secondary"
            style={{ width: '100%', marginTop: '12px' }}
            onClick={handleLogout}
          >
            Sign Out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/notes" element={<Notes />} />
          <Route path="/notes/:folder/:filename" element={<NoteEditor />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/email" element={<Email />} />
          <Route path="/arxiv" element={<ArxivDigest />} />
          <Route path="/actions" element={<Actions />} />
          <Route path="/accounts" element={<Accounts accounts={accounts} onRefresh={loadAccounts} />} />
        </Routes>
      </main>
    </div>
  )
}

// Icons
function MicrosoftIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 21 21" fill="none">
      <rect x="1" y="1" width="9" height="9" fill="#F25022"/>
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00"/>
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF"/>
      <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}

function NotesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>
  )
}

function TasksIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 11l3 3L22 4"/>
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
    </svg>
  )
}

function CalendarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
      <line x1="16" y1="2" x2="16" y2="6"/>
      <line x1="8" y1="2" x2="8" y2="6"/>
      <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  )
}

function EmailIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  )
}

function ArxivIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      <line x1="8" y1="7" x2="16" y2="7"/>
      <line x1="8" y1="11" x2="16" y2="11"/>
      <line x1="8" y1="15" x2="12" y2="15"/>
    </svg>
  )
}

function ActionsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="3" y1="12" x2="21" y2="12"/>
      <line x1="3" y1="6" x2="21" y2="6"/>
      <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  )
}

export default App
