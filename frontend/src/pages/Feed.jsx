import { useState, useEffect, useCallback } from 'react'
import styles from './Feed.module.css'

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

function Stars({ rating }) {
  return (
    <span className={styles.stars}>
      {[1,2,3,4,5].map(n => (
        <svg key={n} width="13" height="13" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
            fill={n <= rating ? '#6366F1' : 'transparent'}
            stroke={n <= rating ? '#6366F1' : '#2d3155'}
            strokeWidth="1.5" strokeLinejoin="round"
          />
        </svg>
      ))}
    </span>
  )
}

function timeAgo(iso) {
  const diff  = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins  < 1)  return 'just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days  < 7)  return `${days}d ago`
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

function FeedCard({ item, onViewRestaurant, onViewDish, onViewUser }) {
  return (
    <div className={styles.card}>
      {/* Left: avatar + timeline line */}
      <div className={styles.avatarCol}>
        <button className={styles.avatarBtn} onClick={() => onViewUser && onViewUser(item.user_email)}>{item.username.charAt(0).toUpperCase()}</button>
        <div className={styles.timelineLine} />
      </div>

      {/* Right: content */}
      <div className={styles.content}>
        <div className={styles.cardHeader}>
          <div className={styles.meta}>
            <button className={styles.usernameBtn} onClick={() => onViewUser && onViewUser(item.user_email)}>@{item.username}</button>
            <span className={styles.dot}>·</span>
            <span className={styles.time}>{timeAgo(item.logged_at)}</span>
          </div>
          <span className={styles.typePill} data-type={item.type}>
            {item.type === 'homemade' ? '🏠 Homemade' : '🍽️ Restaurant'}
          </span>
        </div>

        <div className={styles.dishRow}>
          <button
            className={styles.dishName}
            onClick={() => item.restaurant_name && onViewDish && onViewDish(item.dish_name, item.restaurant_name)}
            disabled={!item.restaurant_name}
          >
            {item.dish_name}
          </button>
          {item.restaurant_name && (
            <button className={styles.restaurantLink} onClick={() => onViewRestaurant && onViewRestaurant(item.restaurant_name)}>
              at {item.restaurant_name}
            </button>
          )}
        </div>

        <div className={styles.ratingRow}>
          <Stars rating={item.rating} />
          <span className={styles.ratingLabel}>{RATING_LABELS[item.rating]}</span>
        </div>

        {item.review && (
          <p className={styles.reviewText}>{item.review}</p>
        )}
      </div>
    </div>
  )
}

export default function Feed({ onViewDish, onViewRestaurant, onViewUser }) {
  const [items,   setItems]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  const token = localStorage.getItem('token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/feed', { headers: authHeaders })
      if (!res.ok) throw new Error()
      setItems(await res.json())
    } catch {
      setError('Could not load your feed.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Feed</h2>
        <p className={styles.sub}>Latest dishes from people you follow</p>
      </div>

      {loading && (
        <div className={styles.state}>
          <div className={styles.spinner} />
          <p>Loading feed…</p>
        </div>
      )}

      {error && !loading && (
        <div className={styles.state}>
          <div className={styles.stateIcon}>⚠️</div>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="#4e5272" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="9" cy="7" r="4" stroke="#4e5272" strokeWidth="1.5"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke="#4e5272" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <p className={styles.emptyTitle}>Nothing here yet</p>
          <p className={styles.emptyHint}>
            Follow people from the Search page to see their dishes here
          </p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className={styles.feed}>
          {items.map(item => (
            <FeedCard
              key={item.id}
              item={item}
              onViewDish={onViewDish}
              onViewRestaurant={onViewRestaurant}
              onViewUser={onViewUser}
            />
          ))}
        </div>
      )}
    </div>
  )
}