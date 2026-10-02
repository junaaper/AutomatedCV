/** Fixed, animated aurora behind every page: drifting blurred colour fields,
 * a faint grid that fades out from the top, and film grain. */
export function Background() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-1/3 left-1/2 h-[70vmax] w-[70vmax] -translate-x-1/2 rounded-full bg-violet-600/25 blur-[120px] animate-aurora-1" />
      <div className="absolute -top-1/4 -left-1/4 h-[55vmax] w-[55vmax] rounded-full bg-cyan-500/15 blur-[120px] animate-aurora-2" />
      <div className="absolute top-1/3 -right-1/4 h-[50vmax] w-[50vmax] rounded-full bg-fuchsia-600/15 blur-[130px] animate-aurora-3" />
      <div className="absolute inset-0 grid-backdrop" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-ink-950/40 to-ink-950" />
      <div className="absolute inset-0 noise" />
    </div>
  )
}
