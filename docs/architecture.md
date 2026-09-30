# Architecture — Phase 1

## Overview
Pay-via-Mail is a testnet/sandbox cryptocurrency payment platform. A sender
enters a recipient's email address instead of a wallet address; the backend
creates an internal ledger record ("payment") and, once a real blockchain
layer is integrated in a later phase, would submit an on-chain transaction.

**No real cryptocurrency moves anywhere in this codebase.** All blockchain
interaction goes through `MockBlockchainAdapter`.

## Components
- **FastAPI app** (`app/main.py`) — HTTP API, mounted routers, CORS.
- **SQLAlchemy models** (`app/models/`) — `User`, `Wallet`, `Payment`, plus
  a single `enums.py` holding every enum used across the schema so the
  full state machine is visible in one place.
- **Security layer** (`app/security/`) — bcrypt password hashing, JWT
  access/refresh tokens, a `get_current_user` FastAPI dependency, and a
  `require_roles(...)` RBAC dependency factory for admin/compliance routes.
- **Blockchain abstraction** (`app/blockchain/adapter.py`) — a
  `BlockchainAdapter` interface with a `MockBlockchainAdapter`
  implementation. Real `BitcoinAdapter` / `EthereumAdapter` / `SolanaAdapter`
  classes are meant to be added later, following the same interface,
  without changing any calling code.
- **Services** (`app/services/`) — `wallet_service` (provisions one wallet
  per supported network on registration) and `email_service` (mock
  provider; swap for SES/SendGrid/etc. later).
- **Routers** (`app/routers/`) — `auth`, `users`, `wallets`, `payments`,
  `networks`, `admin`.

## Why a mock private key column exists on Wallet
Real wallets need a private key (or a reference to one held by a signer
service). Phase 1 stores a clearly-fake placeholder string
(`mockkey_<uuid>`) so the schema shape matches what a real implementation
will need, without ever handling real key material. This field is never
included in any Pydantic response schema and is asserted-absent in tests
(`test_wallet_private_key_never_exposed`).

## Payment status states
```
CREATED → PENDING → SUBMITTED → CONFIRMING → COMPLETED
                                            → FAILED
                                            → EXPIRED
                                            → CANCELLED
```
Phase 1 only exercises `CREATED` → `PENDING` (a payment is recorded and
queued). The remaining states are wired into the model/enum now so Phase 2
(actual mock blockchain submission and confirmation simulation) can drive
the same field without a schema change.

## Roles
`USER`, `COMPLIANCE_OFFICER`, `ADMIN`, `SUPER_ADMIN`. There is deliberately
no public "become admin" endpoint — see `scripts/make_admin.py` for the
dev-only path to promote a user locally.

## What's deliberately deferred to later phases
- Refresh-token server-side revocation (rotation happens, but old tokens
  remain valid until natural expiry — a real deployment would track
  issued/blacklisted tokens)
- CSRF protection (not applicable here: this is a stateless bearer-token
  API with no cookie-based session, so CSRF's usual attack vector doesn't
  apply — this is worth confirming explicitly rather than assuming)
- Distributed rate limiting (current implementation is in-memory,
  single-process — see `security/rate_limit.py`)

## Phase 3 additions — KYC/AML, compliance, security hardening

- **`app/compliance/provider.py`** — `ComplianceProvider` interface +
  `MockComplianceProvider` (identity verification, sanctions screening,
  risk scoring — all simulated, deterministic, and clearly documented
  as non-real).
- **KYC workflow** — `POST /kyc/submit`, `GET /kyc/mine`,
  `POST /admin/kyc/{id}/approve|reject`. A submission auto-fails
  sanctions screening even on an explicit approve attempt (see
  `MockComplianceProvider.SIMULATED_SANCTIONED_NAME`), and approval
  moves the user to `KYC_VERIFIED`.
- **`app/services/compliance_service.py`** — configurable (not
  hard-coded) daily transaction limits by verification state, velocity
  monitoring (transactions/hour), and risk scoring via the compliance
  provider. Crossing any threshold moves a payment/withdrawal to
  `held_for_review=True` rather than rejecting outright — a human
  (admin/compliance role) then releases or rejects it via
  `POST /admin/payments/{id}/release|reject` (same pattern for
  withdrawals).
- **Withdrawals now require `KYC_VERIFIED`** — enforced in
  `withdrawal_processing.py` regardless of amount, per the spec's
  explicit rule (`IF user is not KYC_VERIFIED: restrict withdrawals`).
- **Account suspension** — `POST /admin/users/{id}/suspend|unsuspend`.
  Suspension sets `verification_state=SUSPENDED` but deliberately does
  **not** set `is_active=False`: that flag gates login itself, and a
  suspended user should still be able to log in and see their account
  status — they just can't transact. Enforcement happens in
  `compliance_service.assert_account_active`, checked at the start of
  both payment and withdrawal processing.
- **Audit logging** — `app/models/audit_log.py` + `write_audit_log(...)`.
  Every hold, release, rejection, KYC decision, and suspension writes
  an entry. `GET /admin/audit-logs` (admin-only) lists them, newest
  first, optionally filtered by `resource_type`.
- **Security hardening**:
  - `POST /auth/refresh` — refresh-token rotation (see the deferred-items
    note above for its limitation).
  - `security/rate_limit.py` — a simple in-memory, per-IP sliding-window
    limiter (`RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`),
    exempting `/`, `/health`, and the docs routes.
  - `security/secure_headers.py` — `X-Content-Type-Options`,
    `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` on every
    response.
  - Role-based access control was already in place from Phase 1
    (`security/rbac.py`); Phase 3 adds the `require_compliance`
    dependency to gate KYC review and held-transaction release/reject
    endpoints to `COMPLIANCE_OFFICER`/`ADMIN`/`SUPER_ADMIN`.

## Phase 2 additions — cross-chain routing, conversion, withdrawals

- **`app/services/exchange_service.py`** — `MockExchangeProvider`, a
  fixed-rate (never real-market) conversion engine. `ExchangeProvider`
  is the interface a real liquidity provider/DEX aggregator would
  implement later.
- **`app/services/routing_service.py`** — `route_payment(...)` ties
  together the network fee (from the blockchain adapter), an optional
  simulated conversion, and a flat platform fee, returning the final
  amount the recipient's ledger will be credited.
- **`app/models/ledger_balance.py`** — `LedgerBalance`: a per-user,
  per-asset internal balance, separate from the per-network `Wallet`
  balance. This is the "AVAILABLE_BALANCE" in the spec's payment
  lifecycle diagram — what a payment settles into and what a
  withdrawal draws from.
- **`app/models/withdrawal.py`** — `Withdrawal`: request → validate
  destination address (via the same mock adapter) → debit ledger →
  simulate broadcast → `COMPLETED` or `FAILED` (with automatic refund
  on failure).
- **`app/services/payment_processing.py`** — orchestrates the full
  payment lifecycle: sender wallet balance check → routing → debit →
  simulated blockchain submit/broadcast/confirm → recipient ledger
  credit. Includes `retry_payment(...)` for re-attempting a `FAILED`
  payment.
- **Testnet faucet** (`POST /wallets/faucet`) — since payments now
  enforce sender balance, and wallets start at zero, this endpoint
  lets any user top up their own mock wallet for testing. It has no
  production equivalent — real funds would only ever arrive via an
  actual on-chain deposit.
- **Deterministic failure sentinel** — `MockBlockchainAdapter` always
  succeeds except for one reserved amount
  (`SIMULATED_BROADCAST_FAILURE_AMOUNT` in `blockchain/adapter.py`),
  used only by the test suite to exercise the failure/refund/retry
  path without relying on real network flakiness.
