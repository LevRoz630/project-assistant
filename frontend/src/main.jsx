import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ToastProvider } from './components/Toast'
import './index.css'

// Inject browser timezone into all fetch requests so the backend can
// return timezone-aware dates (handles GMT/BST automatically).
const _fetch = window.fetch
window.fetch = (url, opts = {}) => {
  opts.headers = {
    ...opts.headers,
    'X-Timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
  }
  return _fetch(url, opts)
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <App />
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
