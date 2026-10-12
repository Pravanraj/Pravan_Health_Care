"""Analytics API router serving operational KPIs, admission trends, and readmission patterns."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User
from src.services.analytics_service import AnalyticsService
from src.api.dependencies import require_any_authenticated

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])


@router.get("/summary-kpis")
def get_kpis(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Retrieve operational KPIs (total volume, 30d readmission rate, avg LOS, mortality)."""
    return AnalyticsService.get_summary_kpis(db)


@router.get("/admissions-trend")
def get_admissions_trend(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Retrieve historical admissions, 30-day readmissions, and average LOS by month."""
    return AnalyticsService.get_admissions_trend(db)


@router.get("/los-analysis")
def get_los_analysis(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Analyze Length of Stay distributions across patient age brackets and admission types."""
    return AnalyticsService.get_los_by_cohort(db)


@router.get("/readmission-by-category")
def get_readmission_categories(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Retrieve 30-day readmission percentages by primary diagnosis category and admission type."""
    return AnalyticsService.get_readmission_by_category(db)


@router.get("/medication-impact")
def get_medication_impact(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Analyze association between insulin dosage adjustments and 30-day readmissions."""
    return AnalyticsService.get_medication_impact(db)
