from fastapi import APIRouter

from app.models.enums import Asset, Network

router = APIRouter(prefix="/networks", tags=["networks"])


@router.get("")
def list_supported_networks():
    return {
        "networks": [n.value for n in Network],
        "assets": [a.value for a in Asset],
    }
