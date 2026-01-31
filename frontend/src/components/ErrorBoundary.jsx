import { Component } from 'react'

/**
 * Error Boundary component to catch JavaScript errors in child components.
 * Prevents the entire app from crashing when a component fails.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <h2>Something went wrong</h2>
            <p>An error occurred while rendering this page.</p>
            {this.props.showDetails && this.state.error && (
              <pre className="error-details">
                {this.state.error.toString()}
              </pre>
            )}
            <div className="error-boundary-actions">
              <button className="btn btn-primary" onClick={this.handleRetry}>
                Try Again
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => window.location.reload()}
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
