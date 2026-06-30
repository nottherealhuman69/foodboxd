import { useState, useEffect, useCallback } from 'react'
import styles from './Trylist.module.css'

/* ── Icons ── */
function BookmarkIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M5 3h14a1 1 0 011 1v17l-8-4-8 4V4a1 1 0 011-1z"
        stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function DishIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="13" r="7" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M12 6V4M9 4h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M8 13h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function RestaurantIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M3 21V10.5M21 21V10.5M12 3v18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M3 10.5C3 7.5 6 5 8.5 5h7C18 5 21 7.5 21 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M2 21h20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

function ListsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function ChevronRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const FILTERS = ['All', 'Dishes', 'Restaurants']

const authH = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token')}`,
})

export default function Trylist({ onViewDish, onViewRestaurant, onViewList }) {
  /* Wishlist state */
  const [items,    setItems]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [filter,   setFilter]   = useState('All')
  const [removing, setRemoving] = useState({})

  /* Tabs */
  const [activeTab, setActiveTab] = useState('wishlist')

  /* My Lists state */
  const [lists,        setLists]        = useState([])
  const [listsLoading, setListsLoading] = useState(false)
  const [listsError,   setListsError]   = useState('')

  /* Create list modal */
  const [showModal,   setShowModal]   = useState(false)
  const [createName,  setCreateName]  = useState('')
  const [createDesc,  setCreateDesc]  = useState('')
  const [creating,    setCreating]    = useState(false)
  const [createError, setCreateError] = useState('')

  /* ── Wishlist fetch ── */
  const fetchTrylist = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/trylist', { headers: authH() })
      if (!res.ok) throw new Error()
      setItems(await res.json())
    } catch {
      setError('Could not load your trylist. Please refresh.')
    } finally {
      setLoading(false)
    }
  }, [])

  /* ── Lists fetch ── */
  const fetchLists = useCallback(async () => {
    setListsLoading(true)
    setListsError('')
    try {
      const res = await fetch('/api/lists', { headers: authH() })
      if (!res.ok) throw new Error()
      setLists(await res.json())
    } catch {
      setListsError('Could not load your lists. Please refresh.')
    } finally {
      setListsLoading(false)
    }
  }, [])

  useEffect(() => { fetchTrylist() }, [fetchTrylist])
  useEffect(() => { if (activeTab === 'lists') fetchLists() }, [activeTab, fetchLists])

  /* ── Wishlist remove ── */
  const remove = async (id) => {
    setRemoving(prev => ({ ...prev, [id]: true }))
    try {
      const res = await fetch(`/api/trylist/${id}`, { method: 'DELETE', headers: authH() })
      if (res.ok) setItems(prev => prev.filter(i => i.id !== id))
    } catch {}
    finally {
      setRemoving(prev => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  /* ── Create list ── */
  const handleCreate = async (e) => {
    e.preventDefault()
    if (!createName.trim()) { setCreateError('List name is required.'); return }
    setCreating(true)
    setCreateError('')
    try {
      const res = await fetch('/api/lists', {
        method: 'POST',
        headers: authH(),
        body: JSON.stringify({ name: createName.trim(), description: createDesc.trim() || null }),
      })
      if (!res.ok) throw new Error()
      const newList = await res.json()
      setLists(prev => [newList, ...prev])
      setShowModal(false)
      setCreateName('')
      setCreateDesc('')
      setActiveTab('lists')
    } catch {
      setCreateError('Failed to create list. Please try again.')
    } finally {
      setCreating(false)
    }
  }

  const closeModal = () => {
    setShowModal(false)
    setCreateName('')
    setCreateDesc('')
    setCreateError('')
  }

  /* ── Derived ── */
  const filtered = items.filter(i => {
    if (filter === 'Dishes')      return i.item_type === 'dish'
    if (filter === 'Restaurants') return i.item_type === 'restaurant'
    return true
  })
  const dishCount       = items.filter(i => i.item_type === 'dish').length
  const restaurantCount = items.filter(i => i.item_type === 'restaurant').length

  return (
    <div className={styles.page}>
      {/* Header row */}
      <div className={styles.headerRow}>
        <div className={styles.header}>
          <div className={styles.headerIcon}><BookmarkIcon /></div>
          <div>
            <h2 className={styles.title}>Trylist</h2>
            <p className={styles.sub}>
              {activeTab === 'wishlist'
                ? (items.length === 0 ? 'Your wishlist is empty' : `${items.length} item${items.length !== 1 ? 's' : ''} saved`)
                : (lists.length === 0 ? 'No custom lists yet' : `${lists.length} list${lists.length !== 1 ? 's' : ''}`)}
            </p>
          </div>
        </div>
        <button className={styles.createBtn} onClick={() => setShowModal(true)}>
          <PlusIcon /> Create List
        </button>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'wishlist' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('wishlist')}
        >
          <BookmarkIcon /> Wishlist
          {items.length > 0 && <span className={styles.tabBadge}>{items.length}</span>}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'lists' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('lists')}
        >
          <ListsIcon /> My Lists
          {lists.length > 0 && <span className={styles.tabBadge}>{lists.length}</span>}
        </button>
      </div>

      {/* ── Wishlist tab ── */}
      {activeTab === 'wishlist' && (
        <>
          {items.length > 0 && (
            <div className={styles.filters}>
              {FILTERS.map(f => (
                <button
                  key={f}
                  className={`${styles.filterBtn} ${filter === f ? styles.filterActive : ''}`}
                  onClick={() => setFilter(f)}
                >
                  {f}
                  <span className={styles.filterCount}>
                    {f === 'All' ? items.length : f === 'Dishes' ? dishCount : restaurantCount}
                  </span>
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className={styles.state}>
              <div className={styles.spinner} />
              <p>Loading your trylist…</p>
            </div>
          )}
          {error && !loading && (
            <div className={styles.state}>
              <p className={styles.errorText}>{error}</p>
              <button className={styles.retryBtn} onClick={fetchTrylist}>Retry</button>
            </div>
          )}
          {!loading && !error && items.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M5 3h14a1 1 0 011 1v17l-8-4-8 4V4a1 1 0 011-1z"
                    stroke="#4e5272" strokeWidth="1.5" strokeLinejoin="round"/>
                </svg>
              </div>
              <p className={styles.emptyTitle}>Nothing saved yet</p>
              <p className={styles.emptyHint}>
                Browse dishes and restaurants, then hit <strong>+ Trylist</strong> to save them here.
              </p>
            </div>
          )}

          {!loading && !error && filtered.length > 0 && (
            <div className={styles.list}>
              {filtered.map(item => (
                <div key={item.id} className={styles.card}>
                  <div
                    className={styles.cardMain}
                    onClick={() => {
                      if (item.item_type === 'dish') onViewDish?.(item.dish_name, item.restaurant_name)
                      else onViewRestaurant?.(item.restaurant_name)
                    }}
                  >
                    <div className={`${styles.typeIcon} ${item.item_type === 'dish' ? styles.dishType : styles.restaurantType}`}>
                      {item.item_type === 'dish' ? <DishIcon /> : <RestaurantIcon />}
                    </div>
                    <div className={styles.cardBody}>
                      <p className={styles.cardName}>
                        {item.item_type === 'dish' ? item.dish_name : item.restaurant_name}
                      </p>
                      <p className={styles.cardSub}>
                        {item.item_type === 'dish' ? `at ${item.restaurant_name}` : 'Restaurant'}
                      </p>
                    </div>
                    <div className={styles.typePill}>
                      {item.item_type === 'dish' ? '🍽️ Dish' : '🏠 Place'}
                    </div>
                  </div>
                  <button
                    className={styles.removeBtn}
                    onClick={() => remove(item.id)}
                    disabled={!!removing[item.id]}
                    title="Remove from trylist"
                  >
                    {removing[item.id] ? <span className={styles.removingDot} /> : <TrashIcon />}
                  </button>
                </div>
              ))}
            </div>
          )}

          {!loading && !error && items.length > 0 && filtered.length === 0 && (
            <div className={styles.state}>
              <p style={{ color: '#6b6f8a', fontSize: 14 }}>No {filter.toLowerCase()} in your trylist yet.</p>
            </div>
          )}
        </>
      )}

      {/* ── My Lists tab ── */}
      {activeTab === 'lists' && (
        <>
          {listsLoading && (
            <div className={styles.state}>
              <div className={styles.spinner} />
              <p>Loading your lists…</p>
            </div>
          )}
          {listsError && !listsLoading && (
            <div className={styles.state}>
              <p className={styles.errorText}>{listsError}</p>
              <button className={styles.retryBtn} onClick={fetchLists}>Retry</button>
            </div>
          )}
          {!listsLoading && !listsError && lists.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}><ListsIcon /></div>
              <p className={styles.emptyTitle}>No lists yet</p>
              <p className={styles.emptyHint}>
                Hit <strong>Create List</strong> to make a curated collection — like "Best Biryanis" or "Date Night Spots".
              </p>
              <button className={styles.createBtnEmpty} onClick={() => setShowModal(true)}>
                <PlusIcon /> Create your first list
              </button>
            </div>
          )}

          {!listsLoading && !listsError && lists.length > 0 && (
            <div className={styles.listsGrid}>
              {lists.map(lst => (
                <button
                  key={lst.id}
                  className={styles.listCard}
                  onClick={() => onViewList?.(lst.id)}
                >
                  <div className={styles.listCardIcon}><ListsIcon /></div>
                  <div className={styles.listCardBody}>
                    <p className={styles.listCardName}>{lst.name}</p>
                    {lst.description && (
                      <p className={styles.listCardDesc}>{lst.description}</p>
                    )}
                    <p className={styles.listCardMeta}>
                      {lst.item_count} item{lst.item_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <ChevronRight />
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Create List Modal ── */}
      {showModal && (
        <div className={styles.modalBackdrop} onClick={closeModal}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>Create a new list</h3>
            <form onSubmit={handleCreate} className={styles.modalForm}>
              <label className={styles.modalLabel}>
                List name <span className={styles.required}>*</span>
              </label>
              <input
                className={styles.modalInput}
                placeholder="e.g. Best Biryanis, Date Night Spots…"
                value={createName}
                onChange={e => setCreateName(e.target.value)}
                autoFocus
                maxLength={120}
              />
              <label className={styles.modalLabel}>Description <span className={styles.optional}>(optional)</span></label>
              <textarea
                className={styles.modalTextarea}
                placeholder="What's this list about?"
                value={createDesc}
                onChange={e => setCreateDesc(e.target.value)}
                rows={3}
                maxLength={500}
              />
              {createError && <p className={styles.modalError}>{createError}</p>}
              <div className={styles.modalActions}>
                <button type="submit" className={styles.modalSubmit} disabled={creating || !createName.trim()}>
                  {creating ? 'Creating…' : 'Create list'}
                </button>
                <button type="button" className={styles.modalCancel} onClick={closeModal}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
