from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.enums import Asset, Network
from app.models.user import User
from app.security.dependencies import get_current_user
from app.services.routing_service import route_payment, RoutingError

class QuoteIn(BaseModel):
    recipient: str
    amount: Decimal = Field(gt=0)
    asset: Asset = Asset.USDC
    source_chain: Network
class QuoteOut(BaseModel):
    recipient:str; amount:Decimal; asset:Asset; source_chain:Network; destination_chain:Network|None; estimated_fee:Decimal; estimated_total:Decimal; estimated_time_seconds:int; route_status:str; environment:str
router=APIRouter(prefix="/api/v1/payments",tags=["payments"])
@router.post("/quote",response_model=QuoteOut)
def quote(payload:QuoteIn,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    try: r=route_payment(payload.asset,payload.source_chain,payload.amount,payload.asset)
    except RoutingError as e: raise HTTPException(400,str(e))
    return QuoteOut(recipient=payload.recipient,amount=payload.amount,asset=payload.asset,source_chain=payload.source_chain,destination_chain=payload.source_chain,estimated_fee=r.network_fee+r.platform_fee,estimated_total=payload.amount+r.network_fee+r.platform_fee,estimated_time_seconds=30,route_status="available_testnet_simulation",environment="testnet")
