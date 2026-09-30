"""
Central application configuration.

All settings are loaded from environment variables / a local .env file.
Never hard-code secrets here. See .env.example for the full list of
supported variables.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Pay-via-Mail"
    app_env: str = "development"
    debug: bool = True

    # --- Development admin bootstrap ---
    # Enabled only for local development. Never enable this mechanism in production.
    dev_auto_create_admin: bool = True
    dev_admin_email: str = "admin@example.com"
    dev_admin_password: str = ""
    dev_admin_full_name: str = "TumaChain Admin"

    # --- Database ---
    database_url: str = "sqlite:///./pay_via_mail.db"

    # --- JWT / Security ---
    jwt_secret_key: str = "changeme-dev-secret-do-not-use-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Email (mock/dev provider) ---
    email_provider: str = "mock"
    email_from_address: str = "noreply@payviamail.dev"

    # --- Blockchain ---
    # mock keeps the existing TumaChain sandbox payment engine. arc_testnet
    # enables the Arc Testnet read-only integration and wallet UI.
    blockchain_mode: str = "arc_testnet"
    arc_rpc_url: str = "https://rpc.testnet.arc.io"
    arc_chain_id: int = 5042002
    arc_explorer_url: str = "https://explorer.testnet.arc.io"

    # --- CORS ---
    # API uses bearer Authorization headers, so credentials/cookies are not required.
    # Keep wildcard for local/test deployments; production can set CORS_ORIGINS.
    cors_origins: List[str] = ["*"]

    # --- Future production integration placeholders ---
    btc_rpc_url: str = ""
    eth_rpc_url: str = ""
    sol_rpc_url: str = ""
    evm_testnet_rpc_url: str = ""
    exchange_api_key: str = ""
    exchange_api_secret: str = ""
    kyc_provider_api_key: str = ""
    sanctions_screening_api_key: str = ""
    sms_provider_api_key: str = ""
    webhook_secret: str = ""

    # --- Phase 3: compliance / limits (configurable, NOT hard-coded legal
    # thresholds — a real deployment would set these per jurisdiction and
    # per the actual regulated provider's requirements) ---
    compliance_provider: str = "mock"

    # Transaction/velocity limits, expressed in USD-equivalent, by
    # verification state. Deliberately conservative dev defaults.
    unverified_daily_limit_usd: float = 100.0
    email_verified_daily_limit_usd: float = 10000.0
    kyc_verified_daily_limit_usd: float = 50000.0

    large_transaction_flag_usd: float = 5000.0  # single tx above this is flagged for review
    velocity_max_tx_per_hour: int = 10  # more than this many tx/hour flags the account

    # Simple in-memory rate limiting (Phase 3 security hardening).
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
