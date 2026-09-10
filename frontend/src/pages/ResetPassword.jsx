import { useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import styles from './Auth.module.css'

export default function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirm,  setConfirm]  = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [done,     setDone]     = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password.length < 6) { setError('Password must be at least 6 characters'); return }
    if (password !== confirm) { setError('Passwords do not match'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.detail || 'Could not reset password'); return }
      setDone(true)
      setTimeout(() => navigate('/login'), 1500)
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <AuthCard>
        <h1 className={styles.heading}>Invalid link</h1>
        <p className={styles.subheading}>This reset link is missing or malformed.</p>
        <div className={styles.footer}>
          <Link to="/forgot-password" className={styles.footerLink}>Request a new link</Link>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard>
      <h1 className={styles.heading}>Set a new password</h1>
      {done ? (
        <>
          <p className={styles.subheading}>Password updated. Redirecting to sign in…</p>
          <div className={styles.footer}>
            <Link to="/login" className={styles.footerLink}>Go to sign in</Link>
          </div>
        </>
      ) : (
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="password">New password</label>
            <input id="password" name="password" type="password" autoComplete="new-password" required
              placeholder="••••••••" value={password}
              onChange={e => { setPassword(e.target.value); setError('') }} className={styles.input} />
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="confirm">Confirm password</label>
            <input id="confirm" name="confirm" type="password" autoComplete="new-password" required
              placeholder="••••••••" value={confirm}
              onChange={e => { setConfirm(e.target.value); setError('') }} className={styles.input} />
          </div>
          {error && <p className={styles.error}>{error}</p>}
          <button type="submit" disabled={loading} className={styles.primaryBtn}>
            {loading ? 'Saving…' : 'Reset password'}
          </button>
        </form>
      )}
    </AuthCard>
  )
}
