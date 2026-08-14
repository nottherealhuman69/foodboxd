import { useState, useRef, useEffect } from 'react'
import { StarRating } from './StarRating'
import styles from './RatingDistribution.module.css'

export function RatingBars({ reviews }) {
  const counts = [5, 4, 3, 2, 1].map(star => reviews.filter(r => r.rating === star).length)
  const maxCount = Math.max(...counts, 1)
  const total = reviews.length

  return (
    <div className={styles.popover}>
      <p className={styles.popoverTitle}>{total} rating{total !== 1 ? 's' : ''}</p>
      <div className={styles.bars}>
        {[5, 4, 3, 2, 1].map((star, idx) => {
          const count = counts[idx]
          const pct = (count / maxCount) * 100
          return (
            <div key={star} className={styles.barRow}>
              <span className={styles.barLabel}>{star}★</span>
              <div className={styles.barTrack}>
                <div className={styles.barFill} style={{ width: `${pct}%` }} />
              </div>
              <span className={styles.barCount}>{count}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function RatingDistribution({ reviews, avgRating, size = 18 }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button className={styles.trigger} onClick={() => setOpen(o => !o)}>
        <StarRating rating={avgRating} size={size} />
        <span className={styles.avgNum}>{avgRating.toFixed(1)}</span>
        <span className={styles.label}>avg rating</span>
      </button>

      {open && <RatingBars reviews={reviews} />}
    </div>
  )
}