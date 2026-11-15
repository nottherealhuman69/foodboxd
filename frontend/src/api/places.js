// Restaurants, dishes, recipes and place search. Backend: routers/places.py
import { request, path, query } from './client'

export const restaurants      = ()     => request('/restaurants')
export const restaurantDishes = (name) => request(path`/restaurants/${name}/dishes`)
export const restaurantPage   = (name) => request(path`/restaurants/${name}/page`)
export const dishes           = ()     => request('/dishes')

export const dishPage = (dishName, restaurantName) =>
  request(path`/dishes/${dishName}/restaurant/${restaurantName}`)

export const recipePage = (dishName, ownerEmail) =>
  request('/recipes/page' + query({ dish_name: dishName, owner: ownerEmail }))

export const search = (q, itemType = 'dish') =>
  request('/search/dishes-restaurants' + query({ q, item_type: itemType }))
