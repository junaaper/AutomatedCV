"""Import every ORM model here so Alembic autogenerate and tests see the full metadata."""

from app.auth.models import RefreshToken, User
from app.cv.models import CvChunk, CvDocument

__all__ = ["CvChunk", "CvDocument", "RefreshToken", "User"]
