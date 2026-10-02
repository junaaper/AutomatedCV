import type { ApplicationStatus, Verdict } from './types'

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

export function timeAgo(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  for (const [unit, size] of units) {
    if (seconds >= size) return rtf.format(-Math.floor(seconds / size), unit)
  }
  return 'just now'
}

export function scoreTone(score: number): { label: string; color: string; glow: string } {
  if (score >= 75) return { label: 'Strong fit', color: '#34d399', glow: 'rgb(52 211 153 / 0.35)' }
  if (score >= 50) return { label: 'Good fit', color: '#a78bfa', glow: 'rgb(167 139 250 / 0.35)' }
  if (score >= 30) return { label: 'Stretch', color: '#fbbf24', glow: 'rgb(251 191 36 / 0.3)' }
  return { label: 'Long shot', color: '#fb7185', glow: 'rgb(251 113 133 / 0.3)' }
}

export const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string }> = {
  match: { label: 'Match', color: 'text-match', bg: 'bg-match/10 ring-match/25' },
  partial: { label: 'Partial', color: 'text-partial', bg: 'bg-partial/10 ring-partial/25' },
  missing: { label: 'Missing', color: 'text-missing', bg: 'bg-missing/10 ring-missing/25' },
}

export const STATUS_META: Record<ApplicationStatus, { label: string; dot: string }> = {
  saved: { label: 'Saved', dot: 'bg-violet-400' },
  applied: { label: 'Applied', dot: 'bg-cyan-400' },
  interviewing: { label: 'Interviewing', dot: 'bg-amber-400' },
  offer: { label: 'Offer', dot: 'bg-emerald-400' },
  rejected: { label: 'Closed', dot: 'bg-zinc-500' },
}

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  'saved',
  'applied',
  'interviewing',
  'offer',
  'rejected',
]

export function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}
