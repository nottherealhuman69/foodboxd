import styles from './Profile.module.css'

const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

export default function Profile({ entries = [], loading, fetchError, onNavigate }) {
  const avgRating = entries.length
    ? (entries.reduce((s, e) => s + e.rating, 0) / entries.length).toFixed(1)
    : null

  if (loading) return (
    <div className={styles.page}>
      <div className={styles.loadingWrap}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>Loading your diary…</p>
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

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Profile</h2>
        <p className={styles.sub}>Your food diary at a glance.</p>
      </div>

      {/* Stats row */}
      <div className={styles.statsRow}>
        <div className={styles.statCard}>
          <span className={styles.statCount}>{entries.length}</span>
          <span className={styles.statLabel}>Dishes logged</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statCount}>{avgRating ?? '—'}</span>
          <span className={styles.statLabel}>Avg rating</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statCount}>{entries.filter(e => e.type === 'restaurant').length}</span>
          <span className={styles.statLabel}>Restaurant</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statCount}>{entries.filter(e => e.type === 'homemade').length}</span>
          <span className={styles.statLabel}>Homemade</span>
        </div>
      </div>

      {/* Diary section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Recent diary</h3>
          {entries.length > 0 && (
            <button className={styles.seeAll} onClick={() => onNavigate('reviews')}>
              See all →
            </button>
          )}
        </div>

        {entries.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <path d="M12 2a9 9 0 100 18A9 9 0 0012 2z" stroke="#4e5272" strokeWidth="1.5"/>
                <path d="M8 12s1.5 2 4 2 4-2 4-2" stroke="#4e5272" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M9 9h.01M15 9h.01" stroke="#4e5272" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <p className={styles.emptyText}>No dishes logged yet</p>
            <button className={styles.ctaBtn} onClick={() => onNavigate('create')}>
              Log your first dish
            </button>
          </div>
        ) : (
          <div className={styles.diaryList}>
            {entries.slice(0, 5).map(entry => (
              <DiaryCard key={entry.id} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DiaryCard({ entry }) {
  const date = new Date(entry.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })

  return (
    <div className={styles.diaryCard}>
      <div className={styles.diaryMain}>
        <div className={styles.diaryTop}>
          <span className={styles.dishName}>{entry.dishName}</span>
          <span className={styles.typePill} data-type={entry.type}>
            {entry.type === 'homemade' ? '🏠 Homemade' : '🍽 Restaurant'}
          </span>
        </div>
        {entry.restaurantName && (
          <span className={styles.restaurant}>{entry.restaurantName}</span>
        )}
        <div className={styles.diaryMeta}>
          <Stars rating={entry.rating} />
          <span className={styles.diaryDate}>{date}</span>
        </div>
        {entry.review && (
          <p className={styles.reviewSnippet}>{entry.review}</p>
        )}
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