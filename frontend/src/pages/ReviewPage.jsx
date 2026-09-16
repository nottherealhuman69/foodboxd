import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarRating, StarPicker } from '../components/StarRating'
import PageState from '../components/PageState'
import CommentThread from '../components/CommentThread'
import TagPicker, { TaggedWith } from '../components/TagPicker'
import { RATING_LABELS } from '../utils/reviews'
import ShareButton from '../components/ShareButton'
import { reviewUrl } from '../utils/links'
import shared from '../components/shared.module.css'
import styles from './ReviewPage.module.css'

const TABS = [
  { id: 'likes',    label: 'Likes' },
  { id: 'comments', label: 'Comments' },
]

export default function ReviewPage({ reviewId, initialTab = 'comments', onBack, onViewUser, onViewDish, onViewRestaurant, onViewMeal }) {
  const [review,  setReview]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [tab,     setTab]     = useState(initialTab)
  const [editing, setEditing] = useState(false)

  const [likes,        setLikes]        = useState(null)
  const [likesLoading, setLikesLoading] = useState(false)

  const [comments,        setComments]        = useState(null)
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [commentText,     setCommentText]     = useState('')
  const [posting,         setPosting]         = useState(false)

  const myEmail = localStorage.getItem('email')

  async function loadReview() {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/detail`)
      if (!res.ok) throw new Error()
      setReview(await res.json())
    } catch {
      setError('Could not load this review.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadReview() }, [reviewId])

  // A dish review that belongs to a meal has no page of its own —
  // the meal owns the conversation, so bounce there.
  useEffect(() => {
    if (review?.meal_id != null) {
      onViewMeal?.(review.meal_id, initialTab)
    }
  }, [review])

  const loadLikes = async () => {
    setLikesLoading(true)
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/likes`)
      if (!res.ok) throw new Error()
      setLikes(await res.json())
    } catch {
      setLikes([])
    } finally {
      setLikesLoading(false)
    }
  }

  const loadComments = async () => {
    setCommentsLoading(true)
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/comments`)
      if (!res.ok) throw new Error()
      setComments(await res.json())
    } catch {
      setComments([])
    } finally {
      setCommentsLoading(false)
    }
  }

  useEffect(() => {
    if (tab === 'likes' && likes === null) loadLikes()
    if (tab === 'comments' && comments === null) loadComments()
  }, [tab])

  const toggleLike = async () => {
    const prev = { liked: review.user_liked, count: review.like_count }
    setReview(r => ({ ...r, user_liked: !r.user_liked, like_count: r.like_count + (r.user_liked ? -1 : 1) }))
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/like`, { method: 'POST' })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setReview(r => ({ ...r, user_liked: data.liked, like_count: data.like_count }))
      setLikes(null) // refresh likers list next time it's opened
    } catch {
      setReview(r => ({ ...r, user_liked: prev.liked, like_count: prev.count }))
    }
  }

  const postComment = async (e) => {
    e.preventDefault()
    if (!commentText.trim() || posting) return
    setPosting(true)
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: commentText.trim(), parent_id: null }),
      })
      if (!res.ok) throw new Error()
      const newComment = await res.json()
      setComments(prev => [...(prev || []), newComment])
      setReview(r => ({ ...r, comment_count: r.comment_count + 1 }))
      setCommentText('')
    } catch {
      // silently fail
    } finally {
      setPosting(false)
    }
  }

  if (loading || error) {
    return (
      <div className={shared.page}>
        <button className={shared.backBtn} onClick={onBack}>← Back</button>
        <PageState loading={loading} error={error} />
      </div>
    )
  }

  if (editing) {
    return (
      <div className={shared.page}>
        <button className={shared.backBtn} onClick={() => setEditing(false)}>← Cancel</button>
        <EditReviewForm
          review={review}
          onCancel={() => setEditing(false)}
          onSaved={() => { setEditing(false); loadReview() }}
        />
      </div>
    )
  }

  const date = new Date(review.logged_at).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
  const isOwner = review.user_email === myEmail

  return (
    <div className={shared.page}>
      <button className={shared.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back
      </button>

      <div className={styles.reviewHeader}>
        <button className={styles.avatarBtn} onClick={() => onViewUser?.(review.user_email)}>
          {review.username.charAt(0).toUpperCase()}
        </button>
        <div>
          <button className={styles.usernameBtn} onClick={() => onViewUser?.(review.user_email)}>
            @{review.username}
          </button>
          <p className={styles.date}>{date}</p>
        </div>
        <span className={shared.typePill} data-type={review.type}>
          {review.type === 'homemade' ? '🏠 Homemade' : '🍽️ Restaurant'}
        </span>
      </div>

            <h2
        className={styles.dishName}
        style={{ cursor: (onViewDish && review.restaurant_name) ? 'pointer' : 'default' }}
        onClick={() => review.restaurant_name && onViewDish?.(review.dish_name, review.restaurant_name)}
      >
        {review.dish_name}
      </h2>
        {review.restaurant_name && (
          <p
            className={styles.restaurant}
            style={{ cursor: onViewRestaurant ? 'pointer' : 'default' }}
            onClick={() => onViewRestaurant?.(review.restaurant_name)}
          >
            {review.restaurant_name}
          </p>
        )}

      <div className={styles.ratingRow}>
        <StarRating rating={review.rating} showLabel />
      </div>

      {review.type === 'homemade' && review.recipe_owner && (
        <p className={styles.date} style={{ marginTop: 8 }}>
          Recipe by{' '}
          <button className={styles.usernameBtn} onClick={() => onViewUser?.(review.recipe_owner_email)}>
            @{review.recipe_owner}
          </button>
        </p>
      )}

      {review.tagged?.length > 0 && (
        <p style={{ marginTop: 8 }}>
          <TaggedWith tagged={review.tagged} onViewUser={onViewUser} />
        </p>
      )}

      {review.review && <p className={styles.reviewText}>{review.review}</p>}
      {review.recipe && (
        <details className={styles.recipeDetails}>
          <summary>View recipe</summary>
          <p>{review.recipe}</p>
        </details>
      )}

      <div className={styles.pageActions}>
        <button className={`${styles.likeBtn} ${review.user_liked ? styles.likeBtnActive : ''}`} onClick={toggleLike}>
          {review.user_liked ? '❤️' : '🤍'} {review.like_count}
        </button>
        <ShareButton url={reviewUrl(review.id)} />
        {isOwner && (
          <button className={styles.editBtn} onClick={() => setEditing(true)}>Edit</button>
        )}
      </div>

      <div className={styles.tabs}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${styles.tabBtn} ${tab === t.id ? styles.tabActive : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            <span className={styles.tabCount}>
              {t.id === 'likes' ? review.like_count : review.comment_count}
            </span>
          </button>
        ))}
      </div>

      {tab === 'likes' && (
        <div className={styles.likesList}>
          {likesLoading && <p className={styles.loadingText}>Loading…</p>}
          {!likesLoading && likes?.length === 0 && <p className={styles.emptyText}>No likes yet.</p>}
          {!likesLoading && likes?.map(l => (
            <button key={l.user_email} className={styles.likeRow} onClick={() => onViewUser?.(l.user_email)}>
              <span className={styles.likeAvatar}>{l.username.charAt(0).toUpperCase()}</span>
              <span className={styles.likeUsername}>@{l.username}</span>
            </button>
          ))}
        </div>
      )}

      {tab === 'comments' && (
        <div className={styles.commentsSection}>
          {commentsLoading && <p className={styles.loadingText}>Loading…</p>}
          {!commentsLoading && comments?.length === 0 && <p className={styles.emptyText}>No comments yet.</p>}
          {!commentsLoading && comments?.length > 0 && (
            <CommentThread
              comments={comments}
              setComments={setComments}
              commentType="review"
              basePath={`/api/reviews/${reviewId}/comments`}
              myEmail={myEmail}
              onViewUser={onViewUser}
              onCountChange={(delta) => setReview(r => ({ ...r, comment_count: Math.max(0, r.comment_count + delta) }))}
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
  )
}

function EditReviewForm({ review, onCancel, onSaved }) {
  const [dishName,       setDishName]       = useState(review.dish_name || '')
  const [restaurantName, setRestaurantName] = useState(review.restaurant_name || '')
  const [recipe,         setRecipe]         = useState(review.recipe || '')
  const [rating,         setRating]         = useState(review.rating || 0)
  const [hover,          setHover]          = useState(0)
  const [text,           setText]           = useState(review.review || '')
  const [taggedEmails,   setTaggedEmails]   = useState((review.tagged || []).map(t => t.email))
  const [friends,        setFriends]        = useState([])
  const [saving,         setSaving]         = useState(false)
  const [error,          setError]          = useState('')

  useEffect(() => {
    apiFetch('/api/friends').then(r => r.ok ? r.json() : []).then(setFriends).catch(() => {})
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    if (!dishName.trim() || rating === 0) return
    setSaving(true)
    setError('')
    try {
      const res = await apiFetch(`/api/reviews/${review.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          dish_name:          dishName.trim(),
          type:               review.type,
          restaurant_name:    restaurantName.trim() || null,
          recipe:             review.type === 'homemade' ? (recipe.trim() || null) : null,
          recipe_owner_email: review.recipe_owner_email || null,
          rating,
          review:             text.trim() || null,
          tagged_emails:      taggedEmails,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Could not save changes.')
      }
      onSaved()
    } catch (err) {
      setError(err.message || 'Could not save changes.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className={styles.editForm} onSubmit={submit}>
      <h2 className={styles.dishName}>Edit review</h2>

      <label className={styles.editLabel}>Dish name</label>
      <input className={styles.editInput} value={dishName} onChange={e => setDishName(e.target.value)} required />

      <label className={styles.editLabel}>Restaurant {review.type === 'homemade' && <span className={styles.date}>(optional)</span>}</label>
      <input className={styles.editInput} value={restaurantName} onChange={e => setRestaurantName(e.target.value)} />

      {review.type === 'homemade' && (
        <>
          <label className={styles.editLabel}>Recipe</label>
          <textarea className={`${styles.editInput} ${styles.editTextarea}`} rows={3} value={recipe} onChange={e => setRecipe(e.target.value)} />
        </>
      )}

      <label className={styles.editLabel}>Rating</label>
      <div className={styles.ratingRow}>
        <StarPicker value={rating} hoverValue={hover} onHover={setHover} onLeave={() => setHover(0)} onChange={setRating} size={26} />
        {rating > 0 && <span className={styles.ratingLabelInline}>{RATING_LABELS[Math.round(rating)]}</span>}
      </div>

      <label className={styles.editLabel}>Review</label>
      <textarea className={`${styles.editInput} ${styles.editTextarea}`} rows={5} maxLength={1000} value={text} onChange={e => setText(e.target.value)} />

      <label className={styles.editLabel}>Who were you with?</label>
      <TagPicker options={friends} value={taggedEmails} onChange={setTaggedEmails} />

      {error && <p className={styles.emptyText} style={{ color: '#f87171' }}>{error}</p>}

      <div className={styles.editActions}>
        <button type="submit" className={styles.commentSubmit} disabled={saving || !dishName.trim() || rating === 0}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" className={styles.editBtn} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
