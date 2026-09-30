export const EMPTY_FILTERS = {
  q: '',
  type: 'all',
  minRating: 0,
  tried: 'any',
  restaurant: '',
  addedBy: '',
  hasNote: false,
}

export const restaurantOf = (i) => i.item_type === 'restaurant' ? i.name : i.restaurant_name

export function filterListItems(items, f) {
  const q = f.q.trim().toLowerCase()
  return items.filter(i => {
    if (f.type !== 'all' && i.item_type !== f.type) return false
    if (f.minRating > 0 && (i.avg_rating == null || i.avg_rating < f.minRating)) return false
    if (f.tried === 'tried'   && i.my_rating == null) return false
    if (f.tried === 'untried' && i.my_rating != null) return false
    if (f.restaurant && (restaurantOf(i) || '').toLowerCase() !== f.restaurant.toLowerCase()) return false
    if (f.addedBy && i.added_by_username !== f.addedBy) return false
    if (f.hasNote && !i.note?.trim()) return false
    if (q && ![i.name, i.restaurant_name, i.note].some(s => s?.toLowerCase().includes(q))) return false
    return true
  })
}

// Panel filters only; the search box is visible on its own so it isn't counted.
export function countActiveFilters(f) {
  return Number(f.type !== 'all') + Number(f.minRating > 0) + Number(f.tried !== 'any')
       + Number(!!f.restaurant) + Number(!!f.addedBy) + Number(f.hasNote)
}