"""
test_api_endpoints.py
=====================
API test cases for the AI-Powered Hospital Management System.
Tests cover:
 - Root health check
 - Patient workflow initiation
 - Ticket retrieval
 - Doctor ticket listing
 - Input validation
"""

import sys, os
# Ensure the app module is discoverable by Python when running from /tests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile
import pytest
from fastapi.testclient import TestClient

# Import application modules
from app.main import app
from app.db import init_db, SessionLocal
from app.models import Base, Doctor


# --------------------------------------------------------------------------
# FIXTURE: Create isolated test client + temporary DB
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """
    Creates a temporary SQLite database and test client.
    This ensures that tests do not modify the production data.
    """
    # Create a temporary file for the SQLite DB
    db_fd, db_path = tempfile.mkstemp()
    os.environ["HMS_DB"] = db_path

    # Initialize a clean database for testing
    init_db(Base)

    # Use FastAPI's TestClient for testing API routes
    with TestClient(app) as c:
        yield c

    # Clean up temporary database after tests
    os.close(db_fd)
    os.unlink(db_path)


# --------------------------------------------------------------------------
# TESTS
# --------------------------------------------------------------------------

def test_root_endpoint(client):
    """
    ✅ Test the root health check endpoint.
    Expected: 200 OK and "AI Hospital" message.
    """
    res = client.get("/")
    assert res.status_code == 200
    assert "AI Hospital" in res.json()["message"]


def test_start_patient_workflow(client):
    """
    ✅ Test starting a new patient workflow.
    Expected: Returns ticket_id and success message.
    """
    payload = {
        "name": "John Doe",
        "age": 45,
        "symptoms": "fever and cough"
    }
    res = client.post("/api/patients/start", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert "ticket_id" in data
    assert isinstance(data["ticket_id"], int)
    assert data["message"] == "Workflow started successfully"


def test_ticket_not_found(client):
    """
    ✅ Test requesting a non-existing ticket.
    Expected: 404 with 'Ticket not found' message.
    """
    res = client.get("/api/tickets/999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_doctor_ticket_listing(client):
    """
    ✅ Test adding a doctor manually and retrieving their tickets.
    Expected: Returns empty list or assigned tickets.
    """
    db = SessionLocal()
    doc = Doctor(name="Dr. Alice", specialty="General", max_patients=5)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()

    res = client.get(f"/api/doctor/{doc.id}/tickets")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_patient_ticket_flow(client):
    """
    ✅ Test full patient flow:
    - Create a patient
    - Retrieve ticket info
    """
    payload = {
        "name": "Jane Doe",
        "age": 30,
        "symptoms": "chest pain"
    }

    res = client.post("/api/patients/start", json=payload)
    assert res.status_code == 200
    ticket_id = res.json()["ticket_id"]

    res2 = client.get(f"/api/tickets/{ticket_id}")
    assert res2.status_code == 200

    data = res2.json()
    assert data["id"] == ticket_id
    assert "status" in data
    assert "urgency" in data
    assert "patient" in data


def test_invalid_input(client):
    """
    ✅ Test invalid input (missing name).
    Expected: 422 validation error from FastAPI.
    """
    payload = {"age": 30, "symptoms": "headache"}
    res = client.post("/api/patients/start", json=payload)
    assert res.status_code == 422
