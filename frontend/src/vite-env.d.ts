/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API base URL: http://localhost:8000 locally, "/api" behind the Pages proxy. */
  readonly VITE_API_URL?: string
  readonly VITE_TURNSTILE_SITE_KEY?: string
  readonly VITE_SENTRY_DSN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
