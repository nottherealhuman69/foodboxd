import { useNavigate } from 'react-router-dom'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const navigate = useNavigate()
  const email = localStorage.getItem('email') || 'there'
  const firstName = email.split('@')[0]

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('email')
    navigate('/login')
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.dot} />
        <h1 className={styles.greeting}>Hi, {firstName} 👋</h1>
        <p className={styles.sub}>You're logged in as <span className={styles.email}>{email}</span></p>
        <button onClick={logout} className={styles.logoutBtn}>Sign out</button>
      </div>
    </div>
  )
}