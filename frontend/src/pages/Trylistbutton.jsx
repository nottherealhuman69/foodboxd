import { useState, useEffect } from 'react'
import * as api from '../api'
import styles from './TrylistButton.module.css'

export default function TrylistButton({ itemType, dishName, restaurantName }) {
  const [inList,  setInList]  = useState(false)
  const [itemId,  setItemId]  = useState(null)
  const [working, setWorking] = useState(false)

  useEffect(() => {
    if (!restaurantName) return
    api.trylist.check({ itemType, restaurantName, dishName })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) { setInList(data.in_trylist); setItemId(data.id) } })
      .catch(() => {})
  }, [itemType, dishName, restaurantName])

  const toggle = async () => {
    if (working) return
    setWorking(true)
    try {
      if (inList && itemId) {
        const res = await api.trylist.remove(itemId)
        if (res.ok) { setInList(false); setItemId(null) }
      } else {
        const res = await api.trylist.add({ item_type: itemType, dish_name: dishName || null, restaurant_name: restaurantName })
        if (res.ok) { const d = await res.json(); setInList(true); setItemId(d.id) }
      }
    } catch {}
    finally { setWorking(false) }
  }

  return (
    <button
      className={`${styles.btn} ${inList ? styles.saved : ''}`}
      onClick={toggle}
      disabled={working}
      title={inList ? 'Remove from Trylist' : 'Add to Trylist'}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path d="M5 3h14a1 1 0 011 1v17l-8-4-8 4V4a1 1 0 011-1z" fill={inList ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
      </svg>
      {working ? (inList ? 'Removing…' : 'Saving…') : (inList ? 'Trylisted ✓' : '+ Trylist')}
    </button>
  )
}
