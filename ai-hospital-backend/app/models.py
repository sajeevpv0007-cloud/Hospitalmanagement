"""
models.py
=========
SQLAlchemy ORM models for the AI-Powered Hospital Management System.
Contains tables for:
 - Patient
 - Doctor
 - Ticket
 - AgentLog
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship
import datetime
import enum

# SQLAlchemy Base class
Base = declarative_base()

# ---------------------------------------------------------------------------
# ENUM DEFINITIONS
# ---------------------------------------------------------------------------

class UrgencyEnum(str, enum.Enum):
    """Defines urgency levels for patient triage."""
    critical = "critical"
    urgent = "urgent"
    normal = "normal"


class TicketStatus(str, enum.Enum):
    """Defines various statuses in the patient workflow."""
    created = "created"
    triage_done = "triage_done"
    diagnostics_ordered = "diagnostics_ordered"
    physician_review = "physician_review"
    pharmacy = "pharmacy"
    billing = "billing"
    discharged = "discharged"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# TABLE DEFINITIONS
# ---------------------------------------------------------------------------

class Patient(Base):
    """Stores patient demographic and symptom data."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    symptoms = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Doctor(Base):
    """Stores doctor profile and workload limits."""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    max_patients = Column(Integer, default=5)
    pushover_user = Column(String, nullable=True)


class Ticket(Base):
    """Tracks patient workflow, doctor assignment, and urgency."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    status = Column(Enum(TicketStatus), default=TicketStatus.created)
    urgency = Column(Enum(UrgencyEnum), default=UrgencyEnum.normal)
    priority_score = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    patient = relationship("Patient")
    doctor = relationship("Doctor")


class AgentLog(Base):
    """Stores AI agent outputs for each ticket stage."""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    agent_name = Column(String)
    stage = Column(String)
    structured_output = Column(Text)  # typically JSON
    raw_message = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    ticket = relationship("Ticket")
