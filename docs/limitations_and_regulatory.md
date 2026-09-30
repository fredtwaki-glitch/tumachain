# Limitations & Regulatory Considerations

## Current limitations (post-Phase 3)
- No real blockchain connectivity — `MockBlockchainAdapter` only.
- No real email delivery — `MockEmailService` only logs in-process.
- No real KYC/AML/sanctions provider — `MockComplianceProvider` always
  approves structurally-complete submissions and only catches one
  reserved test name as "sanctioned."
- Refresh tokens rotate but are not server-side revoked — an old
  refresh token stays valid until it naturally expires even after a
  newer one has been issued.
- Rate limiting is in-memory and per-process — a multi-instance
  deployment would need a shared store (Redis, etc.).
- No CSRF protection — not applicable to this stateless bearer-token
  API (no cookie session), but worth re-confirming if a browser-session
  auth mode is ever added.
- SQLite is used for development; a production deployment should move to
  PostgreSQL (the SQLAlchemy layer does not depend on SQLite specifically).
- Compliance thresholds (daily limits, velocity, large-transaction
  amount) are configurable via environment variables but the *values*
  shipped are dev defaults, not calibrated to any real jurisdiction.

## Regulatory considerations (for any real-money phase)
Operating a service that moves value between people — even crypto-to-crypto
or crypto-to-fiat via email — is very likely to implicate money-transmitter,
AML/CTF, and sanctions-screening obligations in most jurisdictions. Before
any real-money functionality is enabled, this project would need, at
minimum:
- Legal review of money-transmitter licensing requirements in every
  jurisdiction served.
- A real KYC/AML provider integration in place of `MockComplianceProvider`
  (the `ComplianceProvider` interface is designed for a drop-in swap).
- Real sanctions screening against OFAC and equivalent lists — the mock
  screen here catches exactly one hard-coded test name and nothing else.
- Configurable, jurisdiction-specific transaction/velocity limits,
  calibrated with actual compliance/legal input — never the dev defaults
  shipped here.
- A compliance officer role with real review tooling and case management,
  not just the `COMPLIANCE_OFFICER` role and a flat admin-style API.
- Data protection / privacy compliance (GDPR, etc.) for storing emails,
  KYC documents, and audit trails — this build stores only a document
  *type* and a *reference string*, never actual document images/numbers,
  but a real system would need a proper encrypted-document pipeline.
- A real dispute/appeal process for suspended accounts and rejected KYC.

This document is not legal advice — it's a checklist of things a real
legal and compliance review would need to cover.
