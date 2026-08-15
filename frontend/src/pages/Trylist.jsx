import { useState } from 'react'
import { useFetch, apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import MyLists from './Mylists'
import styles from './Trylist.module.css'
import GroupLists from './GroupLists'

function BookmarkIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M5 3h14a1 1 0 011 1v17l-8-4-8 4V4a1 1 0 011-1z"
        stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  )
}

function GroupNavIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M3.5 19c0-3 2.5-4.8 5.5-4.8s5.5 1.8 5.5 4.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M16 5.4a3.2 3.2 0 010 5.2M17.5 14.6c2 .7 3.3 2.3 3.3 4.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
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

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"
        stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function ListsNavIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M14 6.5h7M14 10h4M14 17.5h7M14 21h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

const FILTERS = ['All', 'Dishes', 'Restaurants']

export default function Trylist({ onViewDish, onViewRestaurant }) {
  const [tab, setTab] = useState('trylist')
  const { data: items, loading, error, refetch } = useFetch('/api/trylist')
  const [filter,   setFilter]   = useState('All')
  const [removing, setRemoving] = useState({})

  const remove = async (id) => {
    setRemoving(prev => ({ ...prev, [id]: true }))
    try {
      const res = await apiFetch(`/api/trylist/${id}`, { method: 'DELETE' })
      if (res.ok) refetch()
    } catch {}
    finally {
      setRemoving(prev => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  const filtered = (items || []).filter(i => {
    if (filter === 'Dishes')      return i.item_type === 'dish'
    if (filter === 'Restaurants') return i.item_type === 'restaurant'
    return true
  })

  const dishCount       = (items || []).filter(i => i.item_type === 'dish').length
  const restaurantCount = (items || []).filter(i => i.item_type === 'restaurant').length

  return (
    <>
      <div className={styles.tabBarOuter}>
        <button
          className={`${styles.tab} ${tab === 'trylist' ? styles.tabActive : ''}`}
          onClick={() => setTab('trylist')}
        >
          <BookmarkIcon /> Trylist
        </button>
        <button
          className={`${styles.tab} ${tab === 'lists' ? styles.tabActive : ''}`}
          onClick={() => setTab('lists')}
        >
          <ListsNavIcon /> My Lists
        </button>
        <button
          className={`${styles.tab} ${tab === 'groups' ? styles.tabActive : ''}`}
          onClick={() => setTab('groups')}
        >
          <GroupNavIcon /> Group Lists
        </button>
      </div>

      {tab === 'lists' ? (
        <MyLists onViewDish={onViewDish} onViewRestaurant={onViewRestaurant} />
      ) : tab === 'groups' ? (
        <GroupLists onViewDish={onViewDish} onViewRestaurant={onViewRestaurant} />
      ) : (
        <div className={styles.page}>
          <div className={styles.header}>
            <div className={styles.headerIcon}><BookmarkIcon /></div>
            <div>
              <h2 className={styles.title}>Trylist</h2>
              <p className={styles.sub}>
                {!items || items.length === 0
                  ? 'Your wishlist is empty'
                  : `${items.length} item${items.length !== 1 ? 's' : ''} saved`}
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
                        <p className={styles.cardName}>{item.dish_name || item.restaurant_name}</p>
                        {item.dish_name && item.restaurant_name && (
                          <p className={styles.cardSub}>{item.restaurant_name}</p>
                        )}
                      </div>
                      <span className={styles.typePill}>
                        {item.item_type === 'dish' ? 'Dish' : 'Restaurant'}
                      </span>
                    </div>
                    <button
                      className={styles.removeBtn}
                      disabled={removing[item.id]}
                      onClick={() => remove(item.id)}
                      title="Remove from Trylist"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}
