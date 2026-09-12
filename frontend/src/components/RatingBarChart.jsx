import styles from './RatingBarChart.module.css'

const STARS = [1, 2, 3, 4, 5]

/**
 * RatingBarChart — a vertical bar graph of how many reviews gave each star rating.
 *
 *   x-axis : star rating, 1 → 5
 *   y-axis : number of reviews
 *
 * Props
 *   reviews   – array of objects with a `rating` field. Counts are derived from it.
 *   counts    – optional [n1, n2, n3, n4, n5] to bypass `reviews` entirely.
 *   height    – px height of the plot area (bars only). Default 64.
 *   compact   – strips the axes/captions down to bars + star numbers, for list rows.
 *   showTotal – show the "N reviews" line underneath. Ignored when compact.
 */
export default function RatingBarChart({
  reviews = [],
  counts: countsProp,
  height = 64,
  compact = false,
  showTotal = true,
}) {
  const counts = countsProp
    ?? STARS.map(star => reviews.filter(r => Number(r.rating) === star).length)

  const total    = counts.reduce((a, b) => a + b, 0)
  const maxCount = Math.max(...counts, 1)

  const plotH  = compact ? 24 : height
  const topPad = compact ? 0 : 14          // headroom for the count labels above bars

  // Zero-count ratings keep a 2px stub so the category still reads on the axis.
  const barHeight = c => (c === 0 ? 2 : Math.max(3, Math.round((c / maxCount) * plotH)))

  const tip = (star, c) =>
    `${c} ${c === 1 ? 'review' : 'reviews'} at ${star} star${star === 1 ? '' : 's'}`

  const summary = `Ratings: ${STARS.map((s, i) => `${s} star ${counts[i]}`).join(', ')}`

  if (compact) {
    return (
      <div className={styles.compactWrap} role="img" aria-label={summary}>
        <div className={styles.compactPlot} style={{ height: plotH }}>
          {STARS.map((star, i) => (
            <div key={star} className={styles.compactCol} title={tip(star, counts[i])}>
              <div
                className={counts[i] > 0 ? styles.compactBar : styles.compactBarEmpty}
                style={{ height: barHeight(counts[i]) }}
              />
            </div>
          ))}
        </div>
        <div className={styles.compactAxis}>
          {STARS.map(star => (
            <span key={star} className={styles.compactTick}>{star}</span>
          ))}
        </div>
      </div>
    )
  }

  // y-axis ticks: max, an optional midpoint, and zero.
  const mid   = Math.round(maxCount / 2)
  const ticks = [maxCount]
  if (maxCount >= 4 && mid > 0 && mid < maxCount) ticks.push(mid)
  ticks.push(0)

  return (
    <div className={styles.wrap} role="img" aria-label={summary}>
      <div className={styles.chart}>
        <span className={styles.yCaption} style={{ height: plotH + topPad }}>
          reviews
        </span>

        <div className={styles.yAxis} style={{ height: plotH + topPad }}>
          {ticks.map(t => (
            <span
              key={t}
              className={styles.yTick}
              style={{ bottom: (t / maxCount) * plotH - 5 }}
            >
              {t}
            </span>
          ))}
        </div>

        <div className={styles.plotWrap}>
          <div className={styles.plot} style={{ height: plotH + topPad }}>
            {ticks.filter(t => t > 0).map(t => (
              <div
                key={`grid-${t}`}
                className={styles.grid}
                style={{ bottom: (t / maxCount) * plotH }}
              />
            ))}

            {STARS.map((star, i) => {
              const c = counts[i]
              const h = barHeight(c)
              return (
                <div key={star} className={styles.col} title={tip(star, c)}>
                  {c > 0 && (
                    <span className={styles.count} style={{ bottom: h + 3 }}>{c}</span>
                  )}
                  <div
                    className={c > 0 ? styles.bar : styles.barEmpty}
                    style={{ height: h }}
                  />
                </div>
              )
            })}
          </div>

          <div className={styles.xAxis}>
            {STARS.map(star => (
              <span key={star} className={styles.xTick}>{star}★</span>
            ))}
          </div>
        </div>
      </div>

      {showTotal && (
        <span className={styles.total}>
          {total} {total === 1 ? 'review' : 'reviews'}
        </span>
      )}
    </div>
  )
}
