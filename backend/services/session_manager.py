"""
services/session_manager.py - Gestor de estado de sesión y conexiones WebSocket
"""

import secrets
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException, WebSocket
from backend.database import get_all_cubes


# Diccionario principal de sesiones en memoria
# session_id (str) -> dict con la información de la sesión
sessions: Dict[str, dict] = {}


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
        Si un cliente está desconectado/muerto, lo remueve silenciosamente.
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


def make_session_id() -> str:
    """Genera un ID de sesión de 12 caracteres hex."""
    return secrets.token_hex(6)


def get_session_or_404(session_id: str) -> dict:
    """Devuelve la sesión o lanza 404 si no existe."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Sesión '{session_id}' no encontrada")
    return session


def all_connected_players_ready(session: dict) -> bool:
    """Verifica si todos los jugadores conectados están listos."""
    connected_players = [p for p in session["players"] if p["connected"]]
    return bool(connected_players) and all(p["ready"] for p in connected_players)


def reassign_host(session: dict):
    """
    Si el host actual se desconectó, asigna el rol de host al siguiente
    jugador que siga conectado.
    """
    connected_players = [p for p in session["players"] if p["connected"]]
    if connected_players:
        session["host"] = connected_players[0]["username"]


def get_connected_player_order(session: dict) -> List[str]:
    """Devuelve la lista de usernames de jugadores conectados."""
    return [p["username"] for p in session["players"] if p["connected"]]


def session_public_state(session: dict, target_username: Optional[str] = None) -> dict:
    """
    Devuelve una versión 'limpia' de la sesión para enviar al cliente.
    Excluye datos internos como las conexiones WebSocket o estado sensible no formateado.
    """
    from backend.modes import registry

    mode_key = session.get("mode")
    state = {
        "id":            session["id"],
        "host":          session["host"],
        "players":       session["players"],
        "max_players":   session["max_players"],
        "started":       session["started"],
        "created_at":    session["created_at"],
        "mode":          mode_key,
        "mode_name":     registry.get_mode_name(mode_key) if mode_key else None,
        "mode_config":   session.get("mode_config"),
        "all_ready":     all_connected_players_ready(session) and not session["started"],
    }

    if mode_key and registry.is_valid_mode(mode_key):
        handler = registry.get_mode_handler(mode_key)
        state.update(handler.get_public_config_options(session))
        if target_username:
            state["draft_state"] = handler.get_player_sync_state(session, target_username)

    return state
