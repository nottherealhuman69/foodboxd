import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Notifications.module.css'

export default function Notifications() {
  const [requests, setRequests] = useState([])
  const [activity, setActivity] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [acting,   setActing]   = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [reqRes, actRes] = await Promise.all([
        apiFetch('/api/friends/requests/pending'),
        apiFetch('/api/notifications/activity'),
      ])
      if (!reqRes.ok) throw new Error()
      setRequests(await reqRes.json())
      setActivity(actRes.ok ? await actRes.json() : [])
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
      setRequests(prev => prev.filter(r => r.id !== id))
    } catch {
      setError('Something went wrong. Try again.')
    } finally {
      setActing(prev => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  const isEmpty = requests.length === 0 && activity.length === 0

  return (
    <div className={shared.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Notifications</h2>
        <p className={styles.sub}>Friend requests and activity</p>
      </div>

      <PageState
        loading={loading}
        error={error}
        empty={!loading && !error && isEmpty}
        emptyTitle="You're all caught up"
        emptyHint="No pending friend requests or activity"
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

      {!loading && !error && activity.length > 0 && (
        <div className={styles.list} style={{ marginTop: requests.length > 0 ? 16 : 0 }}>
          {activity.map(a => (
            <div key={`${a.type}-${a.review_id}-${a.created_at}`} className={styles.requestCard}>
              <div className={styles.info}>
                <p className={styles.name}>@{a.actor_username}</p>
                <p className={styles.sub2}>
                  {a.type === 'like' ? 'liked' : 'commented on'} your review of {a.dish_name}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}