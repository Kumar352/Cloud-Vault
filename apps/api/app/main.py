from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.vault import router as vault_router

app = FastAPI(
    title="CloudVault API",
    version="1.0.0",
    swagger_ui_init_oauth={
        "clientId": "cloudvault-api",
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": "openid profile email",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-File-Name"],
)

app.include_router(auth_router)
app.include_router(vault_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small status response for the local web app."""
    return {"status": "ok", "service": "cloudvault-api"}
