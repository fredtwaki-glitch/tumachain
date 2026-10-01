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

import logging

logger = logging.getLogger("tumachain")

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


@app.on_event("startup")
def bootstrap_schema_and_seed_data() -> None:
    """Create any brand-new tables, patch legacy SQLite databases, and seed
    dev-only data — run as a startup event (not at import time) so a
    transient DB issue surfaces as a clear, logged failure instead of
    crashing the process before FastAPI even finishes constructing `app`.

    NOTE: `ensure_v2_schema()` is dialect-aware (SQLite and Postgres) and
    idempotent, so it's safe to run on every boot. `alembic upgrade head`
    (run as part of the start command) remains the preferred path for new
    tables/future migrations, but is allowed to fail there — e.g. against
    a Postgres database Alembic has never tracked, with no shell/console
    access available to stamp it first (as on Render's free tier). This
    function is the fallback that keeps the service usable regardless.
    """
    try:
        Base.metadata.create_all(bind=engine)
        ensure_v2_schema()
    except Exception:
        # Never let a schema-patch failure take the whole service down —
        # especially on tiers with no shell access to diagnose/retry it
        # interactively. Log loudly so it's visible, but keep serving.
        logger.exception(
            "Schema bootstrap failed. Columns some endpoints rely on may "
            "still be missing; check logs/DB directly when you can."
        )

    if settings.app_env != "development":
        return

    try:
        with SessionLocal() as seed_db:
            ensure_development_admin(seed_db)
            for seed_user in seed_db.query(User).all():
                ensure_missing_wallets_for_user(seed_db, seed_user)
    except Exception:
        # Dev-only convenience: never let seeding failures take the whole
        # app down, since real requests don't depend on it.
        logger.exception("Development data seeding failed; continuing without it.")


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
