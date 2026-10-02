import { Server } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { API_URL } from '../lib/api'
import { Button } from './ui'

type Phase = 'checking' | 'waking' | 'ready' | 'down'

// Render's free tier sleeps after 15 idle minutes and takes ~30-50s to wake.
// Rather than hiding that, we show it honestly.
const EXPECTED_WAKE_SECONDS = 45
const GIVE_UP_SECONDS = 150

async function ping(timeoutMs: number): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/healthz`, { signal: AbortSignal.timeout(timeoutMs) })
    return res.ok
  } catch {
    return false
  }
}

export function WakeGate({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>('checking')
  const [elapsed, setElapsed] = useState(0)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    const started = Date.now()
    const tick = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 250)

    ;(async () => {
      if (await ping(2500)) {
        if (!cancelled) setPhase('ready')
        return
      }
      if (!cancelled) setPhase('waking')
      while (!cancelled) {
        if (await ping(8000)) {
          if (!cancelled) setPhase('ready')
          return
        }
        if ((Date.now() - started) / 1000 > GIVE_UP_SECONDS) {
          if (!cancelled) setPhase('down')
          return
        }
        await new Promise((r) => setTimeout(r, 2000))
      }
    })()

    return () => {
      cancelled = true
      clearInterval(tick)
    }
  }, [attempt])

  if (phase === 'ready') return <>{children}</>
  if (phase === 'checking') return null

  const progress = Math.min(elapsed / EXPECTED_WAKE_SECONDS, 0.96)

  return (
    <div className="grid min-h-dvh place-items-center px-4">
      <AnimatePresence mode="wait">
        <motion.div
          key={phase}
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 1.02 }}
          transition={{ duration: 0.5 }}
          className="flex w-full max-w-md flex-col items-center text-center"
        >
          {/* Pulsing orb with orbiting rings */}
          <div className="relative mb-10 grid size-40 place-items-center">
            <motion.div
              className="absolute inset-0 rounded-full bg-gradient-to-br from-violet-500/40 to-cyan-400/30 blur-3xl"
              animate={{ scale: [1, 1.25, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            />
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="absolute rounded-full border border-white/10"
                style={{ inset: i * 16 }}
                animate={{ rotate: i % 2 ? -360 : 360 }}
                transition={{ duration: 10 + i * 6, repeat: Infinity, ease: 'linear' }}
              >
                <span className="absolute -top-1 left-1/2 size-2 -translate-x-1/2 rounded-full bg-cyan-300 shadow-[0_0_12px_#67e8f9]" />
              </motion.div>
            ))}
            <div className="relative grid size-16 place-items-center rounded-2xl bg-ink-850 ring-1 ring-white/15">
              <Server className="size-7 text-violet-200" />
            </div>
          </div>

          {phase === 'waking' ? (
            <>
              <h1 className="font-display text-4xl text-white">
                Waking up the <span className="text-gradient italic">server</span>
              </h1>
              <p className="mt-3 text-[15px] leading-relaxed text-white/55">
                This demo runs on a free tier that naps after 15 quiet minutes. It usually takes
                30–50 seconds to wake up, and is quick after that.
              </p>
              <div className="mt-8 w-full">
                <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400"
                    animate={{ width: `${progress * 100}%` }}
                    transition={{ ease: 'easeOut', duration: 0.6 }}
                  />
                </div>
                <div className="mt-3 flex justify-between font-mono text-xs text-white/40">
                  <span className="shimmer-text">booting container…</span>
                  <span>{elapsed}s</span>
                </div>
              </div>
            </>
          ) : (
            <>
              <h1 className="font-display text-4xl text-white">The server isn't answering</h1>
              <p className="mt-3 text-[15px] leading-relaxed text-white/55">
                It may be down for maintenance, or a free-tier limit was hit. Try again in a
                minute.
              </p>
              <Button
                className="mt-8"
                onClick={() => {
                  setElapsed(0)
                  setPhase('checking')
                  setAttempt((a) => a + 1)
                }}
              >
                Try again
              </Button>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
