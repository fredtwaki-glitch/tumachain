Write-Host "TumaChain Arc Testnet configuration" -ForegroundColor Cyan
Write-Host "RPC: https://rpc.testnet.arc.io"
Write-Host "Chain ID: 5042002"
Write-Host "Explorer: https://explorer.testnet.arc.io"
Write-Host ""
Write-Host "Start TumaChain with:" -ForegroundColor Green
Write-Host "  cd backend"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload"
Write-Host ""
Write-Host "Then open http://127.0.0.1:8000/ and go to Multi-Chain Wallets."
