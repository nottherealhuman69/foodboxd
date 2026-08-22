import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import { StatGrid, StatCard } from '../components/StatCard'
import PageState from '../components/PageState'
import { avgRating } from '../utils/reviews'
import shared from '../components/shared.module.css'
import styles from './Profile.module.css'


export default function Profile({ entries = [], loading, fetchError, onNavigate, onViewReview, onViewUser, onViewDish, onViewRestaurant }) {
  const [section, setSection] = useState('dishes')
  const [friends, setFriends] = useState(null)
  const [friendsLoading, setFriendsLoading] = useState(true)
  const [friendsError, setFriendsError] = useState('')
  const [lists, setLists] = useState(null)
  const [listsLoading, setListsLoading] = useState(true)
  const [listsError, setListsError] = useState('')
  const cardProps = { onViewReview, onViewDish, onViewRestaurant }
  

  useEffect(() => {
    apiFetch('/api/friends')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setFriends(data))
      .catch(() => setFriendsError('Could not load friends.'))
      .finally(() => setFriendsLoading(false))
  }, [])

  useEffect(() => {
  apiFetch('/api/lists')
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(data => setLists(data))
    .catch(() => setListsError('Could not load your lists.'))
    .finally(() => setListsLoading(false))
}, [])

  const friendCount = friends ? friends.length : null

  if (loading || fetchError) return (
    <div className={shared.page}>
      <PageState loading={loading} error={fetchError} />
    </div>
  )

  const avg = avgRating(entries)
  const restaurantEntries = entries.filter(e => e.type === 'restaurant')
  const homemadeEntries   = entries.filter(e => e.type === 'homemade')

  return (
    <div className={shared.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Profile</h2>
        <p className={styles.sub}>Your food diary at a glance.</p>
      </div>

      <StatGrid cols={6}>
        <StatCard count={entries.length}        label="Dishes logged" onClick={() => setSection('dishes')}     active={section === 'dishes'} />
        <StatCard count={avg}                   label="Avg rating" />
        <StatCard count={restaurantEntries.length} label="Restaurant"  onClick={() => setSection('restaurant')} active={section === 'restaurant'} />
        <StatCard count={homemadeEntries.length}   label="Homemade"    onClick={() => setSection('homemade')}   active={section === 'homemade'} />
        <StatCard count={friendCount}           label="Friends"      onClick={() => setSection('friends')}    active={section === 'friends'} />
        <StatCard count={lists ? lists.length : null} label="Lists"   onClick={() => setSection('lists')}      active={section === 'lists'} />
      </StatGrid>

      {section === 'dishes' && (
        entries.length === 0 ? (
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
              {entries.slice(0, 5).map(entry => <DiaryCard key={entry.id} entry={entry} {...cardProps}/>)}
            </div>
          </div>
        )
      )}

      {section === 'restaurant' && (
        restaurantEntries.length === 0 ? (
          <PageState
            empty
            emptyTitle="No restaurant dishes logged"
            emptyHint="Log a dish from a restaurant to see it here"
            emptyAction={<button className={shared.ctaBtn} onClick={() => onNavigate('create')}>Log a dish</button>}
          />
        ) : (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <h3 className={shared.sectionTitle}>Restaurant dishes</h3>
              <button className={styles.seeAll} onClick={() => onNavigate('reviews', 'Restaurant')}>See all →</button>
            </div>
            <div className={styles.diaryList}>
              {restaurantEntries.map(entry => <DiaryCard key={entry.id} entry={entry} {...cardProps} />)}
            </div>
          </div>
        )
      )}

      {section === 'homemade' && (
        homemadeEntries.length === 0 ? (
          <PageState
            empty
            emptyTitle="No homemade dishes logged"
            emptyHint="Log something you cooked at home"
            emptyAction={<button className={shared.ctaBtn} onClick={() => onNavigate('create')}>Log a dish</button>}
          />
        ) : (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <h3 className={shared.sectionTitle}>Homemade dishes</h3>
              <button className={styles.seeAll} onClick={() => onNavigate('reviews', 'Homemade')}>See all →</button>
            </div>
            <div className={styles.diaryList}>
              {homemadeEntries.map(entry => <DiaryCard key={entry.id} entry={entry} {...cardProps} />)}
            </div>
          </div>
        )
      )}


      {section === 'friends' && (
        <div className={styles.section}>
          <h3 className={shared.sectionTitle}>Friends</h3>
          <PageState loading={friendsLoading} error={friendsError} />
          {!friendsLoading && !friendsError && friends !== null && friends.length === 0 && (
            <PageState
              empty
              emptyTitle="No friends yet"
              emptyHint="Search for people and send friend requests"
              emptyAction={<button className={shared.ctaBtn} onClick={() => onNavigate('search')}>Find friends</button>}
            />
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
        <h3 className={shared.sectionTitle}>My Lists</h3>
        <PageState loading={listsLoading} error={listsError} />
        {!listsLoading && !listsError && lists !== null && lists.length === 0 && (
          <PageState empty emptyTitle="No lists yet" emptyHint='Create one from the Trylist tab — like "Best Biryanis in Hyderabad".' />
        )}
        {!listsLoading && !listsError && lists && lists.length > 0 && (
          <div className={styles.listsGrid}>
            {lists.map(l => (
              <div key={l.id} className={styles.listCard} onClick={() => onNavigate?.('trylist')}>
                <div className={styles.listCardTop}>
                  <p className={styles.listCardName}>{l.name}</p>
                  <span className={`${styles.visibilityPill} ${l.is_public ? styles.publicPill : styles.privatePill}`}>
                    {l.is_public ? 'Public' : 'Private'}
                  </span>
                </div>
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

function DiaryCard({ entry, onViewReview, onViewDish, onViewRestaurant }) {
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
    <div
      className={styles.friendCard}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className={styles.friendAvatar}>{friend.username?.[0]?.toUpperCase()}</div>
      <div className={styles.friendInfo}>
        <p className={styles.friendName}>@{friend.username}</p>
        <p className={styles.friendMeta}>
          {friend.review_count} dish{friend.review_count !== 1 ? 'es' : ''} logged
        </p>
      </div>
    </div>
  )
}