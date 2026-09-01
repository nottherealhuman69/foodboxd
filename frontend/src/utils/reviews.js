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
    likeCount:      r.like_count ?? 0,
    commentCount:   r.comment_count ?? 0,
  }
}

export function normaliseMeal(m) {
  return {
    id:             m.id,
    kind:           'meal',
    type:           'meal',
    title:          m.title ?? '',
    restaurantName: m.restaurant_name ?? '',
    rating:         m.rating,
    review:         m.review ?? '',
    loggedAt:       m.logged_at,
    dishCount:      m.dish_count ?? 0,
    dishAvg:        m.dish_avg ?? null,
    dishes:         (m.dishes ?? []).map(d => ({
      id: d.id, dishName: d.dish_name, rating: d.rating, review: d.review ?? '',
    })),
  }
}

export function avgRating(entries) {
  if (!entries?.length) return null
  return (entries.reduce((s, e) => s + e.rating, 0) / entries.length).toFixed(1)
}

export function usernameFrom(email) {
  return email ? email.split('@')[0] : '?'
}
