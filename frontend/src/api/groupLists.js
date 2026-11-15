// Shared group lists, invites and members. Backend: routers/group_lists.py
import { request, path } from './client'

export const list            = ()           => request('/group-lists')
export const invites         = ()           => request('/group-lists/invites')
export const create          = (body)       => request('/group-lists', { method: 'POST', body })
export const get             = (id)         => request(path`/group-lists/${id}`)
export const remove          = (id)         => request(path`/group-lists/${id}`, { method: 'DELETE' })
export const leave           = (id)         => request(path`/group-lists/${id}/leave`, { method: 'POST' })
export const invite          = (id, body)   => request(path`/group-lists/${id}/invite`, { method: 'POST', body })
export const respondToInvite = (id, body)   => request(path`/group-lists/${id}/invite`, { method: 'PATCH', body })
export const setVisibility   = (id, body)   => request(path`/group-lists/${id}/visibility`, { method: 'PATCH', body })
export const items           = (id)         => request(path`/group-lists/${id}/items`)
export const addItem         = (id, body)   => request(path`/group-lists/${id}/items`, { method: 'POST', body })
export const removeItem      = (id, itemId) => request(path`/group-lists/${id}/items/${itemId}`, { method: 'DELETE' })
