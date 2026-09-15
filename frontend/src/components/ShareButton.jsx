import { useState, useEffect, useRef } from 'react'
import styles from './ShareButton.module.css'

async function copyText(text) {
  // Clipboard API needs a secure context (https or localhost).
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch { /* fall through */ }
  }
  // Fallback: http://192.168.x.x during dev, older Safari, etc.
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.cssText = 'position:fixed;top:-1000px;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}

export default function ShareButton({ url, label = 'Share' }) {
  const [status, setStatus] = useState('idle')   // idle | copied | failed
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  const handleClick = async () => {
    const ok = await copyText(url)
    setStatus(ok ? 'copied' : 'failed')
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setStatus('idle'), 2500)
  }

  return (
    <div className={styles.wrap}>
      <button
        className={`${styles.btn} ${status === 'copied' ? styles.copied : ''}`}
        onClick={handleClick}
        title="Copy link to this dish"
      >
        {status === 'copied' ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M4 12.5l5 5L20 6.5" stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M10 13.5a4 4 0 006 .5l3-3a4 4 0 00-5.5-5.5L12 7"
                  stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            <path d="M14 10.5a4 4 0 00-6-.5l-3 3A4 4 0 0010.5 18.5L12 17"
                  stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        )}
        {status === 'copied' ? 'Link copied' : label}
      </button>

      {status === 'failed' && (
        <input className={styles.fallback} readOnly value={url}
               onFocus={e => e.target.select()} />
      )}
    </div>
  )
}