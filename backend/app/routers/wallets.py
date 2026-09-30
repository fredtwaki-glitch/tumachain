from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.ledger_balance import FaucetRequest
from app.schemas.wallet import WalletOut
from app.security.dependencies import get_current_user
from app.services.wallet_service import faucet_credit

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("", response_model=List[WalletOut])
def list_my_wallets(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Wallet).filter(Wallet.user_id == current_user.id).all()


@router.post("/faucet", response_model=WalletOut)
def faucet(
    payload: FaucetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    TESTNET-ONLY faucet: credits mock balance to the caller's own wallet
    so payment/withdrawal flows can be exercised. Never available for
    real funds — this endpoint has no production equivalent.
    """
    try:
        return faucet_credit(db, current_user, payload.network, payload.amount)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
