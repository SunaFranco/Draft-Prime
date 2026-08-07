"""
routes/session.py - Sistema de sesiones con WebSocket

Maneja todo el ciclo de vida de una sesión de draft:
  - Crear sesión (genera ID único)
  - Consultar estado
  - Conexión WebSocket en tiempo real (join, ready, leave)

El estado vive en memoria. En el futuro se puede persistir en Redis o DB.
"""

import json
import random
import secrets
import ssl
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from backend.database import get_all_cubes, get_cube_by_id

router = APIRouter()



# ══════════════════════════════════════════════════════════════════════════════
# ESTADO GLOBAL EN MEMORIA
# ══════════════════════════════════════════════════════════════════════════════

# Diccionario principal de sesiones
# Clave: session_id (str), Valor: dict con toda la info de la sesión
sessions: Dict[str, dict] = {}

YGOPRODECK_API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
CARD_CACHE: Dict[str, dict] = {}

MODE_NAMES = {
    "cube_draft_yugioh": "Draft cube yugioh",
    "subasta_pokemon": "Subasta pokemon",
}



# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION MANAGER
# Administra las conexiones WebSocket activas agrupadas por sesión.
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC (validación de request body)
# ══════════════════════════════════════════════════════════════════════════════

class CreateSessionRequest(BaseModel):
    username: str   # Nombre del jugador que crea la sesión (se convierte en host)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════

def make_session_id() -> str:
    """Genera un ID de sesión de 12 caracteres hex (ej: 'b43ce3c59eef')."""
    return secrets.token_hex(6)


def get_session_or_404(session_id: str) -> dict:
    """Devuelve la sesión o lanza 404 si no existe."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Sesión '{session_id}' no encontrada")
    return session


def all_connected_players_ready(session: dict) -> bool:
    connected_players = [p for p in session["players"] if p["connected"]]
    return bool(connected_players) and all(p["ready"] for p in connected_players)


def get_available_modes() -> List[dict]:
    """Devuelve los modos de juego disponibles para el frontend."""
    return [{"key": key, "name": name} for key, name in MODE_NAMES.items()]


def get_available_cubes() -> List[dict]:
    """Devuelve los cubes disponibles en formato compatible con el frontend."""
    return [{"key": cube["id"], "title": cube["title"]} for cube in get_all_cubes()]


def session_public_state(session: dict) -> dict:
    """
    Devuelve una versión 'limpia' de la sesión para enviar al cliente.
    Excluye datos internos como las conexiones WebSocket.
    """
    state = {
        "id":            session["id"],
        "host":          session["host"],
        "players":       session["players"],
        "max_players":   session["max_players"],
        "started":       session["started"],
        "created_at":    session["created_at"],
        "mode":          session.get("mode"),
        "mode_name":     MODE_NAMES.get(session.get("mode"), None),
        "mode_config":   session.get("mode_config"),
        "all_ready":     all_connected_players_ready(session) and not session["started"],
    }

    if session.get("mode") == "cube_draft_yugioh":
        state["available_cubes"] = get_available_cubes()

    return state


def reassign_host(session: dict):
    """
    Si el host actual se desconectó, asigna el host al siguiente
    jugador que siga conectado.
    """
    connected_players = [p for p in session["players"] if p["connected"]]
    if connected_players:
        session["host"] = connected_players[0]["username"]


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS REST
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/create")
async def create_session(data: CreateSessionRequest):
    """
    Crea una nueva sesión de draft.

    - Genera un ID único de 12 chars
    - El usuario que crea pasa a ser el host
    - Devuelve el session_id para construir la URL de invitación

    Ejemplo de uso:
        POST /session/create
        Body: { "username": "Alice" }

        Response: { "session_id": "b43ce3c59eef", "host": "Alice", ... }
    """
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="El username no puede estar vacío")
    if len(username) > 24:
        raise HTTPException(status_code=400, detail="Username muy largo (máx. 24 caracteres)")

    session_id = make_session_id()

    # Garantizar que el ID sea único (colisión extremadamente improbable)
    while session_id in sessions:
        session_id = make_session_id()

    sessions[session_id] = {
        "id":          session_id,
        "host":        username,
        "players": [
            {
                "username":  username,
                "ready":     False,
                "connected": True,   # El creador empieza conectado
            }
        ],
        "max_players": 4,
        "started":     False,
        "created_at":  datetime.utcnow().isoformat(),
    }

    return {
        "session_id":  session_id,
        "session_url": f"/?session={session_id}",   # URL de invitación
        **session_public_state(sessions[session_id]),
    }


@router.get("/{session_id}")
def get_session(session_id: str):
    """
    Devuelve el estado actual de una sesión.
    Útil para que el frontend cargue el estado inicial al abrir la URL.

    Ejemplo de uso:
        GET /session/b43ce3c59eef
    """
    session = get_session_or_404(session_id)
    return session_public_state(session)


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str, username: str):
    """
    Conexión WebSocket para una sesión.

    Parámetros:
        session_id: ID de la sesión (en la ruta)
        username:   Nombre del jugador (query param)

    URL de conexión: ws://localhost:8000/session/b43ce3c59eef/ws?username=Bob

    Mensajes que el servidor envía (broadcast o personal):
        { "event": "session_state",  "data": { ...estado completo... } }
        { "event": "player_joined",  "data": { "username": "...", "players": [...] } }
        { "event": "player_left",    "data": { "username": "...", "players": [...] } }
        { "event": "player_ready",   "data": { "username": "...", "ready": true } }
        { "event": "host_changed",   "data": { "new_host": "..." } }
        { "event": "error",          "data": { "message": "..." } }

    Mensajes que el cliente puede enviar:
        { "action": "toggle_ready" }
    """
    username = username.strip()

    # ── Validaciones antes de aceptar la conexión ──────────────────────────
    session = sessions.get(session_id)

    if not session:
        # Aceptar para poder enviar el error y luego cerrar
        await websocket.accept()
        await websocket.send_json({
            "event": "error",
            "data":  {"message": f"Sesión '{session_id}' no existe"}
        })
        await websocket.close(code=4004)
        return

    if not username:
        await websocket.accept()
        await websocket.send_json({
            "event": "error",
            "data":  {"message": "Username requerido"}
        })
        await websocket.close(code=4001)
        return

    # Verificar si el username ya está en la sesión
    existing_player = next(
        (p for p in session["players"] if p["username"] == username), None
    )

    if existing_player:
        # Reconexión: el jugador estaba antes y vuelve a conectarse
        existing_player["connected"] = True
        await manager.connect(session_id, username, websocket)
        await manager.send_personal(websocket, {
            "event": "session_state",
            "data":  session_public_state(session),
        })
        await manager.broadcast(session_id, {
            "event": "player_joined",
            "data":  {
                "username":    username,
                "reconnected": True,
                "host":        session["host"],
                "players":     session["players"],
            },
        })

    else:
        # Jugador nuevo: verificar que haya lugar
        connected_count = len([p for p in session["players"] if p["connected"]])
        total_count = len(session["players"])

        if total_count >= session["max_players"]:
            await websocket.accept()
            await websocket.send_json({
                "event": "error",
                "data":  {"message": "La sesión está llena (máx. 4 jugadores)"}
            })
            await websocket.close(code=4003)
            return

        # Agregar jugador nuevo a la sesión
        new_player = {"username": username, "ready": False, "connected": True}
        session["players"].append(new_player)

        await manager.connect(session_id, username, websocket)

        # Enviar estado completo solo al recién llegado
        await manager.send_personal(websocket, {
            "event": "session_state",
            "data":  session_public_state(session),
        })

        # Notificar a todos que alguien llegó
        await manager.broadcast(session_id, {
            "event": "player_joined",
            "data":  {
                "username":    username,
                "reconnected": False,
                "host":        session["host"],
                "players":     session["players"],
            },
        })

    # ── Loop principal: escuchar mensajes del cliente ──────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "Mensaje inválido (no es JSON)"}
                })
                continue

            action = message.get("action")

            # ── Acción: toggle_ready ────────────────────────────────────────
            if action == "toggle_ready":
                player = next(
                    (p for p in session["players"] if p["username"] == username), None
                )
                if player:
                    player["ready"] = not player["ready"]
                    await manager.broadcast(session_id, {
                        "event": "player_ready",
                        "data":  {
                            "username": username,
                            "ready":    player["ready"],
                            "host":     session["host"],
                            "players":  session["players"],
                        },
                    })

                    if all_connected_players_ready(session):
                        await manager.broadcast(session_id, {
                            "event": "all_ready",
                            "data":  {
                                "host":    session["host"],
                                "players": session["players"],
                            },
                        })

            elif action == "start_game":
                if username != session["host"]:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Solo el host puede iniciar la partida."}
                    })
                    continue

                if not all_connected_players_ready(session):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Todos los jugadores deben estar listos para empezar."}
                    })
                    continue

                if session["started"]:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "La partida ya ha comenzado."}
                    })
                    continue

                await manager.broadcast(session_id, {
                    "event": "mode_selection",
                    "data":  {
                        "host":            session["host"],
                        "players":         session["players"],
                        "available_modes": get_available_modes(),
                    },
                })

            elif action == "choose_mode":
                if username != session["host"]:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Solo el host puede elegir el modo."}
                    })
                    continue

                mode = message.get("mode")
                if mode not in MODE_NAMES:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Modo inválido."}
                    })
                    continue

                session["mode"] = mode
                session["mode_config"] = None

                await manager.broadcast(session_id, {
                    "event": "mode_config",
                    "data":  {
                        "host":           session["host"],
                        "players":        session["players"],
                        "mode":           mode,
                        "mode_name":      MODE_NAMES[mode],
                        "available_cubes": get_available_cubes() if mode == "cube_draft_yugioh" else [],
                    },
                })

            elif action == "configure_mode":
                if username != session["host"]:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Solo el host puede configurar el modo."}
                    })
                    continue

                if session.get("mode") != "cube_draft_yugioh":
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "No se puede configurar este modo."}
                    })
                    continue

                cube_key = message.get("cube_key")
                pack_count = int(message.get("pack_count", 0))
                cards_per_pack = int(message.get("cards_per_pack", 0))

                if not cube_key or (not get_cube_by_id(cube_key) and not cube_key.startswith("custom_")):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Cube inválido."}
                    })
                    continue
                if pack_count < 1 or pack_count > 4:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Cantidad de sobres inválida (1-4)."}
                    })
                    continue
                if cards_per_pack < 3 or cards_per_pack > 9:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Cantidad de cartas por sobre inválida (3-9)."}
                    })
                    continue

                session["mode_config"] = {
                    "cube_key":       cube_key,
                    "pack_count":     pack_count,
                    "cards_per_pack": cards_per_pack,
                }

                await manager.broadcast(session_id, {
                    "event": "mode_configured",
                    "data":  {
                        "host":        session["host"],
                        "players":     session["players"],
                        "mode":         session["mode"],
                        "mode_name":    MODE_NAMES[session["mode"]],
                        "mode_config":  session["mode_config"],
                    },
                })

            else:
                from backend.modes import handle_mode_action
                await handle_mode_action(session, username, message, manager, websocket)

    # ── El cliente se desconectó ───────────────────────────────────────────
    except WebSocketDisconnect:
        manager.disconnect(session_id, username)

        # Marcar al jugador como desconectado en la sesión
        player = next(
            (p for p in session["players"] if p["username"] == username), None
        )
        if player:
            player["connected"] = False
            player["ready"]     = False   # Reset del ready al desconectarse

        # Si el host se fue, reasignar
        old_host = session["host"]
        reassign_host(session)
        new_host = session["host"]

        await manager.broadcast(session_id, {
            "event": "player_left",
            "data":  {
                "username": username,
                "host":     session["host"],
                "players":  session["players"],
            },
        })

        # Notificar cambio de host si ocurrió
        if old_host != new_host:
            await manager.broadcast(session_id, {
                "event": "host_changed",
                "data":  {"new_host": new_host},
            })
