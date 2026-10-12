"""Structured logging configuration and database audit logging helpers."""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.database.models import AuditLog

# Configure application-wide logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("healthcare_system")


def log_audit_event(
    db: Session,
    username: str,
    action: str,
    entity_name: str,
    entity_id: str,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
) -> AuditLog:
    """Record an audit trail entry into the audit_logs table."""
    details_str = json.dumps(details or {})
    audit = AuditLog(
        user_id=user_id,
        username=username or "system",
        action=action.upper(),
        entity_name=entity_name.lower(),
        entity_id=str(entity_id),
        details_json=details_str,
        timestamp=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    logger.info(f"AUDIT: [{username}] {action} {entity_name} id={entity_id}")
    return audit
