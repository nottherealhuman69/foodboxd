import { useState } from 'react'
import { StarRating } from '../components/StarRating'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Reviews.module.css'

const FILTERS = ['All', 'Restaurant', 'Homemade']

export default function Reviews({ entries = [], loading, fetchError, onNavigate, onDelete }) {
  const [filter, setFilter] = useState('All')
  const [sort,   setSort]   = useState('newest')

  if (loading || fetchError) return (
    <div className={shared.page}>
      <PageState loading={loading} error={fetchError} />
    </div>
  )

  const filtered = entries
    .filter(e => filter === 'All' || e.type === filter.toLowerCase())
    .sort((a, b) => {
      if (sort === 'newest')  return new Date(b.loggedAt) - new Date(a.loggedAt)
      if (sort === 'oldest')  return new Date(a.loggedAt) - new Date(b.loggedAt)
      if (sort === 'highest') return b.rating - a.rating
      if (sort === 'lowest')  return a.rating - b.rating
      return 0
    })

  return (
    <div className={shared.page}>
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
          <select className={styles.sortSelect} value={sort} onChange={e => setSort(e.target.value)}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="highest">Highest rated</option>
            <option value="lowest">Lowest rated</option>
          </select>
        )}
      </div>

      {entries.length === 0 ? (
        <PageState
          empty
          emptyTitle="No reviews yet"
          emptyAction={<button className={shared.ctaBtn} onClick={() => onNavigate('create')}>Log your first dish</button>}
        />
      ) : (
        <>
          <div className={styles.filters}>
            {FILTERS.map(f => (
              <button
                key={f}
                className={`${styles.filterBtn} ${filter === f ? styles.filterActive : ''}`}
                onClick={() => setFilter(f)}
              >
                {f}
                <span className={styles.filterCount}>
                  {f === 'All'        ? entries.length
                  : f === 'Restaurant' ? entries.filter(e => e.type === 'restaurant').length
                  :                     entries.filter(e => e.type === 'homemade').length}
                </span>
              </button>
            ))}
          </div>
          {filtered.length === 0
            ? <p className={styles.noMatch}>No {filter.toLowerCase()} dishes yet.</p>
            : <div className={styles.list}>{filtered.map(e => <ReviewCard key={e.id} entry={e} onDelete={onDelete} />)}</div>
          }
        </>
      )}
    </div>
  )
}

function ReviewCard({ entry, onDelete }) {
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
      {entry.recipe && (
        <details className={styles.recipeDetails}>
          <summary className={styles.recipeSummary}>View recipe</summary>
          <p className={styles.recipeText}>{entry.recipe}</p>
        </details>
      )}
      <div className={styles.cardActions}>
        <button className={styles.deleteBtn} onClick={() => onDelete(entry.id)} title="Delete review">
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
            <path d="M4 5h12M8 5V3h4v2M6 5l1 11h6l1-11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Delete
        </button>
      </div>
    </div>
  )
}
