// Other users: search and profile data. Backend: routers/users.py
import { request, path, query } from './client'

export const search     = (q = '') => request('/users/search' + query({ q }))
export const reviews    = (email)  => request(path`/users/${email}/reviews`)
export const meals      = (email)  => request(path`/users/${email}/meals`)
export const friends    = (email)  => request(path`/users/${email}/friends`)
export const lists      = (email)  => request(path`/users/${email}/lists`)
export const groupLists = (email)  => request(path`/users/${email}/group-lists`)
