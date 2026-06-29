import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../hooks/useApi'
import { normaliseReview, RATING_LABELS } from '../utils/reviews'
import { StarRating } from '../components/StarRating'
import FriendButton from '../components/FriendButton'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Search.module.css'

const TABS = ['all', 'reviews', 'users']

export default function Search({ onViewDish, onViewRestaurant, onViewUser }) {
  const [query,     setQuery]     = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const [reviews,   setReviews]   = useState([])
  const [users,     setUsers]     = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState('')
  const inputRef = useRef(null)

  const myEmail    = localStorage.getItem('email') || ''
  const myUsername = myEmail.split('@')[0]

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [revRes, userRes] = await Promise.all([
          apiFetch('/api/reviews/all'),
          apiFetch('/api/users/search?q='),
        ])
        if (!revRes.ok || !userRes.ok) throw new Error()
        setReviews((await revRes.json()).map(r => ({
          id:             `rv-${r.id}`,
          type:           'review',
          dishName:       r.dish_name,
          restaurantName: r.restaurant_name || '',
          review:         r.review || '',
          rating:         r.rating,
          loggedAt:       r.logged_at,
          user:           r.user_email ? r.user_email.split('@')[0] : myUsername,
        })))
        setUsers((await userRes.json()).map(u => ({
          id:                `u-${u.email}`,
          type:              'user',
          email:             u.email,
          username:          u.email.split('@')[0],
          review_count:      u.review_count,
          friendship_status: u.friendship_status,
        })))
      } catch {
        setError('Could not load data. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const q = query.toLowerCase()
  const filteredReviews = reviews.filter(r =>
    r.dishName.toLowerCase().includes(q) ||
    r.restaurantName.toLowerCase().includes(q) ||
    r.user.toLowerCase().includes(q)
  )
  const filteredUsers = users.filter(u =>
    u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
  )

  const items = activeTab === 'reviews' ? filteredReviews
              : activeTab === 'users'   ? filteredUsers
              : [...filteredReviews, ...filteredUsers]

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.searchBar}>
          <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <input
            ref={inputRef}
            className={styles.searchInput}
            placeholder="Search dishes, restaurants, people…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
        </div>
        <div className={styles.tabs}>
          {TABS.map(t => (
            <button
              key={t}
              className={`${styles.tab} ${activeTab === t ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <PageState loading={loading} error={error} />

      {!loading && !error && (
        <div className={styles.results}>
          {items.length === 0
            ? <p className={styles.noResults}>No results for "{query}"</p>
            : items.map(item =>
                item.type === 'review'
                  ? <ReviewCard key={item.id} item={item} onViewDish={onViewDish} onViewRestaurant={onViewRestaurant} />
                  : <UserCard   key={item.id} item={item} onViewProfile={onViewUser} />
              )
          }
        </div>
      )}
    </div>
  )
}

function ReviewCard({ item, onViewDish, onViewRestaurant }) {
  const date = new Date(item.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
  return (
    <div
      className={styles.card}
      style={{ cursor: item.restaurantName ? 'pointer' : 'default' }}
      onClick={() => item.restaurantName && onViewDish?.(item.dishName, item.restaurantName)}
    >
      <div className={styles.cardIcon} data-type="review">✍️</div>
      <div className={styles.cardBody}>
        <div className={styles.cardMeta}>
          <span className={styles.pill} data-type="review">Review</span>
          <span className={styles.cardSub}>by @{item.user} · {date}</span>
        </div>
        <h3 className={styles.cardTitle}>
          {item.dishName}
          {item.restaurantName && (
            <button className={styles.restaurantLink} onClick={e => { e.stopPropagation(); onViewRestaurant?.(item.restaurantName) }}>
              at {item.restaurantName} →
            </button>
          )}
        </h3>
        {item.review && <p className={styles.cardExcerpt}>{item.review}</p>}
        <div className={styles.cardFooter}>
          <StarRating rating={item.rating} showLabel />
        </div>
      </div>
    </div>
  )
}

function UserCard({ item, onViewProfile }) {
  return (
    <div className={styles.card} style={{ cursor: 'pointer' }} onClick={() => onViewProfile?.(item.email)}>
      <div className={styles.cardAvatar}>{item.username.charAt(0).toUpperCase()}</div>
      <div className={styles.cardBody}>
        <div className={styles.userRow}>
          <h3 className={styles.cardTitle}>@{item.username}</h3>
          <FriendButton email={item.email} initialStatus={item.friendship_status} />
        </div>
        <p className={styles.cardSub}>
          {item.review_count > 0 ? `${item.review_count} dish${item.review_count !== 1 ? 'es' : ''} logged` : 'New member'}
        </p>
      </div>
    </div>
  )
}
