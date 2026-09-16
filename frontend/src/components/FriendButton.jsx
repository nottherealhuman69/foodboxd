import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import shared from './shared.module.css'

/**
 * <FriendButton email="user@example.com" initialStatus="following" isPrivate onStatusChange={fn} />
 * Follow model: public accounts are followed instantly; private accounts get a
 * pending request. Owns all follow/unfollow state.
 *
 * Status values: 'following' | 'pending_sent' | 'pending_received' | null
 */
export default function FriendButton({ email, initialStatus, isPrivate, onSent, onStatusChange }) {
  const [status,  setStatus]  = useState(initialStatus)
  const [loading, setLoading] = useState(false)

  // Keep in sync when the parent supplies a status asynchronously (e.g. a profile
  // that loads the follow state after mount) or swaps to a different user.
  useEffect(() => { setStatus(initialStatus) }, [initialStatus])

  const follow = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/friends/request', {
        method: 'POST',
        body: JSON.stringify({ addressee_email: email }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      const next = data.status === 'accepted' ? 'following' : 'pending_sent'
      setStatus(next)
      onSent?.()
      onStatusChange?.(email, next)
    } catch {
      alert('Could not follow. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const unfollow = async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/follow/${encodeURIComponent(email)}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      setStatus(null)
      onStatusChange?.(email, null)
    } catch {
      alert('Could not update. Try again.')
    } finally {
      setLoading(false)
    }
  }

  if (status === 'following')
    return (
      <button className={shared.friendsBadge} onClick={unfollow} disabled={loading} title="Unfollow">
        {loading ? '…' : '✓ Following'}
      </button>
    )
  if (status === 'pending_sent')
    return (
      <button className={shared.pendingBadge} onClick={unfollow} disabled={loading} title="Cancel request">
        {loading ? '…' : 'Requested'}
      </button>
    )
  if (status === 'pending_received')
    return <span className={shared.pendingBadge}>Follows you</span>

  return (
    <button className={shared.addFriendBtn} onClick={follow} disabled={loading}>
      {loading ? '…' : (isPrivate ? '+ Request' : '+ Follow')}
    </button>
  )
}
