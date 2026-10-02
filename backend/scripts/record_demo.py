"""Record real LLM responses for the demo's sample postings.

    uv run python scripts/record_demo.py

Runs the real agent graph for each sample posting against the configured LLM, using the
offline embedder (exactly what demo users get), and records every model response plus
one revision per suggestion chip. Output: app/demo/fixtures/<id>.json. Re-run after
changing prompts, the demo CV or the sample postings.
"""

import asyncio
import json
import selectors
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.types import Command  # noqa: E402

from app.agent.runtime import close_graph, get_graph  # noqa: E402
from app.agent.state import AgentContext  # noqa: E402
from app.applications.models import AgentRun  # noqa: E402
from app.auth.models import User  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.cv.service import ingest_cv  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.demo.content import DEMO_CV, REVISION_SUGGESTIONS, SAMPLE_POSTINGS  # noqa: E402
from app.demo.replay import RecordingChatModel  # noqa: E402
from app.demo.service import FIXTURE_DIR, demo_embedder  # noqa: E402
from app.providers.llm import get_llm  # noqa: E402


async def record(sample, user_id: uuid.UUID) -> dict:
    settings = get_settings()
    recorder = RecordingChatModel(inner=get_llm())
    ctx = AgentContext(llm=recorder, embedder=demo_embedder(), session_factory=SessionLocal)
    async with SessionLocal() as session:
        run = AgentRun(user_id=user_id)
        session.add(run)
        await session.commit()
    config = {"configurable": {"thread_id": str(run.id)}}
    graph = await get_graph()

    inp = {
        "user_id": str(user_id),
        "run_id": str(run.id),
        "posting": sample.posting,
        "revisions": 0,
    }
    await graph.ainvoke(inp, config, context=ctx)
    review = (await graph.aget_state(config)).interrupts[0].value
    snapshot = {k: review[k] for k in ("job", "fit", "evidence", "cover_letter")}
    job = review["job"]
    print(f"  score {review['fit']['score']}  ·  {job['title']} @ {job['company']}")

    for feedback in REVISION_SUGGESTIONS:
        await graph.ainvoke(
            Command(resume={"action": "revise", "feedback": feedback}), config, context=ctx
        )
        print(f"  revision recorded: {feedback}")
    await graph.ainvoke(Command(resume={"action": "reject"}), config, context=ctx)

    return {
        "id": sample.id,
        "model": f"{settings.llm_provider}/{settings.llm_model}",
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "responses": recorder.recorded,
        "snapshot": snapshot,
    }


async def main() -> None:
    if get_settings().llm_provider == "fake":
        sys.exit("Set LLM_PROVIDER to a real provider before recording.")
    FIXTURE_DIR.mkdir(exist_ok=True)
    async with SessionLocal() as session:
        user = User(email=f"recorder-{uuid.uuid4().hex[:8]}@demo.local", password_hash="!")
        session.add(user)
        await session.flush()
        await ingest_cv(session, user.id, DEMO_CV, None, demo_embedder())
        user_id = user.id

    try:
        for sample in SAMPLE_POSTINGS:
            print(f"Recording {sample.id}…")
            fixture = await record(sample, user_id)
            path = FIXTURE_DIR / f"{sample.id}.json"
            path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", "utf-8")
            print(
                f"  -> {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}"
            )
    finally:
        async with SessionLocal() as session:
            await session.delete(await session.get(User, user_id))
            await session.commit()
        await close_graph()
        await engine.dispose()


if __name__ == "__main__":
    factory = None
    if sys.platform == "win32":
        factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())  # noqa: E731
    asyncio.run(main(), loop_factory=factory)
