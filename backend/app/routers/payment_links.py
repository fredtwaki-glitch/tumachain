import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import io
import qrcode
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.payment_request import PaymentRequest
from app.models.user import User
from app.schemas.payment_request import PaymentRequestCreate, PaymentRequestOut
from app.security.dependencies import get_current_user
from app.models.enums import Network
from app.schemas.payment import PaymentOut
from app.services.payment_processing import create_and_process_payment, InsufficientBalanceError, PaymentValidationError

router = APIRouter(prefix="/api/v1/payment-links", tags=["payment-links"])
@router.post("", response_model=PaymentRequestOut)
def create_link(payload: PaymentRequestCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code=secrets.token_urlsafe(6).replace("-","").replace("_","")
    row=PaymentRequest(code=code,creator_id=current_user.id,amount=payload.amount,asset=payload.asset,description=payload.description,expires_at=datetime.now(timezone.utc)+timedelta(days=payload.expires_days))
    db.add(row); db.commit(); db.refresh(row); return row
@router.get("/{code}", response_model=PaymentRequestOut)
def get_link(code: str, db: Session = Depends(get_db)):
    row=db.query(PaymentRequest).filter(PaymentRequest.code==code).first()
    if not row: raise HTTPException(404,"Payment request not found")
    if row.expires_at and row.expires_at < datetime.now(timezone.utc): row.status="EXPIRED"; db.commit()
    return row

@router.get("/{code}/qr")
def payment_link_qr(code: str, db: Session = Depends(get_db)):
    row=db.query(PaymentRequest).filter(PaymentRequest.code==code).first()
    if not row: raise HTTPException(404,"Payment request not found")
    img=qrcode.make(f"tuma://pay/{code}")
    buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control":"public, max-age=300"})

class PaymentLinkPayRequest(__import__("pydantic", fromlist=["BaseModel"]).BaseModel):
    network: Network = Network.ARC_TESTNET
    idempotency_key: str | None = None

@router.post("/{code}/pay", response_model=PaymentOut)
def pay_link(code: str, payload: PaymentLinkPayRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row=db.query(PaymentRequest).filter(PaymentRequest.code==code).first()
    if not row: raise HTTPException(404,"Payment request not found")
    if row.expires_at and row.expires_at < datetime.now(timezone.utc):
        row.status="EXPIRED"; db.commit(); raise HTTPException(400,"Payment request has expired")
    if row.status != "OPEN": raise HTTPException(400,"Payment request is not open")
    try:
        payment=create_and_process_payment(db,current_user,row.creator.email,row.creator_id,__import__("app.models.enums",fromlist=["Asset"]).Asset(row.asset),payload.network,row.amount,None,payload.idempotency_key)
    except (InsufficientBalanceError,PaymentValidationError) as e:
        raise HTTPException(400,str(e))
    return payment
