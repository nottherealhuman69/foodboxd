import { useState, useEffect } from 'react'
import styles from './UserProfile.module.css'

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

export default function UserProfile({ userEmail, onBack }) {
  const [reviews,  setReviews]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [friendStatus, setFriendStatus] = useState(null)
  const [acting,   setActing]   = useState(false)

  const username   = userEmail.split('@')[0]
  const token      = localStorage.getItem('token')
  const myEmail    = localStorage.getItem('email')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        // Get friendship status via user search
        const searchRes = await fetch(
          `/api/users/search?q=${encodeURIComponent(userEmail)}`,
          { headers: authHeaders }
        )
        if (searchRes.ok) {
          const users = await searchRes.json()
          const match = users.find(u => u.email === userEmail)
          if (match) setFriendStatus(match.friendship_status)
        }

        // Get their reviews — for now we fetch all reviews from search context
        // (backend would need a /users/:email/reviews endpoint for other users;
        //  for friends we can reuse the existing data we already loaded in Search)
        // We'll use a dedicated endpoint added below
        const revRes = await fetch(
          `/api/users/${encodeURIComponent(userEmail)}/reviews`,
          { headers: authHeaders }
        )
        if (!revRes.ok) throw new Error()
        const data = await revRes.json()
        setReviews(data.map(r => ({
          id:             r.id,
          dishName:       r.dish_name,
          type:           r.type,
          restaurantName: r.restaurant_name || '',
          rating:         r.rating,
          review:         r.review || '',
          loggedAt:       r.logged_at,
        })))
      } catch {
        setError('Could not load this profile.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [userEmail, token])

  const sendRequest = async () => {
    setActing(true)
    try {
      const res = await fetch('/api/friends/request', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ addressee_email: userEmail }),
      })
      if (!res.ok) throw new Error()
      setFriendStatus('pending_sent')
    } catch {
      alert('Could not send request.')
    } finally {
      setActing(false)
    }
  }

  const avgRating = reviews.length
    ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1)
    : null

  return (
    <div className={styles.page}>
      {/* Back button */}
      <button className={styles.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back to search
      </button>

      {/* User header */}
      <div className={styles.userHeader}>
        <div className={styles.avatar}>{username.charAt(0).toUpperCase()}</div>
        <div className={styles.userInfo}>
          <h2 className={styles.username}>@{username}</h2>
          <p className={styles.email}>{userEmail}</p>
        </div>
        <div className={styles.followWrap}>
          {friendStatus === 'accepted' && (
            <span className={styles.friendsBadge}>✓ Friends</span>
          )}
          {friendStatus === 'pending_sent' && (
            <span className={styles.pendingBadge}>Request sent</span>
          )}
          {friendStatus === 'pending_received' && (
            <span className={styles.pendingBadge}>Requested you</span>
          )}
          {!friendStatus && (
            <button className={styles.followBtn} onClick={sendRequest} disabled={acting}>
              {acting ? '…' : '+ Follow'}
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      {!loading && !error && (
        <div className={styles.statsRow}>
          <div className={styles.statCard}>
            <span className={styles.statCount}>{reviews.length}</span>
            <span className={styles.statLabel}>Dishes logged</span>
          </div>
          <div className={styles.statCard}>
            <span className={styles.statCount}>{avgRating ?? '—'}</span>
            <span className={styles.statLabel}>Avg rating</span>
          </div>
          <div className={styles.statCard}>
            <span className={styles.statCount}>{reviews.filter(r => r.type === 'restaurant').length}</span>
            <span className={styles.statLabel}>Restaurant</span>
          </div>
          <div className={styles.statCard}>
            <span className={styles.statCount}>{reviews.filter(r => r.type === 'homemade').length}</span>
            <span className={styles.statLabel}>Homemade</span>
          </div>
        </div>
      )}

      {/* Reviews */}
      {loading && (
        <div className={styles.state}>
          <div className={styles.spinner} />
          <p>Loading profile…</p>
        </div>
      )}

      {error && !loading && (
        <div className={styles.state}>
          <div className={styles.stateIcon}>⚠️</div>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && reviews.length === 0 && (
        <div className={styles.empty}>
          <p className={styles.emptyText}>No dishes logged yet</p>
        </div>
      )}

      {!loading && !error && reviews.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Diary</h3>
          <div className={styles.reviewList}>
            {reviews.map(r => (
              <ReviewCard key={r.id} entry={r} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ReviewCard({ entry }) {
  const date = new Date(entry.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
  return (
    <div className={styles.card}>
      <div className={styles.cardTop}>
        <div>
          <h4 className={styles.dishName}>{entry.dishName}</h4>
          {entry.restaurantName && (
            <span className={styles.restaurant}>{entry.restaurantName}</span>
          )}
        </div>
        <span className={styles.typePill} data-type={entry.type}>
          {entry.type === 'homemade' ? '🏠 Homemade' : '🍽 Restaurant'}
        </span>
      </div>
      <div className={styles.cardMeta}>
        <Stars rating={entry.rating} />
        <span className={styles.ratingLabel}>{RATING_LABELS[entry.rating]}</span>
        <span className={styles.dot}>·</span>
        <span className={styles.date}>{date}</span>
      </div>
      {entry.review && <p className={styles.reviewText}>{entry.review}</p>}
    </div>
  )
}

function Stars({ rating }) {
  return (
    <span className={styles.stars}>
      {[1,2,3,4,5].map(n => (
        <svg key={n} width="13" height="13" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
            fill={n <= rating ? '#6366F1' : 'transparent'}
            stroke={n <= rating ? '#6366F1' : '#2d3155'}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      ))}
    </span>
  )
}