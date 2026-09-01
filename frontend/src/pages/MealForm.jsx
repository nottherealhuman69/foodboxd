import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarPicker } from '../components/StarRating'
import styles from './CreateReview.module.css'

const MAX_REVIEW_CHARS = 500
const MAX_DISHES = 12

let uid = 0
const emptyDish = () => ({ key: ++uid, name: '', rating: 0, hover: 0, note: '' })

export default function MealForm({ onSaved }) {
  const [restaurantName, setRestaurantName] = useState('')
  const [newRestaurant,  setNewRestaurant]  = useState(false)
  const [title,          setTitle]          = useState('')
  const [rating,         setRating]         = useState(0)
  const [hoverRating,    setHoverRating]    = useState(0)
  const [review,         setReview]         = useState('')
  const [dishes,         setDishes]         = useState([emptyDish(), emptyDish()])

  const [restaurants, setRestaurants] = useState([])
  const [menu,        setMenu]        = useState([])
  const [saving,      setSaving]      = useState(false)
  const [saveError,   setSaveError]   = useState('')

  useEffect(() => {
    apiFetch('/api/restaurants')
      .then(r => (r.ok ? r.json() : []))
      .then(setRestaurants)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!restaurantName.trim() || newRestaurant) { setMenu([]); return }
    apiFetch(`/api/restaurants/${encodeURIComponent(restaurantName)}/dishes`)
      .then(r => (r.ok ? r.json() : []))
      .then(list => setMenu(list.map(d => (typeof d === 'string' ? d : d.dish_name))))
      .catch(() => {})
  }, [restaurantName, newRestaurant])

  const patchDish = (key, changes) =>
    setDishes(prev => prev.map(d => (d.key === key ? { ...d, ...changes } : d)))

  const addDish    = () => setDishes(prev => (prev.length >= MAX_DISHES ? prev : [...prev, emptyDish()]))
  const removeDish = (key) => setDishes(prev => (prev.length <= 1 ? prev : prev.filter(d => d.key !== key)))

  const filled = dishes.filter(d => d.name.trim() && d.rating > 0)
  const dishAvg = filled.length
    ? (filled.reduce((s, d) => s + d.rating, 0) / filled.length).toFixed(1)
    : null

  const duplicate = (() => {
    const names = filled.map(d => d.name.trim().toLowerCase())
    return names.find((n, i) => names.indexOf(n) !== i) || null
  })()

  const canSave = restaurantName.trim() && rating > 0 && filled.length > 0 && !duplicate && !saving

  const reset = () => {
    setRestaurantName(''); setNewRestaurant(false); setTitle('')
    setRating(0); setHoverRating(0); setReview('')
    setDishes([emptyDish(), emptyDish()]); setMenu([])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSave) return
    setSaving(true)
    setSaveError('')
    try {
      const res = await apiFetch('/api/meals', {
        method: 'POST',
        body: JSON.stringify({
          restaurant_name: restaurantName.trim(),
          title:           title.trim() || null,
          rating,
          review:          review.trim() || null,
          dishes: filled.map(d => ({
            dish_name: d.name.trim(),
            rating:    d.rating,
            review:    d.note.trim() || null,
          })),
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save meal')
      }
      const saved = await res.json()
      reset()
      onSaved?.(saved)
    } catch (err) {
      setSaveError(err.message || 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const charsLeft = MAX_REVIEW_CHARS - review.length

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <datalist id="meal-restaurants">
        {restaurants.map(r => <option key={r} value={r} />)}
      </datalist>
      <datalist id="meal-dishes">
        {menu.map(d => <option key={d} value={d} />)}
      </datalist>

      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label} htmlFor="mealRestaurant">Restaurant</label>
          <button type="button" className={styles.toggleLink}
            onClick={() => { setNewRestaurant(v => !v); setRestaurantName(''); setMenu([]) }}>
            {newRestaurant ? '← Pick existing' : '+ Add new restaurant'}
          </button>
        </div>
        <input
          id="mealRestaurant"
          className={styles.input}
          list={newRestaurant ? undefined : 'meal-restaurants'}
          placeholder={newRestaurant ? 'Name the restaurant' : 'Start typing…'}
          value={restaurantName}
          onChange={e => setRestaurantName(e.target.value)}
          autoComplete="off"
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="mealTitle">Call it something (optional)</label>
        <input
          id="mealTitle"
          className={styles.input}
          placeholder="Sunday brunch with Arjun"
          value={title}
          maxLength={120}
          onChange={e => setTitle(e.target.value)}
        />
      </div>

      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label}>Dishes</label>
          {dishAvg && <span className={styles.charCount}>Dishes average {dishAvg}</span>}
        </div>

        <div className={styles.dishRows}>
          {dishes.map((d, i) => (
            <div key={d.key} className={styles.dishRow}>
              <div className={styles.dishRowTop}>
                <input
                  className={`${styles.input} ${styles.dishInput}`}
                  list="meal-dishes"
                  placeholder={`Dish ${i + 1}`}
                  value={d.name}
                  onChange={e => patchDish(d.key, { name: e.target.value })}
                  autoComplete="off"
                />
                <StarPicker
                  size={20}
                  value={d.rating}
                  hoverValue={d.hover}
                  onHover={n => patchDish(d.key, { hover: n })}
                  onLeave={() => patchDish(d.key, { hover: 0 })}
                  onChange={n => patchDish(d.key, { rating: n === d.rating ? 0 : n })}
                />
                <button
                  type="button"
                  className={styles.removeDishBtn}
                  onClick={() => removeDish(d.key)}
                  disabled={dishes.length <= 1}
                  aria-label="Remove dish"
                >×</button>
              </div>
              {d.name.trim() && (
                <input
                  className={`${styles.input} ${styles.dishNote}`}
                  placeholder="One line on this dish (optional)"
                  value={d.note}
                  maxLength={200}
                  onChange={e => patchDish(d.key, { note: e.target.value })}
                />
              )}
            </div>
          ))}
        </div>

        <button type="button" className={styles.addDishBtn} onClick={addDish}
          disabled={dishes.length >= MAX_DISHES}>
          + Add another dish
        </button>
        {duplicate && <p className={styles.saveError}>"{duplicate}" is listed twice.</p>}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>How was the meal overall?</label>
        <div className={styles.starsRow}>
          <StarPicker
            value={rating}
            hoverValue={hoverRating}
            onHover={setHoverRating}
            onLeave={() => setHoverRating(0)}
            onChange={n => setRating(n === rating ? 0 : n)}
          />
        </div>
      </div>

      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label} htmlFor="mealReview">Notes on the meal</label>
          <span className={`${styles.charCount} ${charsLeft < 50 ? styles.charCountWarn : ''}`}>
            {charsLeft}
          </span>
        </div>
        <textarea
          id="mealReview"
          className={`${styles.input} ${styles.textarea} ${styles.reviewArea}`}
          rows={4}
          maxLength={MAX_REVIEW_CHARS}
          placeholder="Who you were with, how it was paced, what you'd order again…"
          value={review}
          onChange={e => setReview(e.target.value)}
        />
      </div>

      {saveError && <p className={styles.saveError}>{saveError}</p>}

      <div className={styles.actions}>
        <button type="submit" className={styles.primaryBtn} disabled={!canSave}>
          {saving ? 'Saving…' : `Save meal${filled.length ? ` (${filled.length} dishes)` : ''}`}
        </button>
        <button type="button" className={styles.ghostBtn} onClick={reset}>Clear</button>
      </div>
    </form>
  )
}