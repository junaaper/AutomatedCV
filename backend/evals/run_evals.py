"""Run the agent eval suite.

    uv run python evals/run_evals.py                  # replay recorded responses (CI, offline)
    uv run python evals/run_evals.py --mode live      # real LLM + real embeddings (weekly)
    uv run python evals/run_evals.py --mode record    # real LLM, save cassettes for replay

Replay and record use the offline embedder so recorded responses stay valid on replay
(retrieved CV passages must match for the quote-grounding check). Live mode measures
the full real stack. Exits non-zero if any threshold in evals/metrics.py fails.
"""

import argparse
import asyncio
import json
import selectors
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from app.agent.runtime import close_graph, get_graph  # noqa: E402
from app.agent.state import AgentContext  # noqa: E402
from app.applications.models import AgentRun  # noqa: E402
from app.auth.models import User  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.cv.models import EMBED_DIM  # noqa: E402
from app.cv.service import ingest_cv  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.demo.content import DEMO_CV  # noqa: E402
from app.demo.replay import RecordingChatModel, ReplayChatModel  # noqa: E402
from app.providers.embeddings import HashingEmbedder, get_embedder  # noqa: E402
from app.providers.llm import get_llm  # noqa: E402
from evals.metrics import (  # noqa: E402
    CaseResult,
    evaluate_case,
    failures,
    markdown_report,
    summarize,
)

EVALS = Path(__file__).resolve().parent
CASSETTES = EVALS / "cassettes"


def load_cases(only: set[str] | None) -> list[dict]:
    cases = yaml.safe_load((EVALS / "cases.yaml").read_text(encoding="utf-8"))
    return [c for c in cases if not only or c["id"] in only]


async def run_case(case: dict, mode: str, user_id: uuid.UUID, embedder) -> tuple[dict, dict | None]:
    if mode == "replay":
        cassette = json.loads((CASSETTES / f"{case['id']}.json").read_text(encoding="utf-8"))
        llm = ReplayChatModel(responses=cassette["responses"])
    elif mode == "record":
        llm = RecordingChatModel(inner=get_llm())
    else:
        llm = get_llm()

    async with SessionLocal() as session:
        run = AgentRun(user_id=user_id)
        session.add(run)
        await session.commit()
    config = {"configurable": {"thread_id": str(run.id)}}
    ctx = AgentContext(llm=llm, embedder=embedder, session_factory=SessionLocal)
    graph = await get_graph()
    try:
        inp = {"user_id": str(user_id), "run_id": str(run.id), "posting": case["posting"]}
        await graph.ainvoke({**inp, "revisions": 0}, config, context=ctx)
        review = (await graph.aget_state(config)).interrupts[0].value
    finally:
        await graph.checkpointer.adelete_thread(str(run.id))
    recorded = {"id": case["id"], "responses": llm.recorded} if mode == "record" else None
    return review, recorded


async def main(args: argparse.Namespace) -> int:
    settings = get_settings()
    live = args.mode == "live"
    if args.mode in ("live", "record") and settings.llm_provider == "fake":
        sys.exit("Set LLM_PROVIDER to a real provider for live/record mode.")
    embedder = get_embedder() if live else HashingEmbedder(EMBED_DIM)
    cases = load_cases(set(args.only.split(",")) if args.only else None)
    CASSETTES.mkdir(exist_ok=True)

    async with SessionLocal() as session:
        user = User(email=f"evals-{uuid.uuid4().hex[:8]}@evals.local", password_hash="!")
        session.add(user)
        await session.flush()
        await ingest_cv(session, user.id, DEMO_CV, None, embedder)
        user_id = user.id

    results: list[CaseResult] = []
    try:
        for i, case in enumerate(cases, 1):
            started = time.perf_counter()
            try:
                review, recorded = await run_case(case, args.mode, user_id, embedder)
                result = evaluate_case(case, review)
                if recorded:
                    recorded["model"] = f"{settings.llm_provider}/{settings.llm_model}"
                    path = CASSETTES / f"{case['id']}.json"
                    path.write_text(
                        json.dumps(recorded, indent=2, ensure_ascii=False) + "\n", "utf-8"
                    )
            except Exception as exc:  # one broken case shouldn't hide the rest
                result = CaseResult(id=case["id"], error=f"{type(exc).__name__}: {exc}")
            results.append(result)
            status = result.error or (
                f"recall {result.recall:.0%}  score {result.score} {result.band}"
                f"{'' if result.in_band else ' OUT OF BAND'}  unsupported {len(result.unsupported)}"
            )
            print(
                f"[{i:2}/{len(cases)}] {case['id']:28} {time.perf_counter() - started:5.1f}s  {status}"
            )
            if args.sleep and i < len(cases):
                await asyncio.sleep(args.sleep)  # stay under free-tier tokens-per-minute
    finally:
        async with SessionLocal() as session:
            await session.delete(await session.get(User, user_id))
            await session.commit()
        await close_graph()
        await engine.dispose()

    summary = summarize(results)
    recorded_models = sorted(
        {
            json.loads(p.read_text(encoding="utf-8")).get("model", "unknown")  # noqa: ASYNC240
            for p in CASSETTES.glob("*.json")
        }
    )
    meta = {
        "mode": args.mode,
        "model": f"recorded {', '.join(recorded_models)}"
        if args.mode == "replay"
        else f"{settings.llm_provider}/{settings.llm_model}",
        "embedder": f"{settings.embed_provider}/{settings.embed_model}"
        if live
        else "offline hashing",
        "when": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    }
    report = markdown_report(results, summary, meta)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")  # noqa: ASYNC240 (CLI script)
    print("\n" + report)
    fails = failures(summary)
    print("RESULT:", "PASS" if not fails else "FAIL: " + "; ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--mode", choices=["replay", "live", "record"], default="replay")
    parser.add_argument("--only", help="comma-separated case ids")
    parser.add_argument("--report", help="write the markdown report here")
    parser.add_argument("--sleep", type=float, default=0, help="seconds between cases")
    factory = None
    if sys.platform == "win32":
        factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())  # noqa: E731
    sys.exit(asyncio.run(main(parser.parse_args()), loop_factory=factory))
