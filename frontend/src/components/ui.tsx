import { LoaderCircle } from 'lucide-react'
import { motion } from 'motion/react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../lib/format'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'

const VARIANTS: Record<Variant, string> = {
  primary:
    'text-white bg-gradient-to-r from-violet-500 via-indigo-500 to-cyan-500 bg-[length:200%_100%] ' +
    'hover:bg-[position:100%_0] shadow-[0_8px_30px_-8px_rgb(124_58_237/0.7)] ' +
    'ring-1 ring-inset ring-white/20',
  secondary: 'text-white bg-white/[0.06] hover:bg-white/[0.1] ring-1 ring-inset ring-white/10',
  ghost: 'text-white/70 hover:text-white hover:bg-white/[0.06]',
  danger: 'text-rose-200 bg-rose-500/10 hover:bg-rose-500/20 ring-1 ring-inset ring-rose-400/25',
  success:
    'text-ink-950 bg-emerald-400 hover:bg-emerald-300 shadow-[0_8px_30px_-8px_rgb(52_211_153/0.7)]',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading,
  icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cn(
        'inline-flex select-none items-center justify-center gap-2 rounded-xl font-medium',
        'transition-all duration-300 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60',
        size === 'sm' && 'h-8 px-3 text-xs',
        size === 'md' && 'h-10 px-4 text-sm',
        size === 'lg' && 'h-12 px-6 text-[15px]',
        VARIANTS[variant],
        className,
      )}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" /> : icon}
      {children}
    </button>
  )
}

export function Card({
  className,
  children,
  glow,
}: {
  className?: string
  children: ReactNode
  glow?: boolean
}) {
  return (
    <div className={cn('glass rounded-2xl', glow && 'ring-gradient', className)}>{children}</div>
  )
}

export function Badge({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ring-inset',
        className ?? 'bg-white/5 text-white/70 ring-white/10',
      )}
    >
      {children}
    </span>
  )
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-violet-300/80">
      {children}
    </p>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="mb-8 flex flex-wrap items-end justify-between gap-4"
    >
      <div className="max-w-2xl">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="mt-2 font-display text-4xl leading-[1.05] tracking-tight text-white sm:text-5xl">
          {title}
        </h1>
        {description && <p className="mt-3 text-[15px] leading-relaxed text-white/55">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </motion.header>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-shimmer rounded-xl bg-[linear-gradient(90deg,rgb(255_255_255/0.03),rgb(255_255_255/0.08),rgb(255_255_255/0.03))] bg-[length:200%_100%]',
        className,
      )}
    />
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      <div className="relative mb-5">
        <div className="absolute inset-0 rounded-2xl bg-violet-500/30 blur-2xl" />
        <div className="relative grid size-14 place-items-center rounded-2xl bg-ink-850 text-violet-300 ring-1 ring-white/10">
          {icon}
        </div>
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-white/50">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

export const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
}
