import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.agent.llm_json import LLMOutputError, invoke_json, parse_json_object
from app.agent.nodes import quote_is_grounded
from app.agent.schemas import AssessedRequirement, JobRequirements, fit_score


def req(kind, verdict):
    return AssessedRequirement(requirement="x", kind=kind, verdict=verdict, reasoning="")


def test_fit_score_weights_must_haves_double():
    assert fit_score([req("must", "match"), req("nice", "missing")]) == 67
    assert fit_score([req("must", "partial"), req("must", "match")]) == 75
    assert fit_score([req("must", "missing")]) == 0
    assert fit_score([]) == 0


def test_requirements_are_deduped_and_capped():
    job = JobRequirements(
        title="t",
        company="c",
        summary="s",
        must_have=["Python", " python ", "SQL"] + [f"skill {i}" for i in range(20)],
    )
    assert job.must_have[:2] == ["Python", "SQL"]
    assert len(job.must_have) == 12


def test_quote_grounding_tolerates_spacing_but_not_invention():
    excerpts = ["Built REST APIs in Python with FastAPI and SQLAlchemy."]
    assert quote_is_grounded("REST APIs in  Python with FastAPI", excerpts)
    assert quote_is_grounded("rest apis in python with fastapi.", excerpts)
    assert not quote_is_grounded("Built REST APIs in Go", excerpts)
    assert quote_is_grounded("Node.js services", ["Wrote Node.js services daily"])
    assert not quote_is_grounded("Nodejs services", ["Wrote Node.js services daily"])
    assert not quote_is_grounded("", excerpts)


def test_parse_json_object_strips_fences_and_prose():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! Here it is: {"a": {"b": 2}} Hope that helps') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        parse_json_object("no json here")


SCHEMA_OK = '{"title": "Dev", "company": "Acme", "must_have": ["Python"], "summary": "A dev role."}'


async def test_invoke_json_retries_once_after_bad_output():
    llm = FakeListChatModel(responses=["not json at all", SCHEMA_OK])
    job = await invoke_json(llm, "sys", "user", JobRequirements)
    assert job.company == "Acme"


async def test_invoke_json_gives_up_after_retries():
    llm = FakeListChatModel(responses=['{"title": "missing fields"}'] * 2)
    with pytest.raises(LLMOutputError):
        await invoke_json(llm, "sys", "user", JobRequirements)
