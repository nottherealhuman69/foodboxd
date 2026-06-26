import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Profile from './Profile'
import Reviews from './Reviews'
import CreateReview from './CreateReview'
import Search from './Search'
import Notifications from './Notifications'
import styles from './Dashboard.module.css'

// ── Icons ──────────────────────────────────────────────────────────────────
function ProfileIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M4 20c0-4 3.582-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  )
}
function ReviewsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 6h16M4 10h16M4 14h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  )
}
function CreateIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M12 8v8M8 12h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  )
}
function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  )
}
function BellIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const NAV = [
  { id: 'profile', label: 'Profile',    icon: ProfileIcon },
  { id: 'reviews', label: 'Reviews',    icon: ReviewsIcon },
  { id: 'create',  label: 'Log a Dish', icon: CreateIcon  },
  { id: 'search',  label: 'Search',     icon: SearchIcon  },
  { id: 'notifs',  label: 'Notifications', icon: BellIcon   },
]

function normalise(r) {
  return {
    id:             r.id,
    dishName:       r.dish_name,
    type:           r.type,
    restaurantName: r.restaurant_name || '',
    recipe:         r.recipe || '',
    rating:         r.rating,
    review:         r.review || '',
    loggedAt:       new Date(r.logged_at),
  }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const email   = localStorage.getItem('email') || ''
  const handle  = email.split('@')[0]
  const [active,    setActive]    = useState('profile')
  const [notifCount, setNotifCount] = useState(0)
  const [menuOpen,  setMenuOpen]  = useState(false)
  const [entries,   setEntries]   = useState([])
  const [loading,   setLoading]   = useState(true)
  const [fetchError,setFetchError]= useState('')

  const token = localStorage.getItem('token')
  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('email')
    navigate('/login')
  }, [navigate])

  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setFetchError('')
    try {
      const res = await fetch('/api/reviews', { headers: authHeaders })
      if (res.status === 401) { logout(); return }
      if (!res.ok) throw new Error()
      const data = await res.json()
      setEntries(data.map(normalise))
    } catch {
      setFetchError('Could not load your reviews. Please refresh.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  const addEntry = async (formData) => {
    const res = await fetch('/api/reviews', {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        dish_name:       formData.dishName,
        type:            formData.type,
        restaurant_name: formData.restaurantName || null,
        recipe:          formData.recipe || null,
        rating:          formData.rating,
        review:          formData.review || null,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to save review')
    }
    const saved = await res.json()
    setEntries(prev => [normalise(saved), ...prev])
    goTo('profile')
  }

  const deleteEntry = async (id) => {
    try {
      const res = await fetch(`/api/reviews/${id}`, {
        method: 'DELETE',
        headers: authHeaders,
      })
      if (!res.ok) throw new Error()
      setEntries(prev => prev.filter(e => e.id !== id))
    } catch {
      alert('Failed to delete. Please try again.')
    }
  }

  const goTo = (id) => { setActive(id); setMenuOpen(false) }

  const reviewCount = entries.length

  return (
    <div className={styles.shell}>
      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${menuOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.brand}>
          <span className={styles.brandDot} />
          <span className={styles.brandName}>forkd</span>
        </div>

        <nav className={styles.nav}>
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`${styles.navItem} ${active === id ? styles.navActive : ''}`}
              onClick={() => goTo(id)}
            >
              <span className={styles.navIcon}><Icon /></span>
              <span className={styles.navLabel}>{label}</span>
              {id === 'reviews' && reviewCount > 0 && (
                <span className={styles.badge}>{reviewCount}</span>
              )}
              {id === 'notifs' && notifCount > 0 && (
                <span className={styles.badge}>{notifCount}</span>
              )}
            </button>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userRow}>
            <div className={styles.avatar}>{handle.charAt(0).toUpperCase()}</div>
            <div className={styles.userInfo}>
              <span className={styles.userHandle}>@{handle}</span>
              <span className={styles.userEmail}>{email}</span>
            </div>
          </div>
          <button onClick={logout} className={styles.logoutBtn} title="Sign out">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {menuOpen && <div className={styles.overlay} onClick={() => setMenuOpen(false)} />}

      {/* Main content */}
      <div className={styles.main}>
        {/* Mobile top bar */}
        <div className={styles.topbar}>
          <button className={styles.menuBtn} onClick={() => setMenuOpen(o => !o)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </button>
          <span className={styles.topbarTitle}>{NAV.find(n => n.id === active)?.label}</span>
        </div>

        {fetchError && <div className={styles.errorBanner}>{fetchError}</div>}

        {active === 'profile' && (
          <Profile entries={entries} loading={loading} fetchError={fetchError} onNavigate={goTo} />
        )}
        {active === 'reviews' && (
          <Reviews entries={entries} loading={loading} fetchError={fetchError} onDelete={deleteEntry} />
        )}
        {active === 'create' && (
          <CreateReview onSave={addEntry} />
        )}
        {active === 'search' && (
          <Search />
        )}
        {active === 'notifs' && (
          <Notifications onBadgeChange={setNotifCount} />
        )}
      </div>
    </div>
  )
}