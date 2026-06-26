import { useState, useEffect } from 'react'
import styles from './DishPage.module.css'

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

export default function DishPage({ dishName, restaurantName, onBack }) {
  const [dish,    setDish]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  const token = localStorage.getItem('token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(
          `/api/dishes/${encodeURIComponent(dishName)}/restaurant/${encodeURIComponent(restaurantName)}`,
          { headers: authHeaders }
        )
        if (!res.ok) throw new Error()
        setDish(await res.json())
      } catch {
        setError('Could not load this dish page.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [dishName, restaurantName])

  return (
    <div className={styles.page}>
      <button className={styles.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back to search
      </button>

      {loading && (
        <div className={styles.state}>
          <div className={styles.spinner} />
          <p>Loading…</p>
        </div>
      )}

      {error && !loading && (
        <div className={styles.state}>
          <div className={styles.stateIcon}>⚠️</div>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && dish && (
        <>
          {/* Hero */}
          <div className={styles.hero}>
            <div className={styles.dishIcon}>🍽️</div>
            <div className={styles.heroBody}>
              <h1 className={styles.dishName}>{dish.dish_name}</h1>
              <div className={styles.restaurantRow}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M3 17V8.5M17 17V8.5M10 3v14" stroke="#8b8fa8" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M3 8.5C3 6 5 4 7 4h6c2 0 4 2 4 4.5" stroke="#8b8fa8" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M2 17h16" stroke="#8b8fa8" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <span className={styles.restaurantName}>{dish.restaurant_name}</span>
              </div>
            </div>
          </div>

          {/* Stats strip */}
          <div className={styles.statsStrip}>
            <div className={styles.statItem}>
              <BigStars rating={dish.avg_rating} />
              <span className={styles.avgRating}>{dish.avg_rating.toFixed(1)}</span>
              <span className={styles.statLabel}>avg rating</span>
            </div>
            <div className={styles.divider} />
            <div className={styles.statItem}>
              <span className={styles.statNum}>{dish.review_count}</span>
              <span className={styles.statLabel}>review{dish.review_count !== 1 ? 's' : ''}</span>
            </div>
            <div className={styles.divider} />
            <div className={styles.statItem}>
              <span className={styles.statNum}>@{dish.created_by}</span>
              <span className={styles.statLabel}>page created by</span>
            </div>
          </div>

          {/* Reviews */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>All reviews</h3>
            <div className={styles.reviewList}>
              {dish.reviews.map(r => (
                <ReviewCard key={r.id} review={r} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function ReviewCard({ review }) {
  const date = new Date(review.logged_at).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.userAvatar}>{review.username.charAt(0).toUpperCase()}</div>
        <div className={styles.cardHeaderBody}>
          <span className={styles.cardUsername}>@{review.username}</span>
          <span className={styles.cardDate}>{date}</span>
        </div>
        <div className={styles.cardRating}>
          <SmallStars rating={review.rating} />
          <span className={styles.cardRatingLabel}>{RATING_LABELS[review.rating]}</span>
        </div>
      </div>
      {review.review && (
        <p className={styles.cardReview}>{review.review}</p>
      )}
    </div>
  )
}

function BigStars({ rating }) {
  return (
    <span className={styles.bigStars}>
      {[1,2,3,4,5].map(n => (
        <svg key={n} width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
            fill={n <= Math.round(rating) ? '#6366F1' : 'transparent'}
            stroke={n <= Math.round(rating) ? '#6366F1' : '#2d3155'}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      ))}
    </span>
  )
}

function SmallStars({ rating }) {
  return (
    <span className={styles.smallStars}>
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