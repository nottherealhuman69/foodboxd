import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import styles from './Auth.module.css'

export default function Signup() {
  const navigate = useNavigate()
  const [form,    setForm]    = useState({ email: '', password: '', confirm: '' })
  const [error,   setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) { setError('Passwords do not match'); return }
    if (form.password.length < 8)       { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email, password: form.password }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Signup failed'); return }
      navigate('/login', { state: { message: 'Account created! Please sign in.' } })
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard>
      <h1 className={styles.heading}>Create account</h1>
      <p className={styles.subheading}>Get started for free</p>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">Email</label>
          <input id="email" name="email" type="email" autoComplete="email" required
            placeholder="you@example.com" value={form.email}
            onChange={handleChange} className={styles.input} />
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">Password</label>
          <input id="password" name="password" type="password" autoComplete="new-password" required
            placeholder="Min. 8 characters" value={form.password}
            onChange={handleChange} className={styles.input} />
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="confirm">Confirm password</label>
          <input id="confirm" name="confirm" type="password" autoComplete="new-password" required
            placeholder="••••••••" value={form.confirm}
            onChange={handleChange} className={styles.input} />
        </div>
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" disabled={loading} className={styles.primaryBtn}>
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <div className={styles.footer}>
        <span className={styles.footerText}>Already have an account?</span>
        <Link to="/login" className={styles.footerLink}>Sign in</Link>
      </div>
    </AuthCard>
  )
}
