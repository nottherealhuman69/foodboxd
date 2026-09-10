import { useState, useId } from 'react'
import { RATING_LABELS } from '../utils/reviews'

const STAR_PATH = 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z'

/**
 * A single star filled from 0 (empty) to 1 (full) — the gradient's hard stop
 * at `fill` gives us clean half-stars.
 */
function Star({ fill, gid, size }) {
  const active = fill > 0
  const pct = `${Math.max(0, Math.min(1, fill)) * 100}%`
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <defs>
        <linearGradient id={gid}>
          <stop offset={pct} stopColor="#6366F1" />
          <stop offset={pct} stopColor="transparent" />
        </linearGradient>
      </defs>
      <path
        d={STAR_PATH}
        fill={`url(#${gid})`}
        stroke={active ? '#6366F1' : '#2d3155'}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/**
 * <StarRating rating={3.5} size={13} showLabel />
 * size    – px, default 13
 * showLabel – append the text label (Poor / Fair / Good / Great / Outstanding)
 */
export function StarRating({ rating, size = 13, showLabel = false }) {
  const uid = useId()
  const r = Number(rating) || 0
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      {[1, 2, 3, 4, 5].map(n => (
        <Star key={n} fill={r - (n - 1)} gid={`${uid}-r-${n}`} size={size} />
      ))}
      {showLabel && (
        <span style={{ fontSize: 12, color: '#818cf8', fontWeight: 500, marginLeft: 2 }}>
          {RATING_LABELS[Math.round(r)]}
        </span>
      )}
    </span>
  )
}

/**
 * <StarPicker value={3.5} onChange={n => ...} />
 * Interactive, supports half stars — clicking the left half of a star picks .5,
 * the right half picks the whole star. Manages its own hover state.
 */
export function StarPicker({ value, onChange, size = 28 }) {
  const [hover, setHover] = useState(0)
  const uid = useId()
  const display = hover || value

  const valueFromEvent = (n, e) => {
    const { left, width } = e.currentTarget.getBoundingClientRect()
    return (e.clientX - left) < width / 2 ? n - 0.5 : n
  }

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          type="button"
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 0 }}
          onMouseMove={e => setHover(valueFromEvent(n, e))}
          onMouseLeave={() => setHover(0)}
          onClick={e => onChange(valueFromEvent(n, e))}
          aria-label={`${n} star${n > 1 ? 's' : ''}`}
        >
          <Star fill={display - (n - 1)} gid={`${uid}-p-${n}`} size={size} />
        </button>
      ))}
    </span>
  )
}
