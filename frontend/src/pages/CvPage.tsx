import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, FileUp, Layers, Search, Trash2, Type, Upload } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import { toast } from 'sonner'
import { Badge, Button, Card, PageHeader, Skeleton, fadeUp } from '../components/ui'
import { api, json } from '../lib/api'
import { cn, timeAgo } from '../lib/format'
import { useCv } from '../lib/queries'
import type { Cv, Evidence } from '../lib/types'

function UploadPanel({ hasCv, onDone }: { hasCv: boolean; onDone?: () => void }) {
  const qc = useQueryClient()
  const [tab, setTab] = useState<'pdf' | 'text'>('pdf')
  const [text, setText] = useState('')
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  const upload = useMutation({
    mutationFn: (body: FormData) => api<Cv>('/cv', { method: 'POST', body }),
    onSuccess: (cv) => {
      qc.setQueryData(['cv'], cv)
      toast.success(`CV indexed into ${cv.chunk_count} searchable chunks`)
      setText('')
      onDone?.()
    },
    onError: (e) => toast.error(e.message),
  })

  function sendFile(file: File | undefined) {
    if (!file) return
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Please choose a PDF file')
      return
    }
    const body = new FormData()
    body.append('file', file)
    upload.mutate(body)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    sendFile(e.dataTransfer.files[0])
  }

  function sendText(e: FormEvent) {
    e.preventDefault()
    const body = new FormData()
    body.append('text', text)
    upload.mutate(body)
  }

  return (
    <Card glow className="p-6 sm:p-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">
            {hasCv ? 'Replace your CV' : 'Add your CV'}
          </h2>
          <p className="text-sm text-white/45">It's split into passages and embedded for retrieval.</p>
        </div>
        <div className="flex rounded-xl bg-black/30 p-1 ring-1 ring-white/[0.06]">
          {(
            [
              ['pdf', 'PDF', FileUp],
              ['text', 'Paste', Type],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={cn(
                'relative flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                tab === key ? 'text-white' : 'text-white/45 hover:text-white/75',
              )}
            >
              {tab === key && (
                <motion.span
                  layoutId="cv-tab"
                  className="absolute inset-0 rounded-lg bg-white/[0.09] ring-1 ring-inset ring-white/10"
                />
              )}
              <Icon className="relative size-3.5" />
              <span className="relative">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {tab === 'pdf' ? (
          <motion.div key="pdf" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <button
              onClick={() => input.current?.click()}
              onDragOver={(e) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              disabled={upload.isPending}
              className={cn(
                'group relative flex w-full flex-col items-center justify-center overflow-hidden rounded-2xl border border-dashed px-6 py-14 transition-all duration-300',
                dragging
                  ? 'scale-[1.01] border-violet-400/70 bg-violet-500/10'
                  : 'border-white/15 bg-black/20 hover:border-violet-400/40 hover:bg-white/[0.03]',
              )}
            >
              <div
                className={cn(
                  'absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgb(139_92_246/0.25),transparent_60%)] opacity-0 transition-opacity duration-500',
                  (dragging || upload.isPending) && 'opacity-100',
                  'group-hover:opacity-60',
                )}
              />
              <motion.div
                animate={upload.isPending ? { y: [0, -8, 0] } : dragging ? { scale: 1.15 } : { scale: 1 }}
                transition={upload.isPending ? { repeat: Infinity, duration: 1.2 } : { type: 'spring' }}
                className="relative mb-4 grid size-14 place-items-center rounded-2xl bg-ink-850 ring-1 ring-white/10"
              >
                <Upload className="size-6 text-violet-300" />
              </motion.div>
              <p className="relative text-[15px] font-medium text-white">
                {upload.isPending ? (
                  <span className="shimmer-text">Extracting & embedding…</span>
                ) : (
                  <>
                    Drop your CV here, or <span className="text-violet-300">browse</span>
                  </>
                )}
              </p>
              <p className="relative mt-1 text-xs text-white/40">PDF up to 5 MB · 10 pages</p>
              <input
                ref={input}
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(e) => {
                  sendFile(e.target.files?.[0])
                  e.target.value = ''
                }}
              />
            </button>
          </motion.div>
        ) : (
          <motion.form
            key="text"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onSubmit={sendText}
          >
            <textarea
              className="field h-64 resize-none font-mono text-[13px] leading-relaxed"
              placeholder="Paste the full text of your CV: experience, projects, skills, education…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div className="mt-3 flex items-center justify-between">
              <span className="font-mono text-xs text-white/35">{text.length.toLocaleString()} chars</span>
              <Button type="submit" loading={upload.isPending} disabled={text.trim().length < 50}>
                Index CV
              </Button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </Card>
  )
}

function Probe() {
  const [query, setQuery] = useState('')
  const search = useMutation({
    mutationFn: (q: string) => api<Evidence[]>('/cv/search', { method: 'POST', ...json({ query: q, k: 4 }) }),
    onError: (e) => toast.error(e.message),
  })
  const suggestions = ['Leadership', 'Python backend', 'Testing & CI', 'Cloud infrastructure']

  return (
    <Card className="flex flex-col p-6">
      <div className="flex items-center gap-2">
        <Search className="size-4 text-cyan-300" />
        <h2 className="text-[15px] font-semibold text-white">Probe your CV</h2>
      </div>
      <p className="mt-1 text-sm text-white/45">
        See exactly which passages the agent will retrieve for a requirement.
      </p>
      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (query.trim()) search.mutate(query.trim())
        }}
      >
        <input
          className="field py-2.5"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. production Kubernetes"
        />
        <Button type="submit" variant="secondary" loading={search.isPending} className="h-auto">
          Search
        </Button>
      </form>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => {
              setQuery(s)
              search.mutate(s)
            }}
            className="rounded-full bg-white/[0.04] px-2.5 py-1 text-xs text-white/55 ring-1 ring-white/10 transition hover:bg-white/[0.08] hover:text-white"
          >
            {s}
          </button>
        ))}
      </div>
      <div className="mt-5 space-y-2.5">
        <AnimatePresence mode="popLayout">
          {search.data?.map((hit, i) => (
            <motion.div
              key={hit.chunk_id + search.submittedAt}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ delay: i * 0.07 }}
              className="rounded-xl bg-black/25 p-3.5 ring-1 ring-white/[0.06]"
            >
              <div className="mb-2 flex items-center gap-3">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(3, hit.similarity * 100)}%` }}
                    transition={{ duration: 0.8, delay: 0.1 + i * 0.07 }}
                  />
                </div>
                <span className="font-mono text-[11px] text-cyan-200/70">
                  {(hit.similarity * 100).toFixed(1)}%
                </span>
              </div>
              <p className="line-clamp-4 text-[13px] leading-relaxed text-white/60">{hit.content}</p>
            </motion.div>
          ))}
        </AnimatePresence>
        {search.data?.length === 0 && <p className="text-sm text-white/40">No passages found.</p>}
      </div>
    </Card>
  )
}

export function CvPage() {
  const { data: cv, isLoading } = useCv()
  const qc = useQueryClient()
  const [replacing, setReplacing] = useState(false)

  const remove = useMutation({
    mutationFn: () => api('/cv', { method: 'DELETE' }),
    onSuccess: () => {
      qc.setQueryData(['cv'], null)
      toast.success('CV deleted')
    },
  })

  return (
    <>
      <PageHeader
        eyebrow="Knowledge base"
        title={
          <>
            Your <span className="text-gradient italic">CV</span>, indexed
          </>
        }
        description="The agent only ever cites what's written here, so the more specific your CV, the stronger your matches."
      />

      {isLoading ? (
        <Skeleton className="h-80" />
      ) : !cv ? (
        <motion.div {...fadeUp} className="mx-auto max-w-2xl">
          <UploadPanel hasCv={false} />
        </motion.div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <motion.div {...fadeUp} className="space-y-6">
            <AnimatePresence>
              {replacing && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                  <UploadPanel hasCv onDone={() => setReplacing(false)} />
                </motion.div>
              )}
            </AnimatePresence>
            <Card className="overflow-hidden">
              <div className="flex flex-wrap items-center gap-3 border-b border-white/[0.06] px-6 py-4">
                <div className="grid size-10 place-items-center rounded-xl bg-violet-500/15 ring-1 ring-violet-400/25">
                  <FileText className="size-5 text-violet-300" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-white">{cv.filename ?? 'Pasted CV'}</p>
                  <p className="text-xs text-white/40">Updated {timeAgo(cv.created_at)}</p>
                </div>
                <Badge className="bg-cyan-400/10 text-cyan-200 ring-cyan-400/20">
                  <Layers className="size-3" /> {cv.chunk_count} chunks
                </Badge>
                <Badge>{cv.content.length.toLocaleString()} chars</Badge>
                <Button variant="secondary" size="sm" onClick={() => setReplacing((r) => !r)}>
                  {replacing ? 'Cancel' : 'Replace'}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  loading={remove.isPending}
                  onClick={() => confirm('Delete your CV? You can upload a new one anytime.') && remove.mutate()}
                  icon={<Trash2 className="size-3.5" />}
                />
              </div>
              <pre className="max-h-[560px] overflow-auto whitespace-pre-wrap px-6 py-5 font-sans text-[13.5px] leading-7 text-white/65">
                {cv.content}
              </pre>
            </Card>
          </motion.div>
          <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.1 }}>
            <Probe />
          </motion.div>
        </div>
      )}
    </>
  )
}
