import { useState } from 'react'
import { useFetch, apiFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import PageState from '../components/PageState'
import { usernameFrom } from '../utils/reviews'
import shared from '../components/shared.module.css'
import styles from './Feed.module.css'
import CommentThread from '../components/CommentThread'
import { TaggedWith } from '../components/TagPicker'

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

export default function Feed({ onViewDish, onViewRestaurant, onViewUser, onViewReview, onViewMeal }) {
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
              key={`${item.kind}-${item.id}`}
              item={item}
              onViewDish={onViewDish}
              onViewRestaurant={onViewRestaurant}
              onViewUser={onViewUser}
              onViewReview={onViewReview}
              onViewMeal={onViewMeal}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FeedCard({ item, onViewDish, onViewRestaurant, onViewUser, onViewReview, onViewMeal }) {
  const isMeal   = item.kind === 'meal'
  const base     = isMeal ? `/api/meals/${item.id}` : `/api/reviews/${item.id}`
  const username = usernameFrom(item.username || item.user_email)
  const myEmail  = localStorage.getItem('email')

  const [liked,     setLiked]     = useState(item.user_liked || false)
  const [likeCount, setLikeCount] = useState(item.like_count || 0)
  const [liking,    setLiking]    = useState(false)

  const [showComments,    setShowComments]    = useState(false)
  const [comments,        setComments]        = useState(null)
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [commentCount,    setCommentCount]    = useState(item.comment_count || 0)
  const [commentText,     setCommentText]     = useState('')
  const [posting,         setPosting]         = useState(false)

  const toggleLike = async () => {
    if (liking) return
    setLiking(true)
    const prevLiked = liked
    const prevCount = likeCount
    setLiked(!liked)
    setLikeCount(liked ? likeCount - 1 : likeCount + 1)
    try {
      const res = await apiFetch(`${base}/like`, { method: 'POST' })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setLiked(data.liked)
      setLikeCount(data.like_count)
    } catch {
      setLiked(prevLiked)
      setLikeCount(prevCount)
    } finally {
      setLiking(false)
    }
  }

  const loadComments = async () => {
    setCommentsLoading(true)
    try {
      const res = await apiFetch(`${base}/comments`)
      if (!res.ok) throw new Error()
      setComments(await res.json())
    } catch {
      setComments([])
    } finally {
      setCommentsLoading(false)
    }
  }

  const handleToggleComments = () => {
    const next = !showComments
    setShowComments(next)
    if (next && comments === null) loadComments()
  }

  const postComment = async (e) => {
    e.preventDefault()
    if (!commentText.trim() || posting) return
    setPosting(true)
    try {
      const res = await apiFetch(`${base}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: commentText.trim(), parent_id: null }),
      })
      if (!res.ok) throw new Error()
      const newComment = await res.json()
      setComments(prev => [...(prev || []), newComment])
      setCommentCount(c => c + 1)
      setCommentText('')
    } catch {
      // silently fail
    } finally {
      setPosting(false)
    }
  }

  const openPost = () => isMeal
    ? onViewMeal?.(item.id, 'comments')
    : onViewReview?.(item.id, 'comments')

  return (
    <div className={styles.card} style={{ cursor: 'pointer' }} onClick={openPost}>
      <div className={styles.avatarCol}>
        <button
          className={styles.avatarBtn}
          onClick={(e) => { e.stopPropagation(); onViewUser?.(item.user_email) }}
        >
          {username.charAt(0).toUpperCase()}
        </button>
        <div className={styles.timelineLine} />
      </div>

      <div className={styles.content}>
        <div className={styles.cardHeader}>
          <div className={styles.meta}>
            <button
              className={styles.usernameBtn}
              onClick={(e) => { e.stopPropagation(); onViewUser?.(item.user_email) }}
            >
              @{username}
            </button>
            <span className={styles.dot}>·</span>
            <span className={styles.time}>{timeAgo(item.logged_at)}</span>
          </div>
          <span className={shared.typePill} data-type={isMeal ? 'meal' : item.type}>
            {isMeal ? '🍽️ Meal' : item.type === 'homemade' ? '🏠 Homemade' : '🍽️ Restaurant'}
          </span>
        </div>

        <div className={styles.dishRow}>
          <button
            className={styles.dishName}
            onClick={(e) => {
              e.stopPropagation()
              if (isMeal) onViewMeal?.(item.id, 'comments')
              else if (item.type === 'homemade') onViewDish?.(item.dish_name, null, item.recipe_owner_email || item.user_email)
              else if (item.restaurant_name) onViewDish?.(item.dish_name, item.restaurant_name)
            }}
            disabled={!isMeal && item.type !== 'homemade' && !item.restaurant_name}
          >
            {isMeal ? (item.title || 'Meal') : item.dish_name}
          </button>
          {item.restaurant_name && (
            <button
              className={styles.restaurantLink}
              onClick={(e) => { e.stopPropagation(); onViewRestaurant?.(item.restaurant_name) }}
            >
              at {item.restaurant_name}
            </button>
          )}
        </div>

        <div className={styles.ratingRow}>
          <StarRating rating={item.rating} showLabel />
        </div>

        {item.tagged?.length > 0 && (
          <div style={{ marginBottom: 6 }} onClick={(e) => e.stopPropagation()}>
            <TaggedWith tagged={item.tagged} onViewUser={onViewUser} />
          </div>
        )}

        {item.review && <p className={styles.reviewText}>{item.review}</p>}

        {isMeal && item.dishes?.length > 0 && (
          <ul className={styles.mealDishes}>
            {item.dishes.map(d => (
              <li key={d.id} className={styles.mealDish}>
                <button
                  className={styles.mealDishName}
                  onClick={(e) => { e.stopPropagation(); onViewDish?.(d.dish_name, item.restaurant_name) }}
                >
                  {d.dish_name}
                </button>
                <StarRating rating={d.rating} size={12} />
              </li>
            ))}
          </ul>
        )}

        <div className={styles.actions} onClick={(e) => e.stopPropagation()}>
          <button className={`${styles.actionBtn} ${liked ? styles.actionLiked : ''}`} onClick={toggleLike}>
            <HeartIcon filled={liked} />
            {likeCount > 0 && <span>{likeCount}</span>}
          </button>
          <button className={`${styles.actionBtn} ${showComments ? styles.actionActive : ''}`} onClick={handleToggleComments}>
            <CommentIcon />
            {commentCount > 0 && <span>{commentCount}</span>}
          </button>
        </div>

        {showComments && (
          <div className={styles.commentsSection} onClick={(e) => e.stopPropagation()}>
            {commentsLoading && <p className={styles.commentsLoading}>Loading…</p>}
            {!commentsLoading && comments && comments.length > 0 && (
              <CommentThread
                comments={comments}
                setComments={setComments}
                commentType={isMeal ? 'meal' : 'review'}
                basePath={`${base}/comments`}
                myEmail={myEmail}
                onViewUser={onViewUser}
                onCountChange={(delta) => setCommentCount(c => Math.max(0, c + delta))}
              />
            )}
            <form className={styles.commentForm} onSubmit={postComment}>
              <input
                className={styles.commentInput}
                placeholder="Add a comment…"
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                maxLength={500}
              />
              <button type="submit" className={styles.commentSubmit} disabled={!commentText.trim() || posting}>
                {posting ? '…' : 'Post'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}

function HeartIcon({ filled }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'}>
      <path d="M12 20s-7-4.35-7-10a4 4 0 0 1 7-2.65A4 4 0 0 1 19 10c0 5.65-7 10-7 10z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

function CommentIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M21 12a8 8 0 0 1-11.6 7.14L4 20l1-4.4A8 8 0 1 1 21 12z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}