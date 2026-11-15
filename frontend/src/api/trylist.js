// The personal try-list. Backend: routers/trylist.py
import { request, path, query } from './client'

export const list   = ()     => request('/trylist')
export const add    = (body) => request('/trylist', { method: 'POST', body })
export const remove = (id)   => request(path`/trylist/${id}`, { method: 'DELETE' })

/** Is this dish/restaurant already on the try-list? */
export const check = ({ itemType, restaurantName, dishName }) =>
  request('/trylist/check' + query({
    item_type: itemType,
    restaurant_name: restaurantName,
    dish_name: dishName || undefined,
  }))
