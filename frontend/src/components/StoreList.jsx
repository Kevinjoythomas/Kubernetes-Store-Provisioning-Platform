import StoreCard from './StoreCard'

function StoreList({ stores, onStoreDeleted, onRefresh }) {
  if (stores.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📦</div>
        <h2>No stores yet</h2>
        <p>Create your first WooCommerce store to get started!</p>
        <p className="empty-state-hint">
          Stores are provisioned automatically on Kubernetes with WordPress + WooCommerce
        </p>
      </div>
    )
  }

  return (
    <div className="stores-container">
      <div className="stores-header">
        <h2 className="stores-title">
          Your Stores <span className="stores-count">({stores.length})</span>
        </h2>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          title="Refresh stores"
        >
          ↻ Refresh
        </button>
      </div>

      <div className="stores-grid">
        {stores.map((store) => (
          <StoreCard
            key={store.id}
            store={store}
            onDeleted={onStoreDeleted}
          />
        ))}
      </div>
    </div>
  )
}

export default StoreList
