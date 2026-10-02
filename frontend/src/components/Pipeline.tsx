import { Brain, Check, FileSearch, PenLine, ScanText, UserCheck, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import type { ReactNode } from 'react'
import { cn } from '../lib/format'
import type { AgentNode } from '../lib/types'

export type StepState = 'pending' | 'active' | 'done' | 'error'

export const PIPELINE: Array<{ node: AgentNode; title: string; desc: string; icon: ReactNode }> = [
  {
    node: 'extract_requirements',
    title: 'Reading the posting',
    desc: 'Pulling out must-haves, nice-to-haves and seniority',
    icon: <ScanText className="size-4" />,
  },
  {
    node: 'retrieve_evidence',
    title: 'Searching your CV',
    desc: 'Vector search for evidence of each requirement',
    icon: <FileSearch className="size-4" />,
  },
  {
    node: 'score_fit',
    title: 'Scoring your fit',
    desc: 'Judging each requirement and verifying every quote',
    icon: <Brain className="size-4" />,
  },
  {
    node: 'draft_cover_letter',
    title: 'Drafting a cover letter',
    desc: 'Grounded only in evidence from your CV',
    icon: <PenLine className="size-4" />,
  },
  {
    node: 'human_review',
    title: 'Your review',
    desc: 'Nothing is saved until you approve',
    icon: <UserCheck className="size-4" />,
  },
]

/** Vertical timeline of agent steps; the active one shimmers, finished ones show a
 * one-line result (e.g. "8 requirements"). */
export function Pipeline({
  states,
  details,
}: {
  states: Record<string, StepState>
  details: Record<string, string | undefined>
}) {
  return (
    <ol className="relative">
      {PIPELINE.map((step, i) => {
        const state = states[step.node] ?? 'pending'
        const last = i === PIPELINE.length - 1
        return (
          <li key={step.node} className="relative flex gap-4 pb-6 last:pb-0">
            {!last && (
              <div className="absolute top-10 bottom-0 left-[19px] w-px bg-white/[0.08]">
                <motion.div
                  className="w-full bg-gradient-to-b from-violet-400 to-cyan-400"
                  initial={{ height: 0 }}
                  animate={{ height: state === 'done' ? '100%' : 0 }}
                  transition={{ duration: 0.6, ease: 'easeInOut' }}
                />
              </div>
            )}
            <div className="relative shrink-0">
              {state === 'active' && (
                <motion.span
                  className="absolute -inset-1.5 rounded-2xl bg-violet-500/30"
                  animate={{ opacity: [0.3, 0.9, 0.3], scale: [0.95, 1.08, 0.95] }}
                  transition={{ duration: 1.8, repeat: Infinity }}
                />
              )}
              <div
                className={cn(
                  'relative grid size-10 place-items-center rounded-xl ring-1 transition-colors duration-500',
                  state === 'pending' && 'bg-white/[0.03] text-white/30 ring-white/10',
                  state === 'active' && 'bg-ink-800 text-violet-200 ring-violet-400/50',
                  state === 'done' && 'bg-gradient-to-br from-violet-500 to-cyan-500 text-white ring-white/20',
                  state === 'error' && 'bg-rose-500/15 text-rose-300 ring-rose-400/40',
                )}
              >
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span
                    key={state}
                    initial={{ scale: 0.4, opacity: 0, rotate: -30 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    exit={{ scale: 0.4, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 22 }}
                  >
                    {state === 'done' ? (
                      <Check className="size-4" strokeWidth={3} />
                    ) : state === 'error' ? (
                      <X className="size-4" />
                    ) : (
                      step.icon
                    )}
                  </motion.span>
                </AnimatePresence>
              </div>
            </div>
            <div className="min-w-0 pt-1.5">
              <p
                className={cn(
                  'text-sm font-medium transition-colors',
                  state === 'pending' ? 'text-white/35' : 'text-white',
                  state === 'active' && 'shimmer-text',
                )}
              >
                {step.title}
              </p>
              <AnimatePresence mode="wait" initial={false}>
                <motion.p
                  key={details[step.node] ?? step.desc}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    'mt-0.5 text-xs',
                    details[step.node] ? 'font-mono text-cyan-200/80' : 'text-white/35',
                  )}
                >
                  {details[step.node] ?? step.desc}
                </motion.p>
              </AnimatePresence>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
