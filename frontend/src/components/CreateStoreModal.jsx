import { useState } from 'react'
import { createStore } from '../api'

function CreateStoreModal({ onClose, onSuccess, onError }) {
  const [formData, setFormData] = useState({
    displayName: '',
    storeType: 'woocommerce'
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Handle form input changes
  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }))
    setError(null)
  }

  // Validate form
  const validate = () => {
    if (!formData.displayName.trim()) {
      setError('Store name is required')
      return false
    }

    if (formData.displayName.length < 3 || formData.displayName.length > 50) {
      setError('Store name must be between 3 and 50 characters')
      return false
    }

    if (!formData.storeType) {
      setError('Store type is required')
      return false
    }

    return true
  }

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!validate()) return

    setLoading(true)
    setError(null)

    try {
      const newStore = await createStore({
        displayName: formData.displayName.trim(),
        storeType: formData.storeType
      })

      onSuccess(newStore)
    } catch (err) {
      setError(err.message)
      onError(err)
    } finally {
      setLoading(false)
    }
  }

  // Handle escape key
  const handleKeyDown = (e) => {
    if (e.key === 'Escape' && !loading) {
      onClose()
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} onKeyDown={handleKeyDown}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <h2>Create New Store</h2>
          <button
            className="modal-close"
            onClick={onClose}
            disabled={loading}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="modal-body">
          {/* Store Name Field */}
          <div className="form-group">
            <label htmlFor="displayName" className="form-label">
              Store Name <span className="required">*</span>
            </label>
            <input
              type="text"
              id="displayName"
              name="displayName"
              className="form-input"
              value={formData.displayName}
              onChange={handleChange}
              placeholder="e.g., My Awesome Store"
              disabled={loading}
              autoFocus
              maxLength={50}
            />
            <span className="form-hint">
              Choose a descriptive name for your store (3-50 characters)
            </span>
          </div>

          {/* Store Type Field */}
          <div className="form-group">
            <label htmlFor="storeType" className="form-label">
              Store Type <span className="required">*</span>
            </label>
            <div className="store-type-options">
              <label
                className={`store-type-option ${
                  formData.storeType === 'woocommerce' ? 'selected' : ''
                }`}
              >
                <input
                  type="radio"
                  name="storeType"
                  value="woocommerce"
                  checked={formData.storeType === 'woocommerce'}
                  onChange={handleChange}
                  disabled={loading}
                />
                <div className="option-content">
                  <div className="option-icon">🛒</div>
                  <div className="option-text">
                    <div className="option-title">WooCommerce</div>
                    <div className="option-desc">WordPress + WooCommerce</div>
                  </div>
                </div>
              </label>

              <label className="store-type-option disabled">
                <input
                  type="radio"
                  name="storeType"
                  value="medusa"
                  disabled
                />
                <div className="option-content">
                  <div className="option-icon">🚧</div>
                  <div className="option-text">
                    <div className="option-title">Medusa</div>
                    <div className="option-desc">Coming Soon</div>
                  </div>
                </div>
                <span className="coming-soon-badge">Coming Soon</span>
              </label>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="form-error">
              <span className="error-icon">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* Modal Footer */}
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !formData.displayName.trim()}
            >
              {loading ? (
                <>
                  <span className="btn-spinner"></span>
                  Creating...
                </>
              ) : (
                <>
                  <span className="btn-icon">+</span>
                  Create Store
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default CreateStoreModal
