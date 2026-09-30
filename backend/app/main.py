from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (ensures models are registered on Base)
from app.routers import (
    auth,
    users,
    wallets,
    payments,
    networks,
    admin,
    balances,
    withdrawals,
    kyc,
    arc,
    identity,
    payment_links,
    settlements,
    merchant,
    payment_quotes,
    payment_v1,
    webhooks,
)
from app.security.rate_limit import RateLimitMiddleware
from app.security.secure_headers import SecureHeadersMiddleware
from app.services.dev_seed import ensure_development_admin
from app.services.wallet_service import ensure_missing_wallets_for_user
from app.services.schema_upgrade import ensure_v2_schema
from app.models.user import User

Base.metadata.create_all(bind=engine)
ensure_v2_schema()

# Development convenience only: create the default local admin account
# after the schema exists. This is gated to APP_ENV=development.
with SessionLocal() as _seed_db:
    ensure_development_admin(_seed_db)
    # Backfill only newly introduced testnet wallet records for existing users.
    for _user in _seed_db.query(User).all():
        ensure_missing_wallets_for_user(_seed_db, _user)

app = FastAPI(
    title=settings.app_name,
    description=(
        "Pay-via-Mail — testnet/sandbox cryptocurrency payment platform. "
        "Arc Testnet wallet connectivity is enabled for development; no mainnet or real-money functionality is enabled."
    ),
    version="0.3.0-phase3",
)

app.add_middleware(SecureHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # TumaChain uses Authorization bearer tokens, not cookie-based auth.
    # Keeping credentials disabled allows wildcard CORS for local/test deployments.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(wallets.router)
app.include_router(payments.router)
app.include_router(networks.router)
app.include_router(balances.router)
app.include_router(withdrawals.router)
app.include_router(kyc.router)
app.include_router(admin.router)
app.include_router(arc.router)
app.include_router(identity.router)
app.include_router(payment_links.router)
app.include_router(settlements.router)
app.include_router(merchant.router)
app.include_router(payment_quotes.router)
app.include_router(payment_v1.router)
app.include_router(webhooks.router)


_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/", include_in_schema=False)
def landing_page():
    """Public landing page."""
    return FileResponse(_FRONTEND / "landing.html", media_type="text/html")


@app.get("/pay/{code}", include_in_schema=False)
def payment_link_page(code: str):
    return FileResponse(_FRONTEND / "pay.html", media_type="text/html")


@app.get("/login", include_in_schema=False)
@app.get("/register", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def app_shell():
    """Existing single-page app (auth + dashboard); it reads the path to pick its auth tab."""
    return FileResponse(_FRONTEND / "index.html", media_type="text/html")


@app.get("/health")
def health():
    return {"status": "ok"}
