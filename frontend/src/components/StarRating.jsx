import { RATING_LABELS } from '../utils/reviews'

const STAR_PATH = 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z'

/**
 * <StarRating rating={3} size={13} showLabel />
 * size    – px, default 13
 * showLabel – append the text label (Poor / Fair / Good / Great / Outstanding)
 */
export function StarRating({ rating, size = 13, showLabel = false }) {
  const rounded = Math.round(rating)
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      {[1, 2, 3, 4, 5].map(n => (
        <svg key={n} width={size} height={size} viewBox="0 0 24 24" fill="none">
          <path
            d={STAR_PATH}
            fill={n <= rounded ? '#6366F1' : 'transparent'}
            stroke={n <= rounded ? '#6366F1' : '#2d3155'}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </svg>
      ))}
      {showLabel && (
        <span style={{ fontSize: 12, color: '#818cf8', fontWeight: 500, marginLeft: 2 }}>
          {RATING_LABELS[rounded]}
        </span>
      )}
    </span>
  )
}

/**
 * <StarPicker value={3} onChange={n => ...} />
 * Interactive version used in CreateReview.
 */
export function StarPicker({ value, hoverValue = 0, onHover, onLeave, onChange, size = 28 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      {[1, 2, 3, 4, 5].map(n => {
        const filled = (hoverValue || value) >= n
        return (
          <button
            key={n}
            type="button"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 0 }}
            onMouseEnter={() => onHover?.(n)}
            onMouseLeave={() => onLeave?.()}
            onClick={() => onChange(n)}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
          >
            <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
              <path
                d={STAR_PATH}
                fill={filled ? '#6366F1' : 'transparent'}
                stroke={filled ? '#6366F1' : '#2d3155'}
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )
      })}
    </span>
  )
}
