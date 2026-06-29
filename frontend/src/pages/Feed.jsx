import { useCallback } from 'react'
import { useFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import PageState from '../components/PageState'
import { usernameFrom } from '../utils/reviews'
import shared from '../components/shared.module.css'
import styles from './Feed.module.css'

function timeAgo(iso) {
  const diff  = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins  < 1)  return 'just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days  < 7)  return `${days}d ago`
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export default function Feed({ onViewDish, onViewRestaurant, onViewUser }) {
  const { data: items, loading, error } = useFetch('/api/feed')

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Feed</h2>
        <p className={styles.sub}>Latest dishes from people you follow</p>
      </div>

      <PageState
        loading={loading}
        error={error}
        empty={!loading && !error && (!items || items.length === 0)}
        emptyTitle="Nothing here yet"
        emptyHint="Follow people from the Search page to see their dishes here"
      />

      {!loading && !error && items?.length > 0 && (
        <div className={styles.feed}>
          {items.map(item => (
            <FeedCard
              key={item.id}
              item={item}
              onViewDish={onViewDish}
              onViewRestaurant={onViewRestaurant}
              onViewUser={onViewUser}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FeedCard({ item, onViewDish, onViewRestaurant, onViewUser }) {
  const username = usernameFrom(item.username || item.user_email)
  return (
    <div className={styles.card}>
      <div className={styles.avatarCol}>
        <button className={styles.avatarBtn} onClick={() => onViewUser?.(item.user_email)}>
          {username.charAt(0).toUpperCase()}
        </button>
        <div className={styles.timelineLine} />
      </div>
      <div className={styles.content}>
        <div className={styles.cardHeader}>
          <div className={styles.meta}>
            <button className={styles.usernameBtn} onClick={() => onViewUser?.(item.user_email)}>
              @{username}
            </button>
            <span className={styles.dot}>·</span>
            <span className={styles.time}>{timeAgo(item.logged_at)}</span>
          </div>
          <span className={shared.typePill} data-type={item.type}>
            {item.type === 'homemade' ? '🏠 Homemade' : '🍽️ Restaurant'}
          </span>
        </div>
        <div className={styles.dishRow}>
          <button
            className={styles.dishName}
            onClick={() => item.restaurant_name && onViewDish?.(item.dish_name, item.restaurant_name)}
            disabled={!item.restaurant_name}
          >
            {item.dish_name}
          </button>
          {item.restaurant_name && (
            <button className={styles.restaurantLink} onClick={() => onViewRestaurant?.(item.restaurant_name)}>
              at {item.restaurant_name}
            </button>
          )}
        </div>
        <div className={styles.ratingRow}>
          <StarRating rating={item.rating} showLabel />
        </div>
        {item.review && <p className={styles.reviewText}>{item.review}</p>}
      </div>
    </div>
  )
}
