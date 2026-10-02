import pytest

from app.cv.extract import CvExtractionError, clean_text, extract_pdf_text
from app.cv.service import chunk_text
from app.main import app
from app.providers.embeddings import get_embedder
from tests.conftest import signup_headers
from tests.pdf import make_pdf

# Each section is long enough (>400 chars) that the splitter can't merge two into one chunk.
BACKEND = (
    "Backend Engineer at Acme (2022-2024). Built REST APIs in Python with FastAPI and "
    "SQLAlchemy, serving two million requests per day. Designed PostgreSQL schemas, wrote "
    "Alembic migrations, and tuned slow queries with indexes. Added pytest suites with "
    "ninety percent coverage and ran them in GitHub Actions. Introduced async background "
    "workers for invoice generation and cut p95 latency of the billing API by forty percent."
)
FRONTEND = (
    "Frontend Developer at Globex (2020-2022). Shipped React and TypeScript dashboards for "
    "logistics customers. Built a component library with Storybook, improved Lighthouse "
    "accessibility scores to ninety eight, and migrated state management from Redux to "
    "TanStack Query. Worked closely with designers in Figma and ran weekly usability "
    "sessions with dispatch teams to prioritise the roadmap and reduce support tickets."
)
EDUCATION = (
    "Education: BSc Computer Science, University of Leeds (2016-2020), first class honours. "
    "Dissertation on graph neural networks for traffic forecasting. Teaching assistant for "
    "the algorithms and data structures module for two years, running weekly lab sessions "
    "for sixty students. Captain of the university chess club and organiser of the annual "
    "student hackathon with three hundred participants and twelve sponsoring companies."
)
CV_TEXT = "\n\n".join(["Ada Lovelace", BACKEND, FRONTEND, EDUCATION])


async def upload_text(client, headers, text=CV_TEXT):
    return await client.post("/cv", data={"text": text}, headers=headers)


# --- pure functions ---


def test_clean_text_normalises_whitespace():
    assert clean_text("a  \t b\r\n\n\n\nc \x00") == "a b\n\nc"


def test_chunking_keeps_sections_apart():
    chunks = chunk_text(CV_TEXT)
    assert len(chunks) >= 3
    assert any("FastAPI" in c and "React" not in c for c in chunks)


def test_extract_pdf_text():
    text = extract_pdf_text(make_pdf(["Ada Lovelace", BACKEND[:90], BACKEND[90:180]]))
    assert "Ada Lovelace" in text and "FastAPI" in text


def test_extract_rejects_empty_pdf():
    with pytest.raises(CvExtractionError, match="scanned"):
        extract_pdf_text(make_pdf([""]))


def test_extract_rejects_garbage():
    with pytest.raises(CvExtractionError):
        extract_pdf_text(b"%PDF-1.4 this is not really a pdf")


# --- endpoints ---


async def test_cv_endpoints_require_auth(client, db):
    assert (await client.get("/cv")).status_code == 401
    assert (await client.post("/cv", data={"text": CV_TEXT})).status_code == 401


async def test_upload_text_then_get(client, auth_headers):
    resp = await upload_text(client, auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["chunk_count"] >= 3
    got = await client.get("/cv", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["content"].startswith("Ada Lovelace")
    assert got.json()["filename"] is None


async def test_upload_pdf(client, auth_headers):
    pdf = make_pdf(["Ada Lovelace", BACKEND[:90], BACKEND[90:180]])
    resp = await client.post(
        "/cv", files={"file": ("cv.pdf", pdf, "application/pdf")}, headers=auth_headers
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["filename"] == "cv.pdf"
    assert "FastAPI" in resp.json()["content"]


async def test_upload_rejects_non_pdf_and_both_or_neither(client, auth_headers):
    not_pdf = await client.post(
        "/cv",
        files={"file": ("cv.docx", b"PK\x03\x04...", "application/zip")},
        headers=auth_headers,
    )
    assert not_pdf.status_code == 422
    assert (await client.post("/cv", headers=auth_headers)).status_code == 422
    both = await client.post(
        "/cv",
        data={"text": CV_TEXT},
        files={"file": ("cv.pdf", make_pdf(["x"]), "application/pdf")},
        headers=auth_headers,
    )
    assert both.status_code == 422


async def test_upload_rejects_too_short_text(client, auth_headers):
    resp = await upload_text(client, auth_headers, text="just a line")
    assert resp.status_code == 422


async def test_reupload_replaces_previous_cv(client, auth_headers):
    await upload_text(client, auth_headers)
    await upload_text(client, auth_headers, text="Grace Hopper\n\n" + FRONTEND)
    got = (await client.get("/cv", headers=auth_headers)).json()
    assert got["content"].startswith("Grace Hopper")
    hits = (await client.post("/cv/search", json={"query": "FastAPI"}, headers=auth_headers)).json()
    assert all("FastAPI" not in h["content"] for h in hits)


async def test_search_finds_the_relevant_section(client, auth_headers):
    await upload_text(client, auth_headers)
    resp = await client.post(
        "/cv/search", json={"query": "React TypeScript dashboards", "k": 1}, headers=auth_headers
    )
    assert resp.status_code == 200
    [top] = resp.json()
    assert "React" in top["content"]
    assert 0 < top["similarity"] <= 1


async def test_search_never_returns_another_users_cv(client, auth_headers):
    await upload_text(client, auth_headers)
    other = await signup_headers(client, "other@example.com")
    resp = await client.post("/cv/search", json={"query": "FastAPI"}, headers=other)
    assert resp.json() == []


async def test_delete_cv(client, auth_headers):
    await upload_text(client, auth_headers)
    assert (await client.delete("/cv", headers=auth_headers)).status_code == 204
    assert (await client.get("/cv", headers=auth_headers)).status_code == 404


async def test_embedding_outage_returns_503_and_keeps_old_cv(client, auth_headers):
    await upload_text(client, auth_headers)

    class Broken:
        async def embed_documents(self, texts):
            raise RuntimeError("quota exceeded")

        embed_queries = embed_documents

    app.dependency_overrides[get_embedder] = lambda: Broken()
    try:
        resp = await upload_text(client, auth_headers, text="Grace Hopper\n\n" + FRONTEND)
    finally:
        app.dependency_overrides.pop(get_embedder)
    assert resp.status_code == 503
    got = (await client.get("/cv", headers=auth_headers)).json()
    assert got["content"].startswith("Ada Lovelace")
