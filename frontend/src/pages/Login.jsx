import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import styles from './Auth.module.css'

export default function Login() {
  const navigate = useNavigate()
  const [form,    setForm]    = useState({ email: '', password: '' })
  const [error,   setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Login failed'); return }
      localStorage.setItem('token', data.token)
      localStorage.setItem('email', data.email)
      navigate('/dashboard')
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard>
      <h1 className={styles.heading}>Welcome back</h1>
      <p className={styles.subheading}>Sign in to your account</p>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">Email</label>
          <input id="email" name="email" type="email" autoComplete="email" required
            placeholder="you@example.com" value={form.email}
            onChange={handleChange} className={styles.input} />
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">Password</label>
          <input id="password" name="password" type="password" autoComplete="current-password" required
            placeholder="••••••••" value={form.password}
            onChange={handleChange} className={styles.input} />
        </div>
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" disabled={loading} className={styles.primaryBtn}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <div className={styles.footer}>
        <span className={styles.footerText}>Don't have an account?</span>
        <Link to="/signup" className={styles.footerLink}>Create one</Link>
      </div>
    </AuthCard>
  )
}
