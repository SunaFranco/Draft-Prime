"""
services/session_manager.py - Gestor de estado de sesión y conexiones WebSocket
"""

import secrets
import time
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

    def disconnect(self, session_id: str, username: str, websocket: WebSocket = None) -> bool:
        """
        Elimina la conexión del usuario de la sesión.
        Si se proporciona websocket, solo desconecta si coincide con el socket activo
        (evita que un socket obsoleto desconecte una reconexión nueva).
        Retorna True si se eliminó, False si el socket era obsoleto.
        """
        if session_id in self.active:
            current_ws = self.active[session_id].get(username)
            if websocket is not None and current_ws is not websocket:
                return False
            self.active[session_id].pop(username, None)
            if not self.active[session_id]:
                self.active.pop(session_id, None)
            return True
        return False

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

        if not self.active[session_id]:
            self.active.pop(session_id, None)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Envía un mensaje solo a un cliente específico."""
        await websocket.send_json(message)

    async def send_personal_to_user(self, session_id: str, username: str, message: dict):
        """Envía un mensaje al socket activo de un jugador en la sesión."""
        websocket = self.active.get(session_id, {}).get(username)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                self.active.get(session_id, {}).pop(username, None)


manager = ConnectionManager()
_websocket_tickets: Dict[str, dict] = {}


def make_session_id() -> str:
    """Genera un ID de sesión de 32 caracteres hex (128 bits)."""
    return secrets.token_hex(16)


def issue_websocket_ticket(session_id: str, auth: dict) -> str:
    ticket = secrets.token_urlsafe(32)
    _websocket_tickets[ticket] = {
        "session_id": session_id,
        "user_id": auth["user"].id,
        "profile": auth["profile"],
        "expires_at": time.time() + 60,
    }
    return ticket


def consume_websocket_ticket(ticket: str, session_id: str) -> Optional[dict]:
    payload = _websocket_tickets.pop(ticket, None)
    if not payload or payload["session_id"] != session_id or payload["expires_at"] < time.time():
        return None
    return payload


def get_or_restore_session(session_id: str) -> Optional[dict]:
    """
    Busca la sesión en memoria RAM.
    Si no está en RAM (por reinicio de servidor o limpieza), intenta restaurarla desde Supabase.
    """
    session = sessions.get(session_id)
    if session:
        return session

    from backend import database
    restored = database.get_full_session(session_id)
    if restored:
        sessions[session_id] = restored
        touch_session(session_id)
        print(f"[SESSION RESTORED] Sesión '{session_id}' restaurada exitosamente desde la base de datos.")
        return restored

    return None


def get_session_or_404(session_id: str) -> dict:
    """Devuelve la sesión o lanza 404 si no existe."""
    session = get_or_restore_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Sesión '{session_id}' no encontrada")
    return session


def all_connected_players_ready(session: dict) -> bool:
    """Verifica si todos los jugadores conectados están listos."""
    connected_players = [p for p in session["players"] if p["connected"]]
    return bool(connected_players) and all(p["ready"] for p in connected_players)


def get_connected_player_order(session: dict) -> List[str]:
    """Devuelve la lista de usernames de jugadores conectados."""
    return [p["username"] for p in session["players"] if p["connected"]]


def can_control_room(session: dict, username: str) -> bool:
    """Admins globales solo controlan salas en las que figuran como participantes."""
    player = next((p for p in session.get("players", []) if p.get("username") == username), None)
    return bool(player and player.get("is_admin"))


def session_public_state(session: dict, target_username: Optional[str] = None) -> dict:
    """
    Devuelve una versión 'limpia' de la sesión para enviar al cliente.
    Excluye datos internos como las conexiones WebSocket o estado sensible no formateado.
    """
    from backend.modes import registry

    mode_key = session.get("mode")
    state = {
        "id":            session["id"],
        "name":          session.get("name") or "Sala anterior",
        "host":          session["host"],
        "can_control":   can_control_room(session, target_username) if target_username else False,
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


def touch_session(session_id: str) -> None:
    """Actualiza la marca de tiempo de última actividad de la sesión."""
    session = sessions.get(session_id)
    if session:
        session["last_activity"] = datetime.utcnow().timestamp()


def cleanup_inactive_sessions(max_age_seconds: int = 10800, empty_timeout_seconds: int = 900) -> int:
    """
    Elimina sesiones inactivas para liberar memoria en RAM:
      - Sesiones sin actividad por más de `max_age_seconds` (default 3 horas).
    - Sesiones sin jugadores conectados por más de `empty_timeout_seconds` (default 15 min).
    """
    now = datetime.utcnow().timestamp()
    to_delete = []

    for s_id, s in list(sessions.items()):
        created_ts = s.get("created_ts") or now
        last_activity = s.get("last_activity", created_ts)
        has_connected = any(p.get("connected", False) for p in s.get("players", []))

        # Las sesiones desconectadas pueden restaurarse desde Supabase al reconectar.
        if not has_connected and (now - last_activity > empty_timeout_seconds):
            to_delete.append(s_id)
        # O si la sesión superó la edad máxima
        elif now - last_activity > max_age_seconds:
            to_delete.append(s_id)

    for s_id in to_delete:
        sessions.pop(s_id, None)
        manager.active.pop(s_id, None)

    if to_delete:
        print(f"[CLEANUP] Se descargaron {len(to_delete)} sesiones inactivas de memoria RAM; Supabase conserva salas e historial.")

    return len(to_delete)
