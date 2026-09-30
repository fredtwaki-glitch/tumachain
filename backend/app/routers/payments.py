from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut
from app.security.dependencies import get_current_user
from app.services.notification_service import notification_service
from app.services.payment_processing import (
    InsufficientBalanceError,
    PaymentValidationError,
    create_and_process_payment,
    retry_payment,
)
from app.services.wallet_service import SUPPORTED_NETWORKS

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.network not in SUPPORTED_NETWORKS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported network"
        )

    if payload.idempotency_key:
        existing = (
            db.query(Payment)
            .filter(Payment.idempotency_key == payload.idempotency_key)
            .first()
        )
        if existing:
            return existing

    identifier = payload.recipient_identifier or payload.recipient_email
    if not identifier:
        raise HTTPException(status_code=400, detail="Recipient identifier is required")
    recipient = None
    if "@" in identifier:
        recipient = db.query(User).filter(User.email == identifier.lower()).first()
    if not recipient:
        recipient = db.query(User).filter(User.username == identifier.lstrip("@")).first()
    if not recipient:
        recipient = db.query(User).filter(User.phone_number == identifier).first()

    try:
        payment = create_and_process_payment(
            db=db,
            sender=current_user,
            recipient_email=recipient.email if recipient else (payload.recipient_email or ""),
            recipient_id=recipient.id if recipient else None,
            asset=payload.asset,
            network=payload.network,
            amount=payload.amount,
            settlement_asset=payload.settlement_asset,
            idempotency_key=payload.idempotency_key,
        )
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PaymentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if payment.recipient_email:
        notification_service.payment_received(
            payment.recipient_email, str(payment.final_amount or payment.amount), payment.asset.value
        )

    return payment


@router.get("/sent", response_model=List[PaymentOut])
def list_sent_payments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Payment).filter(Payment.sender_id == current_user.id).all()


@router.get("/received", response_model=List[PaymentOut])
def list_received_payments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Payment).filter(Payment.recipient_email == current_user.email).all()


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.sender_id != current_user.id and payment.recipient_email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return payment


@router.post("/{payment_id}/retry", response_model=PaymentOut)
def retry_failed_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.sender_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        return retry_payment(db, payment)
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PaymentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
