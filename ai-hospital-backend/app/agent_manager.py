"""
agent_manager.py
=================
This module handles the core workflow orchestration logic:
 - Starts patient workflow (reception + triage)
 - Pushes tickets into a priority queue
 - Background allocation worker assigns patients to doctors
"""

import asyncio
import json
import heapq
from typing import Optional
from .agents import make_agent
from .db import SessionLocal
from .models import (
    Patient, Ticket, Doctor, AgentLog,
    UrgencyEnum, TicketStatus
)
from .notifications import send_pushover, broadcast_to_doctor

# ---------------------------------------------------------------------------
# PRIORITY QUEUE IMPLEMENTATION
# ---------------------------------------------------------------------------

class PriorityQueue:
    """
    Async-safe priority queue to manage patient tickets.
    Lower priority number = higher urgency.
    """
    def __init__(self):
        self._heap = []      # heap of (priority, counter, ticket_id)
        self._counter = 0
        self._lock = asyncio.Lock()

    async def put(self, priority: int, ticket_id: int):
        async with self._lock:
            self._counter += 1
            heapq.heappush(self._heap, (priority, self._counter, ticket_id))
            print(f"🧾 Ticket {ticket_id} added to queue with priority {priority}")

    async def get(self) -> Optional[int]:
        async with self._lock:
            if not self._heap:
                return None
            priority, _, ticket_id = heapq.heappop(self._heap)
            print(f"🎯 Popped ticket {ticket_id} (priority {priority}) for allocation")
            return ticket_id

    async def empty(self):
        async with self._lock:
            return len(self._heap) == 0


# Global queue instance
queue = PriorityQueue()

# ---------------------------------------------------------------------------
# DOCTOR ALLOCATION LOGIC
# ---------------------------------------------------------------------------

def find_available_doctor(db) -> Optional[Doctor]:
    """
    Return first doctor with fewer than max_patients active.
    """
    doctors = db.query(Doctor).all()
    for d in doctors:
        active = db.query(Ticket).filter(
            Ticket.doctor_id == d.id,
            Ticket.status != TicketStatus.discharged
        ).count()
        if active < (d.max_patients or 5):
            return d
    return None


async def allocation_worker():
    """
    Background worker that:
     1. Pops tickets from priority queue
     2. Finds an available doctor
     3. Assigns ticket
     4. Sends push + websocket notification
    """
    print("⚙️ Allocation worker started...")
    while True:
        ticket_id = await queue.get()
        if ticket_id is None:
            await asyncio.sleep(0.5)
            continue

        db = SessionLocal()
        try:
            ticket = db.query(Ticket).get(ticket_id)
            if not ticket:
                continue
            if ticket.doctor_id:
                continue

            doctor = find_available_doctor(db)
            if not doctor:
                # No available doctors — retry later
                print("⏳ No doctors available, requeueing ticket...")
                await queue.put(ticket.priority_score + 5, ticket.id)
                await asyncio.sleep(2)
                continue

            ticket.doctor_id = doctor.id
            db.add(ticket)
            db.commit()

            # Create log
            log = AgentLog(
                ticket_id=ticket.id,
                agent_name="allocator",
                stage="allocation",
                structured_output=json.dumps({"doctor_id": doctor.id}),
                raw_message=f"Assigned to doctor {doctor.name}"
            )
            db.add(log)
            db.commit()

            print(f"✅ Ticket {ticket.id} assigned to Doctor {doctor.name} (ID: {doctor.id})")

            # Send notification
            send_pushover(
                user_key=doctor.pushover_user,
                title="New Patient Assigned",
                message=f"Ticket {ticket.id} assigned to you"
            )

            # WebSocket broadcast
            try:
                await broadcast_to_doctor(doctor.id, {
                    "event": "ticket_assigned",
                    "ticket_id": ticket.id
                })
            except Exception:
                pass
        finally:
            db.close()

        await asyncio.sleep(0.3)


# ---------------------------------------------------------------------------
# PATIENT WORKFLOW START (Reception + Triage)
# ---------------------------------------------------------------------------

async def start_patient_workflow(name: str, age: int = None, symptoms: str = None) -> int:
    """
    Starts a new patient workflow.
    Steps:
      1. Create patient & ticket records
      2. Run Reception agent
      3. Run Triage agent (sets urgency)
      4. Add ticket to allocation queue
    """
    db = SessionLocal()
    try:
        # 1️⃣ Create patient record
        patient = Patient(name=name, age=age, symptoms=symptoms)
        db.add(patient)
        db.commit()
        db.refresh(patient)

        # 2️⃣ Create ticket
        ticket = Ticket(
            patient_id=patient.id,
            status=TicketStatus.created,
            urgency=UrgencyEnum.normal,
            priority_score=50
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # 3️⃣ Reception agent (mock)
        reception_agent = make_agent("reception")
        reception_prompt = f"Register patient: {name}, age {age}, symptoms: {symptoms}"
        reception_response = await reception_agent.send(reception_prompt)
        db.add(AgentLog(
            ticket_id=ticket.id,
            agent_name="reception",
            stage="reception",
            structured_output=reception_response,
            raw_message=reception_response
        ))
        db.commit()
        print(f"📋 Reception completed for {name}")

        # 4️⃣ Triage agent
        triage_agent = make_agent("triage")
        triage_prompt = f"Patient info: {reception_response}. Return JSON {{urgency, score, recommended_tests}}"
        triage_response = await triage_agent.send(triage_prompt)

        # Parse JSON
        try:
            triage_json = json.loads(triage_response)
        except Exception:
            triage_json = {"urgency": "normal", "score": 50, "recommended_tests": []}

        urgency = triage_json.get("urgency", "normal")
        score = int(triage_json.get("score", 50))

        ticket.urgency = UrgencyEnum(urgency) if urgency in [e.value for e in UrgencyEnum] else UrgencyEnum.normal
        ticket.priority_score = max(0, 100 - score)
        ticket.status = TicketStatus.triage_done
        db.add(ticket)
        db.commit()

        db.add(AgentLog(
            ticket_id=ticket.id,
            agent_name="triage",
            stage="triage",
            structured_output=json.dumps(triage_json),
            raw_message=triage_response
        ))
        db.commit()

        print(f"🩺 Triage done: urgency={urgency}, priority={ticket.priority_score}")

        # 5️⃣ Push to allocation queue
        await queue.put(ticket.priority_score, ticket.id)
        return ticket.id

    finally:
        db.close()
