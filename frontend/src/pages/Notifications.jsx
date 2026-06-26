import { useState, useEffect, useCallback } from 'react'
import styles from './Notifications.module.css'

export default function Notifications({ onBadgeChange }) {
  const [requests, setRequests]   = useState([])
  const [loading,  setLoading]    = useState(true)
  const [error,    setError]      = useState('')
  const [acting,   setActing]     = useState({}) // id → 'accept'|'decline'

  const token = localStorage.getItem('token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/friends/requests/pending', { headers: authHeaders })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setRequests(data)
      onBadgeChange(data.length)
    } catch {
      setError('Could not load notifications.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const respond = async (id, action) => {
    setActing(prev => ({ ...prev, [id]: action }))
    try {
      const res = await fetch(`/api/friends/requests/${id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ action }),
      })
      if (!res.ok) throw new Error()
      setRequests(prev => prev.filter(r => r.id !== id))
      onBadgeChange(requests.length - 1)
    } catch {
      setError('Something went wrong. Try again.')
    } finally {
      setActing(prev => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  const timeAgo = (iso) => {
    const diff = Date.now() - new Date(iso).getTime()
    const mins  = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days  = Math.floor(diff / 86400000)
    if (mins < 1)   return 'just now'
    if (mins < 60)  return `${mins}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Notifications</h2>
        <p className={styles.sub}>Friend requests waiting for your response</p>
      </div>

      {loading && (
        <div className={styles.state}>
          <div className={styles.spinner} />
          <p>Loading…</p>
        </div>
      )}

      {error && !loading && (
        <div className={styles.errorBanner}>{error}</div>
      )}

      {!loading && !error && requests.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" stroke="#4e5272" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p className={styles.emptyText}>No pending requests</p>
          <p className={styles.emptyHint}>When someone sends you a friend request it will appear here</p>
        </div>
      )}

      {!loading && requests.length > 0 && (
        <div className={styles.list}>
          {requests.map(req => (
            <div key={req.id} className={styles.card}>
              <div className={styles.avatar}>{req.username.charAt(0).toUpperCase()}</div>
              <div className={styles.cardBody}>
                <div className={styles.cardTop}>
                  <span className={styles.username}>@{req.username}</span>
                  <span className={styles.time}>{timeAgo(req.created_at)}</span>
                </div>
                <p className={styles.cardSub}>
                  {req.review_count > 0
                    ? `${req.review_count} dish${req.review_count !== 1 ? 'es' : ''} logged`
                    : 'New member'}
                  {' · wants to follow you'}
                </p>
                <div className={styles.actions}>
                  <button
                    className={styles.acceptBtn}
                    onClick={() => respond(req.id, 'accept')}
                    disabled={!!acting[req.id]}
                  >
                    {acting[req.id] === 'accept' ? 'Accepting…' : 'Accept'}
                  </button>
                  <button
                    className={styles.declineBtn}
                    onClick={() => respond(req.id, 'decline')}
                    disabled={!!acting[req.id]}
                  >
                    {acting[req.id] === 'decline' ? 'Declining…' : 'Decline'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}