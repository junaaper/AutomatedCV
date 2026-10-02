import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CircleAlert,
  FileText,
  Hourglass,
  LoaderCircle,
  Sparkles,
  SquareKanban,
  ThumbsDown,
  Trophy,
  WandSparkles,
} from 'lucide-react'
import { animate, motion, useMotionValue, useTransform } from 'motion/react'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Badge, Button, Card, PageHeader, Skeleton, fadeUp } from '../components/ui'
import { useAuth } from '../lib/auth'
import { APPLICATION_STATUSES, STATUS_META, cn, timeAgo } from '../lib/format'
import { useApplications, useCv, useRuns } from '../lib/queries'
import type { RunStatus } from '../lib/types'

function Counter({ value, suffix = '' }: { value: number; suffix?: string }) {
  const mv = useMotionValue(0)
  const text = useTransform(mv, (v) => `${Math.round(v)}${suffix}`)
  useEffect(() => {
    const c = animate(mv, value, { duration: 1.2, ease: [0.22, 1, 0.36, 1] })
    return () => c.stop()
  }, [mv, value])
  return <motion.span>{text}</motion.span>
}

function Stat({
  label,
  value,
  suffix,
  icon,
  accent,
  delay,
}: {
  label: string
  value: number
  suffix?: string
  icon: ReactNode
  accent: string
  delay: number
}) {
  return (
    <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay }}>
      <Card className="group relative overflow-hidden p-5">
        <div className={cn('absolute -top-10 -right-10 size-32 rounded-full opacity-40 blur-3xl transition-opacity group-hover:opacity-70', accent)} />
        <div className="relative flex items-center justify-between">
          <span className="text-sm text-white/50">{label}</span>
          <span className="text-white/40">{icon}</span>
        </div>
        <p className="relative mt-3 font-display text-5xl text-white">
          <Counter value={value} suffix={suffix} />
        </p>
      </Card>
    </motion.div>
  )
}

const RUN_META: Record<RunStatus, { label: string; icon: ReactNode; cls: string }> = {
  running: { label: 'Running', icon: <LoaderCircle className="size-3 animate-spin" />, cls: 'bg-violet-500/10 text-violet-200 ring-violet-400/20' },
  awaiting_review: { label: 'Needs review', icon: <Hourglass className="size-3" />, cls: 'bg-amber-400/10 text-amber-200 ring-amber-400/25' },
  completed: { label: 'Saved', icon: <Check className="size-3" />, cls: 'bg-emerald-400/10 text-emerald-200 ring-emerald-400/20' },
  rejected: { label: 'Discarded', icon: <ThumbsDown className="size-3" />, cls: 'bg-white/5 text-white/50 ring-white/10' },
  failed: { label: 'Failed', icon: <CircleAlert className="size-3" />, cls: 'bg-rose-500/10 text-rose-200 ring-rose-400/20' },
}

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

export function DashboardPage() {
  const { user } = useAuth()
  const { data: cv, isLoading: cvLoading } = useCv()
  const { data: apps = [], isLoading: appsLoading } = useApplications()
  const { data: runs = [] } = useRuns()

  const avg = apps.length ? apps.reduce((s, a) => s + a.fit_score, 0) / apps.length : 0
  const active = apps.filter((a) => a.status === 'interviewing' || a.status === 'offer').length
  const pending = runs.filter((r) => r.status === 'awaiting_review')
  // "ada.lovelace42@x.com" -> "Ada"
  const name = (user?.email.split('@')[0].split(/[._+\-\d]/).find(Boolean) ?? 'there').replace(
    /^./,
    (c) => c.toUpperCase(),
  )

  const steps = [
    { done: !!cv, title: 'Add your CV', desc: 'PDF or pasted text, indexed for search', to: '/cv', icon: FileText },
    { done: runs.length > 0, title: 'Analyze a job posting', desc: 'Watch the agent work, step by step', to: '/analyze', icon: WandSparkles },
    { done: apps.length > 0, title: 'Approve & track', desc: 'Edit the letter, approve, move it along', to: '/tracker', icon: SquareKanban },
  ]
  const onboarding = !cvLoading && !appsLoading && steps.some((s) => !s.done)

  return (
    <>
      <PageHeader
        eyebrow={greeting()}
        title={
          <>
            Welcome back, <span className="text-gradient italic">{name}</span>
          </>
        }
        description="Here's where your job search stands."
        actions={
          <Link to="/analyze">
            <Button size="lg" icon={<WandSparkles className="size-4" />}>
              Analyze a job
            </Button>
          </Link>
        }
      />

      {pending.length > 0 && (
        <motion.div {...fadeUp} className="mb-6">
          <Link to={`/analyze/${pending[0].id}`}>
            <div className="group flex items-center gap-4 rounded-2xl bg-gradient-to-r from-amber-400/15 via-amber-400/5 to-transparent p-4 ring-1 ring-amber-300/25 transition hover:ring-amber-300/50">
              <span className="relative grid size-10 place-items-center rounded-xl bg-amber-400/15">
                <span className="absolute inset-0 animate-ping rounded-xl bg-amber-400/20" />
                <Hourglass className="relative size-5 text-amber-200" />
              </span>
              <div className="flex-1">
                <p className="font-medium text-white">
                  {pending.length === 1 ? 'A draft is waiting for your review' : `${pending.length} drafts are waiting for your review`}
                </p>
                <p className="text-sm text-white/50">
                  {pending[0].title} · {pending[0].company}. The agent paused here for you.
                </p>
              </div>
              <ArrowRight className="size-5 text-amber-200 transition group-hover:translate-x-1" />
            </div>
          </Link>
        </motion.div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Applications" value={apps.length} icon={<SquareKanban className="size-4" />} accent="bg-violet-500" delay={0.05} />
        <Stat label="Average fit" value={avg} suffix="%" icon={<Sparkles className="size-4" />} accent="bg-cyan-400" delay={0.1} />
        <Stat label="Interviews & offers" value={active} icon={<Trophy className="size-4" />} accent="bg-emerald-400" delay={0.15} />
        <Stat label="Agent runs" value={runs.length} icon={<WandSparkles className="size-4" />} accent="bg-fuchsia-500" delay={0.2} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        {onboarding ? (
          <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.25 }}>
            <Card glow className="h-full p-6">
              <h2 className="text-[15px] font-semibold text-white">Get set up</h2>
              <p className="text-sm text-white/45">Three steps to your first tailored application.</p>
              <ol className="mt-5 space-y-2">
                {steps.map((s, i) => (
                  <li key={s.title}>
                    <Link
                      to={s.to}
                      className="group flex items-center gap-4 rounded-xl p-3 ring-1 ring-transparent transition hover:bg-white/[0.03] hover:ring-white/[0.06]"
                    >
                      <span
                        className={cn(
                          'grid size-9 shrink-0 place-items-center rounded-full text-sm font-semibold ring-1',
                          s.done
                            ? 'bg-emerald-400/15 text-emerald-300 ring-emerald-400/30'
                            : 'bg-white/[0.04] text-white/60 ring-white/10',
                        )}
                      >
                        {s.done ? <Check className="size-4" strokeWidth={3} /> : i + 1}
                      </span>
                      <div className="flex-1">
                        <p className={cn('text-sm font-medium', s.done ? 'text-white/45 line-through' : 'text-white')}>{s.title}</p>
                        <p className="text-xs text-white/40">{s.desc}</p>
                      </div>
                      {!s.done && <ArrowUpRight className="size-4 text-white/30 transition group-hover:text-violet-300" />}
                    </Link>
                  </li>
                ))}
              </ol>
            </Card>
          </motion.div>
        ) : (
          <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.25 }}>
            <Card className="h-full p-6">
              <h2 className="text-[15px] font-semibold text-white">Pipeline</h2>
              <p className="text-sm text-white/45">Applications by stage</p>
              <div className="mt-6 space-y-3.5">
                {APPLICATION_STATUSES.map((s, i) => {
                  const n = apps.filter((a) => a.status === s).length
                  const pct = apps.length ? (n / apps.length) * 100 : 0
                  return (
                    <div key={s}>
                      <div className="mb-1.5 flex justify-between text-xs">
                        <span className="flex items-center gap-2 text-white/60">
                          <span className={cn('size-1.5 rounded-full', STATUS_META[s].dot)} /> {STATUS_META[s].label}
                        </span>
                        <span className="font-mono text-white/45">{n}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/[0.05]">
                        <motion.div
                          className={cn('h-full rounded-full', STATUS_META[s].dot)}
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.max(pct, n ? 4 : 0)}%` }}
                          transition={{ duration: 1, delay: 0.3 + i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          </motion.div>
        )}

        <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.3 }}>
          <Card className="h-full p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-[15px] font-semibold text-white">Recent agent runs</h2>
                <p className="text-sm text-white/45">Each one is a resumable LangGraph thread</p>
              </div>
            </div>
            {runs.length === 0 ? (
              <div className="space-y-2.5">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-14 opacity-40" />
                ))}
              </div>
            ) : (
              <ul className="-mx-2 space-y-1">
                {runs.slice(0, 6).map((r, i) => {
                  const meta = RUN_META[r.status]
                  return (
                    <motion.li key={r.id} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.35 + i * 0.05 }}>
                      <Link
                        to={`/analyze/${r.id}`}
                        className="flex items-center gap-3 rounded-xl px-2 py-2.5 transition hover:bg-white/[0.03]"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-white">{r.title ?? 'Untitled run'}</p>
                          <p className="truncate text-xs text-white/40">
                            {r.company ?? '…'} · {timeAgo(r.created_at)}
                          </p>
                        </div>
                        <Badge className={meta.cls}>
                          {meta.icon} {meta.label}
                        </Badge>
                      </Link>
                    </motion.li>
                  )
                })}
              </ul>
            )}
          </Card>
        </motion.div>
      </div>
    </>
  )
}
