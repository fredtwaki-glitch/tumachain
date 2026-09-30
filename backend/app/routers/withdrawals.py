from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.withdrawal import Withdrawal
from app.schemas.withdrawal import WithdrawalCreate, WithdrawalOut
from app.security.dependencies import get_current_user
from app.services.withdrawal_processing import (
    InsufficientLedgerBalanceError,
    WithdrawalValidationError,
    request_withdrawal,
)

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])


@router.post("", response_model=WithdrawalOut, status_code=status.HTTP_201_CREATED)
def create_withdrawal(
    payload: WithdrawalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return request_withdrawal(
            db=db,
            user=current_user,
            asset=payload.asset,
            destination_network=payload.destination_network,
            destination_address=payload.destination_address,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
        )
    except InsufficientLedgerBalanceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except WithdrawalValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[WithdrawalOut])
def list_my_withdrawals(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Withdrawal).filter(Withdrawal.user_id == current_user.id).all()


@router.get("/{withdrawal_id}", response_model=WithdrawalOut)
def get_withdrawal(
    withdrawal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")
    if withdrawal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return withdrawal
