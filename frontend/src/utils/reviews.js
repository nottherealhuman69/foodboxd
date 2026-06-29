export const RATING_LABELS = { 1: 'Poor', 2: 'Fair', 3: 'Good', 4: 'Great', 5: 'Outstanding' }

export function normaliseReview(r) {
  return {
    id:             r.id,
    dishName:       r.dish_name,
    type:           r.type,
    restaurantName: r.restaurant_name ?? '',
    recipe:         r.recipe ?? '',
    rating:         r.rating,
    review:         r.review ?? '',
    loggedAt:       r.logged_at,
  }
}

export function avgRating(entries) {
  if (!entries?.length) return null
  return (entries.reduce((s, e) => s + e.rating, 0) / entries.length).toFixed(1)
}

export function usernameFrom(email) {
  return email ? email.split('@')[0] : '?'
}
