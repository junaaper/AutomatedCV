import { useQuery } from '@tanstack/react-query'
import { ApiError, api } from './api'
import type { ApplicationSummary, Cv, RunSummary } from './types'

export function useCv() {
  return useQuery({
    queryKey: ['cv'],
    queryFn: async () => {
      try {
        return await api<Cv>('/cv')
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null
        throw e
      }
    },
  })
}

export function useApplications() {
  return useQuery({
    queryKey: ['applications'],
    queryFn: () => api<ApplicationSummary[]>('/applications'),
  })
}

export function useUsage() {
  return useQuery({
    queryKey: ['usage'],
    queryFn: () => api<{ used: number; limit: number; resets_at: string }>('/usage'),
  })
}

export function useRuns() {
  return useQuery({ queryKey: ['runs'], queryFn: () => api<RunSummary[]>('/runs') })
}
