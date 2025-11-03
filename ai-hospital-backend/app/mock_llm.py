"""
mock_llm.py
===========
A simple mock assistant for local testing (no API calls).
Each agent returns deterministic JSON responses for predictable testing.
"""

import asyncio
import json


class MockAssistant:
    """
    A mock version of an AI assistant.
    Used when USE_REAL_AUTOGEN=false so the system can run offline.
    """

    def __init__(self, name: str):
        self.name = name

    async def send(self, prompt: str) -> str:
        """
        Simulate thinking and return structured JSON depending on agent type.
        """

        # Simulate small processing delay
        await asyncio.sleep(0.2)

        # Reception agent
        if self.name.lower().startswith("reception"):
            return json.dumps({
                "action": "registered",
                "patient_id": 0,
                "message": "Patient registered successfully (mock)."
            })

        # Triage agent
        if self.name.lower().startswith("triage"):
            urgency = "normal"
            score = 60
            if any(word in prompt.lower() for word in ["chest pain", "bleeding", "unconscious"]):
                urgency = "critical"
                score = 95
            elif any(word in prompt.lower() for word in ["fever", "pain", "infection"]):
                urgency = "urgent"
                score = 80
            return json.dumps({
                "urgency": urgency,
                "score": score,
                "recommended_tests": ["CBC", "X-Ray"]
            })

        # Diagnostic agent
        if self.name.lower().startswith("diagnostic"):
            return json.dumps({
                "tests_ordered": ["CBC", "Chest X-ray"],
                "expected_time_mins": 45,
                "notes": "Mock diagnostic plan."
            })

        # Physician agent
        if self.name.lower().startswith("physician"):
            return json.dumps({
                "diagnosis": "Acute bronchitis (mock)",
                "plan": "Rest, hydration, antibiotics",
                "prescription": [{"drug": "Amoxicillin", "dose": "500mg", "freq": "TID"}]
            })

        # Pharmacy agent
        if self.name.lower().startswith("pharmacy"):
            return json.dumps({
                "available": True,
                "items": [{"drug": "Amoxicillin", "qty": 10}],
                "warnings": []
            })

        # Billing agent
        if self.name.lower().startswith("billing"):
            return json.dumps({
                "estimate": 120.0,
                "currency": "USD",
                "items": [
                    {"desc": "Consultation", "amt": 50},
                    {"desc": "Lab Tests", "amt": 70}
                ]
            })

        # Fallback for unknown agents
        return json.dumps({
            "message": f"Mock response from {self.name}"
        })
