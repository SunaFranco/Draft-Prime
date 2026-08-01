"""
connection.py - ConnectionManager separado para WebSockets

Este módulo contiene la clase `ConnectionManager` y la instancia `manager`.
Se extrae desde `session.py` para que la lógica de conexiones esté aislada.
"""

from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # session_id -> username -> WebSocket activo en esa sesión
        self.active: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, session_id: str, username: str, websocket: WebSocket):
        """Acepta la conexión y la registra con el username."""
        await websocket.accept()
        if session_id not in self.active:
            self.active[session_id] = {}
        self.active[session_id][username] = websocket

    def disconnect(self, session_id: str, username: str):
        """Elimina la conexión del usuario de la sesión."""
        if session_id in self.active:
            self.active[session_id].pop(username, None)

    async def broadcast(self, session_id: str, message: dict):
        """
        Envía un mensaje JSON a TODOS los clientes conectados en la sesión.
        Si un cliente está muerto, lo remueve silenciosamente.
        """
        if session_id not in self.active:
            return

        dead_usernames = []
        for username, ws in list(self.active[session_id].items()):
            try:
                await ws.send_json(message)
            except Exception:
                dead_usernames.append(username)

        for username in dead_usernames:
            self.active[session_id].pop(username, None)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Envía un mensaje solo a un cliente específico."""
        await websocket.send_json(message)

    async def send_personal_to_user(self, session_id: str, username: str, message: dict):
        """Envía un mensaje al socket activo de un jugador en la sesión."""
        websocket = self.active.get(session_id, {}).get(username)
        if websocket:
            await websocket.send_json(message)


manager = ConnectionManager()
