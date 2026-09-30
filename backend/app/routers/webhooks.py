import hashlib
import hmac
import json
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.webhook import WebhookEvent

router=APIRouter(prefix="/api/v1/webhooks",tags=["webhooks"])

@router.post("")
async def receive_provider_webhook(request:Request,x_webhook_signature:str=Header(...),x_webhook_id:str|None=Header(default=None),db:Session=Depends(get_db)):
    if not settings.webhook_secret:
        raise HTTPException(503,"Webhook verification secret is not configured")
    body=await request.body()
    expected=hmac.new(settings.webhook_secret.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,x_webhook_signature):
        raise HTTPException(401,"Invalid webhook signature")
    try: payload=json.loads(body.decode() or "{}")
    except json.JSONDecodeError: raise HTTPException(400,"Invalid JSON payload")
    event_id=str(payload.get("id") or x_webhook_id or uuid.uuid4())
    if db.query(WebhookEvent).filter(WebhookEvent.event_id==event_id).first():
        return {"status":"duplicate_ignored","event_id":event_id}
    event=WebhookEvent(event_id=event_id,event_type=str(payload.get("type") or "unknown"),payload_hash=hashlib.sha256(body).hexdigest(),status="RECEIVED")
    db.add(event); db.commit(); db.refresh(event)
    return {"status":"received","event_id":event_id}
