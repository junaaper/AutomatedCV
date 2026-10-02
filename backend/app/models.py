"""Import every ORM model here so Alembic autogenerate and tests see the full metadata."""

from app.auth.models import RefreshToken, User

__all__ = ["RefreshToken", "User"]
