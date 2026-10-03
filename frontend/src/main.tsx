import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'sonner'
import { App } from './App'
import { Background } from './components/Background'
import { WakeGate } from './components/WakeGate'
import { ApiError } from './lib/api'
import { AuthProvider } from './lib/auth'
import './index.css'

// Error monitoring is opt-in: the SDK is only downloaded when a DSN is configured.
const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  import('@sentry/react').then((Sentry) =>
    Sentry.init({ dsn: sentryDsn, environment: import.meta.env.MODE, tracesSampleRate: 0.1 }),
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Background />
    <WakeGate>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </WakeGate>
    <Toaster
      theme="dark"
      position="top-right"
      toastOptions={{
        className: '!bg-ink-850/95 !border-white/10 !text-white !backdrop-blur-xl !rounded-xl',
      }}
    />
  </StrictMode>,
)
