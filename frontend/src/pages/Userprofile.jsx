import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { normaliseReview, avgRating } from '../utils/reviews'
import { StarRating } from '../components/StarRating'
import { StatGrid, StatCard } from '../components/StatCard'
import FriendButton from '../components/FriendButton'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './UserProfile.module.css'

export default function UserProfile({ userEmail, onBack }) {
  const [reviews,     setReviews]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')
  const [friendStatus, setFriendStatus] = useState(null)

  const username = userEmail.split('@')[0]

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [searchRes, revRes] = await Promise.all([
          apiFetch(`/api/users/search?q=${encodeURIComponent(userEmail)}`),
          apiFetch(`/api/users/${encodeURIComponent(userEmail)}/reviews`),
        ])
        if (searchRes.ok) {
          const users = await searchRes.json()
          const match = users.find(u => u.email === userEmail)
          if (match) setFriendStatus(match.friendship_status)
        }
        if (!revRes.ok) throw new Error()
        setReviews((await revRes.json()).map(normaliseReview))
      } catch {
        setError('Could not load this profile.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [userEmail])

  const avg = avgRating(reviews)

  return (
    <div className={shared.page}>
      <button className={shared.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back
      </button>

      <div className={styles.userHeader}>
        <div className={styles.avatar}>{username[0]?.toUpperCase()}</div>
        <div className={styles.userInfo}>
          <p className={styles.username}>@{username}</p>
          <p className={styles.email}>{userEmail}</p>
        </div>
        <FriendButton
          email={userEmail}
          initialStatus={friendStatus}
          onSent={() => setFriendStatus('pending_sent')}
        />
      </div>

      <StatGrid cols={4}>
        <StatCard count={reviews.length}                                      label="Dishes logged" />
        <StatCard count={avg}                                                  label="Avg rating" />
        <StatCard count={reviews.filter(r => r.type === 'restaurant').length} label="Restaurant" />
        <StatCard count={reviews.filter(r => r.type === 'homemade').length}   label="Homemade" />
      </StatGrid>

      <PageState loading={loading} error={error} empty={!loading && !error && reviews.length === 0} emptyTitle="No dishes logged yet" />

      {!loading && !error && reviews.length > 0 && (
        <div>
          <h3 className={shared.sectionTitle}>Diary</h3>
          <div className={styles.reviewList}>
            {reviews.map(r => <ReviewCard key={r.id} entry={r} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function ReviewCard({ entry }) {
  const date = new Date(entry.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
  return (
    <div className={shared.card}>
      <div className={shared.cardTop}>
        <div>
          <p className={shared.dishName}>{entry.dishName}</p>
          {entry.restaurantName && <p className={shared.restaurant}>{entry.restaurantName}</p>}
        </div>
        <span className={shared.typePill} data-type={entry.type}>
          {entry.type === 'homemade' ? '🏠 Homemade' : '🍽️ Restaurant'}
        </span>
      </div>
      <div className={shared.cardMeta}>
        <StarRating rating={entry.rating} showLabel />
        <span className={shared.dot}>·</span>
        <span className={shared.date}>{date}</span>
      </div>
      {entry.review && <p className={shared.reviewText}>{entry.review}</p>}
    </div>
  )
}
