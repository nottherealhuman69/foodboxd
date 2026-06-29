import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarPicker } from '../components/StarRating'
import { RATING_LABELS } from '../utils/reviews'
import styles from './CreateReview.module.css'

const MAX_REVIEW_CHARS = 1000

function SearchDropdown({ id, placeholder, options, value, onChange, disabled }) {
  const [query,   setQuery]   = useState(value || '')
  const [open,    setOpen]    = useState(false)
  const [focused, setFocused] = useState(false)
  const ref = useRef(null)

  useEffect(() => { setQuery(value || '') }, [value])

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = options.filter(o => o.toLowerCase().includes(query.toLowerCase()))
  const select = (val) => { setQuery(val); onChange(val); setOpen(false) }
  const handleInput = (e) => { setQuery(e.target.value); onChange(''); setOpen(true) }

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
          {filtered.length === 0
            ? <div className={styles.dropdownEmpty}>No matches — use "Add new" below</div>
            : filtered.map(opt => (
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
          }
        </div>
      )}
    </div>
  )
}

export default function CreateReview({ onSave }) {
  const [form, setForm] = useState({
    type: 'restaurant', restaurantName: '', dishName: '',
    recipe: '', rating: 0, hoverRating: 0, review: '',
  })
  const set = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  const [saving,         setSaving]         = useState(false)
  const [saveError,      setSaveError]      = useState('')
  const [restaurants,    setRestaurants]    = useState([])
  const [dishes,         setDishes]         = useState([])
  const [loadingCatalog, setLoadingCatalog] = useState(false)
  const [newRestaurant,  setNewRestaurant]  = useState(false)
  const [newDish,        setNewDish]        = useState(false)

  useEffect(() => {
    if (form.type !== 'restaurant') return
    setLoadingCatalog(true)
    apiFetch('/api/restaurants')
      .then(r => r.ok ? r.json() : [])
      .then(setRestaurants)
      .catch(() => {})
      .finally(() => setLoadingCatalog(false))
  }, [form.type])

  useEffect(() => {
    if (!form.restaurantName || newRestaurant) { setDishes([]); return }
    apiFetch(`/api/restaurants/${encodeURIComponent(form.restaurantName)}/dishes`)
      .then(r => r.ok ? r.json() : [])
      .then(setDishes)
      .catch(() => {})
  }, [form.restaurantName, newRestaurant])

  const toggleNewRestaurant = () => {
    setNewRestaurant(v => !v)
    setNewDish(false)
    set('restaurantName', '')
    set('dishName', '')
    setDishes([])
  }

  const toggleNewDish = () => { setNewDish(v => !v); set('dishName', '') }

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
        dishName: form.dishName, type: form.type,
        restaurantName: form.restaurantName, recipe: form.recipe,
        rating: form.rating, review: form.review,
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

  const charsLeft          = MAX_REVIEW_CHARS - form.review.length
  const restaurantSelected = !!form.restaurantName.trim()
  const dishDisabled       = form.type === 'restaurant' && !restaurantSelected && !newDish

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

        {/* 2. Restaurant */}
        {form.type === 'restaurant' && (
          <div className={styles.field}>
            <div className={styles.labelRow}>
              <label className={styles.label} htmlFor="restaurantName">Restaurant</label>
              <button type="button" className={styles.toggleLink} onClick={toggleNewRestaurant}>
                {newRestaurant ? '← Pick existing' : '+ Add new restaurant'}
              </button>
            </div>
            {newRestaurant
              ? <input id="restaurantName" className={styles.input} type="text"
                  placeholder="Type the restaurant name…" value={form.restaurantName}
                  onChange={e => set('restaurantName', e.target.value)} autoFocus />
              : <SearchDropdown id="restaurantName"
                  placeholder={loadingCatalog ? 'Loading…' : 'Search restaurants…'}
                  options={restaurants} value={form.restaurantName}
                  onChange={handleRestaurantChange} disabled={loadingCatalog} />
            }
          </div>
        )}

        {/* 3. Dish name */}
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
          {form.type === 'homemade' || newDish || newRestaurant
            ? <input id="dishName" className={styles.input} type="text"
                placeholder="e.g. Chicken Biryani, Masala Dosa…" value={form.dishName}
                onChange={e => set('dishName', e.target.value)} required />
            : <SearchDropdown id="dishName"
                placeholder={
                  dishDisabled ? 'Select a restaurant first'
                  : dishes.length === 0 && restaurantSelected ? 'No dishes yet — use "+ Add new dish"'
                  : 'Search dishes…'
                }
                options={dishes} value={form.dishName}
                onChange={val => set('dishName', val)} disabled={dishDisabled} />
          }
        </div>

        {/* 4. Recipe (homemade only) */}
        {form.type === 'homemade' && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor="recipe">
              Recipe <span className={styles.labelHint}>optional</span>
            </label>
            <textarea id="recipe" className={`${styles.input} ${styles.textarea}`}
              placeholder="Share ingredients, steps, or a link to the recipe…"
              rows={4} value={form.recipe} onChange={e => set('recipe', e.target.value)} />
          </div>
        )}

        {/* 5. Photo placeholder */}
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
            <StarPicker
              value={form.rating}
              hoverValue={form.hoverRating}
              onHover={n => set('hoverRating', n)}
              onLeave={() => set('hoverRating', 0)}
              onChange={n => set('rating', n)}
              size={28}
            />
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
          <textarea id="review" className={`${styles.input} ${styles.textarea} ${styles.reviewArea}`}
            placeholder="What made it special? How was the texture, flavour, presentation…"
            rows={5} maxLength={MAX_REVIEW_CHARS}
            value={form.review} onChange={e => set('review', e.target.value)} />
        </div>

        {saveError && <p className={styles.saveError}>{saveError}</p>}

        <div className={styles.actions}>
          <button type="submit" className={styles.primaryBtn}
            disabled={!form.dishName.trim() || form.rating === 0 || saving}>
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
