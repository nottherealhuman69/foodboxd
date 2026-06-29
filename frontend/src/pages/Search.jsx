import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../hooks/useApi'
import { RATING_LABELS } from '../utils/reviews'
import { StarRating } from '../components/StarRating'
import FriendButton from '../components/FriendButton'
import PageState from '../components/PageState'
import styles from './Search.module.css'

function fuzzyScore(needle, haystack) {
  if (!needle) return 1
  const n = needle.toLowerCase()
  const h = haystack.toLowerCase()
  if (h.includes(n)) return 100 - h.indexOf(n)
  let ni = 0, score = 0, lastMatch = -1
  for (let hi = 0; hi < h.length && ni < n.length; hi++) {
    if (h[hi] === n[ni]) {
      score += lastMatch === hi - 1 ? 10 : 1
      lastMatch = hi
      ni++
    }
  }
  return ni === n.length ? score : 0
}

function fuzzyFilter(query, items, keyFn) {
  if (!query.trim()) return items
  return items
    .map(item => ({ item, score: fuzzyScore(query.trim(), keyFn(item)) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .map(({ item }) => item)
}

const TABS = [
  { id: 'all',    label: 'All' },
  { id: 'review', label: 'Reviews' },
  { id: 'user',   label: 'People' },
]

function Stars({ rating }) {
  return (
    <span className={styles.stars}>
      {[1,2,3,4,5].map(i => (
        <span key={i} className={i <= Math.round(rating) ? styles.starFilled : styles.starEmpty}>★</span>
      ))}
      <span className={styles.ratingNum}>{Number(rating).toFixed(1)}</span>
    </span>
  )
}

function ReviewCard({ item, onViewDish, onViewRestaurant }) {
  const date = new Date(item.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
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
            <button
              className={styles.restaurantLink}
              onClick={e => { e.stopPropagation(); onViewRestaurant?.(item.restaurantName) }}
            >
              at {item.restaurantName} →
            </button>
          )}
        </h3>
        {item.review && <p className={styles.cardExcerpt}>{item.review}</p>}
        <div className={styles.cardFooter}>
          <Stars rating={item.rating} />
          <span className={styles.ratingLabel}>{RATING_LABELS[item.rating]}</span>
        </div>
      </div>
    </div>
  )
}

function UserCard({ item, onViewProfile }) {
  return (
    <div className={styles.card} onClick={() => onViewProfile?.(item.email)} style={{ cursor: 'pointer' }}>
      <div className={styles.cardAvatar}>{item.username.charAt(0).toUpperCase()}</div>
      <div className={styles.cardBody}>
        <div className={styles.userRow}>
          <h3 className={styles.cardTitle} style={{ marginBottom: 0 }}>@{item.username}</h3>
          <FriendButton email={item.email} initialStatus={item.friendship_status} />
        </div>
        <div className={styles.userStats}>
          <span>{item.review_count > 0 ? `${item.review_count} dish${item.review_count !== 1 ? 'es' : ''} logged` : 'New member'}</span>
        </div>
      </div>
    </div>
  )
}

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

  const filteredReviews = fuzzyFilter(query, reviews, i => `${i.dishName} ${i.restaurantName} ${i.user}`)
  const filteredUsers   = fuzzyFilter(query, users,   i => `${i.username} ${i.email}`)

  const results =
    activeTab === 'review' ? filteredReviews :
    activeTab === 'user'   ? filteredUsers :
    [...filteredReviews, ...filteredUsers]

  const counts = {
    all:    filteredReviews.length + filteredUsers.length,
    review: filteredReviews.length,
    user:   filteredUsers.length,
  }

  const isEmpty = !loading && !error && query.trim() && results.length === 0

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}>🔍</span>
          <input
            ref={inputRef}
            className={styles.searchInput}
            type="search"
            placeholder="Search dishes, restaurants, people…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
          {query && (
            <button className={styles.clearBtn} onClick={() => setQuery('')}>✕</button>
          )}
        </div>
      </div>

      <nav className={styles.tabs}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            <span className={styles.tabCount}>{counts[tab.id]}</span>
          </button>
        ))}
      </nav>

      <main className={styles.results}>
        <PageState loading={loading} error={error} />

        {!loading && !error && !query.trim() && (
          <div className={styles.state}>
            <div className={styles.stateIcon}>🔍</div>
            <p className={styles.stateTitle}>Find your next favourite bite</p>
            <p className={styles.stateSub}>Search across dishes, restaurants and people</p>
            {reviews.length > 0 && (
              <div className={styles.suggestions}>
                {reviews.slice(0, 4).map(i => (
                  <button key={i.id} className={styles.suggestionChip} onClick={() => setQuery(i.dishName)}>
                    {i.dishName}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {isEmpty && (
          <div className={styles.state}>
            <div className={styles.stateIcon}>🫙</div>
            <p className={styles.stateTitle}>No results for "{query}"</p>
            <p className={styles.stateSub}>Try a different spelling or switch tabs</p>
          </div>
        )}

        {!loading && !error && results.length > 0 && (
          <div>
            <p className={styles.resultCount}>
              {results.length} result{results.length !== 1 ? 's' : ''}
              {query && <span> for <span className={styles.queryHighlight}>"{query}"</span></span>}
            </p>
            <div className={styles.resultsList}>
              {results.map(item =>
                item.type === 'review'
                  ? <ReviewCard key={item.id} item={item} onViewDish={onViewDish} onViewRestaurant={onViewRestaurant} />
                  : <UserCard   key={item.id} item={item} onViewProfile={onViewUser} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}