from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth import (
    OIDC_AUDIENCE,
    OIDC_ISSUER,
    has_resource_permission,
    principal_from_verified_claims,
    verify_oidc_token,
)


class OidcAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.alice = principal_from_verified_claims(
            {"sub": "alice-sub", "email": "alice@example.test", "email_verified": True}
        )
        cls.bob = principal_from_verified_claims(
            {"sub": "bob-sub", "email": "bob@example.test", "email_verified": True}
        )

    def token(
        self,
        subject: str,
        *,
        email: str = "alice@example.test",
        issuer: str = OIDC_ISSUER,
        audience: str = OIDC_AUDIENCE,
    ) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "iss": issuer,
                "aud": audience,
                "sub": subject,
                "email": email,
                "email_verified": True,
                "iat": now,
                "exp": now + 300,
            },
            self.private_key,
            algorithm="RS256",
        )

    def client(self, key: object | None = None) -> Mock:
        signing_key = key or self.private_key.public_key()
        client = Mock()
        client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=signing_key)
        return client

    def test_accepts_valid_signature_issuer_audience_and_subject(self) -> None:
        token = self.token(self.alice.subject)
        self.assertEqual(verify_oidc_token(token, jwks_client=self.client()), self.alice)

    def test_rejects_wrong_signature(self) -> None:
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = self.token(self.alice.subject)
        with self.assertRaises(HTTPException) as error:
            verify_oidc_token(token, jwks_client=self.client(other_key.public_key()))
        self.assertEqual(error.exception.status_code, 401)

    def test_rejects_wrong_issuer_or_audience(self) -> None:
        for token in (
            self.token(self.alice.subject, issuer="http://localhost:9999/dex"),
            self.token(self.alice.subject, audience="another-api"),
        ):
            with self.subTest(token=token[:12]), self.assertRaises(HTTPException) as error:
                verify_oidc_token(token, jwks_client=self.client())
            self.assertEqual(error.exception.status_code, 401)

    def test_rejects_unseeded_or_unverified_email(self) -> None:
        for claims in (
            {"sub": "unknown", "email": "mallory@example.test", "email_verified": True},
            {"sub": "alice-sub", "email": "alice@example.test", "email_verified": False},
        ):
            with self.subTest(claims=claims), self.assertRaises(HTTPException) as error:
                principal_from_verified_claims(claims)
            self.assertEqual(error.exception.status_code, 403)

    def test_allows_shared_reader_but_hides_private_resource(self) -> None:
        self.assertTrue(has_resource_permission(self.bob, "shared-brief", "read"))
        self.assertFalse(has_resource_permission(self.bob, "private-notes", "read"))
        self.assertFalse(has_resource_permission(self.bob, "shared-brief", "manage_sharing"))

    def test_owner_can_manage_sharing(self) -> None:
        self.assertTrue(has_resource_permission(self.alice, "shared-brief", "manage_sharing"))


if __name__ == "__main__":
    unittest.main()
