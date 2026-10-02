import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, json, refreshSession, setAccessToken, setSessionExpiredHandler } from './api'
import type { TokenResponse, User } from './types'

interface AuthState {
  user: User | null
  ready: boolean
  login: (email: string, password: string, turnstileToken: string) => Promise<void>
  signup: (email: string, password: string, turnstileToken: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)
  const queryClient = useQueryClient()

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    // Restore the session from the refresh cookie on page load.
    refreshSession().then((data) => {
      setUser(data?.user ?? null)
      setReady(true)
    })
  }, [])

  const accept = useCallback((data: TokenResponse) => {
    setAccessToken(data.access_token)
    setUser(data.user)
  }, [])

  const login = useCallback(
    async (email: string, password: string, turnstile_token: string) =>
      accept(
        await api<TokenResponse>('/auth/login', {
          method: 'POST',
          ...json({ email, password, turnstile_token }),
        }),
      ),
    [accept],
  )

  const signup = useCallback(
    async (email: string, password: string, turnstile_token: string) =>
      accept(
        await api<TokenResponse>('/auth/signup', {
          method: 'POST',
          ...json({ email, password, turnstile_token }),
        }),
      ),
    [accept],
  )

  const logout = useCallback(async () => {
    await api('/auth/logout', { method: 'POST' }).catch(() => undefined)
    setAccessToken(null)
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo(
    () => ({ user, ready, login, signup, logout }),
    [user, ready, login, signup, logout],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
