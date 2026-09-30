from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
