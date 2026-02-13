// Typed fetch wrapper for the FastAPI backend

const getBaseUrl = (): string => {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return window.electronAPI.backendUrl
  }
  return 'http://127.0.0.1:8420'
}

export async function api<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${getBaseUrl()}${endpoint}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `API error: ${res.status}`)
  }
  return res.json()
}

export function getWsUrl(path: string): string {
  const base = getBaseUrl().replace('http', 'ws')
  return `${base}${path}`
}

export function getBackgroundUrl(path: string | null): string | null {
  if (!path) return null
  const filename = path.split(/[\\/]/).pop()
  return `${getBaseUrl()}/api/backgrounds/${filename}`
}
