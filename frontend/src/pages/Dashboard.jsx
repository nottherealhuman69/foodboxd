import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Profile from './Profile'
import Feed from './Feed'
import Reviews from './Reviews'
import CreateReview from './CreateReview'
import Search from './Search'
import Notifications from './Notifications'
import Trylist from './Trylist'
import MyLists from './Mylists'
import DishPage from './DishPage'
import RestaurantPage from './RestaurantPage'
import UserProfile from './UserProfile'
import { apiFetch } from '../hooks/useApi'
import { normaliseReview } from '../utils/reviews'
import styles from './Dashboard.module.css'

const NAV = [
  { id: 'profile', label: 'Profile',      icon: ProfileIcon  },
  { id: 'feed',    label: 'Feed',          icon: FeedIcon     },
  { id: 'reviews', label: 'Reviews',       icon: ReviewsIcon  },
  { id: 'create',  label: 'Log a Dish',    icon: CreateIcon   },
  { id: 'search',  label: 'Search',        icon: SearchIcon   },
  { id: 'trylist', label: 'Trylist',       icon: TrylistIcon  },
  { id: 'notifs',  label: 'Notifications', icon: BellIcon     },
  { id: 'lists',   label: 'My Lists',      icon: ListsIcon    },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const email  = localStorage.getItem('email') || ''
  const handle = email.split('@')[0]

  const [active,      setActive]      = useState('profile')
  const [menuOpen,    setMenuOpen]    = useState(false)
  const [entries,     setEntries]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [fetchError,  setFetchError]  = useState('')
  const [notifCount,  setNotifCount]  = useState(0)
  const [viewingDish,       setViewingDish]       = useState(null)
  const [viewingRestaurant, setViewingRestaurant] = useState(null)
  const [viewingUser,       setViewingUser]       = useState(null)

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('email')
    navigate('/login')
  }, [navigate])

  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setFetchError('')
    try {
      const res = await apiFetch('/api/reviews')
      if (res.status === 401) { logout(); return }
      if (!res.ok) throw new Error()
      setEntries((await res.json()).map(normaliseReview))
    } catch {
      setFetchError('Could not load your reviews. Please refresh.')
    } finally {
      setLoading(false)
    }
  }, [logout])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  const handleSave = async (formData) => {
    const res = await apiFetch('/api/reviews', {
      method: 'POST',
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
    setEntries(prev => [normaliseReview(saved), ...prev])
    goTo('profile')
  }

  const handleDelete = async (id) => {
    const res = await apiFetch(`/api/reviews/${id}`, { method: 'DELETE' })
    if (res.ok) setEntries(prev => prev.filter(e => e.id !== id))
  }

  const goTo = (id) => { setActive(id); setMenuOpen(false) }

  return (
    <div className={styles.shell}>
      {viewingDish && (
        <div className={styles.overlayPage}>
          <DishPage {...viewingDish} onBack={() => setViewingDish(null)} />
        </div>
      )}
      {viewingRestaurant && !viewingDish && (
        <div className={styles.overlayPage}>
          <RestaurantPage restaurantName={viewingRestaurant} onBack={() => setViewingRestaurant(null)} />
        </div>
      )}
      {viewingUser && !viewingDish && !viewingRestaurant && (
        <div className={styles.overlayPage}>
          <UserProfile userEmail={viewingUser} onBack={() => setViewingUser(null)} />
        </div>
      )}

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
              {id === 'reviews' && entries.length > 0 && <span className={styles.badge}>{entries.length}</span>}
              {id === 'notifs'  && notifCount > 0      && <span className={styles.badge}>{notifCount}</span>}
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
          <button onClick={logout} className={styles.logoutBtn} title="Sign out"><LogoutIcon /></button>
        </div>
      </aside>

      <header className={styles.mobileHeader}>
        <span className={styles.brandName} style={{ fontSize: 16 }}>dishlog</span>
        <button className={styles.menuBtn} onClick={() => setMenuOpen(o => !o)}><MenuIcon /></button>
      </header>

      {menuOpen && <div className={styles.overlay} onClick={() => setMenuOpen(false)} />}

      <main className={styles.main}>
        {active === 'profile'  && <Profile entries={entries} loading={loading} fetchError={fetchError} onNavigate={goTo} />}
        {active === 'feed'     && <Feed
                                    onViewDish={(d, r) => setViewingDish({ dishName: d, restaurantName: r })}
                                    onViewRestaurant={setViewingRestaurant}
                                    onViewUser={setViewingUser}
                                  />}
        {active === 'reviews'  && <Reviews entries={entries} loading={loading} fetchError={fetchError} onNavigate={goTo} onDelete={handleDelete} />}
        {active === 'create'   && <CreateReview onSave={handleSave} />}
        {active === 'search'   && <Search
                                    onViewDish={(d, r) => setViewingDish({ dishName: d, restaurantName: r })}
                                    onViewRestaurant={setViewingRestaurant}
                                    onViewUser={setViewingUser}
                                  />}
        {active === 'trylist'  && <Trylist
                                    onViewDish={(d, r) => setViewingDish({ dishName: d, restaurantName: r })}
                                    onViewRestaurant={setViewingRestaurant}
                                  />}
        {active === 'notifs'   && <Notifications onBadgeChange={setNotifCount} />}
        {active === 'lists'    && <MyLists />}
      </main>
    </div>
  )
}

/* ── Icons ── */
function ProfileIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><circle cx="10" cy="6.5" r="3" stroke="currentColor" strokeWidth="1.5"/><path d="M3.5 17c0-3.314 2.91-6 6.5-6s6.5 2.686 6.5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function FeedIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><path d="M2 4h16M2 8h10M2 12h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><circle cx="15" cy="14" r="3" stroke="currentColor" strokeWidth="1.5"/><path d="M15 12.5v1.5l1 1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
}
function ReviewsIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><path d="M3 5h14M3 10h10M3 15h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><circle cx="16" cy="14.5" r="2.5" stroke="currentColor" strokeWidth="1.5"/><path d="M17.5 16.5l1.5 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function CreateIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7.5" stroke="currentColor" strokeWidth="1.5"/><path d="M10 7v6M7 10h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function SearchIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><circle cx="8.5" cy="8.5" r="5" stroke="currentColor" strokeWidth="1.5"/><path d="M13 13l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function TrylistIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><path d="M4 2.5h12a.5.5 0 01.5.5v14l-6.5-3.25L3.5 17V3a.5.5 0 01.5-.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/></svg>
}
function ListsIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><rect x="2" y="2" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><rect x="2" y="12.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><path d="M11 4.5h7M11 7h4.5M11 15h7M11 17.5h4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function BellIcon({ className }) {
  return <svg className={className} viewBox="0 0 20 20" fill="none"><path d="M10 2a6 6 0 00-6 6v3l-1.5 2.5h15L16 11V8a6 6 0 00-6-6z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M8.5 16.5a1.5 1.5 0 003 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function LogoutIcon() {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none"><path d="M7.5 10h9M13 6.5L16.5 10 13 13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M10 3.5H4.5v13H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function MenuIcon() {
  return <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
