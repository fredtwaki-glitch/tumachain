# API Reference — Phase 1 + Phase 2

Interactive docs are always available at `http://127.0.0.1:8000/docs` once
the server is running.

## Auth (`/auth`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | none | Create a user; provisions wallets on all supported networks; sends (mock) verification email |
| POST | `/auth/login` | none | Returns access + refresh JWTs |
| POST | `/auth/verify-email` | none | Consumes a verification token, sets `EMAIL_VERIFIED` |
| POST | `/auth/refresh` | none (refresh token in body) | Rotates a refresh token for a new access + refresh pair |

## KYC (`/kyc`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/kyc/submit` | Bearer | Submit KYC info (name, country, document type/reference) |
| GET | `/kyc/mine` | Bearer | List your own KYC submissions |

Approval/rejection is admin/compliance-only — see Admin below.
Approval moves your account to `KYC_VERIFIED`, required for **all**
withdrawals regardless of amount.

## Users (`/users`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Bearer | Current user's profile |

## Wallets (`/wallets`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/wallets` | Bearer | Current user's wallets (one per supported network) |
| POST | `/wallets/faucet` | Bearer | **TESTNET-ONLY**: credit mock balance to your own wallet on a given network, so payments/withdrawals can be tested |

## Payments (`/payments`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/payments` | Bearer | Create + process a Pay-via-Mail payment (funds must be available — see Faucet below) |
| GET | `/payments/sent` | Bearer | Payments the current user sent |
| GET | `/payments/received` | Bearer | Payments addressed to the current user's email |
| GET | `/payments/{id}` | Bearer | Fetch one payment (sender or recipient only) |
| POST | `/payments/{id}/retry` | Bearer | Re-attempt a `FAILED` payment |

`POST /payments` accepts an optional `idempotency_key`; replaying the same
key returns the original payment instead of creating a duplicate. It also
accepts an optional `settlement_asset` — if different from `asset`, the
payment is simulated-converted (e.g. BTC → USDC) via the mock exchange
provider before crediting the recipient's ledger balance.

A successful `POST /payments` walks `CREATED → PENDING → SUBMITTED →
CONFIRMING → COMPLETED/FAILED` synchronously (all simulated) — **unless**
compliance decisioning holds it (see Compliance below), in which case it
stays at `PENDING` with `held_for_review: true` until an admin/compliance
reviewer releases or rejects it. On a simulated broadcast failure it
becomes `FAILED` and the sender is automatically refunded;
`POST /payments/{id}/retry` re-attempts it.

## Balances (`/balances`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/balances` | Bearer | Current user's internal, off-chain available balance per asset |

## Withdrawals (`/withdrawals`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/withdrawals` | Bearer | Request a withdrawal from your ledger balance to an external (mock) address |
| GET | `/withdrawals` | Bearer | List your withdrawals |
| GET | `/withdrawals/{id}` | Bearer | Fetch one withdrawal (owner only) |

Withdrawals validate the destination address via the same mock
blockchain adapter used for wallets, enforce a minimum amount, and
deduct fee + amount from your ledger balance up front; a simulated
broadcast failure automatically refunds the ledger. **All withdrawals
require a `KYC_VERIFIED` account**, regardless of amount — submit KYC
via `POST /kyc/submit` and have it approved first.

## Networks (`/networks`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/networks` | none | Supported networks and assets |

## Admin (`/admin`) — ADMIN/SUPER_ADMIN only unless noted
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/summary` | Bearer (admin) | Counts, incl. `kyc_pending`, `held_payments`, `held_withdrawals` |
| GET | `/admin/users` | Bearer (admin) | List all users |
| GET | `/admin/payments` | Bearer (admin) | List all payments |
| GET | `/admin/wallets` | Bearer (admin) | List all wallets |
| GET | `/admin/withdrawals` | Bearer (admin) | List all withdrawals |
| GET | `/admin/flagged/payments` | Bearer (admin or compliance) | Payments with `is_flagged: true` |
| GET | `/admin/flagged/withdrawals` | Bearer (admin or compliance) | Withdrawals with `is_flagged: true` |
| POST | `/admin/payments/{id}/release` | Bearer (admin or compliance) | Release a held payment — proceeds to blockchain submission |
| POST | `/admin/payments/{id}/reject` | Bearer (admin or compliance) | Reject a held payment — refunds the sender, sets `CANCELLED` |
| POST | `/admin/withdrawals/{id}/release` | Bearer (admin or compliance) | Release a held withdrawal |
| POST | `/admin/withdrawals/{id}/reject` | Bearer (admin or compliance) | Reject a held withdrawal — refunds the ledger |
| GET | `/admin/kyc/pending` | Bearer (admin or compliance) | List KYC submissions awaiting review |
| POST | `/admin/kyc/{id}/approve` | Bearer (admin or compliance) | Approve KYC — sets user to `KYC_VERIFIED` (auto-fails on a sanctions hit) |
| POST | `/admin/kyc/{id}/reject` | Bearer (admin or compliance) | Reject KYC with a reason — sets user to `KYC_REJECTED` |
| POST | `/admin/users/{id}/suspend` | Bearer (admin) | Suspend an account (blocks transactions, not login) |
| POST | `/admin/users/{id}/unsuspend` | Bearer (admin) | Restore a suspended account's prior verification state |
| GET | `/admin/audit-logs` | Bearer (admin) | List audit log entries, newest first; optional `?resource_type=` filter |

There is no self-service "become admin" endpoint. Use
`scripts/make_admin.py <email>` locally to promote a user for testing.

## Compliance decisioning

Every payment and withdrawal runs through `evaluate_transaction(...)`
(see `docs/architecture.md`), which can move it to `held_for_review:
true` — never an outright rejection — for any of:
- Daily transaction total (USD-equivalent) exceeding the configured
  limit for the account's verification state
- More than `VELOCITY_MAX_TX_PER_HOUR` transactions in the last hour
- A high risk score from the compliance provider
- A single transaction at or above `LARGE_TRANSACTION_FLAG_USD`

A held transaction still debits the sender's balance/ledger (funds are
reserved) and waits for an admin/compliance reviewer to release or
reject it. All thresholds are configurable via environment variables —
see `.env.example` — not hard-coded.

## Error handling
Validation errors (bad email format, non-positive amount, unsupported
asset/network value) return `422` from Pydantic automatically. Business
logic errors (duplicate email, wrong password, not found, forbidden,
suspended account, KYC required) return `400` / `401` / `403` / `404`
with a JSON `{"detail": "..."}` body. Exceeding the rate limit returns
`429`.
