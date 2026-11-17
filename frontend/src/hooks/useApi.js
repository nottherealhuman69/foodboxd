import { useState, useEffect, useCallback } from 'react'

/**
 * useFetch(request, deps?)
 *   request: a function from src/api that returns a fetch Response,
 *            e.g. useFetch(api.feed.get)
 * Returns { data, loading, error, refetch }
 * Re-fetches whenever deps change (defaults to [request]).
 */
export function useFetch(request, deps) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  const refetch = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await request()
      if (!res.ok) throw new Error()
      setData(await res.json())
    } catch {
      setError('Could not load data. Please try again.')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps ?? [request])

  useEffect(() => { refetch() }, [refetch])

  return { data, loading, error, refetch }
}
