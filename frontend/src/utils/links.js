export function dishPath(dishName, restaurantName) {
  return `/dish/${encodeURIComponent(restaurantName)}/${encodeURIComponent(dishName)}`
}

export function dishUrl(dishName, restaurantName) {
  return `${window.location.origin}${dishPath(dishName, restaurantName)}`
}