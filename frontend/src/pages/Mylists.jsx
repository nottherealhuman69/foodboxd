import { useState, useEffect, useCallback } from 'react'
import styles from './MyLists.module.css'

/* ── Icons ── */
function ListsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M14 6.5h7M14 10h4M14 17.5h7M14 21h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}
function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}
function BackIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function LockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M8 11V7a4 4 0 018 0v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}
function GlobeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M12 3c-3 3-4 6-4 9s1 6 4 9M12 3c3 3 4 6 4 9s-1 6-4 9M3 12h18" stroke="currentColor" strokeWidth="1.5"/>
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
  return <span style={{ fontSize: 16 }}>🍽️</span>
}
function RestaurantIcon() {
  return <span style={{ fontSize: 16 }}>🏠</span>
}
function RecipeIcon() {
  return <span style={{ fontSize: 16 }}>📖</span>
}

const TYPE_ICONS = { dish: <DishIcon />, restaurant: <RestaurantIcon />, recipe: <RecipeIcon /> }
const TYPE_LABELS = { dish: 'Dish', restaurant: 'Restaurant', recipe: 'Recipe' }

/* ── Create List Modal ── */
function CreateListModal({ onClose, onCreated }) {
  const [name, setName]       = useState('')
  const [isPublic, setPublic] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [err, setErr]         = useState('')

  const token = localStorage.getItem('token')

  const submit = async () => {
    if (!name.trim()) { setErr('Please enter a list name.'); return }
    setSaving(true); setErr('')
    try {
      const res = await fetch('/api/lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: name.trim(), is_public: isPublic }),
      })
      if (!res.ok) { const d = await res.json(); setErr(d.detail || 'Failed'); return }
      const created = await res.json()
      onCreated(created)
    } catch { setErr('Could not connect to server.') }
    finally { setSaving(false) }
  }

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>Create a new list</h3>

        <div className={styles.field}>
          <label className={styles.label}>List name</label>
          <input
            className={styles.input}
            placeholder="e.g. Best Biryanis in Hyderabad"
            value={name}
            onChange={e => { setName(e.target.value); setErr('') }}
            autoFocus
            onKeyDown={e => e.key === 'Enter' && submit()}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label}>Visibility</label>
          <div className={styles.toggleRow}>
            <button
              className={`${styles.toggleBtn} ${isPublic ? styles.toggleActive : ''}`}
              onClick={() => setPublic(true)}
            >
              <GlobeIcon /> Public
            </button>
            <button
              className={`${styles.toggleBtn} ${!isPublic ? styles.toggleActive : ''}`}
              onClick={() => setPublic(false)}
            >
              <LockIcon /> Private
            </button>
          </div>
        </div>

        {err && <p className={styles.errText}>{err}</p>}

        <div className={styles.modalActions}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.primaryBtn} onClick={submit} disabled={saving}>
            {saving ? 'Creating…' : 'Create list'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Add Item Modal ── */
function AddItemModal({ listId, onClose, onAdded }) {
  const [itemType, setItemType]   = useState('dish')
  const [name, setName]           = useState('')
  const [restaurant, setRestaurant] = useState('')
  const [note, setNote]           = useState('')
  const [saving, setSaving]       = useState(false)
  const [err, setErr]             = useState('')

  const token = localStorage.getItem('token')

  const submit = async () => {
    if (!name.trim()) { setErr('Please enter a name.'); return }
    if (itemType === 'dish' && !restaurant.trim()) { setErr('Please enter the restaurant name.'); return }
    setSaving(true); setErr('')
    try {
      const res = await fetch(`/api/lists/${listId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          item_type: itemType,
          name: name.trim(),
          restaurant_name: itemType === 'dish' ? restaurant.trim() : null,
          note: note.trim() || null,
        }),
      })
      if (!res.ok) { const d = await res.json(); setErr(d.detail || 'Failed'); return }
      const item = await res.json()
      onAdded(item)
    } catch { setErr('Could not connect to server.') }
    finally { setSaving(false) }
  }

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>Add to list</h3>

        <div className={styles.field}>
          <label className={styles.label}>Type</label>
          <div className={styles.typeRow}>
            {['dish', 'restaurant', 'recipe'].map(t => (
              <button
                key={t}
                className={`${styles.typeBtn} ${itemType === t ? styles.typeBtnActive : ''}`}
                onClick={() => { setItemType(t); setErr('') }}
              >
                {TYPE_ICONS[t]} {TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label}>
            {itemType === 'dish' ? 'Dish name' : itemType === 'restaurant' ? 'Restaurant name' : 'Recipe name'}
          </label>
          <input
            className={styles.input}
            placeholder={
              itemType === 'dish' ? 'e.g. Chicken Biryani'
              : itemType === 'restaurant' ? 'e.g. Paradise Biryani'
              : 'e.g. Grandma\'s Dal Makhani'
            }
            value={name}
            onChange={e => { setName(e.target.value); setErr('') }}
            autoFocus
          />
        </div>

        {itemType === 'dish' && (
          <div className={styles.field}>
            <label className={styles.label}>Restaurant</label>
            <input
              className={styles.input}
              placeholder="e.g. Paradise Biryani"
              value={restaurant}
              onChange={e => { setRestaurant(e.target.value); setErr('') }}
            />
          </div>
        )}

        <div className={styles.field}>
          <label className={styles.label}>Note <span className={styles.optional}>(optional)</span></label>
          <input
            className={styles.input}
            placeholder="e.g. The spicy variant is 🔥"
            value={note}
            onChange={e => setNote(e.target.value)}
          />
        </div>

        {err && <p className={styles.errText}>{err}</p>}

        <div className={styles.modalActions}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.primaryBtn} onClick={submit} disabled={saving}>
            {saving ? 'Adding…' : 'Add item'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── List Detail View ── */
function ListDetail({ list, onBack, onListUpdated }) {
  const [items, setItems]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [showAdd, setShowAdd]   = useState(false)
  const [removing, setRemoving] = useState({})

  const token = localStorage.getItem('token')
  const authH = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/lists/${list.id}/items`, { headers: authH })
      if (res.ok) setItems(await res.json())
    } catch {}
    finally { setLoading(false) }
  }, [list.id])

  useEffect(() => { fetchItems() }, [fetchItems])

  const removeItem = async (itemId) => {
    setRemoving(p => ({ ...p, [itemId]: true }))
    try {
      const res = await fetch(`/api/lists/${list.id}/items/${itemId}`, { method: 'DELETE', headers: authH })
      if (res.ok) setItems(p => p.filter(i => i.id !== itemId))
    } catch {}
    finally { setRemoving(p => { const n = { ...p }; delete n[itemId]; return n }) }
  }

  return (
    <div className={styles.page}>
      {showAdd && (
        <AddItemModal
          listId={list.id}
          onClose={() => setShowAdd(false)}
          onAdded={item => { setItems(p => [...p, item]); setShowAdd(false) }}
        />
      )}

      <button className={styles.backBtn} onClick={onBack}>
        <BackIcon /> Back to lists
      </button>

      <div className={styles.detailHeader}>
        <div className={styles.detailMeta}>
          <h2 className={styles.detailTitle}>{list.name}</h2>
          <span className={styles.visibilityPill}>
            {list.is_public ? <><GlobeIcon /> Public</> : <><LockIcon /> Private</>}
          </span>
        </div>
        <button className={styles.addBtn} onClick={() => setShowAdd(true)}>
          <PlusIcon /> Add item
        </button>
      </div>

      {loading && (
        <div className={styles.state}><div className={styles.spinner} /><p>Loading…</p></div>
      )}

      {!loading && items.length === 0 && (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>This list is empty</p>
          <p className={styles.emptyHint}>Add dishes, restaurants, or recipes using the button above.</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className={styles.itemsList}>
          {items.map((item, idx) => (
            <div key={item.id} className={styles.itemCard}>
              <span className={styles.itemIndex}>{idx + 1}</span>
              <div className={styles.itemTypeIcon}>{TYPE_ICONS[item.item_type]}</div>
              <div className={styles.itemBody}>
                <p className={styles.itemName}>{item.name}</p>
                {item.restaurant_name && (
                  <p className={styles.itemSub}>at {item.restaurant_name}</p>
                )}
                {item.note && <p className={styles.itemNote}>"{item.note}"</p>}
              </div>
              <span className={styles.itemTypePill}>{TYPE_LABELS[item.item_type]}</span>
              <button
                className={styles.removeBtn}
                onClick={() => removeItem(item.id)}
                disabled={!!removing[item.id]}
                title="Remove"
              >
                {removing[item.id] ? <span className={styles.removingDot} /> : <TrashIcon />}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Main MyLists page ── */
export default function MyLists() {
  const [lists, setLists]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [openList, setOpenList]   = useState(null)
  const [deleting, setDeleting]   = useState({})

  const token = localStorage.getItem('token')
  const authH = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const fetchLists = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/lists', { headers: authH })
      if (!res.ok) throw new Error()
      setLists(await res.json())
    } catch { setError('Could not load your lists. Please refresh.') }
    finally { setLoading(false) }
  }, [token])

  useEffect(() => { fetchLists() }, [fetchLists])

  const deleteList = async (id, e) => {
    e.stopPropagation()
    setDeleting(p => ({ ...p, [id]: true }))
    try {
      const res = await fetch(`/api/lists/${id}`, { method: 'DELETE', headers: authH })
      if (res.ok) setLists(p => p.filter(l => l.id !== id))
    } catch {}
    finally { setDeleting(p => { const n = { ...p }; delete n[id]; return n }) }
  }

  if (openList) {
    return (
      <ListDetail
        list={openList}
        onBack={() => setOpenList(null)}
        onListUpdated={updated => setLists(p => p.map(l => l.id === updated.id ? updated : l))}
      />
    )
  }

  return (
    <div className={styles.page}>
      {showCreate && (
        <CreateListModal
          onClose={() => setShowCreate(false)}
          onCreated={list => { setLists(p => [list, ...p]); setShowCreate(false) }}
        />
      )}

      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><ListsIcon /></div>
          <div>
            <h2 className={styles.title}>My Lists</h2>
            <p className={styles.sub}>
              {lists.length === 0 ? 'No lists yet' : `${lists.length} list${lists.length !== 1 ? 's' : ''}`}
            </p>
          </div>
        </div>
        <button className={styles.createBtn} onClick={() => setShowCreate(true)}>
          <PlusIcon /> Create list
        </button>
      </div>

      {loading && (
        <div className={styles.state}><div className={styles.spinner} /><p>Loading your lists…</p></div>
      )}
      {error && !loading && (
        <div className={styles.state}>
          <p className={styles.errText}>{error}</p>
          <button className={styles.retryBtn} onClick={fetchLists}>Retry</button>
        </div>
      )}

      {!loading && !error && lists.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📋</div>
          <p className={styles.emptyTitle}>No lists yet</p>
          <p className={styles.emptyHint}>
            Create your first list — like "Best Biryanis in Hyderabad" or "Places to Try".
          </p>
          <button className={styles.createBtn} onClick={() => setShowCreate(true)}>
            <PlusIcon /> Create your first list
          </button>
        </div>
      )}

      {!loading && !error && lists.length > 0 && (
        <div className={styles.grid}>
          {lists.map(list => (
            <div key={list.id} className={styles.listCard} onClick={() => setOpenList(list)}>
              <div className={styles.cardTop}>
                <h3 className={styles.listName}>{list.name}</h3>
                <button
                  className={styles.deleteBtn}
                  onClick={e => deleteList(list.id, e)}
                  disabled={!!deleting[list.id]}
                  title="Delete list"
                >
                  {deleting[list.id] ? <span className={styles.removingDot} /> : <TrashIcon />}
                </button>
              </div>
              <div className={styles.cardMeta}>
                <span className={styles.visibilityPill}>
                  {list.is_public ? <><GlobeIcon /> Public</> : <><LockIcon /> Private</>}
                </span>
                <span className={styles.itemCount}>{list.item_count ?? 0} item{(list.item_count ?? 0) !== 1 ? 's' : ''}</span>
              </div>
              <p className={styles.cardHint}>Click to view →</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}