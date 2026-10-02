import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def normalize_email(value: str) -> str:
    return value.strip().lower()


class _EmailModel(BaseModel):
    email: EmailStr
    turnstile_token: str = Field(min_length=1, max_length=2048)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_email(v) if isinstance(v, str) else v


class SignupRequest(_EmailModel):
    # Upper bound stops someone making argon2 hash megabytes of input.
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(_EmailModel):
    password: str = Field(min_length=1, max_length=128)


class DemoRequest(BaseModel):
    turnstile_token: str = Field(min_length=1, max_length=2048)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_demo: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
