import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { normaliseReview, avgRating } from '../utils/reviews'
import { StarRating } from '../components/StarRating'
import { StatGrid, StatCard } from '../components/StatCard'
import FriendButton from '../components/FriendButton'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './UserProfile.module.css'


export default function UserProfile({ userEmail, onBack, onViewUser, onViewReview, onViewList, onViewDish, onViewRestaurant}) {
  const [reviews,      setReviews]      = useState([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState('')
  const [friendStatus, setFriendStatus] = useState(null)

  const [section,        setSection]        = useState('dishes')
  const [friends,        setFriends]        = useState(null)
  const [friendsLoading, setFriendsLoading] = useState(true)
  const [friendsError,   setFriendsError]   = useState('')

  const [lists,        setLists]        = useState(null)
  const [listsLoading, setListsLoading] = useState(true)
  const [listsError,   setListsError]   = useState('')

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

  // New: load this user's friends list whenever the viewed profile changes
  useEffect(() => {
    setFriends(null)
    setFriendsLoading(true)
    setFriendsError('')
    apiFetch(`/api/users/${encodeURIComponent(userEmail)}/friends`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setFriends(data))
      .catch(() => setFriendsError('Could not load friends.'))
      .finally(() => setFriendsLoading(false))
  }, [userEmail])

  useEffect(() => {
    setLists(null)
    setListsLoading(true)
    setListsError('')
    apiFetch(`/api/users/${encodeURIComponent(userEmail)}/lists`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setLists(data))
      .catch(() => setListsError('Could not load lists.'))
      .finally(() => setListsLoading(false))
  }, [userEmail])

  const avg = avgRating(reviews)
  const friendCount = friends ? friends.length : null

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

      <StatGrid cols={6}>
        <StatCard count={reviews.length}                                      label="Dishes logged" onClick={() => setSection('dishes')}  active={section === 'dishes'} />
        <StatCard count={avg}                                                  label="Avg rating" />
        <StatCard count={reviews.filter(r => r.type === 'restaurant').length} label="Restaurant" />
        <StatCard count={reviews.filter(r => r.type === 'homemade').length}   label="Homemade" />
        <StatCard count={friendCount}                                        label="Friends"      onClick={() => setSection('friends')} active={section === 'friends'} />
        <StatCard count={lists ? lists.length : null}                        label="Lists"        onClick={() => setSection('lists')}   active={section === 'lists'} />
      </StatGrid>

      {section === 'dishes' && (
        <>
          <PageState loading={loading} error={error} empty={!loading && !error && reviews.length === 0} emptyTitle="No dishes logged yet" />
          {!loading && !error && reviews.length > 0 && (
            <div>
              <h3 className={shared.sectionTitle}>Diary</h3>
              <div className={styles.reviewList}>
                {reviews.map(r => (
                  <ReviewCard key={r.id} entry={r} onViewReview={onViewReview}
                              onViewDish={onViewDish} onViewRestaurant={onViewRestaurant} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {section === 'friends' && (
        <div className={styles.section}>
          <h3 className={shared.sectionTitle}>Friends</h3>
          <PageState loading={friendsLoading} error={friendsError} />
          {!friendsLoading && !friendsError && friends !== null && friends.length === 0 && (
            <PageState empty emptyTitle="No friends yet" />
          )}
          {!friendsLoading && !friendsError && friends && friends.length > 0 && (
            <div className={styles.friendsList}>
              {friends.map(f => <FriendCard key={f.email} friend={f} onClick={() => onViewUser?.(f.email)} />)}
            </div>
          )}
        </div>
      )}

      {section === 'lists' && (
        <div className={styles.section}>
          <h3 className={shared.sectionTitle}>Public Lists</h3>
          <PageState loading={listsLoading} error={listsError} />
          {!listsLoading && !listsError && lists !== null && lists.length === 0 && (
            <PageState empty emptyTitle="No public lists yet" />
          )}
          {!listsLoading && !listsError && lists && lists.length > 0 && (
            <div className={styles.listsGrid}>
              {lists.map(l => (
                <div
                  key={l.id}
                  className={styles.listCard}
                  style={{ cursor: 'pointer' }}
                  onClick={() => onViewList?.(l)}
                >
                  <p className={styles.listCardName}>{l.name}</p>
                  <p className={styles.itemCount}>{l.item_count ?? 0} item{(l.item_count ?? 0) !== 1 ? 's' : ''}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ReviewCard({ entry, onViewReview, onViewDish, onViewRestaurant }) {
  const date = new Date(entry.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
  return (
    <div
      className={shared.card}
      style={{ cursor: onViewReview ? 'pointer' : 'default' }}
      onClick={() => onViewReview?.(entry.id, 'comments')}
    >
      <div className={shared.cardTop}>
        <div>
          {entry.restaurantName ? (
            <button
              type="button"
              className={styles.dishNameLink}
              onClick={e => { e.stopPropagation(); onViewDish?.(entry.dishName, entry.restaurantName) }}
            >
              {entry.dishName}
            </button>
          ) : (
            <p className={shared.dishName}>{entry.dishName}</p>
          )}
          {entry.restaurantName && (
            <button
              type="button"
              className={styles.restaurantLink}
              onClick={e => { e.stopPropagation(); onViewRestaurant?.(entry.restaurantName) }}
            >
              {entry.restaurantName}
            </button>
          )}
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


function FriendCard({ friend, onClick }) {
  return (
    <div className={styles.friendCard} onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <div className={styles.friendAvatar}>{(friend.username || friend.email || '?')[0].toUpperCase()}</div>
      <div className={styles.friendInfo}>
        <p className={styles.friendName}>@{friend.username || friend.email?.split('@')[0] || 'unknown'}</p>
        <p className={styles.friendMeta}>{friend.review_count ?? 0} dish{friend.review_count !== 1 ? 'es' : ''} logged</p>
      </div>
    </div>
  )
}