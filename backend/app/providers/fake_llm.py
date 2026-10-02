"""A deterministic, offline stand-in for the LLM (LLM_PROVIDER=fake).

It reads the `TASK:` tag from the system prompt and the JSON inside <input>, then answers
with simple heuristics. Output is plausible rather than smart: it exists so local dev,
the Playwright e2e suite and CI can run the whole agent with no API key or network.
"""

import json
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_INPUT = re.compile(r"<input>\s*(.*?)\s*</input>", re.DOTALL)
_BULLET = re.compile(r"^\s*(?:[-*•▪◦]|\d+[.)])\s+(.*\S)")
_NICE_HEADING = re.compile(r"nice|prefer|bonus|plus|desirable", re.I)
_REQ_HEADING = re.compile(r"require|must|qualif|you have|looking for|skills|experience", re.I)
_COMPANY = re.compile(r"(?i:company|employer)\s*:\s*(.+)|\bat\s+([A-Z][\w&.\- ]{1,40})")
_WORD = re.compile(r"[a-z0-9+#]+")
_STOP = set(
    "and or the a an of in on for with to as at by from is are be our you your we will "
    "years year experience strong good knowledge working skills ability using plus".split()
)


def _keywords(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 1 and w not in _STOP}


def _extract(payload: dict) -> dict:
    lines = [line.rstrip() for line in payload["posting"].splitlines()]
    non_empty = [line.strip() for line in lines if line.strip()]
    title = non_empty[0][:80] if non_empty else "Unknown role"
    company = "Unknown"
    for line in non_empty[:15]:
        if m := _COMPANY.search(line):
            company = (m.group(1) or m.group(2)).strip().rstrip(".")
            break

    must, nice, section = [], [], "must"
    for line in lines:
        if m := _BULLET.match(line):
            (nice if section == "nice" else must).append(m.group(1).rstrip(".;"))
        elif line.strip():
            if _NICE_HEADING.search(line):
                section = "nice"
            elif _REQ_HEADING.search(line):
                section = "must"
    if not must:  # no bullets: fall back to sentences that sound like requirements
        sentences = re.split(r"(?<=[.!?])\s+", payload["posting"])
        must = [s.strip() for s in sentences if _REQ_HEADING.search(s)][:6]
    return {
        "title": title,
        "company": company,
        "location": None,
        "seniority": "unknown",
        "must_have": [m[:80] for m in must[:8]],
        "nice_to_have": [n[:80] for n in nice[:5]],
        "summary": f"{title} at {company}.",
    }


def _best_quote(requirement: str, excerpts: list[str]) -> tuple[float, str | None]:
    wanted = _keywords(requirement)
    best: tuple[float, str | None] = (0.0, None)
    for excerpt in excerpts:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", excerpt):
            words = sentence.split()
            if not words or not wanted:
                continue
            overlap = len(wanted & _keywords(sentence)) / len(wanted)
            if overlap > best[0]:
                best = (overlap, " ".join(words[:25]))
    return best


def _score(payload: dict) -> dict:
    assessments, strengths, gaps = [], [], []
    for item in payload["requirements"]:
        overlap, quote = _best_quote(item["requirement"], item.get("excerpts", []))
        verdict = "match" if overlap >= 0.5 else "partial" if overlap > 0 else "missing"
        assessments.append(
            {
                "requirement": item["requirement"],
                "verdict": verdict,
                "evidence": quote if verdict != "missing" else None,
                "reasoning": f"Keyword overlap {overlap:.0%} with the CV.",
            }
        )
        (strengths if verdict == "match" else gaps if verdict == "missing" else []).append(
            item["requirement"]
        )
    return {"assessments": assessments, "strengths": strengths[:4], "gaps": gaps[:4]}


def _letter(payload: dict) -> str:
    job = payload["job"]
    reqs = payload["fit"]["requirements"]
    matches = [r for r in reqs if r["verdict"] == "match" and r["evidence"]][:3]
    points = " ".join(f'For {r["requirement"]}, my CV shows: "{r["evidence"]}".' for r in matches)
    letter = (
        f"Dear {job['company']} hiring team,\n\n"
        f"I'd like to be considered for the {job['title']} role. {job['summary']}\n\n"
        f"{points or 'My background lines up with several of your core requirements.'}\n\n"
        "I'd welcome the chance to talk about how I could contribute.\n\nKind regards"
    )
    if payload.get("feedback"):
        letter += f"\n\n(Revised per feedback: {payload['feedback']})"
    return letter


class OfflineChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "offline-fake"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kw: Any):
        task = str(messages[0].content).split("\n", 1)[0].removeprefix("TASK:").strip()
        raw = next((m for m in (_INPUT.search(str(msg.content)) for msg in messages) if m), None)
        payload = json.loads(raw.group(1)) if raw else {}
        if task == "extract_requirements":
            text = json.dumps(_extract(payload))
        elif task == "score_fit":
            text = json.dumps(_score(payload))
        elif task == "draft_cover_letter":
            text = _letter(payload)
        else:
            text = "{}"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(text))])
