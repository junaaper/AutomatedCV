# AutomatedCV: Agentic Job-Application Copilot

Paste a job posting. A LangGraph agent extracts the requirements, matches them against your CV with pgvector RAG, scores your fit, drafts a tailored cover letter, and **pauses for your approval** before saving the application to your tracker.

> Status: work in progress. See [PLAN.md](PLAN.md) for the roadmap.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React + TypeScript (Vite) on Cloudflare Pages |
| Backend | FastAPI in Docker on Render |
| Database | Neon Postgres + pgvector, SQLAlchemy + Alembic |
| Agent | LangGraph with the Postgres checkpointer (human-in-the-loop interrupts) |
| LLM | Groq / Gemini / OpenRouter, switched by env var |
| Auth | Custom JWT + argon2, Cloudflare Turnstile |
| CI | GitHub Actions: pytest, Playwright, eval suite, weekly cron |
| Monitoring | Sentry, LangSmith |
