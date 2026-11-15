// The one place that talks to the backend.
//
// Every function in src/api/ goes through `request`, which:
//   - prefixes the base URL (VITE_API_URL, or the Vite dev proxy at /api)
//   - adds the login token
//   - turns `body` objects into JSON
//   - logs the user out if their token has expired (401)
//
// It returns the normal fetch Response, so callers keep using res.ok / res.json().

import { session } from './session'

const API_BASE = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/$/, '')

export async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = auth ? session.getToken() : null
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  // The backend only answers 401 to a request carrying a token when that
  // token is expired or invalid, so the session is over.
  if (res.status === 401 && token) onSessionExpired()
  return res
}

function onSessionExpired() {
  session.clear()
  if (window.location.pathname !== '/login') window.location.assign('/login')
}

/** Tagged template that URL-encodes every inserted value: path`/users/${email}/reviews` */
export function path(strings, ...values) {
  return strings.reduce((out, s, i) =>
    out + s + (i < values.length ? encodeURIComponent(values[i]) : ''), '')
}

/** Builds "?a=1&b=2", skipping null/undefined values. */
export function query(params) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) q.set(k, v)
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}
