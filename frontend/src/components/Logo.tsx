import { useId } from 'react'
import { cn } from '../lib/format'

export function LogoMark({ className }: { className?: string }) {
  // Unique per instance: a shared id breaks when another instance is display:none.
  const gradientId = useId()
  return (
    <span
      className={cn(
        'relative grid size-9 place-items-center rounded-xl bg-ink-850 ring-1 ring-white/10',
        'shadow-[0_0_30px_-6px_rgb(139_92_246/0.6)]',
        className,
      )}
    >
      <svg viewBox="0 0 32 32" className="size-6">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#c4b5fd" />
            <stop offset="1" stopColor="#22d3ee" />
          </linearGradient>
        </defs>
        <path
          d="M9 21.5 14.5 9h3L23 21.5h-3.2l-1.1-2.7h-5.4l-1.1 2.7Zm5.2-5.3h3.6L16 11.7Z"
          fill={`url(#${gradientId})`}
        />
      </svg>
    </span>
  )
}

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="leading-none">
        <span className="block text-[15px] font-semibold tracking-tight text-white">AutomatedCV</span>
        <span className="block font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
          application copilot
        </span>
      </span>
    </span>
  )
}
