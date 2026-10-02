import { ChevronDown, Quote, ShieldCheck } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { cn, VERDICT_META } from '../lib/format'
import type { AssessedRequirement, Evidence, Verdict } from '../lib/types'

const ORDER: Verdict[] = ['match', 'partial', 'missing']

function VerdictPill({ verdict }: { verdict: Verdict }) {
  const meta = VERDICT_META[verdict]
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset',
        meta.bg,
        meta.color,
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {meta.label}
    </span>
  )
}

function Row({
  req,
  evidence,
  index,
}: {
  req: AssessedRequirement
  evidence: Evidence[]
  index: number
}) {
  const [open, setOpen] = useState(false)
  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.25 + index * 0.05 }}
      className="group rounded-xl ring-1 ring-transparent transition hover:bg-white/[0.025] hover:ring-white/[0.06]"
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 px-3 py-2.5 text-left"
      >
        <VerdictPill verdict={req.verdict} />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white/90">
            {req.requirement}
            {req.kind === 'nice' && (
              <span className="ml-2 rounded bg-white/5 px-1.5 py-px align-middle text-[10px] uppercase tracking-wider text-white/40">
                bonus
              </span>
            )}
          </p>
          {req.evidence && (
            <p className="mt-1.5 flex gap-1.5 text-xs leading-relaxed text-white/50">
              <Quote className="mt-0.5 size-3 shrink-0 text-violet-300/60" />
              <span className="italic">{req.evidence}</span>
              {req.evidence_verified && (
                <span title="Quote verified against your CV" className="shrink-0 text-emerald-300/80">
                  <ShieldCheck className="mt-px size-3.5" />
                </span>
              )}
            </p>
          )}
        </div>
        <ChevronDown
          className={cn('mt-0.5 size-4 shrink-0 text-white/25 transition', open && 'rotate-180')}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 px-3 pb-3 pl-[5.25rem]">
              <p className="text-xs text-white/55">{req.reasoning}</p>
              {evidence.length > 0 && (
                <div className="space-y-1.5">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-white/30">
                    Closest CV passages
                  </p>
                  {evidence.map((e) => (
                    <div key={e.chunk_id} className="rounded-lg bg-black/25 p-2.5 ring-1 ring-white/5">
                      <div className="mb-1.5 flex items-center gap-2">
                        <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/5">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400"
                            style={{ width: `${Math.max(4, e.similarity * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[10px] text-white/40">
                          {(e.similarity * 100).toFixed(0)}% similar
                        </span>
                      </div>
                      <p className="line-clamp-3 text-xs leading-relaxed text-white/50">{e.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  )
}

export function RequirementList({
  requirements,
  evidence,
}: {
  requirements: AssessedRequirement[]
  evidence: Record<string, Evidence[]>
}) {
  const sorted = [...requirements].sort(
    (a, b) =>
      (a.kind === b.kind ? 0 : a.kind === 'must' ? -1 : 1) ||
      ORDER.indexOf(a.verdict) - ORDER.indexOf(b.verdict),
  )
  return (
    <ul className="-mx-3 space-y-0.5">
      {sorted.map((req, i) => (
        <Row key={req.requirement} req={req} evidence={evidence[req.requirement] ?? []} index={i} />
      ))}
    </ul>
  )
}

export function VerdictSummary({ requirements }: { requirements: AssessedRequirement[] }) {
  const counts = ORDER.map((v) => ({ v, n: requirements.filter((r) => r.verdict === v).length }))
  const total = requirements.length || 1
  return (
    <div>
      <div className="flex h-2 overflow-hidden rounded-full bg-white/5">
        {counts.map(({ v, n }) => (
          <motion.div
            key={v}
            initial={{ width: 0 }}
            animate={{ width: `${(n / total) * 100}%` }}
            transition={{ duration: 1, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className={cn(v === 'match' && 'bg-match', v === 'partial' && 'bg-partial', v === 'missing' && 'bg-missing')}
          />
        ))}
      </div>
      <div className="mt-2.5 flex gap-4 text-xs">
        {counts.map(({ v, n }) => (
          <span key={v} className="flex items-center gap-1.5 text-white/50">
            <span className={cn('size-2 rounded-full', v === 'match' && 'bg-match', v === 'partial' && 'bg-partial', v === 'missing' && 'bg-missing')} />
            <span className="font-semibold text-white/80">{n}</span> {VERDICT_META[v].label.toLowerCase()}
          </span>
        ))}
      </div>
    </div>
  )
}
