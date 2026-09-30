from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ledger_balance import LedgerBalance
from app.models.user import User
from app.schemas.ledger_balance import LedgerBalanceOut
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/balances", tags=["balances"])


@router.get("", response_model=List[LedgerBalanceOut])
def list_my_balances(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    The current user's internal, off-chain available balances per
    asset — what payments settle into and what withdrawals draw from.
    """
    return db.query(LedgerBalance).filter(LedgerBalance.user_id == current_user.id).all()
