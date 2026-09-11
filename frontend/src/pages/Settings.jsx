import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import styles from './Settings.module.css'

const TABS = [
  { id: 'privacy',  label: 'Privacy' },
  { id: 'security', label: 'Security' },
]

export default function Settings() {
  const [tab, setTab] = useState('privacy')
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Settings</h2>
        <p className={styles.sub}>Manage your account privacy and security.</p>
      </div>

      <div className={styles.tabs}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'privacy'  && <PrivacySection />}
      {tab === 'security' && <SecuritySection />}
    </div>
  )
}

function PrivacySection() {
  const [isPrivate, setIsPrivate] = useState(null)
  const [saving,    setSaving]    = useState(false)
  const [error,     setError]     = useState('')

  useEffect(() => {
    apiFetch('/api/me')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setIsPrivate(!!d.is_private))
      .catch(() => setError('Could not load your privacy setting.'))
  }, [])

  const toggle = async () => {
    if (isPrivate === null || saving) return
    const next = !isPrivate
    setSaving(true)
    setError('')
    setIsPrivate(next) // optimistic
    try {
      const res = await apiFetch('/api/me/privacy', {
        method: 'PATCH',
        body: JSON.stringify({ is_private: next }),
      })
      if (!res.ok) throw new Error()
      const d = await res.json()
      setIsPrivate(!!d.is_private)
    } catch {
      setIsPrivate(!next) // revert
      setError('Could not update your privacy setting.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className={styles.card}>
      <h3 className={styles.cardTitle}>Privacy</h3>
      <div className={styles.toggleRow}>
        <div>
          <p className={styles.rowLabel}>Private account</p>
          <p className={styles.rowHint}>
            {isPrivate
              ? 'Only followers you approve can see your posts.'
              : 'Anyone can follow you and see your posts.'}
          </p>
        </div>
        <button
          type="button"
          className={`${styles.switch} ${isPrivate ? styles.switchOn : ''}`}
          onClick={toggle}
          disabled={isPrivate === null || saving}
          role="switch"
          aria-checked={!!isPrivate}
          aria-label="Private account"
        >
          <span className={styles.knob} />
        </button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </section>
  )
}

function SecuritySection() {
  const [current, setCurrent] = useState('')
  const [next,    setNext]    = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving,  setSaving]  = useState(false)
  const [error,   setError]   = useState('')
  const [ok,      setOk]      = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setOk('')
    if (next.length < 6) { setError('New password must be at least 6 characters.'); return }
    if (next !== confirm) { setError('New passwords do not match.'); return }
    setSaving(true)
    try {
      const res = await apiFetch('/api/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: current, new_password: next }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Could not change password.')
      }
      setOk('Password updated.')
      setCurrent(''); setNext(''); setConfirm('')
    } catch (err) {
      setError(err.message || 'Could not change password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className={styles.card}>
      <h3 className={styles.cardTitle}>Reset password</h3>
      <p className={styles.cardHint}>Enter your current password, then choose a new one.</p>
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.label}>Current password</label>
        <input className={styles.input} type="password" value={current}
          onChange={e => setCurrent(e.target.value)} autoComplete="current-password" required />

        <label className={styles.label}>New password</label>
        <input className={styles.input} type="password" value={next}
          onChange={e => setNext(e.target.value)} autoComplete="new-password" required />

        <label className={styles.label}>Confirm new password</label>
        <input className={styles.input} type="password" value={confirm}
          onChange={e => setConfirm(e.target.value)} autoComplete="new-password" required />

        {error && <p className={styles.error}>{error}</p>}
        {ok    && <p className={styles.ok}>{ok}</p>}

        <button className={styles.primaryBtn} type="submit"
          disabled={saving || !current || !next || !confirm}>
          {saving ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </section>
  )
}
