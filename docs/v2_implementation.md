# TumaChain V2 implementation status

## Implemented
- Identity fields: username, phone, profile metadata, settlement preference, KYC/KYB/AML state placeholders.
- Identity resolution: email, username, phone.
- Versioned payment quote and payment lookup endpoints.
- Payment requests and public `/pay/{code}` pages.
- QR PNG generation using `tuma://pay/{code}` payload.
- Settlement quote and testnet settlement-record abstraction.
- Merchant API credentials are stored as SHA-256 hashes; raw credentials are returned only at creation.
- Webhook endpoint registration with secret hashes.
- Testnet payment processing no longer fabricates blockchain transaction hashes or confirmations.
- Landing page and send flow redesigned around Send / Receive / Request / Settle.

## Intentionally not live
- No production blockchain broadcaster is configured.
- No real bank or M-Pesa settlement provider is configured.
- No regulatory or licensing claim is made.
- KYC/KYB/AML remain integration points until real providers and compliance processes are supplied.
