import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import PageState from '../components/PageState'
import TrylistButton from './TrylistButton'
import DishPage from './DishPage'
import shared from '../components/shared.module.css'
import styles from './RestaurantPage.module.css'

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

export default function RestaurantPage({ restaurantName, onBack }) {
  const [data,        setData]        = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')
  const [viewingDish, setViewingDish] = useState(null)
  const [activeTab,   setActiveTab]   = useState('dishes')

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await apiFetch(`/api/restaurants/${encodeURIComponent(restaurantName)}/page`)
        if (!res.ok) throw new Error()
        setData(await res.json())
      } catch {
        setError('Could not load this restaurant page.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [restaurantName])

  if (viewingDish) {
    return <DishPage dishName={viewingDish} restaurantName={restaurantName} onBack={() => setViewingDish(null)} />
  }

  return (
    <div className={styles.page}>
      <button className={shared.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back to search
      </button>

      <PageState loading={loading} error={error} />

      {!loading && !error && data && (
        <>
          <div className={styles.hero}>
            <div className={styles.heroIcon}>🏠</div>
            <div className={styles.heroBody}>
              <h1 className={styles.restaurantName}>{data.restaurant_name}</h1>
              <p className={styles.createdBy}>
                Page created by <span className={styles.creator}>@{data.created_by}</span>
              </p>
              <div style={{ marginTop: 10 }}>
                <TrylistButton itemType="restaurant" restaurantName={data.restaurant_name} />
              </div>
            </div>
          </div>

          <div className={styles.statsStrip}>
            <div className={styles.statItem}>
              <StarRating rating={data.avg_rating} size={18} />
              <span className={styles.avgRating}>{data.avg_rating.toFixed(1)}</span>
              <span className={styles.statLabel}>avg rating</span>
            </div>
            <div className={styles.divider} />
            <div className={styles.statItem}>
              <span className={styles.statNum}>{data.total_dishes}</span>
              <span className={styles.statLabel}>dish{data.total_dishes !== 1 ? 'es' : ''}</span>
            </div>
            <div className={styles.divider} />
            <div className={styles.statItem}>
              <span className={styles.statNum}>{data.total_reviews}</span>
              <span className={styles.statLabel}>review{data.total_reviews !== 1 ? 's' : ''}</span>
            </div>
          </div>

          <div className={styles.tabs}>
            <button className={`${styles.tab} ${activeTab === 'dishes'  ? styles.tabActive : ''}`} onClick={() => setActiveTab('dishes')}>
              Dishes <span className={styles.tabCount}>{data.dishes.length}</span>
            </button>
            <button className={`${styles.tab} ${activeTab === 'reviews' ? styles.tabActive : ''}`} onClick={() => setActiveTab('reviews')}>
              Reviews <span className={styles.tabCount}>{data.reviews.length}</span>
            </button>
          </div>

          {activeTab === 'dishes' && (
            <div className={styles.dishList}>
              {data.dishes.map(dish => (
                <div key={dish.dish_name} className={styles.dishCard}>
                  <button className={styles.dishCardClickable} onClick={() => setViewingDish(dish.dish_name)}>
                    <div className={styles.dishCardLeft}>
                      <span className={styles.dishIcon}>🍽️</span>
                      <div>
                        <p className={styles.dishName}>{dish.dish_name}</p>
                        <p className={styles.dishReviewCount}>{dish.review_count} review{dish.review_count !== 1 ? 's' : ''}</p>
                      </div>
                    </div>
                    <div className={styles.dishCardRight}>
                      <StarRating rating={dish.avg_rating} />
                      <span className={styles.dishAvg}>{dish.avg_rating.toFixed(1)}</span>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className={styles.chevron}>
                        <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                  </button>
                  <div className={styles.dishCardTrylist}>
                    <TrylistButton itemType="dish" dishName={dish.dish_name} restaurantName={data.restaurant_name} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'reviews' && (
            <div className={styles.reviewList}>
              {data.reviews.map(r => (
                <ReviewCard key={r.id} review={r} onViewDish={() => setViewingDish(r.dish_name)} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ReviewCard({ review, onViewDish }) {
  const date = new Date(review.logged_at).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
  return (
    <div className={styles.reviewCard}>
      <div className={styles.reviewHeader}>
        <div className={styles.reviewAvatar}>{review.username.charAt(0).toUpperCase()}</div>
        <div className={styles.reviewHeaderBody}>
          <span className={styles.reviewUsername}>@{review.username}</span>
          <span className={styles.reviewDate}>{date}</span>
        </div>
        <div className={styles.reviewRating}>
          <StarRating rating={review.rating} showLabel />
        </div>
      </div>
      <button className={styles.dishTag} onClick={onViewDish}>🍽️ {review.dish_name}</button>
      {review.review && <p className={styles.reviewText}>{review.review}</p>}
    </div>
  )
}
