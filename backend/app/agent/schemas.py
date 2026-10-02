"""Structured outputs the agent asks the LLM for, plus the deterministic fit score."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _clean_list(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        item = " ".join(item.split())
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out


class JobRequirements(BaseModel):
    title: str = Field(description="Job title")
    company: str = Field(description="Hiring company, or 'Unknown' if not stated")
    location: str | None = Field(default=None, description="Location / remote policy")
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "unknown"] = "unknown"
    must_have: list[str] = Field(description="Required skills/experience, short phrases")
    nice_to_have: list[str] = Field(default_factory=list, description="Preferred extras")
    summary: str = Field(description="One-sentence summary of the role")

    @field_validator("must_have", "nice_to_have")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        # Caps keep scoring prompts (and free-tier token use) bounded.
        return _clean_list(v)[:12]

    def all_requirements(self) -> list[tuple[str, Literal["must", "nice"]]]:
        return [(r, "must") for r in self.must_have] + [(r, "nice") for r in self.nice_to_have]


Verdict = Literal["match", "partial", "missing"]


class RequirementAssessment(BaseModel):
    requirement: str
    verdict: Verdict
    evidence: str | None = Field(
        default=None, description="Exact quote from the CV excerpts supporting the verdict"
    )
    reasoning: str = Field(description="One short sentence")


class FitAssessmentLLM(BaseModel):
    """What the model returns; we then verify quotes and compute the score ourselves."""

    assessments: list[RequirementAssessment]
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class AssessedRequirement(RequirementAssessment):
    kind: Literal["must", "nice"]
    evidence_verified: bool = False


class FitResult(BaseModel):
    score: int = Field(ge=0, le=100)
    requirements: list[AssessedRequirement]
    strengths: list[str]
    gaps: list[str]


_KIND_WEIGHT = {"must": 2.0, "nice": 1.0}
_VERDICT_CREDIT = {"match": 1.0, "partial": 0.5, "missing": 0.0}


def fit_score(requirements: list[AssessedRequirement]) -> int:
    """Weighted share of requirements met: must-haves count double, partial = half."""
    total = sum(_KIND_WEIGHT[r.kind] for r in requirements)
    if total == 0:
        return 0
    earned = sum(_KIND_WEIGHT[r.kind] * _VERDICT_CREDIT[r.verdict] for r in requirements)
    return round(100 * earned / total)
