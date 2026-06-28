import { useState, useEffect, useRef, useCallback } from 'react'
import styles from './Search.module.css'
import UserProfile from './UserProfile'
import DishPage from './DishPage'
import RestaurantPage from './RestaurantPage'

// ─── Fuzzy match ─────────────────────────────────────────────────────────────
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

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

// ─── Stars ────────────────────────────────────────────────────────────────────
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

// ─── Review Card ──────────────────────────────────────────────────────────────
function ReviewCard({ item, onViewDish, onViewRestaurant }) {
  const date = new Date(item.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
  return (
    <div className={styles.card} style={{cursor: item.restaurantName ? 'pointer' : 'default'}} onClick={() => item.restaurantName && onViewDish && onViewDish(item.dishName, item.restaurantName)}>
      <div className={styles.cardIcon} data-type="review">✍️</div>
      <div className={styles.cardBody}>
        <div className={styles.cardMeta}>
          <span className={styles.pill} data-type="review">Review</span>
          <span className={styles.cardSub}>by @{item.user} · {date}</span>
        </div>
        <h3 className={styles.cardTitle}>
          {item.dishName}
          {item.restaurantName && (
            <button className={styles.restaurantLink} onClick={e => { e.stopPropagation(); onViewRestaurant && onViewRestaurant(item.restaurantName) }}>
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

// ─── User Card ────────────────────────────────────────────────────────────────
function UserCard({ item, onRequestSent, onViewProfile }) {
  const [status,  setStatus]  = useState(item.friendship_status)
  const [loading, setLoading] = useState(false)

  const token = localStorage.getItem('token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const sendRequest = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/friends/request', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ addressee_email: item.email }),
      })
      if (!res.ok) throw new Error()
      setStatus('pending_sent')
      if (onRequestSent) onRequestSent()
    } catch {
      alert('Could not send request. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const friendBtn = () => {
    if (status === 'accepted')         return <span className={styles.friendsBadge}>✓ Friends</span>
    if (status === 'pending_sent')     return <span className={styles.pendingBadge}>Request sent</span>
    if (status === 'pending_received') return <span className={styles.pendingBadge}>Requested you</span>
    return (
      <button className={styles.addFriendBtn} onClick={sendRequest} disabled={loading}>
        {loading ? '…' : '+ Follow'}
      </button>
    )
  }

  return (
    <div className={styles.card} style={{cursor:'pointer'}} onClick={() => onViewProfile && onViewProfile(item.email)}>
      <div className={styles.cardAvatar}>{item.username.charAt(0).toUpperCase()}</div>
      <div className={styles.cardBody}>
        <div className={styles.cardMeta}>
          <span className={styles.pill} data-type="user">Person</span>
        </div>
        <div className={styles.userRow}>
          <h3 className={styles.cardTitle}>@{item.username}</h3>
          {friendBtn()}
        </div>
        <p className={styles.cardSub}>
          {item.review_count > 0
            ? `${item.review_count} dish${item.review_count !== 1 ? 'es' : ''} logged`
            : 'New member'}
        </p>
      </div>
    </div>
  )
}

function ResultCard({ item, onRequestSent, onViewProfile, onViewDish, onViewRestaurant }) {
  if (item.type === 'review') return <ReviewCard item={item} onViewDish={onViewDish} onViewRestaurant={onViewRestaurant} />
  if (item.type === 'user')   return <UserCard item={item} onRequestSent={onRequestSent} onViewProfile={onViewProfile} />
  return null
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Search() {
  const [query,     setQuery]     = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const [reviews,   setReviews]   = useState([])
  const [users,     setUsers]     = useState([])
  const [loading,   setLoading]   = useState(true)
  const [viewingUser, setViewingUser] = useState(null)
  const [viewingDish, setViewingDish] = useState(null) // { dishName, restaurantName }
  const [viewingRestaurant, setViewingRestaurant] = useState(null)
  const [error,     setError]     = useState('')
  const inputRef = useRef(null)

  const token = localStorage.getItem('token')
  const myEmail = localStorage.getItem('email') || ''
  const myUsername = myEmail.split('@')[0]
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  // ── Load reviews (own) + users (everyone else) ───────────────────────────
  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [revRes, userRes] = await Promise.all([
          fetch('/api/reviews/all',     { headers: authHeaders }),
          fetch('/api/users/search?q=', { headers: authHeaders }),
        ])
        if (!revRes.ok || !userRes.ok) throw new Error()

        const rawReviews = await revRes.json()
        const rawUsers   = await userRes.json()

        setReviews(rawReviews.map(r => ({
          id:             `rv-${r.id}`,
          type:           'review',
          dishName:       r.dish_name,
          restaurantName: r.restaurant_name || '',
          review:         r.review || '',
          rating:         r.rating,
          loggedAt:       r.logged_at,
          user:           r.user_email ? r.user_email.split('@')[0] : myUsername,
        })))

        setUsers(rawUsers.map(u => ({
          id:                `u-${u.email}`,
          type:              'user',
          email:             u.email,
          username:          u.username,
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
  }, [token])

  // ── Keyboard shortcut ────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── Fuzzy filter ─────────────────────────────────────────────────────────
  const allItems = [...reviews, ...users]

  const pool = activeTab === 'all'    ? allItems
             : activeTab === 'review' ? reviews
             : users

  const keyFn = (item) => [
    item.dishName, item.restaurantName, item.review, item.username
  ].filter(Boolean).join(' ')

  const results = fuzzyFilter(query, pool, keyFn)

  const counts = {
    all:    allItems.length,
    review: reviews.length,
    user:   users.length,
  }

  const isEmpty = query.trim() && results.length === 0 && !loading

  if (viewingRestaurant) {
    return <RestaurantPage restaurantName={viewingRestaurant} onBack={() => setViewingRestaurant(null)} />
  }

  if (viewingDish) {
    return <DishPage dishName={viewingDish.dishName} restaurantName={viewingDish.restaurantName} onBack={() => setViewingDish(null)} />
  }

  if (viewingUser) {
    return <UserProfile userEmail={viewingUser} onBack={() => setViewingUser(null)} />
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Search your food diary</p>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}>⌕</span>
          <input
            ref={inputRef}
            className={styles.searchInput}
            type="search"
            placeholder="Search dishes, restaurants, reviews, people…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoComplete="off"
            spellCheck="false"
          />
          {query && (
            <button className={styles.clearBtn} onClick={() => setQuery('')} aria-label="Clear">✕</button>
          )}
          <span className={styles.shortcutHint}>/</span>
        </div>
      </section>

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
        {loading && (
          <div className={styles.state}>
            <div className={styles.spinner} />
            <p>Loading…</p>
          </div>
        )}

        {error && !loading && (
          <div className={styles.state}>
            <div className={styles.stateIcon}>⚠️</div>
            <p className={styles.stateTitle}>{error}</p>
          </div>
        )}

        {!loading && !error && !query.trim() && (
          <div className={styles.state}>
            <div className={styles.stateIcon}>🔍</div>
            <p className={styles.stateTitle}>Find your next favourite bite</p>
            <p className={styles.stateSub}>Search across your logged dishes and other users</p>
            {reviews.slice(0, 4).length > 0 && (
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
              {query && (
                <span> for <span className={styles.queryHighlight}>"{query}"</span></span>
              )}
            </p>
            <div className={styles.resultsList}>
              {results.map(item => (
                <ResultCard key={item.id} item={item} onViewProfile={setViewingUser} onViewDish={(d, r) => setViewingDish({ dishName: d, restaurantName: r })} onViewRestaurant={setViewingRestaurant} />
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}