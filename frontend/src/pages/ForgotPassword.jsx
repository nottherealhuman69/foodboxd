import { useState } from 'react'
import { Link } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import styles from './Auth.module.css'

export default function ForgotPassword() {
  const [email,   setEmail]   = useState('')
  const [sent,    setSent]    = useState(false)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Something went wrong. Please try again.')
        return
      }
      setSent(true)
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard>
      <h1 className={styles.heading}>Forgot password?</h1>
      <p className={styles.subheading}>We'll email you a link to reset it.</p>

      {sent ? (
        <>
          <p className={styles.subheading}>
            If that email is registered, a reset link is on its way. Check your inbox
            (and spam) — the link expires in 1 hour.
          </p>
          <div className={styles.footer}>
            <Link to="/login" className={styles.footerLink}>Back to sign in</Link>
          </div>
        </>
      ) : (
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="email">Email</label>
            <input id="email" name="email" type="email" autoComplete="email" required
              placeholder="you@example.com" value={email}
              onChange={e => { setEmail(e.target.value); setError('') }} className={styles.input} />
          </div>
          {error && <p className={styles.error}>{error}</p>}
          <button type="submit" disabled={loading} className={styles.primaryBtn}>
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
          <div className={styles.footer}>
            <Link to="/login" className={styles.footerLink}>Back to sign in</Link>
          </div>
        </form>
      )}
    </AuthCard>
  )
}
