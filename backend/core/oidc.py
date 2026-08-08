"""Generic OIDC authorization-code flow helpers."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from core.config import settings


async def _discovery() -> dict[str, Any]:
    url = f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def build_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    # Google well-known endpoint — works for any standard OIDC provider too
    base = f"{settings.oidc_issuer.rstrip('/')}/o/oauth2/v2/auth"
    # Fall back to generic OIDC if not Google
    if "google" not in settings.oidc_issuer:
        base = f"{settings.oidc_issuer.rstrip('/')}/authorize"
    return f"{base}?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str) -> dict[str, Any]:
    """Exchange auth code for tokens; return token response dict."""
    disc = await _discovery()
    token_endpoint = disc["token_endpoint"]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    disc = await _discovery()
    userinfo_endpoint = disc["userinfo_endpoint"]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()
