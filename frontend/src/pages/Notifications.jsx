import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import shared from '../components/shared.module.css'
import styles from './Notifications.module.css'

function timeAgo(iso) {
  const diff  = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins  < 1)  return 'just now'
  if (mins  < 60) return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days  < 7)  return `${days}d ago`
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export default function Notifications({ onViewReview, onViewUser }) {
  const [requests, setRequests] = useState([])
  const [activity, setActivity] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [acting,   setActing]   = useState({})
  const [invites, setInvites] = useState([])

  const respondToInvite = async (groupListId, action) => {
    setActing(prev => ({ ...prev, [`g${groupListId}`]: action }))
    try {
      const res = await apiFetch(`/api/group-lists/${groupListId}/invite`, {
        method: 'PATCH',
        body: JSON.stringify({ action }),
      })
      if (!res.ok) throw new Error()
      setInvites(prev => prev.filter(i => i.group_list_id !== groupListId))
    } catch {
      setError('Something went wrong. Try again.')
    } finally {
      setActing(prev => { const n = { ...prev }; delete n[`g${groupListId}`]; return n })
    }
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [reqRes, actRes, invRes] = await Promise.all([
        apiFetch('/api/friends/requests/pending'),
        apiFetch('/api/notifications/activity'),
        apiFetch('/api/group-lists/invites'),
      ])
      if (!reqRes.ok) throw new Error()
      setRequests(await reqRes.json())
      setActivity(actRes.ok ? await actRes.json() : [])
      setInvites(invRes.ok ? await invRes.json() : [])
    } catch (e) {
      console.error('notifications load failed:', e)
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

  const isEmpty = requests.length === 0 && activity.length === 0 && invites.length === 0

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
      {!loading && !error && invites.length > 0 && (
        <div className={styles.list} style={{ marginBottom: 16 }}>
          {invites.map(inv => (
            <div key={inv.group_list_id} className={styles.requestCard}>
              <div className={styles.avatar}>{inv.invited_by[0].toUpperCase()}</div>
              <div className={styles.info}>
                <p className={styles.name}>{inv.name}</p>
                <p className={styles.sub2}>
                  @{inv.invited_by_username} invited you to this group list
                </p>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.acceptBtn}
                  disabled={!!acting[`g${inv.group_list_id}`]}
                  onClick={() => respondToInvite(inv.group_list_id, 'accept')}
                >
                  {acting[`g${inv.group_list_id}`] === 'accept' ? '…' : 'Join'}
                </button>
                <button
                  className={styles.declineBtn}
                  disabled={!!acting[`g${inv.group_list_id}`]}
                  onClick={() => respondToInvite(inv.group_list_id, 'decline')}
                >
                  {acting[`g${inv.group_list_id}`] === 'decline' ? '…' : 'Decline'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && requests.length > 0 && (
        <div className={styles.list}>
          {requests.map(req => (
            <div key={req.id} className={styles.requestCard}>
              <div className={styles.avatar}>{req.requester_email[0].toUpperCase()}</div>
              <div className={styles.info}>
                <p className={styles.name}>
                  @<button
                    type="button"
                    className={styles.nameLink}
                    onClick={() => onViewUser?.(req.requester_email)}
                  >
                    {req.requester_email.split('@')[0]}
                  </button>
                </p>
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
            <div
              key={`${a.type}-${a.review_id}-${a.created_at}`}
              className={styles.activityCard}
              role="button"
              tabIndex={0}
              onClick={() => onViewReview?.(a.review_id, a.type === 'like' ? 'likes' : 'comments')}
              onKeyDown={e => { if (e.key === 'Enter') onViewReview?.(a.review_id, a.type === 'like' ? 'likes' : 'comments') }}
            >
              <div className={styles.activityIcon} data-type={a.type}>
                {a.type === 'like' ? '❤️' : '💬'}
              </div>
              <div className={styles.info}>
                <p className={styles.name}>
                  @<button
                    type="button"
                    className={styles.nameLink}
                    onClick={e => { e.stopPropagation(); onViewUser?.(a.actor_email) }}
                  >
                    {a.actor_username}
                  </button>
                </p>
                <p className={styles.sub2}>
                  {a.type === 'like' ? 'liked' : 'commented on'} your review of {a.dish_name}
                </p>
              </div>
              <span className={styles.activityTime}>{timeAgo(a.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}