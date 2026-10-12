"""Reporting and Data Export API router."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User
from src.services.report_service import ReportService
from src.api.dependencies import require_any_authenticated

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("/export/csv")
def export_csv(
    limit: int = Query(5000, ge=10, le=50000),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Download filtered healthcare encounters formatted as a CSV spreadsheet."""
    csv_stream = ReportService.export_to_csv(db, limit=limit)
    return StreamingResponse(
        csv_stream,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=healthcare_encounters_export.csv"},
    )


@router.get("/export/excel")
def export_excel(
    limit: int = Query(5000, ge=10, le=50000),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Download filtered healthcare encounters formatted as an Excel (.xlsx) workbook."""
    excel_stream = ReportService.export_to_excel(db, limit=limit)
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=healthcare_encounters_export.xlsx"},
    )


@router.get("/executive-summary")
def get_executive_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Generate scheduled executive operational overview for hospital leadership."""
    return ReportService.generate_executive_summary_report(db)
