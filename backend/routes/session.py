"""
routes/session.py - Sistema de sesiones con WebSocket y enrutamiento modular
"""

import json
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import backend.database as database
from backend.database import get_all_cubes, get_cube_by_id
from backend.services.session_manager import (
    manager,
    sessions,
    make_session_id,
    get_session_or_404,
    all_connected_players_ready,
    reassign_host,
    session_public_state,
)
from backend.modes import registry
from backend.modes.cube_draft_yugioh import handler as yugioh_handler

router = APIRouter()


def resolve_cube_for_key(cube_key: str) -> Optional[dict]:
    """Helper re-exportado para resolver cubes."""
    return yugioh_handler.resolve_cube_for_key(cube_key, get_cube_by_id_fn=get_cube_by_id)


def get_available_cubes() -> List[dict]:
    """Helper re-exportado para obtener cubes disponibles."""
    return yugioh_handler.get_available_cubes(get_all_cubes_fn=get_all_cubes)


def get_cube_card_pool(cube_key: str) -> List[dict]:
    """Helper re-exportado para obtener el pool de cartas de un cube."""
    return yugioh_handler.get_cube_card_pool(cube_key, resolve_cube_fn=resolve_cube_for_key)


class CreateSessionRequest(BaseModel):
    username: str   # Nombre del jugador que crea la sesión (se convierte en host)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS REST
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/create")
async def create_session(data: CreateSessionRequest):
    """
    Crea una nueva sesión de juego.
    """
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="El username no puede estar vacío")
    if len(username) > 24:
        raise HTTPException(status_code=400, detail="Username muy largo (máx. 24 caracteres)")

    session_id = make_session_id()

    while session_id in sessions:
        session_id = make_session_id()

    sessions[session_id] = {
        "id":          session_id,
        "host":        username,
        "players": [
            {
                "username":  username,
                "ready":     False,
                "connected": True,
            }
        ],
        "max_players": 4,
        "started":     False,
        "created_at":  datetime.utcnow().isoformat(),
    }

    return {
        "session_id":  session_id,
        "session_url": f"/?session={session_id}",
        **session_public_state(sessions[session_id]),
    }


@router.get("/{session_id}")
def get_session(session_id: str):
    """
    Devuelve el estado actual de una sesión.
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
    Maneja eventos generales de lobby (join, ready, choose_mode, leave)
    y delega eventos específicos de juego al handler del modo configurado.
    """
    username = username.strip()
    session = sessions.get(session_id)

    if not session:
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

    existing_player = next(
        (p for p in session["players"] if p["username"] == username), None
    )

    if existing_player:
        existing_player["connected"] = True
        await manager.connect(session_id, username, websocket)
        await manager.send_personal(websocket, {
            "event": "session_state",
            "data":  session_public_state(session, target_username=username),
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

        new_player = {"username": username, "ready": False, "connected": True}
        session["players"].append(new_player)

        await manager.connect(session_id, username, websocket)

        await manager.send_personal(websocket, {
            "event": "session_state",
            "data":  session_public_state(session, target_username=username),
        })

        await manager.broadcast(session_id, {
            "event": "player_joined",
            "data":  {
                "username":    username,
                "reconnected": False,
                "host":        session["host"],
                "players":     session["players"],
            },
        })

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

            # ── 1. Acciones genéricas del Lobby ───────────────────────────────
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
                host_player = next((p for p in session["players"] if p["username"] == session["host"]), None)
                if host_player and not host_player.get("connected", False):
                    old_host = session["host"]
                    reassign_host(session)
                    new_host = session["host"]
                    await manager.broadcast(session_id, {
                        "event": "host_changed",
                        "data":  {"new_host": new_host},
                    })

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
                        "available_modes": registry.get_available_modes(),
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
                if not registry.is_valid_mode(mode):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Modo inválido."}
                    })
                    continue

                session["mode"] = mode
                session["mode_config"] = None

                handler = registry.get_mode_handler(mode)
                extra_data = handler.get_public_config_options(session) if handler else {}

                await manager.broadcast(session_id, {
                    "event": "mode_config",
                    "data":  {
                        "host":       session["host"],
                        "players":    session["players"],
                        "mode":       mode,
                        "mode_name":  registry.get_mode_name(mode),
                        **extra_data,
                    },
                })

            else:
                # ── 2. Delegación a Handlers de Modo de Juego ────────────────
                mode_key = session.get("mode")
                handler = registry.get_mode_handler(mode_key) if mode_key else None

                handled = False
                if handler:
                    handled = await handler.handle_action(
                        session, username, action, message, websocket, manager
                    )

                if not handled:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": f"Acción desconocida: '{action}'"}
                    })

    except WebSocketDisconnect:
        was_active = manager.disconnect(session_id, username, websocket)

        if not was_active:
            return

        player = next(
            (p for p in session["players"] if p["username"] == username), None
        )
        if player:
            player["connected"] = False
            player["ready"]     = False

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

        if old_host != new_host:
            await manager.broadcast(session_id, {
                "event": "host_changed",
                "data":  {"new_host": new_host},
            })
