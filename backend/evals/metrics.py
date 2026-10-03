"""Scoring for the agent eval suite. Pure functions so they're unit-testable."""

import re
from dataclasses import dataclass, field

# A sentence naming a skill the candidate lacks is fine if it's framed as a gap, as
# willingness to learn, or as describing the employer's work ("help build your Kubernetes
# platform"); otherwise it's an unsupported claim.
_HEDGE = re.compile(
    r"\b(not|no|never|yet|eager|keen|learn\w*|limited|new to|grow\w*|develop\w*|excited to|"
    r"look(ing)? forward|gap|lack\w*|aim|plan\w*|hope|willing|would|could|ready to|quickly|"
    r"opportunit\w*|your|join\w*|help build|contribute to)\b"
    r"|n't",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")

THRESHOLDS = {
    "recall": 0.80,  # mean share of expected must-haves extracted
    "company": 0.90,  # share of cases with the right company
    "in_band": 0.80,  # share of cases whose fit score lands in the expected band
    "grounded": 0.95,  # share of match/partial verdicts backed by a verified CV quote
    "letter_ok": 0.90,  # share of letters within the length bounds
    "unsupported": 0,  # total letter sentences claiming skills the CV lacks
}
# Lower bound is deliberately low: for a poor fit the prompt asks for a shorter letter
# rather than padding, so ~70 words is correct behaviour there.
LETTER_WORDS = (60, 360)


def contains_term(text: str, term: str) -> bool:
    """Whole-term match. Short terms (Go, C#, dbt) are case-sensitive to avoid "go to"."""
    flags = 0 if len(term) <= 3 else re.IGNORECASE
    return re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", text, flags) is not None


def requirement_recall(expected: list[list[str]], extracted: list[str]) -> float:
    if not expected:
        return 1.0
    haystack = [r.lower() for r in extracted]
    hits = sum(any(alt.lower() in r for alt in group for r in haystack) for group in expected)
    return hits / len(expected)


def unsupported_claims(letter: str, absent: list[str]) -> list[str]:
    flagged = []
    for sentence in _SENTENCE.split(letter):
        for term in absent:
            if contains_term(sentence, term) and not _HEDGE.search(sentence):
                flagged.append(f"{term}: {sentence.strip()[:140]}")
    return flagged


def grounding(fit: dict) -> tuple[int, int]:
    """(verdicts backed by a verified quote, match/partial verdicts)."""
    claimed = [r for r in fit["requirements"] if r["verdict"] != "missing"]
    return sum(bool(r["evidence_verified"]) for r in claimed), len(claimed)


@dataclass
class CaseResult:
    id: str
    error: str | None = None
    recall: float = 0.0
    company_ok: bool = False
    title_ok: bool = False
    score: int | None = None
    band: tuple[int, int] = (0, 100)
    grounded: int = 0
    claimed: int = 0
    unsupported: list[str] = field(default_factory=list)
    words: int = 0

    @property
    def in_band(self) -> bool:
        return self.score is not None and self.band[0] <= self.score <= self.band[1]

    @property
    def letter_ok(self) -> bool:
        return LETTER_WORDS[0] <= self.words <= LETTER_WORDS[1]


def evaluate_case(case: dict, review: dict) -> CaseResult:
    exp, job, fit = case["expect"], review["job"], review["fit"]
    letter = review["cover_letter"]
    grounded, claimed = grounding(fit)
    return CaseResult(
        id=case["id"],
        recall=requirement_recall(exp["must_have"], job["must_have"] + job["nice_to_have"]),
        company_ok=exp["company"].lower() in job["company"].lower(),
        title_ok=exp["title"].lower() in job["title"].lower(),
        score=fit["score"],
        band=tuple(exp["score"]),
        grounded=grounded,
        claimed=claimed,
        unsupported=unsupported_claims(letter, exp.get("absent", [])),
        words=len(letter.split()),
    )


def summarize(results: list[CaseResult]) -> dict:
    ok = [r for r in results if r.error is None]
    n = len(ok) or 1
    claimed = sum(r.claimed for r in ok)
    return {
        "cases": len(results),
        "errors": len(results) - len(ok),
        "recall": sum(r.recall for r in ok) / n,
        "company": sum(r.company_ok for r in ok) / n,
        "title": sum(r.title_ok for r in ok) / n,
        "in_band": sum(r.in_band for r in ok) / n,
        "grounded": (sum(r.grounded for r in ok) / claimed) if claimed else 1.0,
        "letter_ok": sum(r.letter_ok for r in ok) / n,
        "unsupported": sum(len(r.unsupported) for r in ok),
    }


def failures(summary: dict) -> list[str]:
    out = [f"{summary['errors']} case(s) errored"] if summary["errors"] else []
    for key, threshold in THRESHOLDS.items():
        value = summary[key]
        bad = value > threshold if key == "unsupported" else value < threshold
        if bad:
            out.append(f"{key} = {value:.2f} (threshold {threshold})")
    return out


def markdown_report(results: list[CaseResult], summary: dict, meta: dict) -> str:
    fails = failures(summary)
    lines = [
        "# Agent eval report",
        "",
        f"Mode: **{meta['mode']}** · model: `{meta['model']}` · embeddings: `{meta['embedder']}` · "
        f"{meta['when']}",
        "",
        f"**{'PASS' if not fails else 'FAIL'}**" + (f": {'; '.join(fails)}" if fails else ""),
        "",
        "| Metric | Value | Threshold |",
        "| --- | --- | --- |",
    ]
    for key, threshold in THRESHOLDS.items():
        value = summary[key]
        shown = f"{value}" if key == "unsupported" else f"{value:.0%}"
        limit = f"≤ {threshold}" if key == "unsupported" else f"≥ {threshold:.0%}"
        lines.append(f"| {key} | {shown} | {limit} |")
    lines += [
        "",
        "| Case | Recall | Company | Score (band) | Grounded | Letter words | Unsupported claims |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        if r.error:
            lines.append(f"| {r.id} | error: {r.error[:80]} | | | | | |")
            continue
        lines.append(
            f"| {r.id} | {r.recall:.0%} | {'✓' if r.company_ok else '✗'} | "
            f"{r.score} ({r.band[0]}–{r.band[1]}) {'✓' if r.in_band else '✗'} | "
            f"{r.grounded}/{r.claimed} | {r.words}{'' if r.letter_ok else ' ✗'} | "
            f"{'; '.join(r.unsupported) or '–'} |"
        )
    return "\n".join(lines) + "\n"
