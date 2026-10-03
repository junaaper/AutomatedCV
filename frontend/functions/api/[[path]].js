// Cloudflare Pages Function: proxies /api/* to the FastAPI backend on Render.
//
// Serving the API from the same origin as the app means the refresh-token cookie is
// first-party (browsers increasingly block third-party cookies, which would log users out
// on every reload) and no CORS preflights are needed. Responses are streamed, so the
// agent's Server-Sent Events pass straight through.
//
// Set API_ORIGIN (e.g. https://automatedcv-api.onrender.com) in the Pages project settings.

const HOP_BY_HOP = ['connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'host']

export async function onRequest({ request, env }) {
  if (!env.API_ORIGIN) {
    return new Response(JSON.stringify({ detail: 'API_ORIGIN is not configured' }), {
      status: 500,
      headers: { 'content-type': 'application/json' },
    })
  }
  const url = new URL(request.url)
  const target = new URL(url.pathname.replace(/^\/api/, '') + url.search, env.API_ORIGIN)

  const headers = new Headers(request.headers)
  for (const h of HOP_BY_HOP) headers.delete(h)
  // The backend rate-limits per client IP; pass the real one through.
  const clientIp = request.headers.get('CF-Connecting-IP')
  if (clientIp) headers.set('X-Forwarded-For', clientIp)
  headers.set('X-Forwarded-Proto', 'https')

  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
    redirect: 'manual',
  })
  return new Response(upstream.body, upstream)
}
