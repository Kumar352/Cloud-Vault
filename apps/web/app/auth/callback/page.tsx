"use client";

import { useEffect, useState } from "react";

const issuer = process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "http://localhost:5556/dex";

function encodeBase64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => (binary += String.fromCharCode(byte)));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export default function AuthCallback() {
  const [message, setMessage] = useState("Completing secure sign-in…");

  useEffect(() => {
    async function exchangeCode() {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const returnedState = params.get("state");
      const state = sessionStorage.getItem("cloudvault_oidc_state");
      const verifier = sessionStorage.getItem("cloudvault_pkce_verifier");
      if (!code || !returnedState || returnedState !== state || !verifier) {
        setMessage("Sign-in could not be verified. Return to the home page and try again.");
        return;
      }
      if (sessionStorage.getItem("cloudvault_exchanging_code") === code) return;
      sessionStorage.setItem("cloudvault_exchanging_code", code);

      const response = await fetch(`${issuer}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "authorization_code",
          client_id: "cloudvault-api",
          redirect_uri: `${window.location.origin}/auth/callback`,
          code,
          code_verifier: verifier,
        }),
      });
      if (!response.ok) {
        sessionStorage.removeItem("cloudvault_exchanging_code");
        setMessage("The local identity service rejected sign-in. Please try again.");
        return;
      }
      const tokenResponse = (await response.json()) as { access_token?: string; expires_in?: number };
      if (!tokenResponse.access_token) {
        sessionStorage.removeItem("cloudvault_exchanging_code");
        setMessage("The local identity service returned no access token.");
        return;
      }
      sessionStorage.setItem("cloudvault_access_token", tokenResponse.access_token);
      sessionStorage.setItem("cloudvault_token_expires", String(Date.now() + (tokenResponse.expires_in ?? 300) * 1000));
      sessionStorage.removeItem("cloudvault_oidc_state");
      sessionStorage.removeItem("cloudvault_pkce_verifier");
      window.location.replace("/");
    }
    void exchangeCode().catch(() => {
      sessionStorage.removeItem("cloudvault_exchanging_code");
      setMessage("Could not reach the local identity service.");
    });
  }, []);

  return (
    <main className="auth-page">
      <section className="auth-card">
        <span className="brand-mark" aria-hidden="true">C</span>
        <p className="eyebrow">CloudVault · local sign-in</p>
        <h1>Almost there</h1>
        <p>{message}</p>
      </section>
    </main>
  );
}

export { encodeBase64Url };
