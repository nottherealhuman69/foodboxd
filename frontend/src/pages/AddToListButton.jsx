import { useState, useRef, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import styles from './AddToListButton.module.css'

export default function AddToListButton({ itemType, name, restaurantName }) {
  const [open,    setOpen]    = useState(false)
  const [lists,   setLists]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  //const [addedTo, setAddedTo] = useState(new Set())
  const [savingId, setSavingId] = useState(null)
  const wrapRef = useRef(null)
  const [addedTo, setAddedTo] = useState({}) // { [listId]: 'added' | 'already' }

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggleDropdown = () => {
    setOpen(o => !o)
    if (!lists) {
      setLoading(true)
      setError('')
      apiFetch('/api/lists')
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => setLists(data))
        .catch(() => setError('Could not load your lists.'))
        .finally(() => setLoading(false))
    }
  }

const addToList = async (listId) => {
    if (savingId) return
    setSavingId(listId)
    try {
      const res = await apiFetch(`/api/lists/${listId}/items`, {
        method: 'POST',
        body: JSON.stringify({
          item_type: itemType,
          name,
          restaurant_name: itemType === 'dish' ? restaurantName : null,
        }),
      })
      if (res.ok) {
        setAddedTo(prev => ({ ...prev, [listId]: 'added' }))
      } else if (res.status === 409) {
        setAddedTo(prev => ({ ...prev, [listId]: 'already' }))
      }
    } catch {}
    finally { setSavingId(null) }
  }

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button className={styles.btn} onClick={toggleDropdown} title="Add to list">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
          <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
          <path d="M14 6.5h7M14 10h4M14 17.5h7M14 21h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
        </svg>
        + List
      </button>

      {open && (
        <div className={styles.dropdown}>
          {loading && <p className={styles.dropdownMsg}>Loading your lists…</p>}
          {error && <p className={styles.dropdownMsgErr}>{error}</p>}
          {!loading && !error && lists && lists.length === 0 && (
            <p className={styles.dropdownMsg}>You don't have any lists yet. Create one from the Trylist tab.</p>
          )}
          {!loading && !error && lists && lists.length > 0 && (
                <div className={styles.dropdownList}>
                    {lists.map(l => {
                    const status = addedTo[l.id]
                    return (
                        <button
                        key={l.id}
                        className={styles.dropdownItem}
                        onClick={() => addToList(l.id)}
                        disabled={!!status || savingId === l.id}
                        >
                        <span className={styles.listName}>{l.name}</span>
                        {status === 'added' ? (
                            <span className={styles.checkmark}>✓ Added</span>
                        ) : status === 'already' ? (
                            <span className={styles.alreadyLabel}>Already in list</span>
                        ) : savingId === l.id ? (
                            <span className={styles.saving}>Adding…</span>
                        ) : (
                            <span className={styles.itemCount}>{l.item_count} item{l.item_count !== 1 ? 's' : ''}</span>
                        )}
                        </button>
                    )
                    })}
                </div>
                )}
        </div>
      )}
    </div>
  )
}