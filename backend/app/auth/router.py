import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agent.runtime import get_graph
from app.auth.deps import CurrentUser
from app.auth.models import User
from app.auth.schemas import DemoRequest, LoginRequest, SignupRequest, TokenResponse, UserOut
from app.auth.security import create_access_token, hash_password, verify_password
from app.auth.service import (
    InvalidRefreshToken,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.auth.turnstile import TurnstileVerifier, get_turnstile_verifier
from app.config import get_settings
from app.db import SessionDep
from app.demo.service import create_demo_user, purge_expired_demo_users
from app.limits.ratelimit import rate_limit

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _cookie_path() -> str:
    # Scoped to the auth routes so the cookie isn't sent with every API call.
    return f"{get_settings().cookie_path_prefix}/auth"


Verifier = Annotated[TurnstileVerifier, Depends(get_turnstile_verifier)]


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_days * 24 * 3600,
        path=_cookie_path(),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=_cookie_path(),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


async def _require_captcha(verify: TurnstileVerifier, token: str, request: Request) -> None:
    if not await verify(token, request.client.host if request.client else None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Captcha verification failed")


async def _login_response(session: SessionDep, response: Response, user: User) -> TokenResponse:
    refresh = await issue_refresh_token(session, user.id)
    await session.commit()
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=create_access_token(user.id, is_demo=user.is_demo),
        user=UserOut.model_validate(user),
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED, dependencies=[rate_limit("auth", 10)])
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    verify: Verifier,
) -> TokenResponse:
    await _require_captcha(verify, body.turnstile_token, request)
    user = User(email=body.email, password_hash=await hash_password(body.password))
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email exists") from None
    return await _login_response(session, response, user)


@router.post("/demo", status_code=status.HTTP_201_CREATED, dependencies=[rate_limit("demo", 5)])
async def demo_login(
    body: DemoRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    verify: Verifier,
) -> TokenResponse:
    """One-click throwaway account with a sample CV and tracker, deleted after 24h."""
    await _require_captcha(verify, body.turnstile_token, request)
    try:
        await purge_expired_demo_users(session, (await get_graph()).checkpointer)
    except Exception:  # cleanup is opportunistic; never block a demo sign-in on it
        log.exception("Demo purge failed")
        await session.rollback()
    user = await create_demo_user(session)
    return await _login_response(session, response, user)


@router.post("/login", dependencies=[rate_limit("auth", 10)])
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    verify: Verifier,
) -> TokenResponse:
    await _require_captcha(verify, body.turnstile_token, request)
    user = await session.scalar(select(User).where(User.email == body.email))
    if not await verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return await _login_response(session, response, user)


@router.post("/refresh", response_model=TokenResponse, dependencies=[rate_limit("refresh", 30)])
async def refresh(
    response: Response,
    session: SessionDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse | JSONResponse:
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")
    try:
        user, new_token = await rotate_refresh_token(session, refresh_token)
    except InvalidRefreshToken:
        rejected = JSONResponse(
            {"detail": "Invalid refresh token"}, status_code=status.HTTP_401_UNAUTHORIZED
        )
        _clear_refresh_cookie(rejected)
        return rejected
    await session.commit()
    _set_refresh_cookie(response, new_token)
    return TokenResponse(
        access_token=create_access_token(user.id, is_demo=user.is_demo),
        user=UserOut.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: SessionDep,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> None:
    if refresh_token:
        await revoke_refresh_token(session, refresh_token)
        await session.commit()
    _clear_refresh_cookie(response)


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
