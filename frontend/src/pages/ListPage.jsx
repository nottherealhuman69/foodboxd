import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Mylists.module.css'

const TYPE_ICONS  = { dish: '🍽️', restaurant: '🏠', recipe: '📖' }
const TYPE_LABELS = { dish: 'Dish', restaurant: 'Restaurant', recipe: 'Recipe' }

export default function ListPage({ listId, listName, onBack, onViewDish, onViewRestaurant }) {
  const [items,   setItems]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    apiFetch(`/api/lists/${listId}/items`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setItems(data))
      .catch(() => setError('Could not load this list.'))
      .finally(() => setLoading(false))
  }, [listId])

  return (
    <div className={shared.page}>
      <button className={shared.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back
      </button>

      <div className={styles.detailHeader}>
        <h2 className={styles.detailTitle}>{listName}</h2>
      </div>

      <PageState loading={loading} error={error} />

      {!loading && !error && items.length === 0 && (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>This list is empty</p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className={styles.itemsList}>
          {items.map((item, idx) => {
            const clickable = (item.item_type === 'dish' && item.restaurant_name) || item.item_type === 'restaurant'
            const handleClick = () => {
              if (item.item_type === 'dish' && item.restaurant_name) {
                onViewDish?.(item.name, item.restaurant_name)
              } else if (item.item_type === 'restaurant') {
                onViewRestaurant?.(item.name)
              }
            }
            return (
              <div
                key={item.id}
                className={styles.itemCard}
                style={{ cursor: clickable ? 'pointer' : 'default' }}
                onClick={clickable ? handleClick : undefined}
              >
                <span className={styles.itemIndex}>{idx + 1}</span>
                <div className={styles.itemTypeIcon}>{TYPE_ICONS[item.item_type]}</div>
                <div className={styles.itemBody}>
                  <p className={styles.itemName}>{item.name}</p>
                  {item.restaurant_name && <p className={styles.itemSub}>at {item.restaurant_name}</p>}
                  {item.note && <p className={styles.itemNote}>"{item.note}"</p>}
                </div>
                <span className={styles.itemTypePill}>{TYPE_LABELS[item.item_type]}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}