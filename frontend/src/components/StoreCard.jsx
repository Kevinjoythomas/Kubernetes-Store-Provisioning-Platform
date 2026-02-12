import { useState } from 'react'
import { deleteStore } from '../api'

function StoreCard({ store, onDeleted }) {
  const [showConfirm, setShowConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [expanded, setExpanded] = useState(false)

  // Get status badge color
  const getStatusColor = (phase) => {
    switch (phase) {
      case 'Ready':
        return 'success'
      case 'Provisioning':
      case 'Installing':
      case 'Configuring':
        return 'warning'
      case 'Failed':
        return 'error'
      case 'Deleting':
        return 'neutral'
      default:
        return 'neutral'
    }
  }

  // Check if phase is transitional (needs spinner)
  const isTransitional = (phase) => {
    return ['Provisioning', 'Installing', 'Configuring', 'Deleting'].includes(phase)
  }

  // Format timestamp to relative time
  const formatRelativeTime = (timestamp) => {
    if (!timestamp) return null

    const date = new Date(timestamp)
    const now = new Date()
    const diffInSeconds = Math.floor((now - date) / 1000)

    if (diffInSeconds < 60) return 'just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }

  // Handle delete
  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteStore(store.id)
      onDeleted(store.id)
    } catch (error) {
      console.error('Error deleting store:', error)
      alert(`Failed to delete store: ${error.message}`)
    } finally {
      setDeleting(false)
      setShowConfirm(false)
    }
  }

  return (
    <div className="store-card">
      {/* Card Header */}
      <div className="card-header">
        <div className="card-title-section">
          <h3 className="card-title">{store.displayName || store.id}</h3>
          <div className="card-badges">
            <span className="badge badge-type">WooCommerce</span>
            <span className={`badge badge-${getStatusColor(store.phase)}`}>
              {isTransitional(store.phase) && (
                <span className="badge-spinner"></span>
              )}
              {store.phase || 'Unknown'}
            </span>
          </div>
        </div>
      </div>

      {/* Card Body */}
      <div className="card-body">
        {/* URLs */}
        {store.phase === 'Ready' && store.url && (
          <div className="card-links">
            <a
              href={store.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card-link"
            >
              <span className="link-icon">🔗</span>
              <span className="link-text">Visit Store</span>
            </a>
            <a
              href={store.adminUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="card-link"
            >
              <span className="link-icon">⚙️</span>
              <span className="link-text">WP Admin</span>
            </a>
          </div>
        )}

        {/* Status Message */}
        {store.message && (
          <div className={`card-message ${store.phase === 'Failed' ? 'card-message-error' : ''}`}>
            {store.message}
          </div>
        )}

        {/* Metadata */}
        <div className="card-meta">
          <div className="meta-item">
            <span className="meta-label">ID:</span>
            <span className="meta-value">{store.id}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Created:</span>
            <span className="meta-value">{formatRelativeTime(store.createdAt)}</span>
          </div>
          {store.readyAt && (
            <div className="meta-item">
              <span className="meta-label">Ready:</span>
              <span className="meta-value">{formatRelativeTime(store.readyAt)}</span>
            </div>
          )}
        </div>

        {/* Expandable Events */}
        {store.events && store.events.length > 0 && (
          <div className="card-events">
            <button
              className="events-toggle"
              onClick={() => setExpanded(!expanded)}
            >
              <span className={`toggle-icon ${expanded ? 'expanded' : ''}`}>▶</span>
              Activity Log ({store.events.length})
            </button>
            {expanded && (
              <div className="events-list">
                {store.events.map((event, index) => (
                  <div key={index} className="event-item">
                    <span className="event-time">
                      {formatRelativeTime(event.timestamp)}
                    </span>
                    <span className="event-message">{event.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Card Footer */}
      <div className="card-footer">
        {!showConfirm ? (
          <button
            className="btn btn-danger btn-sm"
            onClick={() => setShowConfirm(true)}
            disabled={deleting || store.phase === 'Deleting'}
          >
            🗑️ Delete
          </button>
        ) : (
          <div className="confirm-delete">
            <span className="confirm-text">Delete this store?</span>
            <div className="confirm-actions">
              <button
                className="btn btn-danger btn-sm"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Yes, Delete'}
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowConfirm(false)}
                disabled={deleting}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default StoreCard
