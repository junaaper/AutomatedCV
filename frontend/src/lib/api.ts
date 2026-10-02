import type { RunEvent, TokenResponse } from './types'

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// The access token lives only in memory; the refresh token is an httpOnly cookie.
let accessToken: string | null = null
let onSessionExpired: (() => void) | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

// Single-flight refresh: concurrent 401s share one refresh request. The backend
// treats reuse of a rotated refresh token as theft, so two parallel refreshes
// would log the user out.
let refreshing: Promise<TokenResponse | null> | null = null

export function refreshSession(): Promise<TokenResponse | null> {
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, { method: 'POST', credentials: 'include' })
      if (!res.ok) return null
      const data = (await res.json()) as TokenResponse
      accessToken = data.access_token
      return data
    } catch {
      return null
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return String(body.detail[0].msg).replace(/^Value error, /, '')
    }
  } catch {
    /* not JSON */
  }
  return `Request failed (${res.status})`
}

async function rawFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include' })
  if (res.status === 401 && retry && !path.startsWith('/auth/')) {
    if (await refreshSession()) return rawFetch(path, init, false)
    accessToken = null
    onSessionExpired?.()
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  return res
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await rawFetch(path, init)
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) })

/**
 * POSTs and reads a Server-Sent Events response (EventSource can't POST or send
 * headers, so this parses the stream by hand).
 */
export async function streamEvents(
  path: string,
  body: unknown,
  onEvent: (e: RunEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await rawFetch(path, { method: 'POST', ...json(body ?? {}), signal })
  const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      let event = 'message'
      let data = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7)
        else if (line.startsWith('data: ')) data += line.slice(6)
      }
      if (data) onEvent({ event, data: JSON.parse(data) } as RunEvent)
    }
  }
}
