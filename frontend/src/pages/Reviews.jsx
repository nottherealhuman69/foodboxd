import { useState } from 'react'
import styles from './Reviews.module.css'

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }
const FILTERS = ['All', 'Restaurant', 'Homemade']

export default function Reviews({ entries = [], loading, fetchError, onNavigate, onDelete }) {
  const [filter, setFilter] = useState('All')
  const [sort, setSort] = useState('newest')

  if (loading) return (
    <div className={styles.page}>
      <div className={styles.loadingWrap}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>Loading reviews…</p>
      </div>
    </div>
  )

  if (fetchError) return (
    <div className={styles.page}>
      <div className={styles.errorWrap}>
        <p className={styles.errorText}>{fetchError}</p>
      </div>
    </div>
  )

  const filtered = entries
    .filter(e => filter === 'All' || e.type === filter.toLowerCase())
    .sort((a, b) => {
      if (sort === 'newest') return new Date(b.loggedAt) - new Date(a.loggedAt)
      if (sort === 'oldest') return new Date(a.loggedAt) - new Date(b.loggedAt)
      if (sort === 'highest') return b.rating - a.rating
      if (sort === 'lowest') return a.rating - b.rating
      return 0
    })

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Reviews</h2>
          <p className={styles.sub}>
            {entries.length === 0
              ? 'Your dish reviews will appear here.'
              : `${entries.length} dish${entries.length !== 1 ? 'es' : ''} logged`}
          </p>
        </div>
        {entries.length > 0 && (
          <select
            className={styles.sortSelect}
            value={sort}
            onChange={e => setSort(e.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="highest">Highest rated</option>
            <option value="lowest">Lowest rated</option>
          </select>
        )}
      </div>

      {entries.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M4 6h16M4 11h11M4 16h8" stroke="#4e5272" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="18" cy="17" r="3" stroke="#4e5272" strokeWidth="1.5"/>
              <path d="M20.5 19.5l2 2" stroke="#4e5272" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <p className={styles.emptyText}>No reviews yet</p>
          <button className={styles.ctaBtn} onClick={() => onNavigate('create')}>
            Log your first dish
          </button>
        </div>
      ) : (
        <>
          {/* Filter pills */}
          <div className={styles.filters}>
            {FILTERS.map(f => (
              <button
                key={f}
                className={`${styles.filterBtn} ${filter === f ? styles.filterActive : ''}`}
                onClick={() => setFilter(f)}
              >
                {f}
                {f === 'All' && <span className={styles.filterCount}>{entries.length}</span>}
                {f === 'Restaurant' && <span className={styles.filterCount}>{entries.filter(e => e.type === 'restaurant').length}</span>}
                {f === 'Homemade' && <span className={styles.filterCount}>{entries.filter(e => e.type === 'homemade').length}</span>}
              </button>
            ))}
          </div>

          {filtered.length === 0 ? (
            <p className={styles.noMatch}>No {filter.toLowerCase()} dishes yet.</p>
          ) : (
            <div className={styles.list}>
              {filtered.map(entry => (
                <ReviewCard key={entry.id} entry={entry} onDelete={onDelete} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ReviewCard({ entry, onDelete }) {
  const date = new Date(entry.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })

  return (
    <div className={styles.card}>
      <div className={styles.cardTop}>
        <div className={styles.cardLeft}>
          <span className={styles.dishName}>{entry.dishName}</span>
          {entry.restaurantName && (
            <span className={styles.restaurant}>{entry.restaurantName}</span>
          )}
        </div>
        <div className={styles.cardRight}>
          <span className={styles.typePill} data-type={entry.type}>
            {entry.type === 'homemade' ? '🏠 Homemade' : '🍽 Restaurant'}
          </span>
        </div>
      </div>

      <div className={styles.cardMeta}>
        <Stars rating={entry.rating} />
        <span className={styles.ratingLabel}>{RATING_LABELS[entry.rating]}</span>
        <span className={styles.dot}>·</span>
        <span className={styles.date}>{date}</span>
      </div>

      {entry.review && (
        <p className={styles.reviewText}>{entry.review}</p>
      )}

      {entry.recipe && (
        <details className={styles.recipeDetails}>
          <summary className={styles.recipeSummary}>View recipe</summary>
          <p className={styles.recipeText}>{entry.recipe}</p>
        </details>
      )}
      <div className={styles.cardActions}>
        <button
          className={styles.deleteBtn}
          onClick={() => onDelete(entry.id)}
          title="Delete review"
        >
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <path d="M4 5h12M8 5V3h4v2M6 5l1 11h6l1-11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Delete
        </button>
      </div>
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