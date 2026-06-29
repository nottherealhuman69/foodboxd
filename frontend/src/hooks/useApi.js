import { useState, useEffect, useCallback } from 'react'

export function authHeaders() {
  const token = localStorage.getItem('token')
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
}

export function apiFetch(path, options = {}) {
  return fetch(path, { ...options, headers: { ...authHeaders(), ...options.headers } })
}

/**
 * useFetch(path, deps?)
 * Returns { data, loading, error, refetch }
 * Re-fetches whenever deps change (defaults to [path]).
 */
export function useFetch(path, deps) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  const refetch = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch(path)
      if (!res.ok) throw new Error()
      setData(await res.json())
    } catch {
      setError('Could not load data. Please try again.')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps ?? [path])

  useEffect(() => { refetch() }, [refetch])

  return { data, loading, error, refetch }
}
