import { ArrowRight, Check, FileSearch, Quote, ShieldCheck, Sparkles, UserCheck } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Logo } from '../components/Logo'
import { ScoreRing } from '../components/ScoreRing'
import { Turnstile } from '../components/Turnstile'
import { Button } from '../components/ui'
import { useAuth } from '../lib/auth'
import { cn } from '../lib/format'

type Mode = 'login' | 'signup'

const FEATURES = [
  { icon: FileSearch, text: 'RAG over your CV with pgvector' },
  { icon: ShieldCheck, text: 'Every quote verified, no invented skills' },
  { icon: UserCheck, text: 'Human-in-the-loop: you approve before anything is saved' },
]

/** Floating product preview on the hero side. */
function HeroPreview() {
  const rows = [
    { t: 'Python & FastAPI APIs', v: 'match' },
    { t: 'PostgreSQL query tuning', v: 'match' },
    { t: 'CI with pytest', v: 'partial' },
    { t: 'Kubernetes in production', v: 'missing' },
  ] as const
  return (
    <div className="relative mx-auto mt-10 h-[270px] w-full max-w-[520px] [@media(max-height:860px)]:hidden">
      <motion.div
        initial={{ opacity: 0, y: 30, rotate: -4 }}
        animate={{ opacity: 1, y: 0, rotate: -4 }}
        transition={{ delay: 0.3, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="glass absolute top-6 left-0 w-[290px] rounded-2xl p-4"
      >
        <p className="font-mono text-[10px] uppercase tracking-widest text-white/35">Requirements</p>
        <ul className="mt-3 space-y-2.5">
          {rows.map((r, i) => (
            <motion.li
              key={r.t}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.9 + i * 0.15 }}
              className="flex items-center justify-between gap-3 text-[13px] text-white/80"
            >
              {r.t}
              <span
                className={cn(
                  'size-2 shrink-0 rounded-full',
                  r.v === 'match' && 'bg-match shadow-[0_0_10px] shadow-match',
                  r.v === 'partial' && 'bg-partial shadow-[0_0_10px] shadow-partial',
                  r.v === 'missing' && 'bg-missing shadow-[0_0_10px] shadow-missing',
                )}
              />
            </motion.li>
          ))}
        </ul>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.5, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="glass absolute top-0 right-2 rounded-3xl p-3"
      >
        <motion.div animate={{ y: [0, -6, 0] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}>
          <ScoreRing score={78} size={150} />
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 30, rotate: 3 }}
        animate={{ opacity: 1, y: 0, rotate: 2 }}
        transition={{ delay: 0.7, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="glass absolute right-6 bottom-0 w-[300px] rounded-2xl p-4"
      >
        <div className="flex items-center gap-2 text-[11px] font-medium text-emerald-300">
          <ShieldCheck className="size-3.5" /> Evidence verified against your CV
        </div>
        <p className="mt-2 flex gap-2 text-[13px] italic leading-relaxed text-white/70">
          <Quote className="mt-0.5 size-3.5 shrink-0 text-violet-300/70" />
          Tuned slow queries with indexes, cutting p95 latency of the billing API by 40%.
        </p>
      </motion.div>
    </div>
  )
}

export function AuthPage() {
  const { login, signup, demo } = useAuth()
  const [demoBusy, setDemoBusy] = useState(false)
  const [mode, setMode] = useState<Mode>('signup')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // Turnstile runs invisibly; keep its token in a ref so a click can wait for it.
  const captcha = useRef<string | null>(null)
  const [captchaKey, setCaptchaKey] = useState(0)

  /** Resolves the current token, waiting briefly if the challenge hasn't finished. */
  async function captchaToken(): Promise<string> {
    for (let waited = 0; !captcha.current && waited < 15_000; waited += 100) {
      await new Promise((r) => setTimeout(r, 100))
    }
    if (!captcha.current) throw new Error('The captcha check did not complete. Please reload and try again.')
    return captcha.current
  }

  /** Tokens are single-use: after any attempt, remount the widget for a fresh one. */
  function renewCaptcha() {
    captcha.current = null
    setCaptchaKey((k) => k + 1)
  }

  async function attempt(run: (token: string) => Promise<void>, setPending: (b: boolean) => void) {
    setPending(true)
    setError(null)
    try {
      await run(await captchaToken())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      renewCaptcha()
    } finally {
      setPending(false)
    }
  }

  const tryDemo = () => attempt((token) => demo(token), setDemoBusy)

  function submit(e: FormEvent) {
    e.preventDefault()
    attempt((token) => (mode === 'login' ? login : signup)(email, password, token), setBusy)
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.15fr_1fr]">
      {/* Hero */}
      <section className="relative hidden flex-col justify-between overflow-hidden px-12 py-10 lg:flex xl:px-20">
        <Logo />
        <div className="py-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex items-center gap-2 rounded-full bg-white/[0.04] px-3 py-1 text-xs text-white/60 ring-1 ring-white/10">
              <Sparkles className="size-3.5 text-violet-300" /> LangGraph agent · human-in-the-loop
            </span>
            <h1 className="mt-6 font-display text-6xl leading-[0.98] tracking-tight text-white xl:text-7xl">
              Apply with <span className="text-gradient italic">evidence</span>,
              <br />
              not adjectives.
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-relaxed text-white/55">
              Paste a job posting. An agent reads it, finds proof in your CV, scores your fit,
              and drafts a cover letter that only says true things. Then it waits for you.
            </p>
            <ul className="mt-8 space-y-3">
              {FEATURES.map(({ icon: Icon, text }, i) => (
                <motion.li
                  key={text}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  className="flex items-center gap-3 text-sm text-white/70"
                >
                  <span className="grid size-7 place-items-center rounded-lg bg-white/[0.05] ring-1 ring-white/10">
                    <Icon className="size-3.5 text-cyan-300" />
                  </span>
                  {text}
                </motion.li>
              ))}
            </ul>
          </motion.div>
          <HeroPreview />
        </div>
        <p className="font-mono text-[11px] text-white/25">
          FastAPI · LangGraph · pgvector · React — running entirely on free tiers
        </p>
      </section>

      {/* Form */}
      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-[420px]"
        >
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <div className="glass ring-gradient rounded-3xl p-7 sm:p-8">
            <div className="relative mb-7 grid grid-cols-2 rounded-xl bg-black/30 p-1 ring-1 ring-white/[0.06]">
              {(['signup', 'login'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    setMode(m)
                    setError(null)
                  }}
                  className={cn(
                    'relative z-10 rounded-lg py-2 text-sm font-medium transition-colors',
                    mode === m ? 'text-white' : 'text-white/45 hover:text-white/75',
                  )}
                >
                  {mode === m && (
                    <motion.span
                      layoutId="auth-tab"
                      className="absolute inset-0 -z-10 rounded-lg bg-white/[0.09] ring-1 ring-inset ring-white/10"
                      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                    />
                  )}
                  {m === 'signup' ? 'Create account' : 'Sign in'}
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={mode}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2 }}
              >
                <h2 className="font-display text-3xl text-white">
                  {mode === 'signup' ? 'Start applying smarter' : 'Welcome back'}
                </h2>
                <p className="mt-1.5 text-sm text-white/45">
                  {mode === 'signup'
                    ? 'Free, private, and your data stays yours.'
                    : 'Pick up where your applications left off.'}
                </p>
              </motion.div>
            </AnimatePresence>

            <form onSubmit={submit} className="mt-6 space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-white/55">Email</span>
                <input
                  className="field"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ada@example.com"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 flex justify-between text-xs font-medium text-white/55">
                  Password
                  {mode === 'signup' && <span className="text-white/30">8+ characters</span>}
                </span>
                <input
                  className="field"
                  type="password"
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                  minLength={mode === 'signup' ? 8 : 1}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </label>

              <Turnstile key={captchaKey} onToken={(t) => (captcha.current = t)} />

              <AnimatePresence>
                {error && (
                  <motion.p
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-200 ring-1 ring-rose-400/20"
                  >
                    {error}
                  </motion.p>
                )}
              </AnimatePresence>

              <Button type="submit" size="lg" className="w-full" loading={busy}>
                {mode === 'signup' ? 'Create account' : 'Sign in'}
                {!busy && <ArrowRight className="size-4" />}
              </Button>
            </form>

            <div className="my-6 flex items-center gap-3 text-[11px] uppercase tracking-[0.2em] text-white/25">
              <span className="h-px flex-1 bg-white/10" /> or <span className="h-px flex-1 bg-white/10" />
            </div>
            <Button
              type="button"
              variant="secondary"
              size="lg"
              className="w-full"
              loading={demoBusy}
              disabled={busy}
              onClick={tryDemo}
              icon={<Sparkles className="size-4 text-violet-300" />}
            >
              Explore the demo, no signup
            </Button>
            <p className="mt-2 text-center text-xs text-white/35">
              A sample CV and tracker, plus recorded agent runs that work even offline.
            </p>

            <p className="mt-6 flex items-center justify-center gap-2 text-xs text-white/35">
              <Check className="size-3.5 text-emerald-400/70" />
              Protected by Cloudflare Turnstile · passwords hashed with argon2id
            </p>
          </div>
        </motion.div>
      </section>
    </div>
  )
}
