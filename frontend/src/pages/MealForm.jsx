import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { StarPicker } from '../components/StarRating'
import { RATING_LABELS } from '../utils/reviews'
import { SearchDropdown } from './Createreview'
import styles from './CreateReview.module.css'

const MAX_REVIEW_CHARS = 1000
const MAX_DISHES = 12

let uid = 0
const emptyDish = () => ({ key: ++uid, name: '', rating: 0, hover: 0, note: '', isNew: false })

export default function MealForm({ onSaved }) {
  const [restaurantName, setRestaurantName] = useState('')
  const [newRestaurant,  setNewRestaurant]  = useState(false)
  const [title,          setTitle]          = useState('')
  const [rating,         setRating]         = useState(0)
  const [hoverRating,    setHoverRating]    = useState(0)
  const [review,         setReview]         = useState('')
  const [dishes,         setDishes]         = useState([emptyDish(), emptyDish()])

  const [restaurants,    setRestaurants]    = useState([])
  const [menu,           setMenu]           = useState([])
  const [loadingCatalog, setLoadingCatalog] = useState(false)
  const [saving,         setSaving]         = useState(false)
  const [saveError,      setSaveError]      = useState('')

  useEffect(() => {
    setLoadingCatalog(true)
    apiFetch('/api/restaurants')
      .then(r => r.ok ? r.json() : [])
      .then(setRestaurants)
      .catch(() => {})
      .finally(() => setLoadingCatalog(false))
  }, [])

  useEffect(() => {
    if (!restaurantName.trim() || newRestaurant) { setMenu([]); return }
    apiFetch(`/api/restaurants/${encodeURIComponent(restaurantName)}/dishes`)
      .then(r => r.ok ? r.json() : [])
      .then(setMenu)
      .catch(() => {})
  }, [restaurantName, newRestaurant])

  const patchDish = (key, changes) =>
    setDishes(prev => prev.map(d => (d.key === key ? { ...d, ...changes } : d)))

  const addDish    = () => setDishes(prev => prev.length >= MAX_DISHES ? prev : [...prev, emptyDish()])
  const removeDish = (key) => setDishes(prev => prev.length <= 1 ? prev : prev.filter(d => d.key !== key))

  const toggleNewRestaurant = () => {
    setNewRestaurant(v => !v)
    setRestaurantName('')
    setMenu([])
    setDishes(prev => prev.map(d => ({ ...d, name: '', isNew: false })))
  }

  const handleRestaurantChange = (val) => {
    setRestaurantName(val)
    setDishes(prev => prev.map(d => ({ ...d, name: '', isNew: false })))
  }

  const restaurantSelected = !!restaurantName.trim()
  // A dish picked in one row shouldn't be offered in the others.
  const optionsFor = (key) => {
    const taken = dishes.filter(d => d.key !== key).map(d => d.name.trim().toLowerCase())
    return menu.filter(o => !taken.includes(o.toLowerCase()))
  }

  const filled  = dishes.filter(d => d.name.trim() && d.rating > 0)
  const dishAvg = filled.length
    ? (filled.reduce((s, d) => s + d.rating, 0) / filled.length).toFixed(1)
    : null

  const duplicate = (() => {
    const names = filled.map(d => d.name.trim().toLowerCase())
    return names.find((n, i) => names.indexOf(n) !== i) || null
  })()

  const canSave = restaurantSelected && rating > 0 && filled.length > 0 && !duplicate && !saving

  const reset = () => {
    setRestaurantName(''); setNewRestaurant(false); setTitle('')
    setRating(0); setHoverRating(0); setReview('')
    setDishes([emptyDish(), emptyDish()]); setMenu([]); setSaveError('')
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

      {/* Restaurant */}
      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label} htmlFor="mealRestaurant">
            Restaurant <span className={styles.required}>*</span>
          </label>
          <button type="button" className={styles.toggleLink} onClick={toggleNewRestaurant}>
            {newRestaurant ? '← Pick existing' : '+ Add new restaurant'}
          </button>
        </div>
        {newRestaurant
          ? <input id="mealRestaurant" className={styles.input} type="text"
              placeholder="Type the restaurant name…" value={restaurantName}
              onChange={e => setRestaurantName(e.target.value)} autoFocus />
          : <SearchDropdown id="mealRestaurant"
              placeholder={loadingCatalog ? 'Loading…' : 'Search restaurants…'}
              options={restaurants} value={restaurantName}
              onChange={handleRestaurantChange} disabled={loadingCatalog} />
        }
      </div>

      {/* Meal title */}
      <div className={styles.field}>
        <label className={styles.label} htmlFor="mealTitle">
          Call it something <span className={styles.labelHint}>optional</span>
        </label>
        <input id="mealTitle" className={styles.input} type="text"
          placeholder="Sunday brunch with Arjun" value={title}
          maxLength={120} onChange={e => setTitle(e.target.value)} />
      </div>

      {/* Dishes */}
      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label}>
            Dishes <span className={styles.required}>*</span>
          </label>
          {dishAvg && <span className={styles.charCount}>Dishes average {dishAvg}</span>}
        </div>

        <div className={styles.dishRows}>
          {dishes.map((d, i) => {
            const freeText = newRestaurant || d.isNew
            const opts     = optionsFor(d.key)
            return (
              <div key={d.key} className={styles.dishRow} style={{ zIndex: dishes.length - i }}>
                <div className={styles.dishRowTop}>
                  <span className={styles.dishIndex}>{i + 1}</span>
                  <div className={styles.dishField}>
                    {freeText
                      ? <input className={styles.input} type="text"
                          placeholder="e.g. Chicken Biryani" value={d.name}
                          onChange={e => patchDish(d.key, { name: e.target.value })} />
                      : <SearchDropdown
                          placeholder={
                            !restaurantSelected ? 'Select a restaurant first'
                            : menu.length === 0 ? 'No dishes yet — use "+ New"'
                            : 'Search dishes…'
                          }
                          options={opts} value={d.name}
                          onChange={val => patchDish(d.key, { name: val })}
                          disabled={!restaurantSelected} />
                    }
                  </div>
                  <button type="button" className={styles.removeDishBtn}
                    onClick={() => removeDish(d.key)} disabled={dishes.length <= 1}
                    aria-label="Remove dish">×</button>
                </div>

                <div className={styles.dishRowBottom}>
                  <StarPicker
                    size={20}
                    value={d.rating}
                    hoverValue={d.hover}
                    onHover={n => patchDish(d.key, { hover: n })}
                    onLeave={() => patchDish(d.key, { hover: 0 })}
                    onChange={n => patchDish(d.key, { rating: n === d.rating ? 0 : n })}
                  />
                  {d.rating > 0 && (
                    <span className={styles.dishRatingLabel}>{RATING_LABELS[d.rating]}</span>
                  )}
                  {!newRestaurant && restaurantSelected && (
                    <button type="button" className={styles.toggleLink}
                      onClick={() => patchDish(d.key, { isNew: !d.isNew, name: '' })}>
                      {d.isNew ? '← Pick existing' : '+ New dish'}
                    </button>
                  )}
                </div>

                {d.name.trim() && (
                  <input className={`${styles.input} ${styles.dishNote}`} type="text"
                    placeholder="One line on this dish (optional)" value={d.note}
                    maxLength={200} onChange={e => patchDish(d.key, { note: e.target.value })} />
                )}
              </div>
            )
          })}
        </div>

        <button type="button" className={styles.addDishBtn} onClick={addDish}
          disabled={dishes.length >= MAX_DISHES}>
          + Add another dish
        </button>
        {duplicate && <p className={styles.saveError}>"{duplicate}" is listed twice.</p>}
      </div>

      {/* Overall rating */}
      <div className={styles.field}>
        <label className={styles.label}>
          How was the meal overall? <span className={styles.required}>*</span>
        </label>
        <div className={styles.starsRow}>
          <StarPicker
            value={rating}
            hoverValue={hoverRating}
            onHover={setHoverRating}
            onLeave={() => setHoverRating(0)}
            onChange={n => setRating(n === rating ? 0 : n)}
            size={28}
          />
          {rating > 0 && <span className={styles.ratingLabel}>{RATING_LABELS[rating]}</span>}
        </div>
      </div>

      {/* Meal notes */}
      <div className={styles.field}>
        <div className={styles.labelRow}>
          <label className={styles.label} htmlFor="mealReview">
            Notes <span className={styles.labelHint}>optional</span>
          </label>
          <span className={`${styles.charCount} ${charsLeft < 100 ? styles.charCountWarn : ''}`}>
            {charsLeft}
          </span>
        </div>
        <textarea id="mealReview" className={`${styles.input} ${styles.textarea} ${styles.reviewArea}`}
          rows={5} maxLength={MAX_REVIEW_CHARS}
          placeholder="Who you were with, how it was paced, what you'd order again…"
          value={review} onChange={e => setReview(e.target.value)} />
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