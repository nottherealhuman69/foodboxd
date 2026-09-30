import { useState, useEffect } from 'react'
import { apiFetch } from '../hooks/useApi'
import { SearchDropdown } from '../pages/Createreview'
import styles from '../pages/Mylists.module.css'
import cr from '../pages/CreateReview.module.css'

const TYPES = [
  { id: 'dish',       icon: '🍽️', label: 'Dish' },
  { id: 'restaurant', icon: '🏠', label: 'Restaurant' },
  { id: 'recipe',     icon: '📖', label: 'Recipe' },
]

export default function AddListItemModal({ endpoint, title = 'Add to list', onClose, onAdded }) {
  const [itemType,       setItemType]       = useState('dish')
  const [restaurantName, setRestaurantName] = useState('')
  const [dishName,       setDishName]       = useState('')
  const [recipeName,     setRecipeName]     = useState('')
  const [newRestaurant,  setNewRestaurant]  = useState(false)
  const [newDish,        setNewDish]        = useState(false)
  const [note,           setNote]           = useState('')

  const [restaurants,    setRestaurants]    = useState([])
  const [menu,           setMenu]           = useState([])
  const [loadingCatalog, setLoadingCatalog] = useState(true)
  const [saving,         setSaving]         = useState(false)
  const [err,            setErr]            = useState('')

  // Restaurant catalog, loaded once.
  useEffect(() => {
    apiFetch('/api/restaurants')
      .then(r => r.ok ? r.json() : [])
      .then(setRestaurants)
      .catch(() => {})
      .finally(() => setLoadingCatalog(false))
  }, [])

  // Menu for the picked restaurant (dish type only; a new restaurant has no menu).
  useEffect(() => {
    if (itemType !== 'dish' || !restaurantName.trim() || newRestaurant) { setMenu([]); return }
    let cancelled = false
    apiFetch(`/api/restaurants/${encodeURIComponent(restaurantName)}/dishes`)
      .then(r => r.ok ? r.json() : [])
      .then(data => { if (!cancelled) setMenu(data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [itemType, restaurantName, newRestaurant])

  const switchType = (t) => {
    setItemType(t)
    setRestaurantName(''); setDishName(''); setRecipeName('')
    setNewRestaurant(false); setNewDish(false); setErr('')
  }

  const toggleNewRestaurant = () => {
    setNewRestaurant(v => !v)
    setNewDish(false)
    setRestaurantName(''); setDishName(''); setErr('')
  }

  const toggleNewDish = () => { setNewDish(v => !v); setDishName(''); setErr('') }

  const handleRestaurantChange = (val) => {
    setRestaurantName(val)
    setDishName('')
    setNewDish(false)
    setErr('')
  }

  const restaurantSelected = !!restaurantName.trim()
  const dishFreeText       = newRestaurant || newDish

  const submit = async () => {
    const name = itemType === 'dish' ? dishName
               : itemType === 'restaurant' ? restaurantName
               : recipeName

    if (itemType !== 'recipe' && !restaurantSelected) {
      setErr(newRestaurant ? 'Type the restaurant name.' : 'Pick a restaurant.'); return
    }
    if (!name.trim()) {
      setErr(itemType === 'dish'
        ? (dishFreeText ? 'Type the dish name.' : 'Pick a dish.')
        : 'Enter a recipe name.')
      return
    }

    setSaving(true); setErr('')
    try {
      const res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          item_type:       itemType,
          name:            name.trim(),
          restaurant_name: itemType === 'dish' ? restaurantName.trim() : null,
          note:            note.trim() || null,
        }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setErr(d.detail || 'Could not add the item.')
        return
      }
      onAdded(await res.json())
    } catch {
      setErr('Could not reach the server.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>{title}</h3>

        {/* Type */}
        <div className={styles.field}>
          <label className={styles.label}>Type</label>
          <div className={styles.typeRow}>
            {TYPES.map(t => (
              <button
                key={t.id}
                type="button"
                className={`${styles.typeBtn} ${itemType === t.id ? styles.typeBtnActive : ''}`}
                onClick={() => switchType(t.id)}
              >
                <span>{t.icon}</span> {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Restaurant (dish + restaurant types) */}
        {itemType !== 'recipe' && (
          <div className={styles.field} style={{ position: 'relative', zIndex: 2 }}>
            <div className={cr.labelRow}>
              <label className={styles.label} htmlFor="listRestaurant">Restaurant</label>
              <button type="button" className={cr.toggleLink} onClick={toggleNewRestaurant}>
                {newRestaurant ? '← Pick existing' : '+ Add new restaurant'}
              </button>
            </div>
            {newRestaurant
              ? <input
                  id="listRestaurant"
                  className={styles.input}
                  type="text"
                  placeholder="Type the restaurant name…"
                  value={restaurantName}
                  onChange={e => { setRestaurantName(e.target.value); setErr('') }}
                  autoFocus
                />
              : <SearchDropdown
                  id="listRestaurant"
                  placeholder={loadingCatalog ? 'Loading…' : 'Search restaurants…'}
                  options={restaurants}
                  value={restaurantName}
                  onChange={handleRestaurantChange}
                  disabled={loadingCatalog}
                />
            }
          </div>
        )}

        {/* Dish (dish type only) */}
        {itemType === 'dish' && (
          <div className={styles.field} style={{ position: 'relative', zIndex: 1 }}>
            <div className={cr.labelRow}>
              <label className={styles.label} htmlFor="listDish">Dish</label>
              {restaurantSelected && !newRestaurant && (
                <button type="button" className={cr.toggleLink} onClick={toggleNewDish}>
                  {newDish ? '← Pick existing' : '+ Add new dish'}
                </button>
              )}
            </div>
            {dishFreeText
              ? <input
                  id="listDish"
                  className={styles.input}
                  type="text"
                  placeholder="e.g. Chicken Biryani"
                  value={dishName}
                  onChange={e => { setDishName(e.target.value); setErr('') }}
                  autoFocus={newDish}
                />
              : <SearchDropdown
                  id="listDish"
                  placeholder={
                    !restaurantSelected ? 'Select a restaurant first'
                    : menu.length === 0 ? 'No dishes yet — use "+ Add new dish"'
                    : 'Search dishes…'
                  }
                  options={menu}
                  value={dishName}
                  onChange={val => { setDishName(val); setErr('') }}
                  disabled={!restaurantSelected}
                />
            }
          </div>
        )}

        {/* Recipe (free text) */}
        {itemType === 'recipe' && (
          <div className={styles.field}>
            <label className={styles.label} htmlFor="listRecipe">Recipe name</label>
            <input
              id="listRecipe"
              className={styles.input}
              type="text"
              placeholder="e.g. Amma's dal"
              value={recipeName}
              onChange={e => { setRecipeName(e.target.value); setErr('') }}
              autoFocus
            />
          </div>
        )}

        {/* Note */}
        <div className={styles.field}>
          <label className={styles.label}>
            Note <span className={styles.optional}>(optional)</span>
          </label>
          <input
            className={styles.input}
            placeholder="e.g. The spicy variant is 🔥"
            value={note}
            onChange={e => setNote(e.target.value)}
          />
        </div>

        {err && <p className={styles.errText}>{err}</p>}

        <div className={styles.modalActions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button type="button" className={styles.primaryBtn} onClick={submit} disabled={saving}>
            {saving ? 'Adding…' : 'Add item'}
          </button>
        </div>
      </div>
    </div>
  )
}