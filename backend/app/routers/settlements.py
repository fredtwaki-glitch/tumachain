from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.settlement import Settlement
from app.schemas.settlement import SettlementQuoteRequest, SettlementQuoteOut
from app.security.dependencies import get_current_user
from app.services.settlement_service import settlement_provider

router=APIRouter(prefix="/api/v1/settlements",tags=["settlements"])

@router.post("/quote",response_model=SettlementQuoteOut)
def quote(payload:SettlementQuoteRequest,current_user:User=Depends(get_current_user)):
    q=settlement_provider.create_quote(payload.amount,payload.asset,payload.destination_method,payload.destination_currency)
    return SettlementQuoteOut(amount=q.amount,asset=q.asset,destination_method=q.destination_method,destination_currency=q.destination_currency,fee=q.fee,total=q.total,provider=q.provider,environment=q.environment)

@router.post("")
def create_settlement(payload:SettlementQuoteRequest,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    q=settlement_provider.create_quote(payload.amount,payload.asset,payload.destination_method,payload.destination_currency)
    row=Settlement(user_id=current_user.id,provider=q.provider,source_asset=q.asset,destination_method=q.destination_method,destination_currency=q.destination_currency,amount=q.amount,fee=q.fee,status="PENDING",environment=q.environment)
    db.add(row); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"environment":row.environment,"provider":row.provider,"message":"Testnet/simulation only; no real-world settlement was executed."}

@router.get("/{settlement_id}")
def get_settlement(settlement_id:str,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=db.query(Settlement).filter(Settlement.id==settlement_id,Settlement.user_id==current_user.id).first()
    if not row: raise HTTPException(404,"Settlement not found")
    return row
