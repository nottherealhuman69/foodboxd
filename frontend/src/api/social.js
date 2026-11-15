// Follows and friend requests. Backend: routers/social.py
import { request, path } from './client'

export const friends          = ()         => request('/friends')
export const sendRequest      = (body)     => request('/friends/request', { method: 'POST', body })
export const pendingRequests  = ()         => request('/friends/requests/pending')
export const respondToRequest = (id, body) => request(path`/friends/requests/${id}`, { method: 'PATCH', body })
export const unfollow         = (email)    => request(path`/follow/${email}`, { method: 'DELETE' })
