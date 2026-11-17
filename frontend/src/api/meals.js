// Meals (multi-dish posts): CRUD, likes and comments. Backend: routers/meals.py
// Same function names as reviews.js, so code can work with either (see posts.forKind).
import { request, path } from './client'

export const list   = ()         => request('/meals')
export const get    = (id)       => request(path`/meals/${id}`)
export const create = (body)     => request('/meals', { method: 'POST', body })
export const update = (id, body) => request(path`/meals/${id}`, { method: 'PATCH', body })
export const remove = (id)       => request(path`/meals/${id}`, { method: 'DELETE' })
export const detail = (id)       => request(path`/meals/${id}/detail`)

export const likes      = (id) => request(path`/meals/${id}/likes`)
export const toggleLike = (id) => request(path`/meals/${id}/like`, { method: 'POST' })

export const comments      = (id)            => request(path`/meals/${id}/comments`)
export const addComment    = (id, body)      => request(path`/meals/${id}/comments`, { method: 'POST', body })
export const deleteComment = (id, commentId) => request(path`/meals/${id}/comments/${commentId}`, { method: 'DELETE' })
