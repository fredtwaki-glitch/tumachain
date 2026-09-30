# TumaChain — PayMail UI Complete (Phase 3 Sandbox)

This delivery keeps the existing FastAPI/SQLAlchemy Phase 3 backend and replaces the placeholder frontend with a responsive PayMail/TumaChain UI implemented from the reference screens in `Tuma chain pototype.docx`.

**Mode:** TESTNET / SIMULATED ONLY. No real cryptocurrency or real-money transactions are enabled.

## What was completed

The frontend now contains working screens for:

- Dashboard
- Multi-Chain Wallets
- Send Crypto via Email
- Transactions Ledger
- KYC & Compliance
- Admin Operations & Governance
- Login / registration
- Account profile / sign out
- Responsive mobile navigation
- Testnet/sandbox status indicators
- API-connected wallet, balance, payment, withdrawal and KYC actions
- Admin API integration with graceful role/access handling

The visual language follows the supplied reference: dark control-plane layout, fixed left navigation, purple active states, green testnet/compliance indicators, card-based dashboards, tables, stepper workflow, routing preview, KYC rule cards and admin governance panels.

The frontend is served by FastAPI itself, so there is no separate Node/Vite setup required for this version.

## Project structure

```text
TumaChain_Phase3_UI_Complete/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html
├── docs/
├── scripts/
├── start_tumachain.bat
├── .gitignore
└── README.md
```

## Run on Windows / PyCharm

### 1. Open the project

Open the folder containing this README in PyCharm.

### 2. Create the virtual environment

In the PyCharm Terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use PyCharm's Python Interpreter settings to select the `.venv` interpreter directly.

### 3. Install dependencies

```powershell
cd backend
python -m pip install -r requirements.txt
```

### 4. Configure `.env`

From the `backend` folder:

```powershell
copy .env.example .env
```

Keep this as a local development configuration. Do not place real API keys or private keys in the project.

### 5. Run migrations

```powershell
cd backend
alembic upgrade head
```

### Development admin account

In the default development configuration, TumaChain automatically creates a
local administrator when the application initializes the database:

```text
Email:    admin@example.com
Password: walenisi1
Role:     ADMIN
```

The account is marked email-verified and receives the standard mock/testnet
wallet records. This bootstrap is restricted to `APP_ENV=development` and
`DEV_AUTO_CREATE_ADMIN=true`; do not enable it for production deployments.

### 6. Start the application

```powershell
cd backend
uvicorn app.main:app --reload
```

Then open:

**http://127.0.0.1:8000/**

API documentation remains available at:

**http://127.0.0.1:8000/docs**

The same FastAPI process serves the new UI from `/`.

### One-click Windows launcher

After installing dependencies, you can also double-click:

```text
start_tumachain.bat
```

It starts the FastAPI server on `127.0.0.1:8000`.

## Demo flow

1. Create a test account.
2. Log in.
3. The backend automatically creates the supported testnet wallet records.
4. Open **Dashboard**.
5. Open **Multi-Chain Wallets**.
6. Use the backend faucet/API flow to create test balances where required.
7. Open **Send via Email**.
8. Enter a recipient email, asset, network and amount.
9. Submit the simulated payment.
10. Open **Transactions Ledger** to inspect the result.
11. Open **KYC & Compliance** to submit mock verification data.
12. If an ADMIN/COMPLIANCE role is configured, open **Admin Portal**.

## Reference UI

The intended UI is based on the six supplied reference screens in the prototype DOCX:

- Admin Operations & Governance
- Multi-Chain Wallets
- Send Crypto via Email
- Transactions Ledger
- KYC & Compliance Operations
- Dashboard

The implementation uses the supplied terminology and layout direction while connecting controls to the existing backend rather than using hard-coded demo transactions.

## Backend status

The existing Phase 3 backend remains the source of truth for:

- Authentication and JWT sessions
- User roles
- Wallet records
- Balances
- Payments
- Withdrawals
- KYC submissions
- Compliance checks
- Admin authorization
- Simulated blockchain/payment processing

## Testing

Run:

```powershell
cd backend
python -m pytest -q
```

The test suite requires the dependencies in `backend/requirements.txt` to be installed.

## Important

This is a sandbox/testnet prototype. The UI deliberately labels the environment as simulated and does not claim that a database record is a real blockchain transfer.

## Arc Testnet integration

This build includes a development Arc Testnet integration alongside the existing TumaChain mock/sandbox payment engine.

Arc Testnet settings:
- Network: Arc Testnet
- Chain ID: 5042002
- RPC: https://rpc.testnet.arc.io
- Native asset/gas: USDC (18 decimals)
- Explorer: https://explorer.testnet.arc.io

The **Multi-Chain Wallets** page now has an **Arc Testnet Wallet** panel. With MetaMask (or another EVM browser wallet), click **Connect Arc Wallet**. The browser wallet signs transactions; the TumaChain backend never receives the private key.

The page can:
- Check Arc Testnet RPC health.
- Connect/switch the browser wallet to Arc Testnet.
- Read the connected address's native USDC balance through the backend RPC proxy.
- Submit a direct native-USDC Arc Testnet transfer from the user's connected wallet.
- Open the resulting transaction in Arc Explorer.

The direct Arc wallet transfer is intentionally separate from the existing Pay-via-Mail internal ledger. Pay-via-Mail remains sandbox/mock unless a future phase explicitly adds on-chain settlement and recipient-wallet resolution.

### Arc endpoints

- `GET /arc/config` — public Arc Testnet configuration
- `GET /arc/status` — RPC reachability and latest block
- `GET /arc/balance?address=0x...` — native USDC balance for an EVM address

For testnet funds, use the Circle faucet linked from the Arc documentation.


## Render deployment

This repository is configured so Render can run the FastAPI app from the project root.

**Build Command**
```text
pip install -r backend/requirements.txt
```

**Start Command**
```text
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
```

**Health Check**
```text
/health
```

The frontend is served by FastAPI at `/`, so production does not require a separate frontend host and the browser uses the same origin for API requests.

For local testing, do not double-click `frontend/index.html` as the primary method. Start FastAPI and open `http://127.0.0.1:8000/`. If the HTML is opened directly from disk, the UI now falls back to `http://127.0.0.1:8000` for API calls.


## TumaChain V2

V2 evolves the existing Pay-via-Mail sandbox into an identity-first stablecoin payment and settlement architecture.

### New V2 surfaces
- Tuma username and optional phone identity
- `POST /api/v1/identity/resolve`
- `POST /api/v1/payments/quote`
- payment request links under `/pay/{code}`
- QR-ready public payment identifiers
- settlement quote abstraction
- merchant API credential and webhook endpoint creation
- explicit testnet/simulation state; no fabricated blockchain hashes or confirmations

### Testnet safety
The current project does not have production blockchain broadcasting or live fiat settlement providers configured. Payment records remain explicitly pending/simulated and do not claim that funds moved on-chain.

Run locally:
`uvicorn app.main:app --app-dir backend --reload`

Run tests:
`pytest backend/tests -q`

Apply database migrations:
`alembic -c backend/alembic.ini upgrade head`


## V2 completion status
The V2 build preserves the existing authentication, wallet, admin and database architecture while adding identity resolution, payment links/QR, payment quotes, merchant APIs, webhook ingestion, settlement abstraction, testnet safety controls and V2 admin visibility. Live blockchain broadcasting, live M-Pesa, live KYC/AML and real-world settlement remain deliberately unconfigured until genuine providers, credentials, compliance and production controls are supplied. See `docs/v2_compliance_matrix.md`.
