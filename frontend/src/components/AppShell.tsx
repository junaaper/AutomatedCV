import { FileText, LayoutDashboard, LogOut, Sparkles, SquareKanban, WandSparkles } from 'lucide-react'
import { motion } from 'motion/react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { useAuth } from '../lib/auth'
import { cn } from '../lib/format'
import { Logo, LogoMark } from './Logo'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/analyze', label: 'Analyze a job', icon: WandSparkles, end: false },
  { to: '/tracker', label: 'Tracker', icon: SquareKanban, end: false },
  { to: '/cv', label: 'My CV', icon: FileText, end: false },
]

function NavItem({ item, compact }: { item: (typeof NAV)[number]; compact?: boolean }) {
  const location = useLocation()
  const active = item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={cn(
        'relative flex items-center gap-3 rounded-xl text-sm font-medium transition-colors',
        compact ? 'px-3 py-2' : 'px-3 py-2.5',
        active ? 'text-white' : 'text-white/50 hover:text-white/90',
      )}
    >
      {active && (
        <motion.span
          layoutId={compact ? 'nav-active-compact' : 'nav-active'}
          className="absolute inset-0 rounded-xl bg-white/[0.07] ring-1 ring-inset ring-white/10"
          transition={{ type: 'spring', stiffness: 380, damping: 32 }}
        />
      )}
      <Icon className={cn('relative size-[18px]', active && 'text-violet-300')} />
      <span className={cn('relative', compact && 'hidden sm:inline')}>{item.label}</span>
    </NavLink>
  )
}

export function AppShell() {
  const { user, logout } = useAuth()
  return (
    <div className="min-h-dvh lg:pl-64">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/[0.06] bg-ink-950/60 px-4 py-6 backdrop-blur-xl lg:flex">
        <div className="px-2">
          <Logo />
        </div>
        <nav className="mt-10 flex flex-col gap-1">
          {NAV.map((item) => (
            <NavItem key={item.to} item={item} />
          ))}
        </nav>
        <div className="mt-auto">
          <div className="glass rounded-2xl p-3">
            <div className="flex items-center gap-3">
              <div className="grid size-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-violet-500 to-cyan-400 text-sm font-semibold text-white">
                {user?.email[0]?.toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-white">{user?.email}</p>
                <p className="text-xs text-white/40">{user?.is_demo ? 'Demo account' : 'Signed in'}</p>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                className="grid size-8 place-items-center rounded-lg text-white/40 transition hover:bg-white/5 hover:text-white"
              >
                <LogOut className="size-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center gap-2 border-b border-white/[0.06] bg-ink-950/70 px-4 py-3 backdrop-blur-xl lg:hidden">
        <LogoMark className="size-8" />
        <nav className="flex flex-1 items-center justify-center gap-1">
          {NAV.map((item) => (
            <NavItem key={item.to} item={item} compact />
          ))}
        </nav>
        <button onClick={logout} title="Sign out" className="p-2 text-white/50">
          <LogOut className="size-4" />
        </button>
      </header>

      {user?.is_demo && (
        <div className="border-b border-violet-400/15 bg-gradient-to-r from-violet-500/15 via-cyan-500/10 to-transparent px-4 py-2.5 text-center text-xs text-white/70 sm:px-8">
          <Sparkles className="mr-1.5 inline size-3.5 -translate-y-px text-violet-300" />
          <span className="font-medium text-white">Demo account.</span> Sample postings replay
          recorded AI runs, so they're instant and work even if the model API is down. Everything
          resets after 24 hours.{' '}
          <button onClick={logout} className="font-medium text-violet-300 underline-offset-2 hover:underline">
            Create your own account
          </button>
        </div>
      )}

      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:py-12">
        <Outlet />
      </main>
    </div>
  )
}
