export function dishPath(dishName, restaurantName) {
  return `/dish/${encodeURIComponent(restaurantName)}/${encodeURIComponent(dishName)}`
}

export function dishUrl(dishName, restaurantName) {
  return `${window.location.origin}${dishPath(dishName, restaurantName)}`
}

export function reviewPath(reviewId) {
  return `/review/${reviewId}`
}
export function reviewUrl(reviewId) {
  return `${window.location.origin}${reviewPath(reviewId)}`
}


export function restaurantPath(restaurantName) {
  return `/restaurant/${encodeURIComponent(restaurantName)}`
}

export function restaurantUrl(restaurantName) {
  return `${window.location.origin}${restaurantPath(restaurantName)}`
}

export function userPath(userEmail) {
  return `/user/${encodeURIComponent(userEmail)}`
}

export function userUrl(userEmail) {
  return `${window.location.origin}${userPath(userEmail)}`
}

export function recipePath(dishName, ownerEmail) {
  return `/recipe/${encodeURIComponent(ownerEmail)}/${encodeURIComponent(dishName)}`
}