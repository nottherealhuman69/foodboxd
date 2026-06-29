import { useState, useEffect } from 'react'
import styles from './TrylistButton.module.css'

/**
 * TrylistButton
 * Props:
 *   itemType        'dish' | 'restaurant'
 *   dishName        string (required when itemType === 'dish')
 *   restaurantName  string (always required)
 */
export default function TrylistButton({ itemType, dishName, restaurantName }) {
  const [inList,  setInList]  = useState(false)
  const [itemId,  setItemId]  = useState(null)
  const [working, setWorking] = useState(false)

  const token = localStorage.getItem('token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  // Check current trylist state on mount
  useEffect(() => {
    if (!restaurantName) return
    async function check() {
      try {
        const params = new URLSearchParams({ item_type: itemType, restaurant_name: restaurantName })
        if (dishName) params.set('dish_name', dishName)
        const res = await fetch(`/api/trylist/check?${params}`, { headers: authHeaders })
        if (res.ok) {
          const data = await res.json()
          setInList(data.in_trylist)
          setItemId(data.id)
        }
        // If the request fails we just leave inList=false and show the button anyway
      } catch {
        // Silently fail — button still renders in default (not saved) state
      }
    }
    check()
  }, [itemType, dishName, restaurantName, token])

  const toggle = async () => {
    if (working) return
    setWorking(true)
    try {
      if (inList && itemId) {
        const res = await fetch(`/api/trylist/${itemId}`, {
          method: 'DELETE',
          headers: authHeaders,
        })
        if (res.ok) { setInList(false); setItemId(null) }
      } else {
        const res = await fetch('/api/trylist', {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify({
            item_type: itemType,
            dish_name: dishName || null,
            restaurant_name: restaurantName,
          }),
        })
        if (res.ok) {
          const data = await res.json()
          setInList(true)
          setItemId(data.id)
        }
      }
    } catch {
      // Silently fail
    } finally {
      setWorking(false)
    }
  }

  return (
    <button
      className={`${styles.btn} ${inList ? styles.saved : ''}`}
      onClick={toggle}
      disabled={working}
      title={inList ? 'Remove from Trylist' : 'Add to Trylist'}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path
          d="M5 3h14a1 1 0 011 1v17l-8-4-8 4V4a1 1 0 011-1z"
          fill={inList ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
      {working
        ? (inList ? 'Removing…' : 'Saving…')
        : (inList ? 'Trylisted ✓' : '+ Trylist')}
    </button>
  )
}