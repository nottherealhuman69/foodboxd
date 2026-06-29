import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import { RATING_LABELS } from '../utils/reviews'
import PageState from '../components/PageState'
import TrylistButton from './TrylistButton'
import shared from '../components/shared.module.css'
import styles from './DishPage.module.css'

export default function DishPage({ dishName, restaurantName, onBack }) {
  const [dish,    setDish]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await apiFetch(
          `/api/dishes/${encodeURIComponent(dishName)}/restaurant/${encodeURIComponent(restaurantName)}`
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
      <button className={shared.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back to search
      </button>

      <PageState loading={loading} error={error} />

      {!loading && !error && dish && (
        <>
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
              <div style={{ marginTop: 12 }}>
                <TrylistButton itemType="dish" dishName={dish.dish_name} restaurantName={dish.restaurant_name} />
              </div>
            </div>
          </div>

          <div className={styles.statsStrip}>
            <div className={styles.statItem}>
              <StarRating rating={dish.avg_rating} size={20} />
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

          <div className={styles.section}>
            <h3 className={shared.sectionTitle}>All reviews</h3>
            <div className={styles.reviewList}>
              {dish.reviews.map(r => <ReviewCard key={r.id} review={r} />)}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function ReviewCard({ review }) {
  const date = new Date(review.logged_at).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
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
          <StarRating rating={review.rating} showLabel />
        </div>
      </div>
      {review.review && <p className={styles.cardReview}>{review.review}</p>}
    </div>
  )
}
