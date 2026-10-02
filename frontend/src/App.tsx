import { LoaderCircle } from 'lucide-react'
import { Suspense, lazy } from 'react'
import type { ReactNode } from 'react'
import { Navigate, Outlet, RouterProvider, createBrowserRouter } from 'react-router'
import { AppShell } from './components/AppShell'
import { useAuth } from './lib/auth'
import { AuthPage } from './pages/AuthPage'

// Pages load on demand, which keeps the first paint (and the cold-start screen) light.
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const AnalyzePage = lazy(() => import('./pages/AnalyzePage').then((m) => ({ default: m.AnalyzePage })))
const TrackerPage = lazy(() => import('./pages/TrackerPage').then((m) => ({ default: m.TrackerPage })))
const CvPage = lazy(() => import('./pages/CvPage').then((m) => ({ default: m.CvPage })))

function Splash() {
  return (
    <div className="grid min-h-[50dvh] place-items-center">
      <LoaderCircle className="size-6 animate-spin text-violet-300" />
    </div>
  )
}

const page = (el: ReactNode) => <Suspense fallback={<Splash />}>{el}</Suspense>

function RequireAuth() {
  const { user, ready } = useAuth()
  if (!ready) return <Splash />
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

function GuestOnly() {
  const { user, ready } = useAuth()
  if (!ready) return <Splash />
  return user ? <Navigate to="/" replace /> : <AuthPage />
}

const router = createBrowserRouter([
  { path: '/login', element: <GuestOnly /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: page(<DashboardPage />) },
          // One route for new and existing runs, so navigating to a run's URL
          // mid-stream doesn't remount the page.
          { path: 'analyze/:runId?', element: page(<AnalyzePage />) },
          { path: 'tracker', element: page(<TrackerPage />) },
          { path: 'cv', element: page(<CvPage />) },
          { path: '*', element: <Navigate to="/" replace /> },
        ],
      },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
