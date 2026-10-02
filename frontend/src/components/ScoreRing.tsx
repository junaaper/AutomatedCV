import { animate, motion, useMotionValue, useTransform } from 'motion/react'
import { useEffect, useId } from 'react'
import { scoreTone } from '../lib/format'

/** Animated radial gauge: the arc sweeps in and the number counts up. */
export function ScoreRing({ score, size = 168 }: { score: number; size?: number }) {
  const id = useId()
  const stroke = size * 0.075
  const r = (size - stroke) / 2
  const circumference = 2 * Math.PI * r
  const tone = scoreTone(score)

  const value = useMotionValue(0)
  const display = useTransform(value, (v) => Math.round(v).toString())
  const dash = useTransform(value, (v) => circumference * (1 - v / 100))

  useEffect(() => {
    const controls = animate(value, score, { duration: 1.6, ease: [0.22, 1, 0.36, 1] })
    return () => controls.stop()
  }, [score, value])

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <div
        className="absolute inset-4 rounded-full blur-2xl"
        style={{ background: tone.glow }}
        aria-hidden
      />
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={`${id}-g`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#a78bfa" />
            <stop offset="1" stopColor={tone.color} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(255 255 255 / 0.07)" strokeWidth={stroke} />
        {/* tick marks */}
        {Array.from({ length: 40 }, (_, i) => {
          const a = (i / 40) * 2 * Math.PI
          const r1 = r - stroke * 1.1
          const r2 = r1 - (i % 5 === 0 ? 5 : 2.5)
          return (
            <line
              key={i}
              x1={size / 2 + r1 * Math.cos(a)}
              y1={size / 2 + r1 * Math.sin(a)}
              x2={size / 2 + r2 * Math.cos(a)}
              y2={size / 2 + r2 * Math.sin(a)}
              stroke="rgb(255 255 255 / 0.12)"
              strokeWidth={1}
            />
          )
        })}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`url(#${id}-g)`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset: dash }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="flex items-baseline">
          <motion.span className="font-display text-[3.4em] leading-none text-white" style={{ fontSize: size * 0.3 }}>
            {display}
          </motion.span>
          <span className="ml-0.5 text-sm text-white/40">/100</span>
        </div>
        <span className="mt-1 text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: tone.color }}>
          {tone.label}
        </span>
      </div>
    </div>
  )
}
