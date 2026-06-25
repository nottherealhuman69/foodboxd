import { useState } from 'react'
import styles from './CreateReview.module.css'

const MAX_REVIEW_CHARS = 1000

export default function CreateReview({ onSave }) {
  const [form, setForm] = useState({
    dishName: '',
    type: 'restaurant',       // 'restaurant' | 'homemade'
    restaurantName: '',
    recipe: '',
    rating: 0,
    hoverRating: 0,
    review: '',
  })

  const set = (field, value) => setForm(prev => ({ ...prev, [field]: value }))

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.dishName.trim() || form.rating === 0) return
    setSaving(true)
    setSaveError('')
    try {
      await onSave({
        dishName: form.dishName,
        type: form.type,
        restaurantName: form.restaurantName,
        recipe: form.recipe,
        rating: form.rating,
        review: form.review,
      })
      handleReset()
    } catch (err) {
      setSaveError(err.message || 'Failed to save. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setForm({
      dishName: '',
      type: 'restaurant',
      restaurantName: '',
      recipe: '',
      rating: 0,
      hoverRating: 0,
      review: '',
    })
  }


  const charsLeft = MAX_REVIEW_CHARS - form.review.length

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h2 className={styles.title}>Log a Dish</h2>
        <p className={styles.sub}>Record what you ate, rate it, and capture the moment.</p>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>

        {/* Dish name */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="dishName">Dish name <span className={styles.required}>*</span></label>
          <input
            id="dishName"
            className={styles.input}
            type="text"
            placeholder="e.g. Chicken Biryani, Masala Dosa…"
            value={form.dishName}
            onChange={e => set('dishName', e.target.value)}
            required
          />
        </div>

        {/* Type toggle */}
        <div className={styles.field}>
          <label className={styles.label}>Where was this?</label>
          <div className={styles.toggle}>
            <button
              type="button"
              className={`${styles.toggleBtn} ${form.type === 'restaurant' ? styles.toggleActive : ''}`}
              onClick={() => set('type', 'restaurant')}
            >
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
                <path d="M3 17V8.5M17 17V8.5M10 3v14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M3 8.5C3 6 5 4 7 4h6c2 0 4 2 4 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M2 17h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Restaurant
            </button>
            <button
              type="button"
              className={`${styles.toggleBtn} ${form.type === 'homemade' ? styles.toggleActive : ''}`}
              onClick={() => set('type', 'homemade')}
            >
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
                <path d="M3 9.5L10 3l7 6.5V17a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                <path d="M7.5 18V12.5h5V18" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              </svg>
              Homemade
            </button>
          </div>
        </div>

        {/* Conditional fields */}
        {form.type === 'restaurant' && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor="restaurantName">Restaurant</label>
            <input
              id="restaurantName"
              className={styles.input}
              type="text"
              placeholder="e.g. Paradise Biryani, MTR…"
              value={form.restaurantName}
              onChange={e => set('restaurantName', e.target.value)}
            />
          </div>
        )}

        {form.type === 'homemade' && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor="recipe">
              Recipe
              <span className={styles.labelHint}>optional</span>
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

        {/* Photo */}
        <div className={styles.field}>
          <label className={styles.label}>
            Photo
            <span className={styles.labelHint}>optional</span>
          </label>
          <button type="button" className={styles.photoBtn} disabled>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            <span>Add a photo</span>
            <span className={styles.photoBadge}>Coming soon</span>
          </button>
        </div>

        {/* Star rating */}
        <div className={styles.field}>
          <label className={styles.label}>Rating <span className={styles.required}>*</span></label>
          <div className={styles.starsRow}>
            {[1, 2, 3, 4, 5].map(n => (
              <button
                key={n}
                type="button"
                className={styles.starBtn}
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

        {/* Review text */}
        <div className={styles.field}>
          <div className={styles.labelRow}>
            <label className={styles.label} htmlFor="review">
              Review
              <span className={styles.labelHint}>optional</span>
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

        {/* Submit */}
        {saveError && <p className={styles.saveError}>{saveError}</p>}
        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.primaryBtn}
            disabled={!form.dishName.trim() || form.rating === 0 || saving}
          >
            {saving ? 'Saving…' : 'Save to diary'}
          </button>
          {(form.dishName || form.rating || form.review) && (
            <button type="button" className={styles.ghostBtn} onClick={handleReset}>
              Clear
            </button>
          )}
        </div>

      </form>
    </div>
  )
}

/* ── Helpers ── */
const RATING_LABELS = {
  1: 'Poor',
  2: 'Fair',
  3: 'Good',
  4: 'Great',
  5: 'Outstanding',
}

function renderStars(n) {
  return '★'.repeat(n) + '☆'.repeat(5 - n)
}

function StarIcon({ filled }) {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
        fill={filled ? '#6366F1' : 'transparent'}
        stroke={filled ? '#6366F1' : '#2d3155'}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  )
}