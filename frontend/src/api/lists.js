// Personal custom lists. Backend: routers/lists.py
import { request, path } from './client'

export const list       = ()           => request('/lists')
export const create     = (body)       => request('/lists', { method: 'POST', body })
export const remove     = (id)         => request(path`/lists/${id}`, { method: 'DELETE' })
export const items      = (id)         => request(path`/lists/${id}/items`)
export const addItem    = (id, body)   => request(path`/lists/${id}/items`, { method: 'POST', body })
export const removeItem = (id, itemId) => request(path`/lists/${id}/items/${itemId}`, { method: 'DELETE' })
