// The home feed. Backend: routers/feed.py
import { request } from './client'

export const get = () => request('/feed')
