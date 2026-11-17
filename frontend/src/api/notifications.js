// Activity notifications. Backend: routers/notifications.py
import { request, query } from './client'

export const activity = () => request('/notifications/activity')

/** since: ISO timestamp of when notifications were last viewed (optional) */
export const unseenCount = (since) =>
  request('/notifications/unseen_count' + query({ since: since || undefined }))
