import shared from './shared.module.css'

/**
 * <StatGrid cols={4}>
 *   <StatCard count={42} label="Dishes logged" />
 *   <StatCard count="4.2" label="Avg rating" />
 * </StatGrid>
 */
export function StatGrid({ cols = 4, children }) {
  return (
    <div
      className={shared.statsRow}
      style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
    >
      {children}
    </div>
  )
}

export function StatCard({ count, label }) {
  return (
    <div className={shared.statCard}>
      <span className={shared.statCount}>{count ?? '—'}</span>
      <span className={shared.statLabel}>{label}</span>
    </div>
  )
}
