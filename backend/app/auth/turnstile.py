from collections.abc import Awaitable, Callable

import httpx

from app.config import get_settings

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

TurnstileVerifier = Callable[[str, str | None], Awaitable[bool]]


async def verify_turnstile(token: str, remote_ip: str | None) -> bool:
    """Server-side check of a Cloudflare Turnstile token. Fails closed on network errors."""
    data = {"secret": get_settings().turnstile_secret_key, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(SITEVERIFY_URL, data=data)
            resp.raise_for_status()
            return bool(resp.json().get("success"))
    except (httpx.HTTPError, ValueError):
        return False


def get_turnstile_verifier() -> TurnstileVerifier:
    """FastAPI dependency so tests can swap in a verifier that doesn't hit the network."""
    return verify_turnstile
