import { useState } from 'react'
import './Accounts.css'

const API_BASE = 'http://localhost:8000'

function Accounts({ accounts, onRefresh }) {
  const [loading, setLoading] = useState(false)

  const handleAddAccount = (type) => {
    window.location.href = `${API_BASE}/auth/login/${type}`
  }

  const handleRemoveAccount = async (purpose) => {
    if (!confirm(`Remove this ${purpose} account?`)) return

    setLoading(true)
    try {
      await fetch(`${API_BASE}/auth/logout?purpose=${purpose}`, {
        credentials: 'include',
      })
      onRefresh()
    } catch (error) {
      console.error('Failed to remove account:', error)
    } finally {
      setLoading(false)
    }
  }

  const hasEmailAccount = accounts?.has_email_account
  const hasStorageAccount = accounts?.has_storage_account

  return (
    <>
      <div className="content-header">
        <h2>Connected Accounts</h2>
      </div>

      <div className="content-body">
        <div className="accounts-intro">
          <p>
            Connect different Microsoft accounts for different services. Use one account for
            email/calendar and another for OneDrive notes and To Do tasks.
          </p>
        </div>

        <div className="accounts-grid">
          {/* Email & Calendar Account */}
          <div className="account-card">
            <div className="account-card-header">
              <div className="account-icon email">
                <MailIcon />
              </div>
              <div>
                <h3>Email & Calendar</h3>
                <p>Outlook mail and calendar access</p>
              </div>
            </div>

            {accounts?.accounts?.find(a => a.purpose === 'email') ? (
              <div className="account-connected">
                <div className="account-user">
                  <div className="account-avatar">
                    {accounts.accounts.find(a => a.purpose === 'email')?.name?.charAt(0)}
                  </div>
                  <div>
                    <div className="account-name">
                      {accounts.accounts.find(a => a.purpose === 'email')?.name}
                    </div>
                    <div className="account-email">
                      {accounts.accounts.find(a => a.purpose === 'email')?.email}
                    </div>
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleRemoveAccount('email')}
                  disabled={loading}
                >
                  Remove
                </button>
              </div>
            ) : accounts?.accounts?.find(a => a.purpose === 'primary') ? (
              <div className="account-connected">
                <div className="account-user">
                  <div className="account-avatar primary">
                    {accounts.accounts.find(a => a.purpose === 'primary')?.name?.charAt(0)}
                  </div>
                  <div>
                    <div className="account-name">
                      {accounts.accounts.find(a => a.purpose === 'primary')?.name}
                    </div>
                    <div className="account-email">
                      {accounts.accounts.find(a => a.purpose === 'primary')?.email}
                    </div>
                    <div className="account-badge">Using Primary Account</div>
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleAddAccount('email')}
                >
                  Use Different
                </button>
              </div>
            ) : (
              <div className="account-empty">
                <p>No email account connected</p>
                <button
                  className="btn btn-primary"
                  onClick={() => handleAddAccount('email')}
                >
                  Connect Account
                </button>
              </div>
            )}
          </div>

          {/* Notes & Tasks Account */}
          <div className="account-card">
            <div className="account-card-header">
              <div className="account-icon storage">
                <StorageIcon />
              </div>
              <div>
                <h3>Notes & Tasks</h3>
                <p>OneDrive storage and Microsoft To Do</p>
              </div>
            </div>

            {accounts?.accounts?.find(a => a.purpose === 'storage') ? (
              <div className="account-connected">
                <div className="account-user">
                  <div className="account-avatar">
                    {accounts.accounts.find(a => a.purpose === 'storage')?.name?.charAt(0)}
                  </div>
                  <div>
                    <div className="account-name">
                      {accounts.accounts.find(a => a.purpose === 'storage')?.name}
                    </div>
                    <div className="account-email">
                      {accounts.accounts.find(a => a.purpose === 'storage')?.email}
                    </div>
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleRemoveAccount('storage')}
                  disabled={loading}
                >
                  Remove
                </button>
              </div>
            ) : accounts?.accounts?.find(a => a.purpose === 'primary') ? (
              <div className="account-connected">
                <div className="account-user">
                  <div className="account-avatar primary">
                    {accounts.accounts.find(a => a.purpose === 'primary')?.name?.charAt(0)}
                  </div>
                  <div>
                    <div className="account-name">
                      {accounts.accounts.find(a => a.purpose === 'primary')?.name}
                    </div>
                    <div className="account-email">
                      {accounts.accounts.find(a => a.purpose === 'primary')?.email}
                    </div>
                    <div className="account-badge">Using Primary Account</div>
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleAddAccount('storage')}
                >
                  Use Different
                </button>
              </div>
            ) : (
              <div className="account-empty">
                <p>No storage account connected</p>
                <button
                  className="btn btn-primary"
                  onClick={() => handleAddAccount('storage')}
                >
                  Connect Account
                </button>
              </div>
            )}
          </div>
        </div>

        {/* All Connected Accounts */}
        <div className="accounts-list-section">
          <h3>All Connected Accounts</h3>
          <div className="accounts-list">
            {accounts?.accounts?.map((account) => (
              <div key={account.purpose} className="account-list-item">
                <div className="account-user">
                  <div className={`account-avatar ${account.purpose}`}>
                    {account.name?.charAt(0)}
                  </div>
                  <div>
                    <div className="account-name">{account.name}</div>
                    <div className="account-email">{account.email}</div>
                  </div>
                </div>
                <div className="account-purpose-badge">{account.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="accounts-help">
          <h4>How it works</h4>
          <ul>
            <li><strong>Primary Account:</strong> Used for all services by default when you first sign in.</li>
            <li><strong>Email Account:</strong> Specifically for reading emails and managing your calendar.</li>
            <li><strong>Storage Account:</strong> For OneDrive notes and Microsoft To Do tasks.</li>
          </ul>
          <p>
            This is useful if you have a work email but want to store personal notes in your
            personal OneDrive, or vice versa.
          </p>
        </div>
      </div>
    </>
  )
}

function MailIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  )
}

function StorageIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
    </svg>
  )
}

export default Accounts
