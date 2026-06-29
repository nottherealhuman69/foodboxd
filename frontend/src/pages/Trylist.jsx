import { useState } from 'react'
import { useFetch, apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Trylist.module.css'

const FILTERS = ['All', 'Dishes', 'Restaurants']

export default function Trylist({ onViewDish, onViewRestaurant }) {
  const { data: items, loading, error, refetch } = useFetch('/api/trylist')
  const [filter,   setFilter]   = useState('All')
  const [removing, setRemoving] = useState({})

  const remove = async (id) => {
    setRemoving(prev => ({ ...prev, [id]: true }))
    try {
      const res = await apiFetch(`/api/trylist/${id}`, { method: 'DELETE' })
      if (res.ok) refetch()
    } catch {}
    finally { setRemoving(prev => { const n = { ...prev }; delete n[id]; return n }) }
  }

  const filtered = (items || []).filter(i => {
    if (filter === 'Dishes')      return i.item_type === 'dish'
    if (filter === 'Restaurants') return i.item_type === 'restaurant'
    return true
  })
  const dishCount       = (items || []).filter(i => i.item_type === 'dish').length
  const restaurantCount = (items || []).filter(i => i.item_type === 'restaurant').length

  return (
    <div className={shared.page}>
      <div className={styles.header}>
        <div className={styles.headerIcon}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M5 3h14a1 1 0 011 1v17l-8-4-8 4V4a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <h2 className={styles.title}>Trylist</h2>
          <p className={styles.sub}>
            {!items || items.length === 0 ? 'Your wishlist is empty' : `${items.length} item${items.length !== 1 ? 's' : ''} saved`}
          </p>
        </div>
      </div>

      <PageState
        loading={loading}
        error={error}
        empty={!loading && !error && (!items || items.length === 0)}
        emptyTitle="Nothing saved yet"
        emptyHint='Browse dishes and restaurants, then hit "+ Trylist" to save them here.'
      />

      {!loading && !error && items?.length > 0 && (
        <>
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
          <div className={styles.list}>
            {filtered.map(item => (
              <div key={item.id} className={styles.card}>
                <div className={styles.cardIcon}>
                  {item.item_type === 'dish' ? '🍽️' : '🏠'}
                </div>
                <div className={styles.cardBody} onClick={() => {
                  if (item.item_type === 'dish') onViewDish?.(item.dish_name, item.restaurant_name)
                  else onViewRestaurant?.(item.restaurant_name)
                }}>
                  <p className={styles.itemName}>{item.dish_name || item.restaurant_name}</p>
                  {item.dish_name && item.restaurant_name && (
                    <p className={styles.itemSub}>{item.restaurant_name}</p>
                  )}
                </div>
                <button
                  className={styles.removeBtn}
                  disabled={removing[item.id]}
                  onClick={() => remove(item.id)}
                >
                  {removing[item.id] ? '…' : '✕'}
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
