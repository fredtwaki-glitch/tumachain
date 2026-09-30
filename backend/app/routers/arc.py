from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user import User
from app.security.dependencies import get_current_user
from app.services.arc_service import get_arc_status, get_native_usdc_balance

router = APIRouter(prefix="/arc", tags=["arc-testnet"])


@router.get("/config")
def config(current_user: User = Depends(get_current_user)):
    """Return the public Arc Testnet connection configuration."""
    from app.services.arc_service import arc_config
    return arc_config()


@router.get("/status")
def status(current_user: User = Depends(get_current_user)):
    try:
        return get_arc_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Arc Testnet RPC unavailable: {exc}") from exc


@router.get("/balance")
def balance(
    address: str = Query(..., min_length=42, max_length=42),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_native_usdc_balance(address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Arc Testnet RPC unavailable: {exc}") from exc
