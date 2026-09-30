import { useState, useRef, useEffect, useMemo } from 'react'
import SortMenu from './SortMenu'
import { EMPTY_FILTERS, countActiveFilters, restaurantOf } from '../utils/listFilter'
import styles from './ListToolbar.module.css'

const TYPES = [
  { id: 'all',        label: 'All' },
  { id: 'dish',       label: 'Dishes' },
  { id: 'restaurant', label: 'Restaurants' },
  { id: 'recipe',     label: 'Recipes' },
]
const TRIED = [
  { id: 'any',     label: 'Any' },
  { id: 'tried',   label: 'Tried' },
  { id: 'untried', label: 'Not tried yet' },
]

const byText = (a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' })

function uniqueSorted(values) {
  const seen = new Map()
  values.filter(Boolean).forEach(v => { if (!seen.has(v.toLowerCase())) seen.set(v.toLowerCase(), v) })
  return [...seen.values()].sort(byText)
}

export default function ListToolbar({
  items, filters, onFiltersChange,
  sort, onSortChange, sortOptions,
  shownCount, showAddedBy = false,
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const set = (key, value) => onFiltersChange({ ...filters, [key]: value })
  const active = countActiveFilters(filters)
  const isFiltering = active > 0 || filters.q.trim() !== ''

  const restaurants = useMemo(() => uniqueSorted(items.map(restaurantOf)), [items])
  const adders      = useMemo(() => uniqueSorted(items.map(i => i.added_by_username)), [items])
  const typeCounts  = useMemo(() => {
    const c = { all: items.length, dish: 0, restaurant: 0, recipe: 0 }
    items.forEach(i => { c[i.item_type] = (c[i.item_type] || 0) + 1 })
    return c
  }, [items])

  return (
    <div className={styles.wrapper}>
      <div className={styles.toolbar}>
        {/* Search */}
        <div className={styles.search}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/>
            <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          <input
            className={styles.searchInput}
            placeholder="Search this list"
            value={filters.q}
            onChange={e => set('q', e.target.value)}
          />
          {filters.q && (
            <button type="button" className={styles.searchClear} onClick={() => set('q', '')} title="Clear search">×</button>
          )}
        </div>

        <div className={styles.right}>
          {/* Filter */}
          <div className={styles.filterWrap} ref={ref}>
            <button
              type="button"
              className={`${styles.trigger} ${active ? styles.triggerActive : ''}`}
              onClick={() => setOpen(o => !o)}
              aria-expanded={open}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M4 5h16l-6 7.5V19l-4 1.5v-8L4 5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
              </svg>
              Filter
              {active > 0 && <span className={styles.badge}>{active}</span>}
            </button>

            {open && (
              <div className={styles.panel}>
                <div className={styles.section}>
                  <p className={styles.sectionLabel}>Type</p>
                  <div className={styles.chips}>
                    {TYPES.map(t => (
                      <button
                        key={t.id}
                        type="button"
                        className={`${styles.chip} ${filters.type === t.id ? styles.chipActive : ''}`}
                        onClick={() => set('type', t.id)}
                        disabled={t.id !== 'all' && !typeCounts[t.id]}
                      >
                        {t.label} <span className={styles.chipCount}>{typeCounts[t.id] || 0}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className={styles.section}>
                  <p className={styles.sectionLabel}>
                    Minimum rating
                    <span className={styles.sectionValue}>
                      {filters.minRating === 0 ? 'Any' : `${filters.minRating.toFixed(1)}★ & up`}
                    </span>
                  </p>
                  <input
                    type="range" min={0} max={5} step={0.5}
                    value={filters.minRating}
                    onChange={e => set('minRating', Number(e.target.value))}
                    className={styles.slider}
                  />
                  <div className={styles.sliderScale}><span>Any</span><span>2.5★</span><span>5★</span></div>
                </div>

                <div className={styles.section}>
                  <p className={styles.sectionLabel}>You've tried it</p>
                  <div className={styles.chips}>
                    {TRIED.map(t => (
                      <button
                        key={t.id}
                        type="button"
                        className={`${styles.chip} ${filters.tried === t.id ? styles.chipActive : ''}`}
                        onClick={() => set('tried', t.id)}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                {restaurants.length > 1 && (
                  <div className={styles.section}>
                    <p className={styles.sectionLabel}>Restaurant</p>
                    <select className={styles.select} value={filters.restaurant} onChange={e => set('restaurant', e.target.value)}>
                      <option value="">All restaurants</option>
                      {restaurants.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>
                )}

                {showAddedBy && adders.length > 1 && (
                  <div className={styles.section}>
                    <p className={styles.sectionLabel}>Added by</p>
                    <select className={styles.select} value={filters.addedBy} onChange={e => set('addedBy', e.target.value)}>
                      <option value="">Anyone</option>
                      {adders.map(u => <option key={u} value={u}>@{u}</option>)}
                    </select>
                  </div>
                )}

                <label className={styles.checkRow}>
                  <input type="checkbox" checked={filters.hasNote} onChange={e => set('hasNote', e.target.checked)} />
                  Only items with a note
                </label>

                <div className={styles.panelFooter}>
                  <button
                    type="button"
                    className={styles.clearBtn}
                    onClick={() => onFiltersChange({ ...EMPTY_FILTERS, q: filters.q })}
                    disabled={!active}
                  >
                    Clear all
                  </button>
                  <button type="button" className={styles.doneBtn} onClick={() => setOpen(false)}>Done</button>
                </div>
              </div>
            )}
          </div>

          <SortMenu options={sortOptions} value={sort} onChange={onSortChange} />
        </div>
      </div>

      {isFiltering && (
        <p className={styles.resultCount}>Showing {shownCount} of {items.length}</p>
      )}
    </div>
  )
}