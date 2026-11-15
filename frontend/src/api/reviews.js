// Dish reviews: CRUD, likes and comments. Backend: routers/reviews.py
import { request, path } from './client'

export const list   = ()         => request('/reviews')
export const all    = ()         => request('/reviews/all')
export const create = (body)     => request('/reviews', { method: 'POST', body })
export const update = (id, body) => request(path`/reviews/${id}`, { method: 'PATCH', body })
export const remove = (id)       => request(path`/reviews/${id}`, { method: 'DELETE' })
export const detail = (id)       => request(path`/reviews/${id}/detail`)

export const likes      = (id) => request(path`/reviews/${id}/likes`)
export const toggleLike = (id) => request(path`/reviews/${id}/like`, { method: 'POST' })

export const comments      = (id)            => request(path`/reviews/${id}/comments`)
export const addComment    = (id, body)      => request(path`/reviews/${id}/comments`, { method: 'POST', body })
export const deleteComment = (id, commentId) => request(path`/reviews/${id}/comments/${commentId}`, { method: 'DELETE' })
