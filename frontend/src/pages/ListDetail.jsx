import { useState, useEffect, useCallback } from 'react'
import styles from './ListDetail.module.css'

function BackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function EditIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
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

function ListIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const authH = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token')}`,
})

export default function ListDetail({ listId, onBack }) {
  const [list,      setList]      = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState('')
  const [editMode,  setEditMode]  = useState(false)
  const [editName,  setEditName]  = useState('')
  const [editDesc,  setEditDesc]  = useState('')
  const [saving,    setSaving]    = useState(false)
  const [deleting,  setDeleting]  = useState(false)
  const [removing,  setRemoving]  = useState({})
  const [addForm,   setAddForm]   = useState({ item_type: 'dish', dish_name: '', restaurant_name: '' })
  const [adding,    setAdding]    = useState(false)
  const [addError,  setAddError]  = useState('')

  const fetchList = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/lists/${listId}`, { headers: authH() })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setList(data)
      setEditName(data.name)
      setEditDesc(data.description || '')
    } catch {
      setError('Could not load this list. Please go back and try again.')
    } finally {
      setLoading(false)
    }
  }, [listId])

  useEffect(() => { fetchList() }, [fetchList])

  const saveEdit = async () => {
    if (!editName.trim()) return
    setSaving(true)
    try {
      const res = await fetch(`/api/lists/${listId}`, {
        method: 'PATCH',
        headers: authH(),
        body: JSON.stringify({ name: editName.trim(), description: editDesc.trim() || null }),
      })
      if (!res.ok) throw new Error()
      const updated = await res.json()
      setList(prev => ({ ...prev, name: updated.name, description: updated.description }))
      setEditMode(false)
    } catch {
      // keep modal open on error
    } finally {
      setSaving(false)
    }
  }

  const deleteList = async () => {
    if (!window.confirm(`Delete "${list.name}"? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await fetch(`/api/lists/${listId}`, { method: 'DELETE', headers: authH() })
      onBack()
    } catch {
      setDeleting(false)
    }
  }

  const removeItem = async (itemId) => {
    setRemoving(prev => ({ ...prev, [itemId]: true }))
    try {
      const res = await fetch(`/api/lists/${listId}/items/${itemId}`, { method: 'DELETE', headers: authH() })
      if (res.ok) setList(prev => ({ ...prev, items: prev.items.filter(i => i.id !== itemId) }))
    } catch {}
    finally {
      setRemoving(prev => { const n = { ...prev }; delete n[itemId]; return n })
    }
  }

  const addItem = async (e) => {
    e.preventDefault()
    setAddError('')
    if (addForm.item_type === 'dish' && (!addForm.dish_name.trim() || !addForm.restaurant_name.trim())) {
      setAddError('Both dish name and restaurant name are required.')
      return
    }
    if (addForm.item_type === 'restaurant' && !addForm.restaurant_name.trim()) {
      setAddError('Restaurant name is required.')
      return
    }
    setAdding(true)
    try {
      const res = await fetch(`/api/lists/${listId}/items`, {
        method: 'POST',
        headers: authH(),
        body: JSON.stringify({
          item_type:       addForm.item_type,
          dish_name:       addForm.item_type === 'dish' ? addForm.dish_name.trim() : null,
          restaurant_name: addForm.restaurant_name.trim(),
        }),
      })
      if (res.status === 409) { setAddError('This item is already in the list.'); return }
      if (!res.ok) throw new Error()
      const newItem = await res.json()
      setList(prev => ({ ...prev, items: [newItem, ...prev.items] }))
      setAddForm(prev => ({ ...prev, dish_name: '', restaurant_name: '' }))
    } catch {
      setAddError('Failed to add item. Please try again.')
    } finally {
      setAdding(false)
    }
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <button className={styles.backBtn} onClick={onBack}><BackIcon /> Back</button>
        <div className={styles.loadingState}><div className={styles.spinner} /></div>
      </div>
    )
  }

  if (error || !list) {
    return (
      <div className={styles.page}>
        <button className={styles.backBtn} onClick={onBack}><BackIcon /> Back</button>
        <p className={styles.errorText}>{error || 'List not found.'}</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <button className={styles.backBtn} onClick={onBack}><BackIcon /> Back to Trylist</button>

      {/* Header */}
      <div className={styles.headerCard}>
        <div className={styles.headerIconWrap}><ListIcon /></div>
        {editMode ? (
          <div className={styles.editForm}>
            <input
              className={styles.editNameInput}
              value={editName}
              onChange={e => setEditName(e.target.value)}
              placeholder="List name"
              autoFocus
              maxLength={120}
            />
            <textarea
              className={styles.editDescInput}
              value={editDesc}
              onChange={e => setEditDesc(e.target.value)}
              placeholder="Description (optional)"
              rows={2}
              maxLength={500}
            />
            <div className={styles.editActions}>
              <button
                className={styles.saveBtn}
                onClick={saveEdit}
                disabled={saving || !editName.trim()}
              >
                {saving ? 'Saving…' : 'Save changes'}
              </button>
              <button
                className={styles.cancelEditBtn}
                onClick={() => {
                  setEditMode(false)
                  setEditName(list.name)
                  setEditDesc(list.description || '')
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className={styles.headerBody}>
            <div className={styles.headerText}>
              <h2 className={styles.listTitle}>{list.name}</h2>
              {list.description && <p className={styles.listDesc}>{list.description}</p>}
              <p className={styles.listMeta}>
                {list.items.length} item{list.items.length !== 1 ? 's' : ''}
              </p>
            </div>
            <div className={styles.headerActions}>
              <button className={styles.editBtn} onClick={() => setEditMode(true)}>
                <EditIcon /> Edit
              </button>
              <button className={styles.deleteListBtn} onClick={deleteList} disabled={deleting}>
                <TrashIcon /> {deleting ? 'Deleting…' : 'Delete list'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add item */}
      <div className={styles.addSection}>
        <h3 className={styles.sectionLabel}>Add item</h3>
        <form className={styles.addForm} onSubmit={addItem}>
          <div className={styles.typeToggle}>
            <button
              type="button"
              className={`${styles.typeBtn} ${addForm.item_type === 'dish' ? styles.typeBtnActive : ''}`}
              onClick={() => setAddForm(prev => ({ ...prev, item_type: 'dish', dish_name: '', restaurant_name: '' }))}
            >
              🍽️ Dish
            </button>
            <button
              type="button"
              className={`${styles.typeBtn} ${addForm.item_type === 'restaurant' ? styles.typeBtnActive : ''}`}
              onClick={() => setAddForm(prev => ({ ...prev, item_type: 'restaurant', dish_name: '', restaurant_name: '' }))}
            >
              🏠 Restaurant
            </button>
          </div>

          <div className={styles.addInputs}>
            {addForm.item_type === 'dish' && (
              <input
                className={styles.addInput}
                placeholder="Dish name (e.g. Chicken Biryani)"
                value={addForm.dish_name}
                onChange={e => setAddForm(prev => ({ ...prev, dish_name: e.target.value }))}
              />
            )}
            <input
              className={styles.addInput}
              placeholder={addForm.item_type === 'dish' ? 'Restaurant name' : 'Restaurant name (e.g. Paradise)'}
              value={addForm.restaurant_name}
              onChange={e => setAddForm(prev => ({ ...prev, restaurant_name: e.target.value }))}
            />
          </div>

          {addError && <p className={styles.addError}>{addError}</p>}

          <button type="submit" className={styles.addBtn} disabled={adding}>
            <PlusIcon /> {adding ? 'Adding…' : 'Add to list'}
          </button>
        </form>
      </div>

      {/* Items list */}
      <div className={styles.itemsSection}>
        <h3 className={styles.sectionLabel}>
          Items
          {list.items.length > 0 && <span className={styles.itemCount}>{list.items.length}</span>}
        </h3>

        {list.items.length === 0 ? (
          <div className={styles.emptyItems}>
            <p className={styles.emptyItemsText}>No items yet — use the form above to add dishes or restaurants.</p>
          </div>
        ) : (
          <div className={styles.itemsList}>
            {list.items.map(item => (
              <div key={item.id} className={styles.itemCard}>
                <div className={`${styles.itemTypeIcon} ${item.item_type === 'dish' ? styles.dishType : styles.restaurantType}`}>
                  {item.item_type === 'dish' ? '🍽️' : '🏠'}
                </div>
                <div className={styles.itemBody}>
                  <p className={styles.itemName}>
                    {item.item_type === 'dish' ? item.dish_name : item.restaurant_name}
                  </p>
                  <p className={styles.itemSub}>
                    {item.item_type === 'dish' ? `at ${item.restaurant_name}` : 'Restaurant'}
                  </p>
                </div>
                <span className={styles.itemPill}>
                  {item.item_type === 'dish' ? 'Dish' : 'Place'}
                </span>
                <button
                  className={styles.removeBtn}
                  onClick={() => removeItem(item.id)}
                  disabled={!!removing[item.id]}
                  title="Remove from list"
                >
                  {removing[item.id] ? <span className={styles.removingDot} /> : <TrashIcon />}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
