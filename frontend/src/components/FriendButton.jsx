import { useState } from 'react'
import { apiFetch } from '../hooks/useApi'
import shared from './shared.module.css'

/**
 * <FriendButton email="user@example.com" initialStatus="pending_sent" onSent={fn} />
 * Owns all friend-request state. Drop in wherever a friend action is needed.
 */
export default function FriendButton({ email, initialStatus, onSent }) {
  const [status,  setStatus]  = useState(initialStatus)
  const [loading, setLoading] = useState(false)

  const send = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/friends/request', {
        method: 'POST',
        body: JSON.stringify({ addressee_email: email }),
      })
      if (!res.ok) throw new Error()
      setStatus('pending_sent')
      onSent?.()
    } catch {
      alert('Could not send request. Try again.')
    } finally {
      setLoading(false)
    }
  }

  if (status === 'accepted')         return <span className={shared.friendsBadge}>✓ Friends</span>
  if (status === 'pending_sent')     return <span className={shared.pendingBadge}>Request sent</span>
  if (status === 'pending_received') return <span className={shared.pendingBadge}>Requested you</span>

  return (
    <button className={shared.addFriendBtn} onClick={send} disabled={loading}>
      {loading ? '…' : '+ Follow'}
    </button>
  )
}
