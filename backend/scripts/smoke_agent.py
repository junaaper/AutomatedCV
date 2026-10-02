"""Run the agent once against the configured (real) providers and print the result.

    uv run python scripts/smoke_agent.py [posting.txt]

Uses the dev database and a dedicated smoke-test user. Ends by rejecting the draft, so
nothing is written to the tracker.
"""

import asyncio
import json
import selectors
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.types import Command  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.agent.runtime import close_graph, get_graph  # noqa: E402
from app.agent.state import AgentContext  # noqa: E402
from app.applications.models import AgentRun  # noqa: E402
from app.auth.models import User  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.cv.service import ingest_cv  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.providers.embeddings import get_embedder  # noqa: E402
from app.providers.llm import get_llm  # noqa: E402

SMOKE_EMAIL = "smoke-test@automatedcv.local"
SAMPLES = Path(__file__).resolve().parents[1] / "tests"


async def main(posting: str, cv: str) -> None:
    s = get_settings()
    print(f"LLM: {s.llm_provider}/{s.llm_model}   embeddings: {s.embed_provider}/{s.embed_model}")
    ctx = AgentContext(llm=get_llm(), embedder=get_embedder(), session_factory=SessionLocal)

    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == SMOKE_EMAIL))
        if user is None:
            user = User(email=SMOKE_EMAIL, password_hash="!disabled")
            session.add(user)
            await session.flush()
        run = AgentRun(user_id=user.id)
        session.add(run)
        await session.commit()
        t = time.perf_counter()
        _, n = await ingest_cv(session, user.id, cv, None, ctx.embedder)
        print(f"CV embedded into {n} chunks in {time.perf_counter() - t:.1f}s")

    graph = await get_graph()
    config = {"configurable": {"thread_id": str(run.id)}}
    inp = {"user_id": str(user.id), "run_id": str(run.id), "posting": posting, "revisions": 0}
    t = time.perf_counter()
    async for chunk in graph.astream(inp, config, context=ctx, stream_mode="updates"):
        for node in chunk:
            print(f"  [{time.perf_counter() - t:5.1f}s] {node}")

    review = (await graph.aget_state(config)).interrupts[0].value
    job, fit = review["job"], review["fit"]
    print("\nJOB:", json.dumps({k: job[k] for k in ("title", "company", "seniority")}))
    print(f"FIT SCORE: {fit['score']}")
    for r in fit["requirements"]:
        flag = "✓" if r["evidence_verified"] else " "
        print(f"  {flag} [{r['kind']:4}] {r['verdict']:7} {r['requirement']}")
        if r["evidence"]:
            print(f"        “{r['evidence']}”")
    print("\nCOVER LETTER:\n" + review["cover_letter"])

    await graph.ainvoke(Command(resume={"action": "reject"}), config, context=ctx)
    await close_graph()
    await engine.dispose()


if __name__ == "__main__":
    sys.path.insert(0, str(SAMPLES.parent))
    from tests.samples import CV_TEXT, POSTING

    posting = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else POSTING
    loop_factory = None
    if sys.platform == "win32":
        loop_factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())  # noqa: E731
    asyncio.run(main(posting, CV_TEXT), loop_factory=loop_factory)
