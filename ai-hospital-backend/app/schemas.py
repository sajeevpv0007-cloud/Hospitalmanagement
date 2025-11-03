"""
schemas.py
==========
Pydantic models used for validating incoming requests and
structuring outgoing API responses.
"""

from pydantic import BaseModel
from typing import Optional, List


class StartRequest(BaseModel):
    """Request body for starting a patient workflow."""
    name: str
    age: Optional[int] = None
    symptoms: Optional[str] = None


class TicketResponse(BaseModel):
    """Response model for a ticket."""
    id: int
    status: str
    urgency: str
    patient: dict
    doctor_id: Optional[int] = None


class DoctorTicketsResponse(BaseModel):
    """Response model for tickets assigned to a doctor."""
    tickets: List[dict]
