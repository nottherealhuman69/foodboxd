import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarRating } from '../components/StarRating'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './ReviewPage.module.css'

const TABS = [
  { id: 'likes',    label: 'Likes' },
  { id: 'comments', label: 'Comments' },
]

export default function MealPage({ mealId, initialTab = 'comments', onBack, onViewUser, onViewDish, onViewRestaurant }) {
  const [meal,    setMeal]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [tab,     setTab]     = useState(initialTab)

  const [likes,        setLikes]        = useState(null)
  const [likesLoading, setLikesLoading] = useState(false)

  const [comments,        setComments]        = useState(null)
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [commentText,     setCommentText]     = useState('')
  const [posting,         setPosting]         = useState(false)

  const myEmail = localStorage.getItem('email')

  useEffect(() => {
    async function load() {
      setLoading(true); setError('')
      try {
        const res = await apiFetch(`/api/meals/${mealId}/detail`)
        if (!res.ok) throw new Error()
        setMeal(await res.json())
      } catch {
        setError('Could not load this meal.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [mealId])

  useEffect(() => {
    if (tab === 'likes' && likes === null) {
      setLikesLoading(true)
      apiFetch(`/api/meals/${mealId}/likes`)
        .then(r => r.ok ? r.json() : [])
        .then(setLikes).catch(() => setLikes([]))
        .finally(() => setLikesLoading(false))
    }
    if (tab === 'comments' && comments === null) {
      setCommentsLoading(true)
      apiFetch(`/api/meals/${mealId}/comments`)
        .then(r => r.ok ? r.json() : [])
        .then(setComments).catch(() => setComments([]))
        .finally(() => setCommentsLoading(false))
    }
  }, [tab])

  const toggleLike = async () => {
    const res = await apiFetch(`/api/meals/${mealId}/like`, { method: 'POST' })
    if (!res.ok) return
    const { liked, like_count } = await res.json()
    setMeal(m => ({ ...m, user_liked: liked, like_count }))
    setLikes(null)
  }

  const postComment = async (e) => {
    e.preventDefault()
    if (!commentText.trim() || posting) return
    setPosting(true)
    try {
      const res = await apiFetch(`/api/meals/${mealId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: commentText.trim() }),
      })
      if (!res.ok) throw new Error()
      const added = await res.json()
      setComments(prev => [...(prev || []), added])
      setMeal(m => ({ ...m, comment_count: m.comment_count + 1 }))
      setCommentText('')
    } catch { /* silently fail */ }
    finally { setPosting(false) }
  }

  const deleteComment = async (commentId) => {
    const res = await apiFetch(`/api/meals/${mealId}/comments/${commentId}`, { method: 'DELETE' })
    if (!res.ok) return
    setComments(prev => prev.filter(c => c.id !== commentId))
    setMeal(m => ({ ...m, comment_count: m.comment_count - 1 }))
  }

  if (loading || error) return (
    <div className={shared.page}>
      <button className={shared.backBtn} onClick={onBack}>← Back</button>
      <PageState loading={loading} error={error} />
    </div>
  )

  const date = new Date(meal.logged_at).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })

  return (
    <div className={shared.page}>
      <button className={shared.backBtn} onClick={onBack}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back
      </button>

      <div className={styles.reviewHeader}>
        <button className={styles.avatarBtn} onClick={() => onViewUser?.(meal.user_email)}>
          {meal.username.charAt(0).toUpperCase()}
        </button>
        <div>
          <button className={styles.usernameBtn} onClick={() => onViewUser?.(meal.user_email)}>
            @{meal.username}
          </button>
          <p className={styles.date}>{date}</p>
        </div>
        <span className={shared.typePill} data-type="meal">🍽️ Meal</span>
      </div>

      <h2 className={styles.dishName}>{meal.title || 'Meal'}</h2>
      <p
        className={styles.restaurant}
        style={{ cursor: onViewRestaurant ? 'pointer' : 'default' }}
        onClick={() => onViewRestaurant?.(meal.restaurant_name)}
      >
        {meal.restaurant_name}
      </p>

      <div className={styles.ratingRow}>
        <StarRating rating={meal.rating} showLabel />
        {meal.dish_avg != null && (
          <span className={styles.date}>· {meal.dish_count} dishes, averaging {meal.dish_avg}</span>
        )}
      </div>

      {meal.review && <p className={styles.reviewText}>{meal.review}</p>}

      <div className={styles.mealDishes}>
        {meal.dishes.map(d => (
          <div key={d.id} className={styles.mealDishRow}>
            <button className={styles.mealDishName}
              onClick={() => onViewDish?.(d.dish_name, meal.restaurant_name)}>
              {d.dish_name}
            </button>
            <StarRating rating={d.rating} size={13} />
            {d.review && <p className={styles.mealDishNote}>{d.review}</p>}
          </div>
        ))}
      </div>

      <button className={styles.likeBtn} onClick={toggleLike}>
        {meal.user_liked ? '❤️' : '🤍'} {meal.like_count}
      </button>

      <div className={styles.tabs}>
        {TABS.map(t => (
          <button key={t.id}
            className={`${styles.tabBtn} ${tab === t.id ? styles.tabActive : ''}`}
            onClick={() => setTab(t.id)}>
            {t.label}
            <span className={styles.tabCount}>
              {t.id === 'likes' ? meal.like_count : meal.comment_count}
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
              @{l.username}
            </button>
          ))}
        </div>
      )}

      {tab === 'comments' && (
        <div className={styles.commentsList}>
          {commentsLoading && <p className={styles.loadingText}>Loading…</p>}
          {!commentsLoading && comments?.length === 0 && <p className={styles.emptyText}>No comments yet.</p>}
          {!commentsLoading && comments?.map(c => (
            <div key={c.id} className={styles.commentRow}>
              <button className={styles.usernameBtn} onClick={() => onViewUser?.(c.user_email)}>
                @{c.username}
              </button>
              <p className={styles.commentText}>{c.content}</p>
              {c.user_email === myEmail && (
                <button className={styles.deleteCommentBtn} onClick={() => deleteComment(c.id)}>Delete</button>
              )}
            </div>
          ))}
          <form onSubmit={postComment} className={styles.commentForm}>
            <input className={styles.commentInput} placeholder="Add a comment…"
              value={commentText} onChange={e => setCommentText(e.target.value)} />
            <button type="submit" className={styles.postBtn} disabled={!commentText.trim() || posting}>
              {posting ? '…' : 'Post'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}