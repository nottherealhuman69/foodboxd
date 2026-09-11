import { useState, useRef, useEffect } from 'react'
import styles from './TagPicker.module.css'

/**
 * Multi-select picker for tagging companions ("went with").
 *
 * props:
 *  - options: [{ email, username }]  — people you follow
 *  - value:   [email, ...]           — selected emails
 *  - onChange(nextEmails)
 */
export default function TagPicker({ options = [], value = [], onChange }) {
  const [query, setQuery] = useState('')
  const [open,  setOpen]  = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (options.length === 0) {
    return <p className={styles.hint}>Follow people to tag who you were with.</p>
  }

  const byEmail = Object.fromEntries(options.map(o => [o.email, o]))
  const add    = (email) => { if (!value.includes(email)) onChange([...value, email]); setQuery('') }
  const remove = (email) => onChange(value.filter(e => e !== email))

  const available = options.filter(o =>
    !value.includes(o.email) &&
    (o.username.toLowerCase().includes(query.toLowerCase()) || o.email.toLowerCase().includes(query.toLowerCase()))
  )

  return (
    <div className={styles.wrap} ref={ref}>
      {value.length > 0 && (
        <div className={styles.chips}>
          {value.map(email => (
            <span key={email} className={styles.chip}>
              @{byEmail[email]?.username || email.split('@')[0]}
              <button type="button" className={styles.chipX} onClick={() => remove(email)} aria-label="Remove">×</button>
            </span>
          ))}
        </div>
      )}
      <input
        type="text"
        className={styles.input}
        placeholder="Search people you follow…"
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
      />
      {open && available.length > 0 && (
        <div className={styles.list}>
          {available.map(o => (
            <button key={o.email} type="button" className={styles.item} onMouseDown={() => add(o.email)}>
              @{o.username}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Renders "with @a, @b" from a list of tagged users [{email, username}].
 * onViewUser?(email) makes the names clickable.
 */
export function TaggedWith({ tagged = [], onViewUser, className }) {
  if (!tagged || tagged.length === 0) return null
  return (
    <span className={`${styles.taggedWith} ${className || ''}`}>
      with{' '}
      {tagged.map((t, i) => (
        <span key={t.email}>
          <button
            type="button"
            className={styles.taggedName}
            onClick={(e) => { e.stopPropagation(); onViewUser?.(t.email) }}
            disabled={!onViewUser}
          >
            @{t.username}
          </button>
          {i < tagged.length - 1 ? ', ' : ''}
        </span>
      ))}
    </span>
  )
}
