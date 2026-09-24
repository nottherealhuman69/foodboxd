// frontend/src/components/ForkButton.jsx
import styles from './ForkButton.module.css'

/**
 * Sends the post's contents to the Log page as a starting point.
 * Nothing is saved until the user submits that form.
 *
 * props:
 *  - onFork()
 */
export default function ForkButton({ onFork }) {
  return (
    <button
      type="button"
      className={styles.btn}
      onClick={(e) => { e.stopPropagation(); onFork?.() }}
      title="Copy this into your log and edit it"
    >
      🍴 Fork
    </button>
  )
}

/**
 * "Forked from @name's Chicken Biryani" — shown on a post that was forked.
 *
 * props:
 *  - source: { kind, id, username, user_email, title } | null
 *  - onViewPost?(kind, id)
 *  - onViewUser?(email)
 */
export function ForkedFrom({ source, onViewPost, onViewUser }) {
  if (!source) return null
  return (
    <p className={styles.forkedFrom}>
      🍴 Forked from{' '}
      <button type="button" className={styles.link}
              onClick={(e) => { e.stopPropagation(); onViewUser?.(source.user_email) }}>
        @{source.username}
      </button>
      {"'s "}
      <button type="button" className={styles.link}
              onClick={(e) => { e.stopPropagation(); onViewPost?.(source.kind, source.id) }}>
        {source.title}
      </button>
    </p>
  )
}

/**
 * Banner at the top of the log form while a fork is in progress.
 *
 * props:
 *  - source: { kind, username, dish_name?, title?, restaurant_name? }
 *  - onClear()
 */
export function ForkBanner({ source, onClear }) {
  if (!source) return null
  const what = source.kind === 'meal'
    ? (source.title || `meal at ${source.restaurant_name}`)
    : source.dish_name
  return (
    <div className={styles.banner}>
      <span>🍴 Forking @{source.username}&apos;s <strong>{what}</strong> — change anything, then save it as your own.</span>
      <button type="button" className={styles.bannerClear} onClick={onClear}>Start blank</button>
    </div>
  )
}