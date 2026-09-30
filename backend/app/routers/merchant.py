import csv
import hashlib
import io
import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, AnyHttpUrl
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.merchant import ApiCredential, WebhookEndpoint
from app.models.payment import Payment
from app.models.settlement import Settlement
from app.models.payment_request import PaymentRequest
from app.security.dependencies import get_current_user
from app.services.audit_service import write_audit_log

router=APIRouter(prefix="/api/v1/merchant",tags=["merchant"])
def h(v): return hashlib.sha256(v.encode()).hexdigest()

class ApiKeyRequest(BaseModel): name: str = "Default"
class WebhookRequest(BaseModel): url: AnyHttpUrl

@router.get("/summary")
def summary(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    sent=db.query(Payment).filter(Payment.sender_id==current_user.id).all()
    links=db.query(PaymentRequest).filter(PaymentRequest.creator_id==current_user.id).count()
    settlements=db.query(Settlement).filter(Settlement.user_id==current_user.id).all()
    return {"total_received":0,"pending":sum(1 for p in sent if p.status.value in {"PENDING","CREATED"}),"completed":sum(1 for p in sent if p.status.value=="COMPLETED"),"failed":sum(1 for p in sent if p.status.value=="FAILED"),"settlement_balance":"0","payment_links":links,"settlements":len(settlements),"environment":"testnet"}

@router.post("/api-keys")
def create_api_key(payload:ApiKeyRequest,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    raw="tuma_"+secrets.token_urlsafe(24)
    row=ApiCredential(user_id=current_user.id,name=payload.name,key_prefix=raw[:12],key_hash=h(raw))
    db.add(row); db.commit(); db.refresh(row)
    write_audit_log(db,"MERCHANT_API_KEY_CREATED","api_credential",row.id,current_user.id,"Secret returned once")
    return {"id":row.id,"name":payload.name,"key":raw,"warning":"Store this key securely. It is shown only once."}

@router.get("/api-keys")
def list_api_keys(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return [{"id":r.id,"name":r.name,"key_prefix":r.key_prefix,"active":r.active,"created_at":r.created_at} for r in db.query(ApiCredential).filter(ApiCredential.user_id==current_user.id).all()]

@router.post("/webhooks")
def create_webhook(payload:WebhookRequest,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    secret="whsec_"+secrets.token_urlsafe(20)
    row=WebhookEndpoint(user_id=current_user.id,url=str(payload.url),secret_hash=h(secret))
    db.add(row); db.commit(); db.refresh(row)
    write_audit_log(db,"MERCHANT_WEBHOOK_CREATED","webhook",row.id,current_user.id,"Secret returned once")
    return {"id":row.id,"url":row.url,"secret":secret,"warning":"Store this secret securely. It is shown only once."}

@router.get("/webhooks")
def list_webhooks(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return [{"id":r.id,"url":r.url,"active":r.active,"created_at":r.created_at} for r in db.query(WebhookEndpoint).filter(WebhookEndpoint.user_id==current_user.id).all()]

@router.get("/payments")
def merchant_payments(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return db.query(Payment).filter(Payment.sender_id==current_user.id).order_by(Payment.created_at.desc()).all()

@router.get("/settlements")
def merchant_settlements(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return db.query(Settlement).filter(Settlement.user_id==current_user.id).order_by(Settlement.created_at.desc()).all()

@router.get("/export.csv")
def export_payments(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.query(Payment).filter(Payment.sender_id==current_user.id).order_by(Payment.created_at.desc()).all()
    buf=io.StringIO(); w=csv.writer(buf); w.writerow(["payment_id","recipient","amount","asset","network","status","environment","created_at"])
    for p in rows: w.writerow([p.id,p.recipient_identifier or p.recipient_email,p.amount,p.asset.value,p.network.value,p.status.value,p.environment,p.created_at.isoformat() if p.created_at else ""])
    return StreamingResponse(iter([buf.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=tumachain-payments.csv"})
