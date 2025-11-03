"""
notifications.py
=================
Handles WebSocket and Pushover notifications for doctors.
"""

import os
import requests
from typing import Dict, List
from fastapi import WebSocket

# Registry to store connected WebSocket clients per doctor
connected_doctors: Dict[int, List[WebSocket]] = {}

# ---------------------------------------------------------------------------
# Pushover Notification (optional)
# ---------------------------------------------------------------------------

def send_pushover(user_key: str, title: str, message: str):
    """
    Sends a push notification using the Pushover API.
    Requires PUSHOVER_TOKEN and PUSHOVER_USER in .env
    """
    if not user_key:
        return  # no pushover user configured

    token = os.getenv("PUSHOVER_TOKEN")
    if not token:
        print("⚠️  Pushover token not configured, skipping notification.")
        return

    try:
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": token, "user": user_key, "title": title, "message": message},
            timeout=5
        )
        if resp.status_code != 200:
            print(f"❌ Pushover error: {resp.text}")
    except Exception as e:
        print(f"❌ Pushover send failed: {e}")

# ---------------------------------------------------------------------------
# WebSocket Registry
# ---------------------------------------------------------------------------

def register_ws(doctor_id: int, ws: WebSocket):
    """Register a WebSocket connection for a doctor."""
    connected_doctors.setdefault(doctor_id, []).append(ws)
    print(f"🩺 Doctor {doctor_id} connected via WebSocket ({len(connected_doctors[doctor_id])} active).")


def unregister_ws(doctor_id: int, ws: WebSocket):
    """Unregister a WebSocket connection when disconnected."""
    if doctor_id in connected_doctors:
        connected_doctors[doctor_id] = [w for w in connected_doctors[doctor_id] if w != ws]
        if not connected_doctors[doctor_id]:
            del connected_doctors[doctor_id]
    print(f"❌ Doctor {doctor_id} disconnected. Remaining sockets: {len(connected_doctors.get(doctor_id, []))}")


async def broadcast_to_doctor(doctor_id: int, data: dict):
    """Send a JSON message to all active WebSocket connections for a doctor."""
    if doctor_id not in connected_doctors:
        return

    for ws in connected_doctors[doctor_id]:
        try:
            await ws.send_json(data)
        except Exception:
            print(f"⚠️ Failed to send WS message to doctor {doctor_id}")
