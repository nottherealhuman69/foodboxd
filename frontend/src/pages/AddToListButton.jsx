import { useState, useRef, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import styles from './AddToListButton.module.css'

/* Personal list ids and group list ids are separate sequences, so #3 can exist
   in both. Everything below keys off `${kind}-${id}` to keep them distinct. */
const keyOf = (l) => `${l.kind}-${l.id}`

export default function AddToListButton({ itemType, name, restaurantName }) {
  const [open,     setOpen]     = useState(false)
  const [lists,    setLists]    = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [savingId, setSavingId] = useState(null)
  const [addedTo,  setAddedTo]  = useState({}) // { [key]: 'added' | 'already' }
  const wrapRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggleDropdown = () => {
    setOpen(o => !o)
    if (lists) return

    setLoading(true)
    setError('')
    Promise.all([
      apiFetch('/api/lists').then(r => (r.ok ? r.json() : Promise.reject())),
      // A failed group fetch shouldn't sink the personal lists.
      apiFetch('/api/group-lists').then(r => (r.ok ? r.json() : [])).catch(() => []),
    ])
      .then(([personal, groups]) => {
        setLists([
          ...personal.map(l => ({ ...l, kind: 'personal' })),
          ...groups.map(l => ({ ...l, kind: 'group' })),
        ])
      })
      .catch(() => setError('Could not load your lists.'))
      .finally(() => setLoading(false))
  }

  const addToList = async (list) => {
    const k = keyOf(list)
    if (savingId) return
    setSavingId(k)
    try {
      const endpoint = list.kind === 'group'
        ? `/api/group-lists/${list.id}/items`
        : `/api/lists/${list.id}/items`
      const res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          item_type: itemType,
          name,
          restaurant_name: itemType === 'dish' ? restaurantName : null,
        }),
      })
      if (res.ok) {
        setAddedTo(prev => ({ ...prev, [k]: 'added' }))
      } else if (res.status === 409) {
        // Group lists name who got there first; personal lists just say "already".
        const detail = await res.json().catch(() => ({}))
        setAddedTo(prev => ({ ...prev, [k]: 'already' }))
        if (list.kind === 'group' && detail.detail) {
          setLists(prev => prev.map(l =>
            keyOf(l) === k ? { ...l, conflictNote: detail.detail } : l
          ))
        }
      }
    } catch {}
    finally { setSavingId(null) }
  }

  const personal = (lists || []).filter(l => l.kind === 'personal')
  const groups   = (lists || []).filter(l => l.kind === 'group')

  const renderRow = (l) => {
    const k = keyOf(l)
    const status = addedTo[k]
    return (
      <button
        key={k}
        className={styles.dropdownItem}
        onClick={() => addToList(l)}
        disabled={!!status || savingId === k}
        title={l.kind === 'group' ? `Shared with ${l.member_count} people` : undefined}
      >
        <span className={styles.listNameWrap}>
          <span className={styles.listName}>{l.name}</span>
          {l.kind === 'group' && <span className={styles.groupBadge}>Group</span>}
        </span>
        {status === 'added' ? (
          <span className={styles.checkmark}>✓ Added</span>
        ) : status === 'already' ? (
          <span className={styles.alreadyLabel}>
            {l.conflictNote || 'Already in list'}
          </span>
        ) : savingId === k ? (
          <span className={styles.saving}>Adding…</span>
        ) : (
          <span className={styles.itemCount}>
            {l.kind === 'group'
              ? `${l.member_count} member${l.member_count !== 1 ? 's' : ''}`
              : `${l.item_count} item${l.item_count !== 1 ? 's' : ''}`}
          </span>
        )}
      </button>
    )
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
            <p className={styles.dropdownMsg}>
              You don't have any lists yet. Create one from the Trylist tab.
            </p>
          )}

          {!loading && !error && personal.length > 0 && (
            <>
              {groups.length > 0 && <p className={styles.sectionLabel}>My lists</p>}
              <div className={styles.dropdownList}>{personal.map(renderRow)}</div>
            </>
          )}

          {!loading && !error && groups.length > 0 && (
            <>
              <p className={styles.sectionLabel}>Group lists</p>
              <div className={styles.dropdownList}>{groups.map(renderRow)}</div>
            </>
          )}
        </div>
      )}
    </div>
  )
}