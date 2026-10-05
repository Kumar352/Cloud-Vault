# CloudVault web

Next.js + TypeScript local workbench for signing in, uploading encrypted files to quarantine, checking scan state, downloading clean versions, sharing files, asking the local assistant, and reviewing audit/anomaly activity.

## Run

Start the local API, Dex, and (for scans) ClamAV using the root README. In a PowerShell terminal from this directory:

    pnpm dev

Open http://localhost:3000. The defaults use the local API at http://127.0.0.1:8000 and local OIDC at http://localhost:5556/dex. These public browser settings may be overridden with NEXT_PUBLIC_API_BASE_URL and NEXT_PUBLIC_OIDC_ISSUER. They are not secrets.

The local access token stays in sessionStorage for the current tab and is cleared at sign-out or when it expires. The synthetic users and sample password are documented in the root README. Do not reuse those credentials or expose this configuration publicly.

## Local checks

    pnpm exec tsc --noEmit
    pnpm build

No Vercel project, hosted API, or paid service is configured.
