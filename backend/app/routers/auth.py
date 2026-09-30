import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Network, VerificationState
from app.models.user import User
from app.schemas.user import EmailVerifyRequest, RefreshRequest, Token, UserLogin, UserOut, UserRegister
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, create_refresh_token, decode_token
from app.services.email_service import email_service
from app.services.wallet_service import create_wallets_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if payload.username and db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        username=payload.username.lower() if payload.username else None,
        phone_number=payload.phone_number,
        verification_state=VerificationState.UNVERIFIED,
        email_verification_token=secrets.token_urlsafe(24),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a wallet record on every supported network up front.
    create_wallets_for_user(db, user)

    email_service.send_verification_email(user.email, user.email_verification_token)

    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/verify-email", response_model=UserOut)
def verify_email(payload: EmailVerifyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verification_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    from datetime import datetime, timezone

    user.verification_state = VerificationState.EMAIL_VERIFIED
    user.email_verification_token = None
    user.email_verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


@router.post("/refresh", response_model=Token)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Rotates a refresh token for a new access + refresh token pair.
    Note: this implementation does not maintain a server-side revocation
    list, so an old refresh token remains cryptographically valid until
    it expires even after rotation — a production build would track
    issued/blacklisted refresh tokens to close that gap.
    """
    token_payload = decode_token(payload.refresh_token)
    if token_payload is None or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    user_id = token_payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=new_refresh_token)
