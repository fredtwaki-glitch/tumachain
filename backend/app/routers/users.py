from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.user import UserOut
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user
