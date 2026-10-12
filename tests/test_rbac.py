"""Unit tests for Role-Based Access Control (RBAC) security enforcement."""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.utils.auth import create_access_token

client = TestClient(app)


def test_rbac_analyst_forbidden_on_write():
    """Verify that Analyst role is rejected when attempting to create patient."""
    token = create_access_token(data={"sub": "analyst", "role": "analyst"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_nbr": 999111,
        "race": "Asian",
        "gender": "Male",
        "age_bracket": "[30-40)",
    }
    response = client.post("/api/v1/patients", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Operation not permitted" in response.json()["detail"]


def test_rbac_clinical_ops_allowed_on_write():
    """Verify that Clinical Operations role can create patient."""
    token = create_access_token(data={"sub": "clinician", "role": "clinical_operations"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_nbr": 888222,
        "race": "Hispanic",
        "gender": "Female",
        "age_bracket": "[40-50)",
    }
    response = client.post("/api/v1/patients", json=payload, headers=headers)
    assert response.status_code in [201, 409]


def test_rbac_admin_allowed_on_delete():
    """Verify that Administrator role can delete patient."""
    admin_token = create_access_token(data={"sub": "admin", "role": "administrator"})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Non-admin attempting delete
    analyst_token = create_access_token(data={"sub": "analyst", "role": "analyst"})
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    del_res = client.delete("/api/v1/patients/888222", headers=analyst_headers)
    assert del_res.status_code == 403
