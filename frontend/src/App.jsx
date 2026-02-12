import { useState, useEffect } from 'react'
import './App.css'
import StoreList from './components/StoreList'
import CreateStoreModal from './components/CreateStoreModal'
import { getStores } from './api'

function App() {
  const [stores, setStores] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [toast, setToast] = useState(null)

  // Fetch stores from API
  const fetchStores = async () => {
    try {
      const data = await getStores()
      setStores(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching stores:', err)
      setError(err.message)
      showToast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  // Initial load
  useEffect(() => {
    fetchStores()
  }, [])

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStores()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  // Show toast notification
  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  // Handle store created
  const handleStoreCreated = (newStore) => {
    setShowCreateModal(false)
    fetchStores()
    showToast(`Store "${newStore.displayName}" created successfully!`, 'success')
  }

  // Handle store deleted
  const handleStoreDeleted = (storeId) => {
    fetchStores()
    showToast('Store deletion initiated', 'info')
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="container">
          <div className="header-content">
            <div className="header-left">
              <h1 className="app-title">
                <span className="title-icon">🚀</span>
                Store Platform
              </h1>
              <p className="app-subtitle">Kubernetes-powered WooCommerce provisioning</p>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              <span className="btn-icon">+</span>
              Create Store
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        <div className="container">
          {loading && stores.length === 0 ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Loading stores...</p>
            </div>
          ) : (
            <StoreList
              stores={stores}
              onStoreDeleted={handleStoreDeleted}
              onRefresh={fetchStores}
            />
          )}
        </div>
      </main>

      {/* Create Store Modal */}
      {showCreateModal && (
        <CreateStoreModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleStoreCreated}
          onError={(err) => showToast(err.message, 'error')}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span className="toast-icon">
            {toast.type === 'success' && '✓'}
            {toast.type === 'error' && '✕'}
            {toast.type === 'info' && 'ℹ'}
          </span>
          <span className="toast-message">{toast.message}</span>
        </div>
      )}
    </div>
  )
}

export default App
