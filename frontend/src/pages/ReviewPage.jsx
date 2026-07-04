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

export default function ReviewPage({ reviewId, initialTab = 'comments', onBack, onViewUser }) {
  const [review,  setReview]  = useState(null)
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
    load()
  }, [reviewId])

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

  const postComment = async (e) => {
    e.preventDefault()
    if (!commentText.trim() || posting) return
    setPosting(true)
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: commentText.trim() }),
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

  const deleteComment = async (commentId) => {
    try {
      const res = await apiFetch(`/api/reviews/${reviewId}/comments/${commentId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      setComments(prev => prev.filter(c => c.id !== commentId))
      setReview(r => ({ ...r, comment_count: r.comment_count - 1 }))
    } catch {
      // silently fail
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

  const date = new Date(review.logged_at).toLocaleDateString('en-IN', {
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

      <h2 className={styles.dishName}>{review.dish_name}</h2>
      {review.restaurant_name && <p className={styles.restaurant}>{review.restaurant_name}</p>}

      <div className={styles.ratingRow}>
        <StarRating rating={review.rating} showLabel />
      </div>

      {review.review && <p className={styles.reviewText}>{review.review}</p>}
      {review.recipe && (
        <details className={styles.recipeDetails}>
          <summary>View recipe</summary>
          <p>{review.recipe}</p>
        </details>
      )}

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
            <div className={styles.commentList}>
              {comments.map(c => (
                <div key={c.id} className={styles.comment}>
                  <button className={styles.commentAvatar} onClick={() => onViewUser?.(c.user_email)}>
                    {c.username.charAt(0).toUpperCase()}
                  </button>
                  <div className={styles.commentBody}>
                    <button className={styles.commentUsername} onClick={() => onViewUser?.(c.user_email)}>
                      @{c.username}
                    </button>
                    <p className={styles.commentContent}>{c.content}</p>
                  </div>
                  {c.user_email === myEmail && (
                    <button className={styles.deleteCommentBtn} onClick={() => deleteComment(c.id)} title="Delete">×</button>
                  )}
                </div>
              ))}
            </div>
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