import styles from './AuthCard.module.css'

export default function AuthCard({ children }) {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logo}>
          <span className={styles.logoDot} />
          <span className={styles.logoText}>dishlog</span>
        </div>
        {children}
      </div>
    </div>
  )
}
