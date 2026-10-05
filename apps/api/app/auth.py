"""Local OIDC token validation and synthetic identity mapping.

This adapter is intentionally limited to the loopback Dex provider used in
local development. Persistent local users are seeded in the SQLite metadata store.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError


OIDC_ISSUER = os.getenv("CLOUDVAULT_OIDC_ISSUER", "http://localhost:5556/dex").rstrip("/")
OIDC_AUDIENCE = os.getenv("CLOUDVAULT_OIDC_AUDIENCE", "cloudvault-api")
OIDC_JWKS_URL = os.getenv("CLOUDVAULT_OIDC_JWKS_URL", f"{OIDC_ISSUER}/keys")

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{OIDC_ISSUER}/auth",
    tokenUrl=f"{OIDC_ISSUER}/token",
    scopes={
        "openid": "Authenticate the local demo user",
        "profile": "Read the synthetic demo user's profile claims",
        "email": "Read the synthetic demo user's verified email claim",
    },
    auto_error=False,
)
router = APIRouter(tags=["identity and authorization"])


class ResourceRole(StrEnum):
    OWNER = "owner"
    COLLABORATOR = "collaborator"


@dataclass(frozen=True)
class Principal:
    user_id: str
    subject: str
    email: str
    tenant_id: str


@dataclass(frozen=True)
class Resource:
    resource_id: str
    tenant_id: str
    owner_id: str
    title: str
    grants: dict[str, ResourceRole]


# These synthetic emails map only verified Dex identities to seeded local users.
DEMO_USERS_BY_EMAIL: dict[str, tuple[str, str]] = {
    "alice@example.test": ("alice", "demo"),
    "bob@example.test": ("bob", "demo"),
}

RESOURCES: dict[str, Resource] = {
    "shared-brief": Resource(
        resource_id="shared-brief",
        tenant_id="demo",
        owner_id="alice",
        title="Synthetic shared brief",
        grants={"bob": ResourceRole.COLLABORATOR},
    ),
    "private-notes": Resource(
        resource_id="private-notes",
        tenant_id="demo",
        owner_id="alice",
        title="Synthetic private notes",
        grants={},
    ),
}

PERMISSIONS: dict[ResourceRole, frozenset[str]] = {
    ResourceRole.OWNER: frozenset({"read", "write", "manage_sharing"}),
    ResourceRole.COLLABORATOR: frozenset({"read"}),
}


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    _require_loopback_oidc_urls()
    return PyJWKClient(OIDC_JWKS_URL, timeout=3, cache_keys=True)


def _require_loopback_oidc_urls() -> None:
    """Prevent this local adapter from silently calling a remote identity host."""
    for value in (OIDC_ISSUER, OIDC_JWKS_URL):
        parsed = urlsplit(value)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise RuntimeError("The Phase 1B identity adapter only permits loopback HTTP URLs")


def principal_from_verified_claims(claims: dict[str, object]) -> Principal:
    """Resolve a verified OIDC subject to the local synthetic principal list."""
    subject = claims.get("sub")
    email = claims.get("email")
    if (
        not isinstance(subject, str)
        or not isinstance(email, str)
        or claims.get("email_verified") is not True
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Identity is not enabled")
    account = DEMO_USERS_BY_EMAIL.get(email.casefold())
    if account is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Identity is not enabled")
    user_id, tenant_id = account
    return Principal(user_id=user_id, subject=subject, email=email, tenant_id=tenant_id)


def verify_oidc_token(token: str, *, jwks_client: PyJWKClient | None = None) -> Principal:
    """Validate signature, fixed algorithm, issuer, audience, expiry, and subject."""
    client = jwks_client or _jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=OIDC_AUDIENCE,
            issuer=OIDC_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "aud"]},
        )
    except (PyJWTError, PyJWKClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return principal_from_verified_claims(claims)


def current_principal(token: str | None = Depends(oauth2_scheme)) -> Principal:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_oidc_token(token)


def resource_role(principal: Principal, resource_id: str) -> ResourceRole | None:
    resource = RESOURCES.get(resource_id)
    if resource is None or resource.tenant_id != principal.tenant_id:
        return None
    if resource.owner_id == principal.user_id:
        return ResourceRole.OWNER
    return resource.grants.get(principal.user_id)


def has_resource_permission(principal: Principal, resource_id: str, permission: str) -> bool:
    role = resource_role(principal, resource_id)
    return role is not None and permission in PERMISSIONS[role]


def authorized_resource(principal: Principal, resource_id: str, permission: str) -> Resource:
    resource = RESOURCES.get(resource_id)
    if resource is None or not has_resource_permission(principal, resource_id, permission):
        # Hide whether an unavailable resource exists from this principal.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


@router.get("/auth/me")
def who_am_i(principal: Principal = Depends(current_principal)) -> dict[str, str]:
    return {"user_id": principal.user_id, "email": principal.email}


@router.get("/resources/{resource_id}")
def read_resource(
    resource_id: str,
    principal: Principal = Depends(current_principal),
) -> dict[str, str]:
    resource = authorized_resource(principal, resource_id, "read")
    return {"resource_id": resource.resource_id, "title": resource.title}


@router.get("/resources/{resource_id}/sharing")
def read_resource_shares(
    resource_id: str,
    principal: Principal = Depends(current_principal),
) -> dict[str, object]:
    resource = authorized_resource(principal, resource_id, "manage_sharing")
    return {
        "resource_id": resource.resource_id,
        "grants": {user_id: role.value for user_id, role in resource.grants.items()},
    }
