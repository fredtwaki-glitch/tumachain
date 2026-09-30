from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.identity import IdentityResolveRequest, IdentityResolveOut
from fastapi.responses import StreamingResponse
import io
import qrcode

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])
@router.post("/resolve", response_model=IdentityResolveOut)
def resolve_identity(payload: IdentityResolveRequest, db: Session = Depends(get_db)):
    ident = payload.identifier.strip()
    q = db.query(User)
    user = None
    if "@" in ident:
        user = q.filter(User.email == ident.lower()).first()
    if not user:
        user = q.filter(User.username == ident.lstrip("@")).first()
    if not user:
        user = q.filter(User.phone_number == ident).first()
    if not user:
        return IdentityResolveOut(found=False)
    wallets = db.query(Wallet).filter(Wallet.user_id == user.id).all()
    preferred = next((w for w in wallets if w.network.value == "EVM_TESTNET"), None)
    return IdentityResolveOut(found=True, user_id=user.id, display_name=user.full_name or user.username or user.email.split("@")[0], preferred_asset="USDC", preferred_chain=preferred.network.value if preferred else None, wallet_available=bool(wallets), settlement_options=["wallet","stablecoin","local_currency"])

@router.get("/qr")
def identity_qr(current_user: User = Depends(__import__("app.security.dependencies", fromlist=["get_current_user"]).get_current_user)):
    if not current_user.username:
        raise HTTPException(400, "Set a TumaChain username before generating an identity QR")
    img=qrcode.make(f"tuma://user/{current_user.username}")
    buf=io.BytesIO(); img.save(buf,format="PNG"); buf.seek(0)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control":"private, max-age=300"})
