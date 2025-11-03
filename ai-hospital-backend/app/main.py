"""
main.py
========
This is the FastAPI entry point for the AI-Powered Hospital Management System.
It:
 - Initializes the database.
 - Seeds default doctors if none exist.
 - Starts the background allocation worker.
 - Exposes REST API endpoints for patients, doctors, and tickets.
 - Handles WebSocket connections for real-time doctor notifications.
"""

import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db, SessionLocal
from .models import Base, Ticket, Doctor
from .schemas import StartRequest
from .agent_manager import start_patient_workflow, allocation_worker
from .notifications import register_ws, unregister_ws

# ---------------------------------------------------------------------------
# APP INITIALIZATION
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Hospital Backend", version="1.0")

# Allow Angular frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# APP STARTUP EVENT
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Called when FastAPI starts.
    Initializes the database, seeds doctors, and starts background workers.
    """
    print("🚀 Starting AI Hospital Backend...")
    init_db(Base)  # Create tables if missing

    db = SessionLocal()

    # Check if doctors already exist
    doctor_count = db.query(Doctor).count()
    if doctor_count == 0:
        print("🩺 No doctors found. Seeding default doctors...")
        doctors = [
            Doctor(name="Dr. Alice", specialty="General Medicine", max_patients=5),
            Doctor(name="Dr. Bob", specialty="Cardiology", max_patients=5),
            Doctor(name="Dr. Clara", specialty="Neurology", max_patients=5),
            Doctor(name="Dr. Daniel", specialty="Orthopedics", max_patients=5),
            Doctor(name="Dr. Emma", specialty="Dermatology", max_patients=5),
            Doctor(name="Dr. Frank", specialty="Pediatrics", max_patients=5),
            Doctor(name="Dr. Grace", specialty="Ophthalmology", max_patients=5),
            Doctor(name="Dr. Henry", specialty="Psychiatry", max_patients=5),
            Doctor(name="Dr. Ivy", specialty="Gynecology", max_patients=5),
            Doctor(name="Dr. Jack", specialty="Radiology", max_patients=5),
        ]
        db.add_all(doctors)
        db.commit()
        print("✅ Default doctors have been seeded.")
    else:
        print(f"🩻 {doctor_count} doctors already exist in the system.")

    db.close()

    # Start the background patient allocation worker
    asyncio.create_task(allocation_worker())
    print("⚙️ Allocation worker started...")


# ---------------------------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------------------------

@app.post("/api/patients/start")
async def api_start_patient(req: StartRequest):
    """
    Start a new patient workflow.

    - Creates a patient record
    - Runs reception & triage agents
    - Adds ticket to priority queue
    - Returns generated ticket ID
    """
    ticket_id = await start_patient_workflow(req.name, req.age, req.symptoms)
    return {"ticket_id": ticket_id, "message": "Workflow started successfully"}


@app.get("/api/tickets/{ticket_id}")
async def api_get_ticket(ticket_id: int):
    """
    Get a specific ticket's status and assignment.
    """
    db = SessionLocal()
    try:
        # ✅ Use new SQLAlchemy 2.x API
        ticket = db.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return {
            "id": ticket.id,
            "status": ticket.status.value,
            "urgency": ticket.urgency.value,
            "patient": {
                "id": ticket.patient.id,
                "name": ticket.patient.name,
                "symptoms": ticket.patient.symptoms,
            },
            "doctor_id": ticket.doctor_id,
        }
    finally:
        db.close()


@app.get("/api/doctor/{doctor_id}/tickets")
async def api_get_doctor_tickets(doctor_id: int):
    """
    Get all tickets assigned to a specific doctor (for doctor dashboard).
    """
    db = SessionLocal()
    try:
        # Check if doctor exists
        doctor = db.get(Doctor, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        tickets = db.query(Ticket).filter(Ticket.doctor_id == doctor_id).all()
        return [
            {
                "id": t.id,
                "status": t.status.value,
                "urgency": t.urgency.value,
                "patient": t.patient.name,
            }
            for t in tickets
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# WEBSOCKET ENDPOINT
# ---------------------------------------------------------------------------

@app.websocket("/ws/doctor/{doctor_id}")
async def websocket_doctor(ws: WebSocket, doctor_id: int):
    """
    WebSocket endpoint for real-time notifications.
    Doctors connect here to receive patient assignment updates.
    """
    await ws.accept()
    register_ws(doctor_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        unregister_ws(doctor_id, ws)
        print(f"Doctor {doctor_id} disconnected from WebSocket.")


# ---------------------------------------------------------------------------
# ROOT ENDPOINT
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Basic health check endpoint."""
    return {"message": "AI Hospital Backend is running!"}
