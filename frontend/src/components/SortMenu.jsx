import { useState, useRef, useEffect } from 'react'
import styles from './SortMenu.module.css'

export default function SortMenu({ options, value, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const current = options.find(o => o.id === value) || options[0]

  return (
    <div className={styles.bar}>
      <div className={styles.wrap} ref={ref}>
        <button type="button" className={styles.trigger}
                onClick={() => setOpen(o => !o)} aria-haspopup="listbox" aria-expanded={open}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M3 6h18M6 12h12M10 18h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          Sort: <strong>{current.label}</strong>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className={open ? styles.chevOpen : ''}>
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        {open && (
          <div className={styles.menu} role="listbox">
            {options.map(o => (
              <button key={o.id} type="button" role="option" aria-selected={o.id === value}
                      className={`${styles.option} ${o.id === value ? styles.active : ''}`}
                      onClick={() => { onChange(o.id); setOpen(false) }}>
                {o.label}
                {o.id === value && <span className={styles.check}>✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}