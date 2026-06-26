import { useState, useEffect, useRef } from 'react'
import styles from './CreateReview.module.css'

const MAX_REVIEW_CHARS = 1000
const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

// ── Searchable dropdown ───────────────────────────────────────────────────────
function SearchDropdown({ id, label, placeholder, options, value, onChange, disabled }) {
  const [query,  setQuery]  = useState(value || '')
  const [open,   setOpen]   = useState(false)
  const [focused, setFocused] = useState(false)
  const ref = useRef(null)

  // Sync external value changes (e.g. reset)
  useEffect(() => { setQuery(value || '') }, [value])

  // Close on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = options.filter(o => o.toLowerCase().includes(query.toLowerCase()))

  const select = (val) => {
    setQuery(val)
    onChange(val)
    setOpen(false)
  }

  const handleInput = (e) => {
    setQuery(e.target.value)
    onChange('')   // clear selection until they pick from list
    setOpen(true)
  }

  return (
    <div className={styles.dropdownWrap} ref={ref}>
      <div className={`${styles.dropdownInput} ${focused ? styles.dropdownFocused : ''} ${disabled ? styles.dropdownDisabled : ''}`}>
        <input
          id={id}
          type="text"
          className={styles.dropdownText}
          placeholder={placeholder}
          value={query}
          onChange={handleInput}
          onFocus={() => { setFocused(true); setOpen(true) }}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          autoComplete="off"
        />
        <span className={styles.dropdownChevron} onClick={() => !disabled && setOpen(o => !o)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </span>
      </div>

      {open && !disabled && (
        <div className={styles.dropdownList}>
          {filtered.length === 0 ? (
            <div className={styles.dropdownEmpty}>No matches — use "Add new" below</div>
          ) : (
            filtered.map(opt => (
              <button
                key={opt}
                type="button"
                className={`${styles.dropdownItem} ${opt === value ? styles.dropdownItemActive : ''}`}
                onMouseDown={() => select(opt)}
              >
                {opt}
                {opt === value && <span className={styles.checkmark}>✓</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function CreateReview({ onSave }) {
  const [form, setForm] = useState({
    type:           'restaurant',
    restaurantName: '',
    dishName:       '',
    recipe:         '',
    rating:         0,
    hoverRating:    0,
    review:         '',
  })
  const set = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  const [saving,    setSaving]    = useState(false)
  const [saveError, setSaveError] = useState('')

  // Catalog data
  const [restaurants,   setRestaurants]   = useState([])
  const [dishes,        setDishes]        = useState([])
  const [loadingCatalog, setLoadingCatalog] = useState(false)

  // "Add new" toggles
  const [newRestaurant, setNewRestaurant] = useState(false)
  const [newDish,       setNewDish]       = useState(false)

  const token = localStorage.getItem('token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  // Load restaurants on mount
  useEffect(() => {
    async function load() {
      setLoadingCatalog(true)
      try {
        const res = await fetch('/api/restaurants', { headers: authHeaders })
        if (res.ok) setRestaurants(await res.json())
      } catch {}
      finally { setLoadingCatalog(false) }
    }
    if (form.type === 'restaurant') load()
  }, [form.type, token])

  // Load dishes when restaurant is selected
  useEffect(() => {
    if (!form.restaurantName || newRestaurant) { setDishes([]); return }
    async function load() {
      try {
        const res = await fetch(
          `/api/restaurants/${encodeURIComponent(form.restaurantName)}/dishes`,
          { headers: authHeaders }
        )
        if (res.ok) setDishes(await res.json())
      } catch {}
    }
    load()
  }, [form.restaurantName, newRestaurant, token])

  // When switching to "add new restaurant", clear dish too
  const toggleNewRestaurant = () => {
    setNewRestaurant(v => !v)
    setNewDish(false)
    set('restaurantName', '')
    set('dishName', '')
    setDishes([])
  }

  // When switching to "add new dish"
  const toggleNewDish = () => {
    setNewDish(v => !v)
    set('dishName', '')
  }

  // When restaurant changes via dropdown, reset dish
  const handleRestaurantChange = (val) => {
    set('restaurantName', val)
    set('dishName', '')
    setNewDish(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.dishName.trim() || form.rating === 0) return
    setSaving(true)
    setSaveError('')
    try {
      await onSave({
        dishName:       form.dishName,
        type:           form.type,
        restaurantName: form.restaurantName,
        recipe:         form.recipe,
        rating:         form.rating,
        review:         form.review,
      })
      handleReset()
    } catch (err) {
      setSaveError(err.message || 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setForm({ type: 'restaurant', restaurantName: '', dishName: '', recipe: '', rating: 0, hoverRating: 0, review: '' })
    setNewRestaurant(false)
    setNewDish(false)
    setDishes([])
  }

  const charsLeft = MAX_REVIEW_CHARS - form.review.length
  const restaurantSelected = !!form.restaurantName.trim()
  const dishDisabled = form.type === 'restaurant' && !restaurantSelected && !newDish

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Log a Dish</h2>
        <p className={styles.sub}>Record what you ate, rate it, and capture the moment.</p>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>

        {/* 1. Type toggle */}
        <div className={styles.field}>
          <label className={styles.label}>Where was this?</label>
          <div className={styles.toggle}>
            <button type="button"
              className={`${styles.toggleBtn} ${form.type === 'restaurant' ? styles.toggleActive : ''}`}
              onClick={() => { set('type', 'restaurant'); handleReset() }}
            >
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
                <path d="M3 17V8.5M17 17V8.5M10 3v14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M3 8.5C3 6 5 4 7 4h6c2 0 4 2 4 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M2 17h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Restaurant
            </button>
            <button type="button"
              className={`${styles.toggleBtn} ${form.type === 'homemade' ? styles.toggleActive : ''}`}
              onClick={() => { set('type', 'homemade'); handleReset(); set('type', 'homemade') }}
            >
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
                <path d="M3 9.5L10 3l7 6.5V17a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                <path d="M7.5 18V12.5h5V18" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              </svg>
              Homemade
            </button>
          </div>
        </div>

        {/* 2. Restaurant section */}
        {form.type === 'restaurant' && (
          <div className={styles.field}>
            <div className={styles.labelRow}>
              <label className={styles.label} htmlFor="restaurantName">Restaurant</label>
              <button type="button" className={styles.toggleLink} onClick={toggleNewRestaurant}>
                {newRestaurant ? '← Pick existing' : '+ Add new restaurant'}
              </button>
            </div>

            {newRestaurant ? (
              <input
                id="restaurantName"
                className={styles.input}
                type="text"
                placeholder="Type the restaurant name…"
                value={form.restaurantName}
                onChange={e => set('restaurantName', e.target.value)}
                autoFocus
              />
            ) : (
              <SearchDropdown
                id="restaurantName"
                placeholder={loadingCatalog ? 'Loading…' : 'Search restaurants…'}
                options={restaurants}
                value={form.restaurantName}
                onChange={handleRestaurantChange}
                disabled={loadingCatalog}
              />
            )}
          </div>
        )}

        {/* 3. Dish name section */}
        <div className={styles.field}>
          <div className={styles.labelRow}>
            <label className={styles.label} htmlFor="dishName">
              Dish name <span className={styles.required}>*</span>
            </label>
            {form.type === 'restaurant' && restaurantSelected && !newRestaurant && (
              <button type="button" className={styles.toggleLink} onClick={toggleNewDish}>
                {newDish ? '← Pick existing' : '+ Add new dish'}
              </button>
            )}
          </div>

          {form.type === 'homemade' || newDish || newRestaurant ? (
            <input
              id="dishName"
              className={styles.input}
              type="text"
              placeholder="e.g. Chicken Biryani, Masala Dosa…"
              value={form.dishName}
              onChange={e => set('dishName', e.target.value)}
              required
            />
          ) : (
            <SearchDropdown
              id="dishName"
              placeholder={
                dishDisabled
                  ? 'Select a restaurant first'
                  : dishes.length === 0 && restaurantSelected
                  ? 'No dishes yet — use "+ Add new dish"'
                  : 'Search dishes…'
              }
              options={dishes}
              value={form.dishName}
              onChange={(val) => set('dishName', val)}
              disabled={dishDisabled}
            />
          )}
        </div>

        {/* 4. Recipe (homemade only) */}
        {form.type === 'homemade' && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor="recipe">
              Recipe <span className={styles.labelHint}>optional</span>
            </label>
            <textarea
              id="recipe"
              className={`${styles.input} ${styles.textarea}`}
              placeholder="Share ingredients, steps, or a link to the recipe…"
              rows={4}
              value={form.recipe}
              onChange={e => set('recipe', e.target.value)}
            />
          </div>
        )}

        {/* 5. Photo */}
        <div className={styles.field}>
          <label className={styles.label}>Photo <span className={styles.labelHint}>optional</span></label>
          <button type="button" className={styles.photoBtn} disabled>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            <span>Add a photo</span>
            <span className={styles.photoBadge}>Coming soon</span>
          </button>
        </div>

        {/* 6. Star rating */}
        <div className={styles.field}>
          <label className={styles.label}>Rating <span className={styles.required}>*</span></label>
          <div className={styles.starsRow}>
            {[1,2,3,4,5].map(n => (
              <button key={n} type="button" className={styles.starBtn}
                onMouseEnter={() => set('hoverRating', n)}
                onMouseLeave={() => set('hoverRating', 0)}
                onClick={() => set('rating', n)}
                aria-label={`${n} star${n > 1 ? 's' : ''}`}
              >
                <StarIcon filled={(form.hoverRating || form.rating) >= n} />
              </button>
            ))}
            {form.rating > 0 && (
              <span className={styles.ratingLabel}>{RATING_LABELS[form.rating]}</span>
            )}
          </div>
        </div>

        {/* 7. Review text */}
        <div className={styles.field}>
          <div className={styles.labelRow}>
            <label className={styles.label} htmlFor="review">
              Review <span className={styles.labelHint}>optional</span>
            </label>
            <span className={`${styles.charCount} ${charsLeft < 100 ? styles.charCountWarn : ''}`}>
              {charsLeft}
            </span>
          </div>
          <textarea
            id="review"
            className={`${styles.input} ${styles.textarea} ${styles.reviewArea}`}
            placeholder="What made it special? How was the texture, flavour, presentation…"
            rows={5}
            maxLength={MAX_REVIEW_CHARS}
            value={form.review}
            onChange={e => set('review', e.target.value)}
          />
        </div>

        {saveError && <p className={styles.saveError}>{saveError}</p>}
        <div className={styles.actions}>
          <button type="submit" className={styles.primaryBtn}
            disabled={!form.dishName.trim() || form.rating === 0 || saving}
          >
            {saving ? 'Saving…' : 'Save to diary'}
          </button>
          {(form.dishName || form.rating || form.review) && (
            <button type="button" className={styles.ghostBtn} onClick={handleReset}>Clear</button>
          )}
        </div>

      </form>
    </div>
  )
}

function StarIcon({ filled }) {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
        fill={filled ? '#6366F1' : 'transparent'}
        stroke={filled ? '#6366F1' : '#2d3155'}
        strokeWidth="1.5" strokeLinejoin="round"
      />
    </svg>
  )
}