from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.kyc_submission import KycSubmission
from app.models.user import User
from app.schemas.kyc import KycOut, KycSubmit
from app.security.dependencies import get_current_user
from app.services.kyc_service import KycValidationError, submit_kyc

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/submit", response_model=KycOut, status_code=status.HTTP_201_CREATED)
def submit_kyc_endpoint(
    payload: KycSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return submit_kyc(
            db=db,
            user=current_user,
            full_name=payload.full_name,
            country=payload.country,
            document_type=payload.document_type,
            document_reference=payload.document_reference,
        )
    except KycValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/mine", response_model=List[KycOut])
def list_my_kyc_submissions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(KycSubmission).filter(KycSubmission.user_id == current_user.id).all()
