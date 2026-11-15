// Signup, login, password reset and account settings. Backend: routers/auth.py
import { request } from './client'

export const signup         = (body) => request('/signup', { method: 'POST', body, auth: false })
export const login          = (body) => request('/login', { method: 'POST', body, auth: false })
export const forgotPassword = (body) => request('/forgot-password', { method: 'POST', body, auth: false })
export const resetPassword  = (body) => request('/reset-password', { method: 'POST', body, auth: false })

export const me             = ()     => request('/me')
export const updatePrivacy  = (body) => request('/me/privacy', { method: 'PATCH', body })
export const changePassword = (body) => request('/change-password', { method: 'POST', body })
