import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import { StatGrid, StatCard } from '../components/StatCard'
import PageState from '../components/PageState'
import { avgRating, RATING_LABELS } from '../utils/reviews'
import shared from '../components/shared.module.css'
import styles from './Profile.module.css'

export default function Profile({ entries = [], loading, fetchError, onNavigate }) {
  const [friendCount, setFriendCount] = useState(null)

  useEffect(() => {
    apiFetch('/api/friends')
      .then(r => r.ok ? r.json() : null)
      .then(data => setFriendCount(data ? data.length : 0))
      .catch(() => setFriendCount(0))
  }, [])

  if (loading || fetchError) return (
    <div className={shared.page}>
      <PageState loading={loading} error={fetchError} />
    </div>
  )

  const avg = avgRating(entries)

  return (
    <div className={shared.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Profile</h2>
        <p className={styles.sub}>Your food diary at a glance.</p>
      </div>

      <StatGrid cols={5}>
        <StatCard count={entries.length}                                   label="Dishes logged" />
        <StatCard count={avg}                                              label="Avg rating" />
        <StatCard count={entries.filter(e => e.type === 'restaurant').length} label="Restaurant" />
        <StatCard count={entries.filter(e => e.type === 'homemade').length}   label="Homemade" />
        <StatCard count={friendCount}                                      label="Friends" />
      </StatGrid>

      {entries.length === 0 ? (
        <PageState
          empty
          emptyTitle="No dishes logged yet"
          emptyHint="Start building your food diary"
          emptyAction={<button className={shared.ctaBtn} onClick={() => onNavigate('create')}>Log your first dish</button>}
        />
      ) : (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h3 className={shared.sectionTitle}>Recent dishes</h3>
            <button className={styles.seeAll} onClick={() => onNavigate('reviews')}>See all →</button>
          </div>
          <div className={styles.diaryList}>
            {entries.slice(0, 5).map(entry => (
              <DiaryCard key={entry.id} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function DiaryCard({ entry }) {
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
