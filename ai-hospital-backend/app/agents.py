"""
agents.py
=========
Agent factory and abstraction layer for the AI-Powered Hospital System.
This file allows the orchestrator to use either:
 - MockAssistant (for local demo)
 - Real LLM agents (for production, via AutoGen)
"""

import os
import json
from typing import Any
from .mock_llm import MockAssistant

# Use mock mode by default (set USE_REAL_AUTOGEN=true in .env for real)
USE_REAL_AUTOGEN = os.getenv("USE_REAL_AUTOGEN", "false").lower() == "true"

# Define system role prompts for clarity (used in real LLM mode)
SYSTEM_PROMPTS = {
    "reception": "You are ReceptionAgent. Register the patient and return JSON with fields: action, patient_id, message.",
    "triage": "You are TriageAgent. Given patient symptoms, return urgency (critical/urgent/normal), score 0-100, and recommended_tests as JSON.",
    "diagnostic": "You are DiagnosticAgent. Recommend diagnostic tests and expected completion time as JSON.",
    "physician": "You are PhysicianAgent. Provide diagnosis, treatment plan, and prescriptions as JSON.",
    "pharmacy": "You are PharmacyAgent. Validate prescription availability and return JSON.",
    "billing": "You are BillingAgent. Produce an estimated cost breakdown in JSON.",
}


class AssistantInterface:
    """
    Generic assistant interface used by orchestrator.

    This interface wraps either:
      - MockAssistant (for local, no API)
      - Real AssistantAgent (for production, using AutoGen/LLMs)
    """

    def __init__(self, name: str):
        self.name = name
        if USE_REAL_AUTOGEN:
            # TODO: Replace with real AutoGen AssistantAgent initialization
            raise NotImplementedError(
                "Real AutoGen integration not yet implemented. Use mock mode."
            )
        else:
            # Use built-in mock assistant for testing
            self._impl = MockAssistant(name)

    async def send(self, prompt: str) -> str:
        """
        Send a prompt to the assistant and return a response string (usually JSON).
        """
        return await self._impl.send(prompt)


def make_agent(role: str) -> AssistantInterface:
    """
    Factory function to create agent instances.
    Example: make_agent('reception'), make_agent('triage'), etc.
    """
    return AssistantInterface(role)
