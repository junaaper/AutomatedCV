#!/bin/sh
# Container entrypoint. Render's free plan has no pre-deploy hook, so migrations run here,
# before the server starts accepting traffic.
set -e

alembic upgrade head

# --proxy-headers: trust X-Forwarded-For from Render's proxy so rate limits see real IPs.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips='*'
