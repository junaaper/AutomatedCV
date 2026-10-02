import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Copy, GripVertical, SquareKanban, Trash2, WandSparkles, X } from 'lucide-react'
import { AnimatePresence, LayoutGroup, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { DragEvent } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { MiniScore } from '../components/MiniScore'
import { RequirementList, VerdictSummary } from '../components/RequirementList'
import { ScoreRing } from '../components/ScoreRing'
import { Button, Card, EmptyState, PageHeader, Skeleton } from '../components/ui'
import { api, json } from '../lib/api'
import { APPLICATION_STATUSES, STATUS_META, cn, timeAgo } from '../lib/format'
import { useApplications } from '../lib/queries'
import type { ApplicationDetail, ApplicationStatus, ApplicationSummary } from '../lib/types'

function useUpdateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<Pick<ApplicationDetail, 'status' | 'notes' | 'cover_letter'>>) =>
      api<ApplicationDetail>(`/applications/${id}`, { method: 'PATCH', ...json(body) }),
    // Optimistic: move the card immediately, roll back if the server refuses.
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ['applications'] })
      const previous = qc.getQueryData<ApplicationSummary[]>(['applications'])
      if (status) {
        qc.setQueryData<ApplicationSummary[]>(['applications'], (apps) =>
          apps?.map((a) => (a.id === id ? { ...a, status } : a)),
        )
      }
      return { previous }
    },
    onError: (e, _v, ctx) => {
      if (ctx?.previous) qc.setQueryData(['applications'], ctx.previous)
      toast.error(e.message)
    },
    onSuccess: (app) => qc.setQueryData(['application', app.id], app),
    onSettled: () => qc.invalidateQueries({ queryKey: ['applications'] }),
  })
}

function BoardCard({ app, onOpen }: { app: ApplicationSummary; onOpen: () => void }) {
  return (
    <motion.div
      layout
      layoutId={app.id}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 400, damping: 34 }}
    >
      <div
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', app.id)
          e.dataTransfer.effectAllowed = 'move'
        }}
        onClick={onOpen}
        className="group cursor-grab rounded-xl bg-ink-850/80 p-3.5 ring-1 ring-white/[0.07] transition hover:-translate-y-0.5 hover:bg-ink-800 hover:ring-violet-400/30 hover:shadow-[0_10px_30px_-12px_rgb(139_92_246/0.5)] active:cursor-grabbing"
      >
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1.5 text-xs text-white/45">
              <Building2 className="size-3 shrink-0" />
              <span className="truncate">{app.company}</span>
            </p>
            <p className="mt-1 line-clamp-2 text-sm font-medium leading-snug text-white">{app.title}</p>
          </div>
          <MiniScore score={app.fit_score} />
        </div>
        <div className="mt-3 flex items-center justify-between text-[11px] text-white/30">
          <span>{timeAgo(app.updated_at)}</span>
          <GripVertical className="size-3.5 opacity-0 transition group-hover:opacity-100" />
        </div>
      </div>
    </motion.div>
  )
}

function Column({
  status,
  apps,
  onDropApp,
  onOpen,
}: {
  status: ApplicationStatus
  apps: ApplicationSummary[]
  onDropApp: (id: string, status: ApplicationStatus) => void
  onOpen: (id: string) => void
}) {
  const [over, setOver] = useState(false)
  const meta = STATUS_META[status]
  return (
    <div
      onDragOver={(e: DragEvent) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e: DragEvent) => {
        e.preventDefault()
        setOver(false)
        const id = e.dataTransfer.getData('text/plain')
        if (id) onDropApp(id, status)
      }}
      className={cn(
        'glass flex min-h-[420px] w-[272px] shrink-0 flex-col rounded-2xl p-2.5 transition-all duration-200',
        over && 'scale-[1.01] bg-violet-500/[0.06] ring-2 ring-violet-400/40',
      )}
    >
      <div className="flex items-center gap-2 px-2 pt-1.5 pb-3">
        <span className={cn('size-2 rounded-full', meta.dot)} />
        <span className="text-sm font-medium text-white/85">{meta.label}</span>
        <span className="ml-auto rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-[11px] text-white/45">
          {apps.length}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2">
        <AnimatePresence mode="popLayout">
          {apps.map((a) => (
            <BoardCard key={a.id} app={a} onOpen={() => onOpen(a.id)} />
          ))}
        </AnimatePresence>
        {apps.length === 0 && (
          <div
            className={cn(
              'flex flex-1 items-center justify-center rounded-xl border border-dashed border-white/[0.07] text-xs text-white/20 transition',
              over && 'border-violet-400/40 text-violet-200/60',
            )}
          >
            Drop here
          </div>
        )}
      </div>
    </div>
  )
}

/** Keyed by the saved value, so it re-seeds when the server copy changes. */
function NotesField({ initial, onSave }: { initial: string; onSave: (notes: string) => void }) {
  const [notes, setNotes] = useState(initial)
  return (
    <textarea
      className="field h-28 resize-none text-sm"
      placeholder="Recruiter name, interview dates, salary range…"
      value={notes}
      onChange={(e) => setNotes(e.target.value)}
      onBlur={() => notes !== initial && onSave(notes)}
    />
  )
}

function Drawer({ id, onClose }: { id: string; onClose: () => void }) {
  const qc = useQueryClient()
  const update = useUpdateApplication()
  const { data: app } = useQuery({
    queryKey: ['application', id],
    queryFn: () => api<ApplicationDetail>(`/applications/${id}`),
  })

  const remove = useMutation({
    mutationFn: () => api(`/applications/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.setQueryData<ApplicationSummary[]>(['applications'], (apps) => apps?.filter((a) => a.id !== id))
      toast.success('Application deleted')
      onClose()
    },
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      <motion.div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />
      <motion.aside
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-white/10 bg-ink-900/95 backdrop-blur-2xl"
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
      >
        <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
          <select
            value={app?.status ?? 'saved'}
            onChange={(e) => update.mutate({ id, status: e.target.value as ApplicationStatus })}
            className="field w-auto py-1.5 pr-8 text-sm"
          >
            {APPLICATION_STATUSES.map((s) => (
              <option key={s} value={s} className="bg-ink-900">
                {STATUS_META[s].label}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              loading={remove.isPending}
              onClick={() => confirm('Delete this application?') && remove.mutate()}
              icon={<Trash2 className="size-3.5" />}
            />
            <Button variant="ghost" size="sm" onClick={onClose} icon={<X className="size-4" />} />
          </div>
        </div>

        {!app ? (
          <div className="space-y-4 p-6">
            <Skeleton className="h-10 w-2/3" />
            <Skeleton className="h-40" />
            <Skeleton className="h-64" />
          </div>
        ) : (
          <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
            <div className="flex items-start gap-6">
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-1.5 text-sm text-violet-200/80">
                  <Building2 className="size-3.5" /> {app.company}
                </p>
                <h2 className="mt-1 font-display text-4xl leading-tight text-white">{app.title}</h2>
                <p className="mt-2 text-sm text-white/50">{app.requirements.summary}</p>
                <p className="mt-3 text-xs text-white/30">Saved {timeAgo(app.created_at)}</p>
              </div>
              <ScoreRing score={app.fit_score} size={120} />
            </div>

            <section>
              <VerdictSummary requirements={app.fit.requirements} />
              <div className="mt-4">
                <RequirementList requirements={app.fit.requirements} evidence={{}} />
              </div>
            </section>

            <section>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Cover letter</h3>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Copy className="size-3.5" />}
                  onClick={() => {
                    navigator.clipboard.writeText(app.cover_letter)
                    toast.success('Copied to clipboard')
                  }}
                >
                  Copy
                </Button>
              </div>
              <div className="rounded-2xl bg-black/25 p-5 font-display text-[17px] leading-[1.75] whitespace-pre-wrap text-white/80 ring-1 ring-white/[0.06]">
                {app.cover_letter}
              </div>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold text-white">Notes</h3>
              <NotesField
                key={app.notes ?? ''}
                initial={app.notes ?? ''}
                onSave={(notes) => update.mutate({ id, notes })}
              />
            </section>

            <details className="group rounded-2xl bg-white/[0.02] ring-1 ring-white/[0.06]">
              <summary className="cursor-pointer list-none px-5 py-3.5 text-sm text-white/60 transition hover:text-white">
                Original posting
              </summary>
              <pre className="whitespace-pre-wrap px-5 pb-5 font-sans text-[13px] leading-relaxed text-white/50">
                {app.posting}
              </pre>
            </details>
          </div>
        )}
      </motion.aside>
    </>
  )
}

export function TrackerPage() {
  const { data: apps, isLoading } = useApplications()
  const update = useUpdateApplication()
  const [openId, setOpenId] = useState<string | null>(null)

  return (
    <>
      <PageHeader
        eyebrow="Tracker"
        title={
          <>
            Every application, <span className="text-gradient italic">in motion</span>
          </>
        }
        description="Drag cards between columns as things progress. Click one for the letter, evidence and notes."
        actions={
          <Link to="/analyze">
            <Button icon={<WandSparkles className="size-4" />}>Analyze a job</Button>
          </Link>
        }
      />

      {isLoading ? (
        <div className="flex gap-4 overflow-hidden">
          {APPLICATION_STATUSES.map((s) => (
            <Skeleton key={s} className="h-[420px] w-[272px] shrink-0" />
          ))}
        </div>
      ) : !apps?.length ? (
        <Card>
          <EmptyState
            icon={<SquareKanban className="size-6" />}
            title="No applications yet"
            description="Analyze a job posting and approve the result. It lands here, ready to track."
            action={
              <Link to="/analyze">
                <Button>Analyze your first job</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <LayoutGroup>
          <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-4 sm:-mx-8 sm:px-8">
            {APPLICATION_STATUSES.map((status) => (
              <Column
                key={status}
                status={status}
                apps={apps.filter((a) => a.status === status)}
                onOpen={setOpenId}
                onDropApp={(id, s) => {
                  if (apps.find((a) => a.id === id)?.status !== s) update.mutate({ id, status: s })
                }}
              />
            ))}
          </div>
        </LayoutGroup>
      )}

      <AnimatePresence>{openId && <Drawer key={openId} id={openId} onClose={() => setOpenId(null)} />}</AnimatePresence>
    </>
  )
}
