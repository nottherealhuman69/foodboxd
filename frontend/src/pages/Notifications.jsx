import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Notifications.module.css'

export default function Notifications({ onBadgeChange }) {
  const [requests, setRequests] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [acting,   setActing]   = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/friends/requests/pending')
      if (!res.ok) throw new Error()
      const data = await res.json()
      setRequests(data)
      onBadgeChange(data.length)
    } catch {
      setError('Could not load notifications.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const respond = async (id, action) => {
    setActing(prev => ({ ...prev, [id]: action }))
    try {
      const res = await apiFetch(`/api/friends/requests/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ action }),
      })
      if (!res.ok) throw new Error()
      const next = requests.filter(r => r.id !== id)
      setRequests(next)
      onBadgeChange(next.length)
    } catch {
      setError('Something went wrong. Try again.')
    } finally {
      setActing(prev => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  return (
    <div className={shared.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Notifications</h2>
        <p className={styles.sub}>Friend requests and activity</p>
      </div>

      <PageState
        loading={loading}
        error={error}
        empty={!loading && !error && requests.length === 0}
        emptyTitle="You're all caught up"
        emptyHint="No pending friend requests"
      />

      {!loading && !error && requests.length > 0 && (
        <div className={styles.list}>
          {requests.map(req => (
            <div key={req.id} className={styles.requestCard}>
              <div className={styles.avatar}>{req.requester_email[0].toUpperCase()}</div>
              <div className={styles.info}>
                <p className={styles.name}>@{req.requester_email.split('@')[0]}</p>
                <p className={styles.sub2}>wants to follow you</p>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.acceptBtn}
                  disabled={!!acting[req.id]}
                  onClick={() => respond(req.id, 'accept')}
                >
                  {acting[req.id] === 'accept' ? '…' : 'Accept'}
                </button>
                <button
                  className={styles.declineBtn}
                  disabled={!!acting[req.id]}
                  onClick={() => respond(req.id, 'decline')}
                >
                  {acting[req.id] === 'decline' ? '…' : 'Decline'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
