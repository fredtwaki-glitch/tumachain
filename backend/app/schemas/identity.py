from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
class IdentityResolveRequest(BaseModel): identifier: str = Field(min_length=1, max_length=320)
class IdentityResolveOut(BaseModel):
    found: bool
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    preferred_asset: Optional[str] = None
    preferred_chain: Optional[str] = None
    wallet_available: bool = False
    settlement_options: List[str] = []
