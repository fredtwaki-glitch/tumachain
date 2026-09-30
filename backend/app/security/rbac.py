from fastapi import Depends, HTTPException, status

from app.models.enums import UserRole
from app.models.user import User
from app.security.dependencies import get_current_user


def require_roles(*allowed_roles: UserRole):
    """
    Returns a FastAPI dependency that only allows through users whose
    role is in `allowed_roles`. Used to gate admin/compliance endpoints.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return dependency


require_admin = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_compliance = require_roles(
    UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN, UserRole.SUPER_ADMIN
)
