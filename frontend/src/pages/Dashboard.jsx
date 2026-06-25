import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Profile from './Profile'
import Reviews from './Reviews'
import CreateReview from './CreateReview'
import styles from './Dashboard.module.css'

const NAV = [
  { id: 'profile', label: 'Profile', icon: ProfileIcon },
  { id: 'reviews', label: 'Reviews', icon: ReviewsIcon },
  { id: 'create', label: 'Log a Dish', icon: CreateIcon },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const email = localStorage.getItem('email') || ''
  const handle = email.split('@')[0]
  const [active, setActive] = useState('profile')
  const [menuOpen, setMenuOpen] = useState(false)
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState('')

  const token = localStorage.getItem('token')

  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  }

  // Load all reviews from API on mount
  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setFetchError('')
    try {
      const res = await fetch('/api/reviews', { headers: authHeaders })
      if (res.status === 401) {
        logout()
        return
      }
      if (!res.ok) throw new Error('Failed to load reviews')
      const data = await res.json()
      // Normalise snake_case from API → camelCase used in components
      setEntries(data.map(normalise))
    } catch (err) {
      setFetchError('Could not load your reviews. Please refresh.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  // Called by CreateReview on submit
  const handleSave = async (formData) => {
    const res = await fetch('/api/reviews', {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        dish_name: formData.dishName,
        type: formData.type,
        restaurant_name: formData.restaurantName || null,
        recipe: formData.recipe || null,
        rating: formData.rating,
        review: formData.review || null,
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to save review')
    }
    const saved = await res.json()
    setEntries(prev => [normalise(saved), ...prev])
    goTo('profile')
  }

  const handleDelete = async (id) => {
    const res = await fetch(`/api/reviews/${id}`, {
      method: 'DELETE',
      headers: authHeaders,
    })
    if (res.ok) {
      setEntries(prev => prev.filter(e => e.id !== id))
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('email')
    navigate('/login')
  }

  const goTo = (id) => { setActive(id); setMenuOpen(false) }

  return (
    <div className={styles.shell}>
      <aside className={`${styles.sidebar} ${menuOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.brand}>
          <span className={styles.brandDot} />
          <span className={styles.brandName}>dishlog</span>
        </div>

        <nav className={styles.nav}>
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`${styles.navItem} ${active === id ? styles.navActive : ''}`}
              onClick={() => goTo(id)}
            >
              <Icon className={styles.navIcon} />
              <span>{label}</span>
              {id === 'reviews' && entries.length > 0 && (
                <span className={styles.badge}>{entries.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userRow}>
            <div className={styles.avatar}>{handle[0]?.toUpperCase()}</div>
            <div className={styles.userInfo}>
              <span className={styles.userName}>{handle}</span>
              <span className={styles.userEmail}>{email}</span>
            </div>
          </div>
          <button onClick={logout} className={styles.logoutBtn} title="Sign out">
            <LogoutIcon />
          </button>
        </div>
      </aside>

      <header className={styles.mobileHeader}>
        <span className={styles.brandName} style={{ fontSize: 16 }}>dishlog</span>
        <button className={styles.menuBtn} onClick={() => setMenuOpen(o => !o)}>
          <MenuIcon />
        </button>
      </header>

      {menuOpen && <div className={styles.overlay} onClick={() => setMenuOpen(false)} />}

      <main className={styles.main}>
        {active === 'profile' && (
          <Profile entries={entries} loading={loading} fetchError={fetchError} onNavigate={goTo} />
        )}
        {active === 'reviews' && (
          <Reviews entries={entries} loading={loading} fetchError={fetchError} onNavigate={goTo} onDelete={handleDelete} />
        )}
        {active === 'create' && (
          <CreateReview onSave={handleSave} />
        )}
      </main>
    </div>
  )
}

// Convert API snake_case response to camelCase for components
function normalise(r) {
  return {
    id: r.id,
    dishName: r.dish_name,
    type: r.type,
    restaurantName: r.restaurant_name ?? '',
    recipe: r.recipe ?? '',
    rating: r.rating,
    review: r.review ?? '',
    loggedAt: new Date(r.logged_at),
  }
}

/* ── Icons ── */
function ProfileIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="6.5" r="3" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M3.5 17c0-3.314 2.91-6 6.5-6s6.5 2.686 6.5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function ReviewsIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none">
      <path d="M3 5h14M3 10h10M3 15h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="16" cy="14.5" r="2.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M17.5 16.5l1.5 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function CreateIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="7.25" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M10 7v6M7 10h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function LogoutIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M13 4.5h2.5A1.5 1.5 0 0117 6v8a1.5 1.5 0 01-1.5 1.5H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M8.5 13.5L12 10l-3.5-3.5M12 10H3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}