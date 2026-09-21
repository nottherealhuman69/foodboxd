// frontend/src/components/RepostButton.jsx
import { useState } from 'react'
import { apiFetch } from '../hooks/useApi'
import styles from './RepostButton.module.css'

/**
 * Toggle for reposting a post you're tagged in.
 *
 * props:
 *  - postType: 'review' | 'meal'
 *  - postId
 *  - initialReposted: boolean
 *  - onChange?(reposted)
 *  - compact?: smaller variant for notification rows
 */
export default function RepostButton({ postType, postId, initialReposted = false, onChange, compact = false }) {
  const [reposted, setReposted] = useState(initialReposted)
  const [busy,     setBusy]     = useState(false)

  const toggle = async (e) => {
    e.stopPropagation()
    if (busy) return
    setBusy(true)
    const prev = reposted
    setReposted(!prev)                       // optimistic
    try {
      const res = await apiFetch(`/api/posts/${postType}/${postId}/repost`, { method: 'POST' })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setReposted(data.reposted)
      onChange?.(data.reposted)
    } catch {
      setReposted(prev)
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      className={`${styles.btn} ${compact ? styles.compact : ''} ${reposted ? styles.active : ''}`}
      onClick={toggle}
      disabled={busy}
      aria-pressed={reposted}
      title={reposted ? 'Remove from your profile' : 'Add to your profile'}
    >
      🔁 {reposted ? 'Reposted' : 'Repost'}
    </button>
  )
}

/**
 * Small "🔁 reposted by @name" tag to sit next to the author's name.
 * Renders nothing when the item isn't a repost.
 *
 * props:
 *  - repostedBy: { email, username } | null
 *  - onViewUser?(email)
 */
export function RepostedBy({ repostedBy, onViewUser }) {
  if (!repostedBy) return null
  return (
    <span className={styles.repostedBy}>
      🔁 reposted by{' '}
      <button
        type="button"
        className={styles.repostedName}
        onClick={(e) => { e.stopPropagation(); onViewUser?.(repostedBy.email) }}
      >
        @{repostedBy.username}
      </button>
    </span>
  )
}