# TumaChain V2 — implementation handoff

Base: existing TumaChain Phase 3 application. The project was evolved in-place; authentication, registration, admin, wallet and Render configuration were retained.

## Implemented
- Identity-first user fields: username, phone, profile metadata, settlement preference, KYC/KYB/AML placeholders.
- Identity resolution by email, username and phone: `POST /api/v1/identity/resolve`.
- Versioned payment quote: `POST /api/v1/payments/quote`.
- Versioned payment lookup: `GET /api/v1/payments/{payment_id}`.
- Payment links: create/get under `/api/v1/payment-links`; public `/pay/{code}` page.
- QR generation endpoint: `/api/v1/payment-links/{code}/qr` using `tuma://pay/{code}`.
- Settlement quote/create abstraction under `/api/v1/settlements`.
- Merchant API-key and webhook registration endpoints.
- Existing testnet blockchain workflow changed so it does not fabricate transaction hashes or confirmations.
- Withdrawal testnet workflow no longer fabricates transaction hashes or completed on-chain withdrawals.
- Landing page repositioned around stablecoin payments/settlement, with Send / Receive / Request / Settle UX.
- Existing project documentation extended with V2 architecture and operational notes.
- Legacy SQLite deployments receive a small runtime schema compatibility upgrade; Alembic migration `0004_v2` is also included.

## Explicit limitations
- No live production blockchain broadcaster was added.
- No real M-Pesa, bank or fiat settlement provider was added.
- KYC/KYB/AML remain integration abstractions.
- Current settlement and unsupported blockchain operations are testnet/simulation and are labeled accordingly.

## QA
- Python syntax compilation: passed for application and tests.
- Full pytest execution: not completed in this environment because package installation was blocked by unavailable outbound package access (`fastapi`/`passlib` could not be installed here).


## Test suite reconciliation
The regression suite was updated for V2 testnet semantics: unsupported live blockchain operations remain PENDING with no fabricated transaction hash or confirmation. Withdrawal tests seed the internal ledger directly instead of depending on fake blockchain confirmation. Arc testnet is included in the wallet set.
