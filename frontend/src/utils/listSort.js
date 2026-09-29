const byText = (a, b) => (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' })
const byDate = (a, b) => new Date(a.added_at) - new Date(b.added_at)

// Numeric sort with missing values always at the bottom.
const byNum = (get, dir) => (a, b) => {
  const x = get(a), y = get(b)
  if (x == null && y == null) return 0
  if (x == null) return 1
  if (y == null) return -1
  return dir === 'desc' ? y - x : x - y
}

const TYPE_ORDER = { dish: 0, restaurant: 1, recipe: 2 }
const restaurantOf = (i) => i.item_type === 'restaurant' ? i.name : i.restaurant_name

export const LIST_SORTS = [
  { id: 'list',        label: 'List order',       cmp: byDate },
  { id: 'recent',      label: 'Recently added',   cmp: (a, b) => byDate(b, a) },
  { id: 'name-asc',    label: 'Name (A–Z)',       cmp: (a, b) => byText(a.name, b.name) },
  { id: 'name-desc',   label: 'Name (Z–A)',       cmp: (a, b) => byText(b.name, a.name) },
  { id: 'rating-desc', label: 'Highest rated',    cmp: byNum(i => i.avg_rating, 'desc') },
  { id: 'rating-asc',  label: 'Lowest rated',     cmp: byNum(i => i.avg_rating, 'asc') },
  { id: 'mine',        label: 'Your rating',      cmp: byNum(i => i.my_rating, 'desc') },
  { id: 'popular',     label: 'Most reviewed',    cmp: byNum(i => i.review_count || null, 'desc') },
  { id: 'restaurant',  label: 'Restaurant (A–Z)', cmp: (a, b) => byText(restaurantOf(a), restaurantOf(b)) || byText(a.name, b.name) },
  { id: 'type',        label: 'Type',             cmp: (a, b) => (TYPE_ORDER[a.item_type] - TYPE_ORDER[b.item_type]) || byText(a.name, b.name) },
]

export const GROUP_LIST_SORTS = [
  ...LIST_SORTS,
  { id: 'added-by', label: 'Added by', cmp: (a, b) => byText(a.added_by_username, b.added_by_username) || byDate(a, b) },
]

// Items arrive in list order and Array.sort is stable, so ties keep list order.
export function sortListItems(items, sortId, sorts = LIST_SORTS) {
  const s = sorts.find(x => x.id === sortId) || sorts[0]
  return [...items].sort(s.cmp)
}