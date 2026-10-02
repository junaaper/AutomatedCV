"""Import every ORM model here so Alembic autogenerate and tests see the full metadata."""

from app.applications.models import AgentRun, Application
from app.auth.models import RefreshToken, User
from app.cv.models import CvChunk, CvDocument

__all__ = ["AgentRun", "Application", "CvChunk", "CvDocument", "RefreshToken", "User"]
