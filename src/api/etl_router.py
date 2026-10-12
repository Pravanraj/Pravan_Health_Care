"""ETL Pipeline trigger and audit inspection API router."""

import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
import pandas as pd
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User, ETLBatch, AuditLog
from src.etl.pipeline import HealthcareETLPipeline
from src.api.dependencies import require_admin

router = APIRouter(prefix="/etl", tags=["ETL Ingestion & Auditing"])


@router.post("/incremental")
def upload_incremental_batch(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Upload and ingest an incremental CSV batch of clinical encounter records."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a CSV file",
        )

    try:
        content = file.file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(e)}",
        )

    pipeline = HealthcareETLPipeline(db)
    result = pipeline.run_pipeline(
        data_source=df,
        batch_type="INCREMENTAL",
    )
    result["source_filename"] = file.filename
    return result


@router.get("/history")
def get_etl_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Retrieve historical ETL batch executions and data quality scores."""
    batches = db.query(ETLBatch).order_by(ETLBatch.created_at.desc()).limit(limit).all()
    return batches


@router.get("/audit-logs")
def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    entity_name: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Query system mutation audit logs with optional action/entity filters."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if entity_name:
        query = query.filter(AuditLog.entity_name == entity_name.lower())

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs
