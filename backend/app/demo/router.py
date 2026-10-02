from fastapi import APIRouter
from pydantic import BaseModel

from app.demo.content import SAMPLE_POSTINGS

router = APIRouter(prefix="/demo", tags=["demo"])


class SamplePostingOut(BaseModel):
    id: str
    title: str
    company: str
    blurb: str
    posting: str


@router.get("/postings")
async def sample_postings() -> list[SamplePostingOut]:
    """Sample postings with recorded agent runs (instant and API-free in demo mode)."""
    return [SamplePostingOut(**vars(s)) for s in SAMPLE_POSTINGS]
