import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Building2,
  Check,
  CircleAlert,
  FileText,
  MapPin,
  PenLine,
  RotateCcw,
  Sparkles,
  ThumbsDown,
  TrendingUp,
  TriangleAlert,
  WandSparkles,
} from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { PIPELINE, Pipeline } from '../components/Pipeline'
import type { StepState } from '../components/Pipeline'
import { RequirementList, VerdictSummary } from '../components/RequirementList'
import { ScoreRing } from '../components/ScoreRing'
import { Badge, Button, Card, EmptyState, PageHeader, Skeleton, fadeUp } from '../components/ui'
import { api, streamEvents } from '../lib/api'
import { useAuth } from '../lib/auth'
import { cn, wordCount } from '../lib/format'
import { useCv } from '../lib/queries'
import type { AgentNode, ResumeAction, Review, RunDetail, RunEvent, SamplePosting } from '../lib/types'

type Phase = 'loading' | 'compose' | 'running' | 'review' | 'done' | 'rejected' | 'error'

const NODE_ORDER = PIPELINE.map((p) => p.node)

function statesUpTo(node: AgentNode | null, active: AgentNode | null): Record<string, StepState> {
  const s: Record<string, StepState> = {}
  const doneIdx = node ? NODE_ORDER.indexOf(node) : -1
  NODE_ORDER.forEach((n, i) => {
    s[n] = i <= doneIdx ? 'done' : n === active ? 'active' : 'pending'
  })
  return s
}

function describeStep(data: Record<string, unknown>): string | undefined {
  switch (data.node) {
    case 'extract_requirements':
      return `${data.requirements} requirements · ${data.company}`
    case 'retrieve_evidence':
      return `${data.chunks} CV passages retrieved`
    case 'score_fit':
      return `fit score ${data.score}/100`
    case 'draft_cover_letter':
      return 'draft ready'
    default:
      return undefined
  }
}

// ---------------------------------------------------------------------------

const normalise = (s: string) => s.split(/\s+/).join(' ').trim()

function SamplePicker({ selected, onPick }: { selected: string; onPick: (posting: string) => void }) {
  const { user } = useAuth()
  const { data: samples } = useQuery({
    queryKey: ['samples'],
    queryFn: () => api<SamplePosting[]>('/demo/postings'),
    staleTime: Infinity,
  })
  if (!samples?.length) return null
  return (
    <div className="mb-5">
      <div className="mb-3 flex items-center gap-2 text-xs text-white/45">
        <Sparkles className="size-3.5 text-violet-300" />
        {user?.is_demo
          ? 'Pick a sample posting. These replay recorded agent runs, instantly and offline.'
          : 'No posting handy? Try a sample.'}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {samples.map((s, i) => {
          const active = normalise(selected) === normalise(s.posting)
          return (
            <motion.button
              key={s.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i }}
              onClick={() => onPick(s.posting)}
              className={cn(
                'group rounded-2xl p-4 text-left ring-1 transition-all duration-300',
                active
                  ? 'bg-violet-500/[0.12] shadow-[0_10px_40px_-15px_rgb(139_92_246/0.7)] ring-violet-400/50'
                  : 'bg-white/[0.03] ring-white/[0.08] hover:-translate-y-0.5 hover:bg-white/[0.05] hover:ring-white/20',
              )}
            >
              <p className="flex items-center gap-1.5 text-xs text-white/45">
                <Building2 className="size-3" /> {s.company}
              </p>
              <p className="mt-1 text-sm font-medium text-white">{s.title}</p>
              <p className="mt-2 text-xs text-white/40">{s.blurb}</p>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}

function Composer({ onStart, busy }: { onStart: (posting: string) => void; busy: boolean }) {
  const [posting, setPosting] = useState('')
  const ok = posting.trim().length >= 100
  return (
    <motion.div {...fadeUp}>
      <SamplePicker selected={posting} onPick={setPosting} />
      <Card glow className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
          <div className="flex items-center gap-2 text-sm text-white/60">
            <FileText className="size-4 text-violet-300" /> Job posting
          </div>
          {posting && (
            <button
              onClick={() => setPosting('')}
              className="rounded-lg px-2 py-1 text-xs text-white/40 transition hover:bg-white/5 hover:text-white/70"
            >
              Clear
            </button>
          )}
        </div>
        <textarea
          value={posting}
          onChange={(e) => setPosting(e.target.value)}
          placeholder="Paste the full job description here: title, company, responsibilities, requirements…"
          className="block h-[300px] w-full resize-none bg-transparent px-5 py-4 text-[14.5px] leading-relaxed text-white/85 outline-none placeholder:text-white/25"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] bg-black/20 px-5 py-3">
          <span className={cn('font-mono text-xs', ok ? 'text-white/35' : 'text-white/25')}>
            {posting.length.toLocaleString()} chars{!ok && posting && ' · need at least 100'}
          </span>
          <Button size="lg" disabled={!ok} loading={busy} onClick={() => onStart(posting)}>
            <WandSparkles className="size-4" /> Analyze fit
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

function JobHeader({ review }: { review: Review }) {
  const { job } = review
  return (
    <motion.div {...fadeUp}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-violet-500/10 text-violet-200 ring-violet-400/20">
          <Building2 className="size-3" /> {job.company}
        </Badge>
        {job.location && (
          <Badge>
            <MapPin className="size-3" /> {job.location}
          </Badge>
        )}
        {job.seniority !== 'unknown' && <Badge className="capitalize">{job.seniority}</Badge>}
      </div>
      <h1 className="mt-3 font-display text-4xl leading-tight text-white sm:text-5xl">{job.title}</h1>
      <p className="mt-2 max-w-3xl text-[15px] text-white/55">{job.summary}</p>
    </motion.div>
  )
}

// Must match REVISION_SUGGESTIONS in backend/app/demo/content.py (they have recorded demo replies).
const REVISE_CHIPS = ['Make it shorter', 'More confident tone', 'Less formal']

function ReviewWorkspace({
  review,
  busy,
  onAction,
}: {
  review: Review
  busy: boolean
  onAction: (a: ResumeAction) => void
}) {
  const [letter, setLetter] = useState(review.cover_letter)
  const [revising, setRevising] = useState(false)
  const [feedback, setFeedback] = useState('')
  const edited = letter.trim() !== review.cover_letter.trim()
  const textarea = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = textarea.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${el.scrollHeight + 2}px`
    }
  }, [letter])

  const { fit } = review
  return (
    <div className="space-y-6 pb-28">
      <JobHeader review={review} />

      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.05 }}>
          <Card glow className="flex flex-col items-center p-6">
            <ScoreRing score={fit.score} />
            <div className="mt-6 w-full">
              <VerdictSummary requirements={fit.requirements} />
            </div>
            {fit.strengths.length > 0 && (
              <div className="mt-6 w-full">
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-300/80">
                  <TrendingUp className="size-3.5" /> Strengths
                </p>
                <ul className="space-y-1.5 text-[13px] text-white/65">
                  {fit.strengths.map((s) => (
                    <li key={s} className="flex gap-2">
                      <Check className="mt-0.5 size-3.5 shrink-0 text-emerald-400/70" /> {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {fit.gaps.length > 0 && (
              <div className="mt-5 w-full">
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-rose-300/80">
                  <TriangleAlert className="size-3.5" /> Gaps
                </p>
                <ul className="space-y-1.5 text-[13px] text-white/65">
                  {fit.gaps.map((g) => (
                    <li key={g} className="flex gap-2">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-rose-400/60" /> {g}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        </motion.div>

        <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.12 }}>
          <Card className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[15px] font-semibold text-white">Requirement by requirement</h2>
              <span className="text-xs text-white/35">click a row for the retrieved passages</span>
            </div>
            <RequirementList requirements={fit.requirements} evidence={review.evidence} />
          </Card>
        </motion.div>
      </div>

      <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.2 }}>
        <Card glow className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] px-6 py-4">
            <div className="flex items-center gap-2">
              <PenLine className="size-4 text-violet-300" />
              <h2 className="text-[15px] font-semibold text-white">Cover letter</h2>
              {review.revisions > 0 && (
                <Badge className="bg-cyan-400/10 text-cyan-200 ring-cyan-400/20">
                  revision {review.revisions}
                </Badge>
              )}
              <AnimatePresence>
                {edited && (
                  <motion.span initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                    <Badge className="bg-amber-400/10 text-amber-200 ring-amber-400/20">edited by you</Badge>
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
            <span className="font-mono text-xs text-white/35">{wordCount(letter)} words</span>
          </div>
          <textarea
            ref={textarea}
            value={letter}
            onChange={(e) => setLetter(e.target.value)}
            spellCheck
            className="mx-auto block min-h-[320px] w-full max-w-[70ch] resize-none bg-transparent px-6 py-8 font-display text-[19px] leading-[1.75] text-white/85 outline-none"
          />
        </Card>
      </motion.div>

      {/* Sticky decision bar */}
      <motion.div
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 260, damping: 26 }}
        className="fixed inset-x-0 bottom-4 z-40 px-4 lg:left-64"
      >
        <div className="glass mx-auto max-w-4xl rounded-2xl p-3 shadow-[0_20px_80px_-20px_rgb(0_0_0/0.9)]">
          <AnimatePresence initial={false}>
            {revising && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="space-y-2 px-1 pb-3">
                  <div className="flex flex-wrap gap-1.5">
                    {REVISE_CHIPS.map((c) => (
                      <button
                        key={c}
                        onClick={() => setFeedback(c)}
                        className="rounded-full bg-white/[0.05] px-2.5 py-1 text-xs text-white/60 ring-1 ring-white/10 transition hover:bg-white/10 hover:text-white"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                  <input
                    autoFocus
                    className="field py-2.5"
                    placeholder="Tell the agent what to change…"
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && feedback.trim()) onAction({ action: 'revise', feedback })
                    }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div className="flex flex-wrap items-center gap-2">
            <p className="mr-auto hidden pl-2 text-xs text-white/45 sm:block">
              Nothing is saved until you approve.
            </p>
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => onAction({ action: 'reject' })}
              icon={<ThumbsDown className="size-4" />}
            >
              Discard
            </Button>
            {revising ? (
              <Button
                variant="secondary"
                loading={busy}
                disabled={!feedback.trim()}
                onClick={() => onAction({ action: 'revise', feedback })}
                icon={<RotateCcw className="size-4" />}
              >
                Send feedback
              </Button>
            ) : (
              <Button
                variant="secondary"
                disabled={busy || !review.can_revise}
                title={review.can_revise ? undefined : 'Revision limit reached'}
                onClick={() => setRevising(true)}
                icon={<RotateCcw className="size-4" />}
              >
                Revise
              </Button>
            )}
            <Button
              variant="success"
              loading={busy && !revising}
              disabled={busy || !letter.trim()}
              onClick={() =>
                onAction(edited ? { action: 'edit', cover_letter: letter } : { action: 'approve' })
              }
              icon={<Check className="size-4" strokeWidth={3} />}
            >
              {edited ? 'Save my version' : 'Approve & save'}
            </Button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

function Celebration({ title, onAgain }: { title: string; onAgain: () => void }) {
  return (
    <motion.div {...fadeUp} className="mx-auto max-w-lg py-16 text-center">
      <div className="relative mx-auto mb-8 grid size-28 place-items-center">
        {Array.from({ length: 12 }, (_, i) => (
          <motion.span
            key={i}
            className="absolute size-2 rounded-full"
            style={{ background: i % 2 ? '#22d3ee' : '#a78bfa' }}
            initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
            animate={{
              x: Math.cos((i / 12) * Math.PI * 2) * 90,
              y: Math.sin((i / 12) * Math.PI * 2) * 90,
              opacity: 0,
              scale: 0.3,
            }}
            transition={{ duration: 1.1, delay: 0.2, ease: 'easeOut' }}
          />
        ))}
        <motion.div
          initial={{ scale: 0, rotate: -45 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 15 }}
          className="grid size-24 place-items-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-400 shadow-[0_0_60px_-10px_rgb(52_211_153/0.8)]"
        >
          <Check className="size-11 text-ink-950" strokeWidth={3} />
        </motion.div>
      </div>
      <h1 className="font-display text-5xl text-white">Saved to your tracker</h1>
      <p className="mt-3 text-white/55">{title} is ready to send. Good luck!</p>
      <div className="mt-8 flex justify-center gap-3">
        <Link to="/tracker">
          <Button size="lg">
            Open tracker <ArrowRight className="size-4" />
          </Button>
        </Link>
        <Button size="lg" variant="secondary" onClick={onAgain}>
          Analyze another
        </Button>
      </div>
    </motion.div>
  )
}

// ---------------------------------------------------------------------------

export function AnalyzePage() {
  const { runId: routeRunId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: cv, isLoading: cvLoading } = useCv()

  const [phase, setPhase] = useState<Phase>(routeRunId ? 'loading' : 'compose')
  const [steps, setSteps] = useState<Record<string, StepState>>(statesUpTo(null, null))
  const [details, setDetails] = useState<Record<string, string | undefined>>({})
  const [review, setReview] = useState<Review | null>(null)
  const [error, setError] = useState<{ message: string; retryable: boolean } | null>(null)
  const [preview, setPreview] = useState<{ title?: string; company?: string; score?: number }>({})
  const [busy, setBusy] = useState(false)
  const runIdRef = useRef<string | null>(routeRunId ?? null)

  const handleEvent = useCallback(
    (e: RunEvent) => {
      switch (e.event) {
        case 'run':
          if (runIdRef.current !== e.data.run_id) {
            runIdRef.current = e.data.run_id
            navigate(`/analyze/${e.data.run_id}`, { replace: true })
          }
          break
        case 'step': {
          const { node } = e.data
          const next = NODE_ORDER[NODE_ORDER.indexOf(node) + 1] ?? null
          setSteps((s) => ({ ...s, [node]: 'done', ...(next ? { [next]: 'active' } : {}) }))
          setDetails((d) => ({ ...d, [node]: describeStep(e.data) }))
          if (node === 'extract_requirements')
            setPreview((p) => ({ ...p, title: String(e.data.title), company: String(e.data.company) }))
          if (node === 'score_fit') setPreview((p) => ({ ...p, score: Number(e.data.score) }))
          break
        }
        case 'review':
          setReview(e.data)
          setPhase('review')
          break
        case 'done':
          setPhase(e.data.status === 'completed' ? 'done' : 'rejected')
          qc.invalidateQueries({ queryKey: ['applications'] })
          break
        case 'error':
          setError(e.data)
          setSteps((s) => {
            const active = Object.entries(s).find(([, v]) => v === 'active')?.[0]
            return active ? { ...s, [active]: 'error' } : s
          })
          setPhase('error')
          break
      }
    },
    [navigate, qc],
  )

  const runStream = useCallback(
    async (path: string, body: unknown) => {
      setBusy(true)
      try {
        await streamEvents(path, body, handleEvent)
      } catch (err) {
        setError({ message: err instanceof Error ? err.message : 'Connection lost', retryable: false })
        setPhase('error')
      } finally {
        setBusy(false)
        qc.invalidateQueries({ queryKey: ['runs'] })
      }
    },
    [handleEvent, qc],
  )

  // Restore a run from the URL (page reload, or the server slept and woke up).
  useEffect(() => {
    if (!routeRunId) {
      runIdRef.current = null
      setPhase('compose')
      return
    }
    if (phase !== 'loading') return // we navigated here ourselves mid-stream
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const load = async () => {
      try {
        const run = await api<RunDetail>(`/runs/${routeRunId}`)
        if (cancelled) return
        const s = run.state
        if (s.job) setPreview({ title: s.job.title, company: s.job.company, score: s.fit?.score })
        if (run.status === 'awaiting_review' && run.review) {
          setReview(run.review)
          setSteps(statesUpTo('draft_cover_letter', 'human_review'))
          setPhase('review')
        } else if (run.status === 'completed') {
          setPreview((p) => ({ ...p, title: s.job?.title }))
          setPhase('done')
        } else if (run.status === 'rejected') {
          setPhase('rejected')
        } else if (run.status === 'failed' || run.retryable) {
          setError({ message: run.error ?? 'This run was interrupted.', retryable: true })
          setPhase('error')
        } else {
          // Still running in the background (e.g. the tab was closed); poll.
          const last = s.fit ? 'score_fit' : s.evidence ? 'retrieve_evidence' : s.job ? 'extract_requirements' : null
          const next = NODE_ORDER[last ? NODE_ORDER.indexOf(last) + 1 : 0]
          setSteps(statesUpTo(last, next))
          setPhase('running')
          timer = setTimeout(load, 2500)
        }
      } catch (err) {
        if (!cancelled) {
          setError({ message: err instanceof Error ? err.message : 'Run not found', retryable: false })
          setPhase('error')
        }
      }
    }
    load()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeRunId])

  function reset() {
    runIdRef.current = null
    setReview(null)
    setError(null)
    setPreview({})
    setDetails({})
    setSteps(statesUpTo(null, null))
    setPhase('compose')
    navigate('/analyze')
  }

  function start(posting: string) {
    setSteps(statesUpTo(null, 'extract_requirements'))
    setDetails({})
    setPreview({})
    setPhase('running')
    runStream('/runs', { posting })
  }

  function decide(action: ResumeAction) {
    if (action.action === 'revise') {
      setSteps(statesUpTo('score_fit', 'draft_cover_letter'))
      setDetails((d) => ({ ...d, draft_cover_letter: undefined }))
      setPhase('running')
    }
    if (action.action === 'reject' && !confirm('Discard this application? Nothing will be saved.')) return
    runStream(`/runs/${runIdRef.current}/resume`, action).then(() => {
      if (action.action !== 'revise' && action.action !== 'reject') toast.success('Application saved')
    })
  }

  function retry() {
    setError(null)
    setPhase('running')
    setSteps((s) => {
      const failed = Object.entries(s).find(([, v]) => v === 'error')?.[0]
      return failed ? { ...s, [failed]: 'active' } : s
    })
    runStream(`/runs/${runIdRef.current}/retry`, {})
  }

  // ---- render ----

  if (!routeRunId && !cvLoading && cv === null) {
    return (
      <>
        <PageHeader eyebrow="Analyze" title="First, your CV" />
        <Card>
          <EmptyState
            icon={<FileText className="size-6" />}
            title="The agent needs your CV to find evidence"
            description="Upload a PDF or paste your CV text. It takes a few seconds to index."
            action={
              <Link to="/cv">
                <Button>
                  Add my CV <ArrowRight className="size-4" />
                </Button>
              </Link>
            }
          />
        </Card>
      </>
    )
  }

  if (phase === 'review' && review) {
    // Keyed by the draft so a revision re-seeds the editable letter.
    return <ReviewWorkspace key={review.cover_letter} review={review} busy={busy} onAction={decide} />
  }

  if (phase === 'done') {
    return <Celebration title={preview.title ?? 'Your application'} onAgain={reset} />
  }

  if (phase === 'rejected') {
    return (
      <motion.div {...fadeUp}>
        <Card>
          <EmptyState
            icon={<ThumbsDown className="size-6" />}
            title="Discarded"
            description="Nothing was saved. On to the next one."
            action={<Button onClick={reset}>Analyze another job</Button>}
          />
        </Card>
      </motion.div>
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Analyze a job"
        title={
          phase === 'compose' ? (
            <>
              How well do you <span className="text-gradient italic">fit</span>?
            </>
          ) : (
            <span className="shimmer-text">{preview.title ?? 'Analyzing…'}</span>
          )
        }
        description={
          phase === 'compose'
            ? 'Paste a posting. The agent extracts requirements, finds proof in your CV, scores each one, and drafts a letter for your review.'
            : preview.company
              ? `at ${preview.company}`
              : 'The agent is working through the posting'
        }
      />

      <AnimatePresence mode="wait">
        {phase === 'compose' || phase === 'loading' ? (
          phase === 'loading' ? (
            <Skeleton key="sk" className="h-96" />
          ) : (
            <Composer key="compose" onStart={start} busy={busy} />
          )
        ) : (
          <motion.div
            key="run"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid gap-6 lg:grid-cols-[360px_1fr]"
          >
            <Card glow className="h-fit p-6">
              <p className="mb-5 font-mono text-[11px] uppercase tracking-[0.2em] text-white/35">
                Agent trace
              </p>
              <Pipeline states={steps} details={details} />
            </Card>

            {phase === 'error' && error ? (
              <Card className="p-8">
                <div className="flex gap-4">
                  <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-rose-500/10 ring-1 ring-rose-400/25">
                    <CircleAlert className="size-5 text-rose-300" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">The run stopped</h2>
                    <p className="mt-1 text-sm text-white/55">{error.message}</p>
                    <p className="mt-3 text-xs text-white/35">
                      Progress is checkpointed, so a retry picks up from the last completed step.
                    </p>
                    <div className="mt-5 flex gap-2">
                      {error.retryable && runIdRef.current && (
                        <Button onClick={retry} icon={<RotateCcw className="size-4" />}>
                          Retry from checkpoint
                        </Button>
                      )}
                      <Button variant="secondary" onClick={reset}>
                        Start over
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ) : (
              <Card className="relative overflow-hidden p-6">
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-violet-400/70 to-transparent">
                  <motion.div
                    className="h-px w-1/3 bg-gradient-to-r from-transparent via-cyan-300 to-transparent"
                    animate={{ x: ['-100%', '300%'] }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                  />
                </div>
                <div className="flex items-start justify-between gap-6">
                  <div className="min-w-0 flex-1 space-y-3">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-9 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </div>
                  <AnimatePresence>
                    {preview.score !== undefined ? (
                      <motion.div initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }}>
                        <ScoreRing score={preview.score} size={120} />
                      </motion.div>
                    ) : (
                      <Skeleton className="size-[120px] rounded-full" />
                    )}
                  </AnimatePresence>
                </div>
                <div className="mt-8 space-y-2.5">
                  {Array.from({ length: 6 }, (_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <Skeleton className="h-5 w-16 rounded-full" />
                      <Skeleton className="h-4 flex-1" />
                    </div>
                  ))}
                </div>
                <p className="mt-8 text-center font-mono text-xs text-white/30">
                  Steps are checkpointed to Postgres, so you can close this tab and come back.
                </p>
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
