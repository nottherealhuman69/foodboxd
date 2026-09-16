import { useState } from 'react'
import { apiFetch } from '../hooks/useApi'
import styles from './CommentThread.module.css'

/**
 * Recursive, threaded comments with likes and replies.
 *
 * props:
 *  - comments:    flat array of { id, user_email, username, content, parent_id, like_count, user_liked }
 *  - setComments: state setter for that flat array
 *  - commentType: 'review' | 'meal'  (routes the like endpoint)
 *  - basePath:    e.g. '/api/reviews/123/comments' or '/api/meals/45/comments'
 *  - myEmail
 *  - onViewUser(email)
 *  - onCountChange(delta)  — keep the post's comment_count in sync
 */
export default function CommentThread({ comments, setComments, commentType, basePath, myEmail, onViewUser, onCountChange }) {
  const roots = comments.filter(c => c.parent_id == null)
  const childrenOf = (id) => comments.filter(c => c.parent_id === id)

  const toggleLike = async (comment) => {
    const prev = { liked: comment.user_liked, count: comment.like_count }
    setComments(cs => cs.map(c => c.id === comment.id
      ? { ...c, user_liked: !c.user_liked, like_count: c.like_count + (c.user_liked ? -1 : 1) }
      : c))
    try {
      const res = await apiFetch(`/api/comments/${commentType}/${comment.id}/like`, { method: 'POST' })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setComments(cs => cs.map(c => c.id === comment.id
        ? { ...c, user_liked: data.liked, like_count: data.like_count } : c))
    } catch {
      setComments(cs => cs.map(c => c.id === comment.id
        ? { ...c, user_liked: prev.liked, like_count: prev.count } : c))
    }
  }

  const postReply = async (parentId, content) => {
    const res = await apiFetch(basePath, {
      method: 'POST',
      body: JSON.stringify({ content, parent_id: parentId }),
    })
    if (!res.ok) throw new Error()
    const added = await res.json()
    setComments(cs => [...cs, added])
    onCountChange?.(1)
  }

  const deleteComment = async (comment) => {
    try {
      const res = await apiFetch(`${basePath}/${comment.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      // Backend cascades child replies — mirror that locally.
      const removed = new Set([comment.id])
      let grew = true
      while (grew) {
        grew = false
        for (const c of comments) {
          if (c.parent_id != null && removed.has(c.parent_id) && !removed.has(c.id)) {
            removed.add(c.id); grew = true
          }
        }
      }
      setComments(cs => cs.filter(c => !removed.has(c.id)))
      onCountChange?.(-removed.size)
    } catch { /* silently fail */ }
  }

  if (roots.length === 0) return null

  return (
    <div className={styles.thread}>
      {roots.map(c => (
        <CommentNode
          key={c.id}
          comment={c}
          childrenOf={childrenOf}
          depth={0}
          myEmail={myEmail}
          onViewUser={onViewUser}
          onToggleLike={toggleLike}
          onReply={postReply}
          onDelete={deleteComment}
        />
      ))}
    </div>
  )
}

function CommentNode({ comment, childrenOf, depth, myEmail, onViewUser, onToggleLike, onReply, onDelete }) {
  const [replying,   setReplying]   = useState(false)
  const [replyText,  setReplyText]  = useState('')
  const [posting,    setPosting]    = useState(false)
  const kids = childrenOf(comment.id)

  const submitReply = async (e) => {
    e.preventDefault()
    if (!replyText.trim() || posting) return
    setPosting(true)
    try {
      await onReply(comment.id, replyText.trim())
      setReplyText('')
      setReplying(false)
    } catch { /* silently fail */ }
    finally { setPosting(false) }
  }

  return (
    <div className={styles.node} style={depth > 0 ? { marginLeft: 16, borderLeft: '1px solid rgba(99,102,241,0.12)', paddingLeft: 12 } : undefined}>
      <div className={styles.row}>
        <button className={styles.avatar} onClick={() => onViewUser?.(comment.user_email)}>
          {comment.username.charAt(0).toUpperCase()}
        </button>
        <div className={styles.body}>
          <button className={styles.username} onClick={() => onViewUser?.(comment.user_email)}>
            @{comment.username}
          </button>
          <p className={styles.content}>{comment.content}</p>
          <div className={styles.actions}>
            <button
              className={`${styles.likeBtn} ${comment.user_liked ? styles.liked : ''}`}
              onClick={() => onToggleLike(comment)}
            >
              {comment.user_liked ? '❤️' : '🤍'}{comment.like_count > 0 ? ` ${comment.like_count}` : ''}
            </button>
            <button className={styles.replyBtn} onClick={() => setReplying(r => !r)}>Reply</button>
          </div>
          {replying && (
            <form className={styles.replyForm} onSubmit={submitReply}>
              <input
                className={styles.replyInput}
                placeholder={`Reply to @${comment.username}…`}
                value={replyText}
                onChange={e => setReplyText(e.target.value)}
                maxLength={500}
                autoFocus
              />
              <button type="submit" className={styles.replySubmit} disabled={!replyText.trim() || posting}>
                {posting ? '…' : 'Reply'}
              </button>
            </form>
          )}
        </div>
        {comment.user_email === myEmail && (
          <button className={styles.deleteBtn} onClick={() => onDelete(comment)} title="Delete">×</button>
        )}
      </div>
      {kids.length > 0 && (
        <div className={styles.children}>
          {kids.map(k => (
            <CommentNode
              key={k.id}
              comment={k}
              childrenOf={childrenOf}
              depth={depth + 1}
              myEmail={myEmail}
              onViewUser={onViewUser}
              onToggleLike={onToggleLike}
              onReply={onReply}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
