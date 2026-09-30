from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentOut
from app.security.dependencies import get_current_user
router=APIRouter(prefix="/api/v1/payments",tags=["payments"])
@router.get("/{payment_id}",response_model=PaymentOut)
def get_payment_v1(payment_id:str,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=db.query(Payment).filter(Payment.id==payment_id).first()
    if not row: raise HTTPException(404,"Payment not found")
    if row.sender_id!=current_user.id and row.recipient_email!=current_user.email: raise HTTPException(403,"Not authorized")
    return row
