import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:p@host/db?sslmode=require",
        "postgresql://u:p@host/db?sslmode=require",
        "postgresql+psycopg://u:p@host/db?sslmode=require",
    ],
)
def test_database_url_is_normalised_to_psycopg(url):
    s = Settings(database_url=url, _env_file=None)
    assert s.database_url == "postgresql+psycopg://u:p@host/db?sslmode=require"


def test_prod_refuses_weak_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(environment="prod", jwt_secret="short", _env_file=None)


def test_cookie_and_cors_settings():
    s = Settings(
        frontend_origin="https://a.pages.dev, https://b.example.com",
        cookie_samesite="none",
        _env_file=None,
    )
    assert s.cors_origins == ["https://a.pages.dev", "https://b.example.com"]
    assert s.cookie_secure  # SameSite=None requires Secure
