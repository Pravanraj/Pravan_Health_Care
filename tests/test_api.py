"""Integration tests for FastAPI REST Endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.database.connection import init_db

# Initialize database
init_db()
client = TestClient(app)


def test_health_check():
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Verify root endpoint metadata."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Healthcare Patient Management System" in response.json()["system"]


def test_analytics_endpoints():
    """Verify summary KPIs endpoint returns expected structure."""
    response = client.get("/api/v1/analytics/summary-kpis")
    assert response.status_code == 200
    data = response.json()
    assert "total_encounters" in data
    assert "total_patients" in data
    assert "readmission_rate_30d_pct" in data


def test_patients_crud_and_pagination():
    """Verify patient creation, retrieval, and search."""
    # Create patient
    new_pat = {
        "patient_nbr": 777001,
        "race": "Caucasian",
        "gender": "Female",
        "age_bracket": "[60-70)",
    }
    create_res = client.post("/api/v1/patients", json=new_pat)
    assert create_res.status_code in [201, 409]

    # Fetch patient
    get_res = client.get("/api/v1/patients/777001")
    assert get_res.status_code == 200
    assert get_res.json()["race"] == "Caucasian"

    # Search patients
    search_res = client.get("/api/v1/patients?search=777001")
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1
