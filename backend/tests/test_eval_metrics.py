from evals.metrics import (
    CaseResult,
    contains_term,
    failures,
    grounding,
    requirement_recall,
    summarize,
    unsupported_claims,
)


def test_contains_term_handles_short_and_symbol_terms():
    assert contains_term("I write Go daily", "Go")
    assert not contains_term("happy to go the extra mile", "Go")
    assert contains_term("Built services in C# and .NET", "C#")
    assert contains_term("modern C++ codebases", "C++")
    assert contains_term("ran KUBERNETES clusters", "Kubernetes")
    assert not contains_term("Rustic charm", "Rust")


def test_requirement_recall_matches_any_alternative():
    expected = [["python", "fastapi"], ["postgres"], ["kafka", "event"]]
    extracted = ["Strong FastAPI skills", "PostgreSQL tuning", "Docker"]
    assert requirement_recall(expected, extracted) == 2 / 3
    assert requirement_recall([], extracted) == 1.0


def test_unsupported_claims_allow_honest_gaps():
    letter = (
        "I have run Kubernetes clusters in production for years. "
        "I haven't used Kafka yet, but I'm eager to learn it. "
        "My PostgreSQL work cut latency by 80%."
    )
    flagged = unsupported_claims(letter, ["Kubernetes", "Kafka"])
    assert len(flagged) == 1 and flagged[0].startswith("Kubernetes")


def test_describing_the_employers_stack_is_not_a_claim():
    letter = "I'm excited by the opportunity to help build a multi-tenant Kubernetes platform."
    assert unsupported_claims(letter, ["Kubernetes"]) == []
    assert unsupported_claims("I am a Kubernetes expert.", ["Kubernetes"]) != []


def test_grounding_counts_only_claimed_verdicts():
    fit = {
        "requirements": [
            {"verdict": "match", "evidence_verified": True},
            {"verdict": "partial", "evidence_verified": False},
            {"verdict": "missing", "evidence_verified": False},
        ]
    }
    assert grounding(fit) == (1, 2)


def test_summary_and_thresholds():
    good = CaseResult(
        id="a",
        recall=1.0,
        company_ok=True,
        title_ok=True,
        score=80,
        band=(70, 100),
        grounded=3,
        claimed=3,
        words=200,
    )
    bad = CaseResult(
        id="b",
        recall=0.5,
        company_ok=False,
        title_ok=True,
        score=90,
        band=(0, 20),
        grounded=1,
        claimed=2,
        words=40,
        unsupported=["Rust: I am a Rust expert"],
    )
    assert failures(summarize([good])) == []
    fails = " ".join(failures(summarize([good, bad])))
    for metric in ("recall", "company", "in_band", "grounded", "letter_ok", "unsupported"):
        assert metric in fails
    assert failures(summarize([CaseResult(id="c", error="boom")]))[0] == "1 case(s) errored"
