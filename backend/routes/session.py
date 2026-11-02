"""
routes/session.py - Sistema de sesiones con WebSocket y enrutamiento modular
"""

import json
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

import backend.database as database
from backend.database import get_all_cubes, get_cube_by_id, save_full_session
from backend.services.session_manager import (
    manager,
    sessions,
    make_session_id,
    get_session_or_404,
    get_or_restore_session,
    all_connected_players_ready,
    can_control_room,
    session_public_state,
    touch_session,
    issue_websocket_ticket,
    consume_websocket_ticket,
)
from backend.routes.auth import get_current_auth_user, require_admin
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
    name: str = Field(min_length=1, max_length=50)
    max_players: int = Field(default=4, ge=2, le=8)


class InviteRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24)


class InviteResponseRequest(BaseModel):
    accept: bool


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS REST
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/create")
async def create_session(
    data: CreateSessionRequest,
    auth: dict = Depends(require_admin),
):
    """
    Crea una nueva sesión de juego.
    """
    profile = auth["profile"]
    username = profile["username"]
    room_name = data.name.strip()
    if not room_name:
        raise HTTPException(status_code=422, detail="El nombre de la sala no puede estar vacío.")

    session_id = make_session_id()

    while session_id in sessions or (
        database.supabase_client
        and database.supabase_client.table("game_sessions").select("session_id").eq(
            "session_id", session_id
        ).limit(1).execute().data
    ):
        session_id = make_session_id()

    now_ts = datetime.utcnow().timestamp()
    new_session = {
        "id":            session_id,
        "name":          room_name,
        "host":          username,
        "created_by":    profile["id"],
        "status":        "active",
        "players": [
            {
                "username":  username,
                "display_name": profile["display_name"],
                "avatar_key": profile["avatar_key"],
                "user_id": profile["id"],
                "is_admin": True,
                "ready":     False,
                "connected": True,
            }
        ],
        "max_players":   data.max_players,
        "started":       False,
        "created_at":    datetime.utcnow().isoformat(),
        "created_ts":    now_ts,
        "last_activity": now_ts,
    }
    sessions[session_id] = new_session
    save_full_session(new_session)

    if database.supabase_client:
        try:
            database.supabase_client.table("game_session_members").insert({
                "session_id": session_id,
                "user_id": profile["id"],
            }).execute()
        except Exception as error:
            sessions.pop(session_id, None)
            database.delete_game_session(session_id)
            raise HTTPException(status_code=503, detail="No se pudo guardar la membresía de la sala.") from error
    else:
        raise HTTPException(status_code=503, detail="Las salas autenticadas requieren Supabase configurado.")

    return {
        "session_id":  session_id,
        **session_public_state(new_session),
    }


@router.get("/{session_id}")
def get_session(session_id: str, auth: dict = Depends(get_current_auth_user)):
    """
    Devuelve el estado actual de una sesión.
    """
    session = get_session_or_404(session_id)
    if not _is_session_member(session_id, auth["user"].id):
        raise HTTPException(status_code=403, detail="No perteneces a esta sala.")
    return session_public_state(session)


def _is_session_member(session_id: str, user_id: str) -> bool:
    if not database.supabase_client:
        return False
    result = database.supabase_client.table("game_session_members").select("user_id").eq(
        "session_id", session_id
    ).eq("user_id", user_id).limit(1).execute()
    return bool(result.data)


@router.post("/{session_id}/websocket-ticket")
def create_websocket_ticket(session_id: str, auth: dict = Depends(get_current_auth_user)):
    session = get_session_or_404(session_id)
    if session.get("status", "active") != "active":
        raise HTTPException(status_code=410, detail="La sala está cerrada.")
    if not _is_session_member(session_id, auth["user"].id):
        raise HTTPException(status_code=403, detail="No perteneces a esta sala.")
    return {"ticket": issue_websocket_ticket(session_id, auth)}


@router.get("/mine/rooms")
def list_my_rooms(auth: dict = Depends(get_current_auth_user)):
    if not database.supabase_client:
        raise HTTPException(status_code=503, detail="Supabase no está configurado.")
    rows = database.supabase_client.table("game_session_members").select(
        "session_id, joined_at"
    ).eq("user_id", auth["user"].id).execute().data or []
    rooms = []
    for row in rows:
        session = get_or_restore_session(row["session_id"])
        if not session:
            continue
        rooms.append({
            "session_id": session["id"],
            "name": session.get("name") or "Sala anterior",
            "status": session.get("status", "active"),
            "mode": session.get("mode"),
            "mode_name": registry.get_mode_name(session.get("mode")) if session.get("mode") else None,
            "players": session.get("players", []),
            "created_at": session.get("created_at"),
        })
    return {"rooms": rooms}


@router.get("/invites/pending")
def list_pending_invites(auth: dict = Depends(get_current_auth_user)):
    if not database.supabase_client:
        raise HTTPException(status_code=503, detail="Supabase no está configurado.")
    invites = database.supabase_client.table("game_session_invites").select(
        "id, session_id, invited_by, created_at"
    ).eq("invited_user_id", auth["user"].id).eq("status", "pending").execute().data or []
    for invite in invites:
        inviter = database.supabase_client.table("profiles").select(
            "username, display_name"
        ).eq("id", invite["invited_by"]).limit(1).execute().data or [{}]
        invite["inviter"] = inviter[0]
        session = get_or_restore_session(invite["session_id"])
        invite["room_status"] = session.get("status", "active") if session else "missing"
        invite["room_name"] = session.get("name") if session else "Sala anterior"
    return {"invites": invites}


@router.post("/{session_id}/invites", status_code=201)
def invite_to_room(
    session_id: str,
    data: InviteRequest,
    auth: dict = Depends(get_current_auth_user),
):
    session = get_session_or_404(session_id)
    if not auth["profile"]["is_admin"] or not _is_session_member(session_id, auth["user"].id):
        raise HTTPException(status_code=403, detail="Solo un admin participante puede invitar.")
    if session.get("status", "active") != "active":
        raise HTTPException(status_code=410, detail="La sala está cerrada.")
    if not database.supabase_client:
        raise HTTPException(status_code=503, detail="Supabase no está configurado.")

    profiles = database.supabase_client.table("profiles").select(
        "id, username"
    ).execute().data or []
    target = next((p for p in profiles if p["username"].casefold() == data.username.strip().casefold()), None)
    if not target:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese nombre.")
    if target["id"] == auth["user"].id:
        raise HTTPException(status_code=409, detail="Ya participas en esta sala.")
    if _is_session_member(session_id, target["id"]):
        raise HTTPException(status_code=409, detail="Ese usuario ya participa en la sala.")

    try:
        result = database.supabase_client.table("game_session_invites").insert({
            "session_id": session_id,
            "invited_user_id": target["id"],
            "invited_by": auth["user"].id,
        }).execute()
    except Exception as error:
        raise HTTPException(status_code=409, detail="Ya hay una invitación pendiente para ese usuario.") from error
    return {"invite": result.data[0] if result.data else {}}


@router.post("/invites/{invite_id}/respond")
def respond_to_invite(
    invite_id: str,
    data: InviteResponseRequest,
    auth: dict = Depends(get_current_auth_user),
):
    if not database.supabase_client:
        raise HTTPException(status_code=503, detail="Supabase no está configurado.")
    rows = database.supabase_client.table("game_session_invites").select("*").eq(
        "id", invite_id
    ).eq("invited_user_id", auth["user"].id).eq("status", "pending").limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Invitación pendiente no encontrada.")

    invite = rows[0]
    if not data.accept:
        database.supabase_client.table("game_session_invites").update({
            "status": "declined",
            "responded_at": datetime.utcnow().isoformat(),
        }).eq("id", invite_id).execute()
        return {"status": "declined"}

    session = get_session_or_404(invite["session_id"])
    if session.get("status", "active") != "active":
        raise HTTPException(status_code=410, detail="La sala ya está cerrada.")
    if len(session.get("players", [])) >= session.get("max_players", 4):
        raise HTTPException(status_code=409, detail="La sala está llena.")

    database.supabase_client.table("game_session_members").insert({
        "session_id": invite["session_id"],
        "user_id": auth["user"].id,
    }).execute()
    database.supabase_client.table("game_session_invites").update({
        "status": "accepted",
        "responded_at": datetime.utcnow().isoformat(),
    }).eq("id", invite_id).execute()
    profile = auth["profile"]
    session["players"].append({
        "username": profile["username"],
        "display_name": profile["display_name"],
        "avatar_key": profile["avatar_key"],
        "user_id": profile["id"],
        "is_admin": profile["is_admin"],
        "ready": False,
        "connected": False,
    })
    save_full_session(session)
    return {"status": "accepted", "session_id": invite["session_id"]}


@router.post("/{session_id}/finish")
async def finish_room_naturally(session_id: str, auth: dict = Depends(get_current_auth_user)):
    return await _close_room(session_id, auth, forced=False)


@router.post("/{session_id}/force-close")
async def force_close_room(session_id: str, auth: dict = Depends(get_current_auth_user)):
    return await _close_room(session_id, auth, forced=True)


async def _close_room(session_id: str, auth: dict, forced: bool) -> dict:
    session = get_session_or_404(session_id)
    if not auth["profile"]["is_admin"] or not _is_session_member(session_id, auth["user"].id):
        raise HTTPException(status_code=403, detail="Solo un admin participante puede cerrar la sala.")
    if session.get("status", "active") != "active":
        raise HTTPException(status_code=410, detail="La sala ya está cerrada.")
    trophy_winners = []
    if not forced:
        naturally_finished = (
            bool(session.get("draft", {}).get("finished"))
            or (
                session.get("mode") == "subasta_pokemon"
                and session.get("subasta", {}).get("current_stage") == 13
                and session.get("subasta", {}).get("event_finished")
            )
        )
        if not naturally_finished:
            raise HTTPException(status_code=409, detail="La partida todavía no figura como finalizada.")

        if session.get("mode") == "subasta_pokemon":
            subasta_state = session.get("subasta", {})
            standings = subasta_state.get("standings", [])
            highest_score = max((int(row.get("points", 0)) for row in standings), default=None)
            trophy_winners = [
                row.get("username") for row in standings
                if highest_score is not None and int(row.get("points", 0)) == highest_score
            ]
            selections = subasta_state.get("trophy_selections", {})
            if not trophy_winners or any(
                len((selections.get(username) or {}).get("pokemon_ids", [])) != 6
                for username in trophy_winners
            ):
                raise HTTPException(status_code=409, detail="Todos los ganadores deben guardar seis Pokémon para el trofeo antes del cierre natural.")

    now = datetime.utcnow().isoformat()
    if not forced and database.supabase_client:
        if trophy_winners:
            trophy_id = f"subasta_{session_id}"
            try:
                database.supabase_client.table("trophies").upsert({
                    "id": trophy_id,
                    "title": session.get("name") or "Sala anterior",
                    "description": f"Trofeo por ganar {session.get('name') or 'la sala'}.",
                    "icon_key": "🏅",
                    "pokemon_ids": [],
                }, on_conflict="id").execute()
                for username in trophy_winners:
                    player = next((item for item in session.get("players", []) if item.get("username") == username), None)
                    selection = subasta_state["trophy_selections"][username]
                    if not player or not player.get("user_id"):
                        raise ValueError(f"No se pudo asociar el ganador {username} con su perfil.")
                    existing_award = database.supabase_client.table("user_trophies").select(
                        "user_id, trophy_id, earned_at"
                    ).eq("user_id", player["user_id"]).eq("source_session_id", session_id).limit(1).execute().data or []
                    award_data = {
                        "user_id": player["user_id"],
                        "trophy_id": trophy_id,
                        "source_session_id": session_id,
                        "pokemon_ids": selection["pokemon_ids"],
                    }
                    if existing_award:
                        database.supabase_client.table("user_trophies").update({
                            "pokemon_ids": selection["pokemon_ids"],
                        }).eq("user_id", player["user_id"]).eq("trophy_id", trophy_id).eq(
                            "earned_at", existing_award[0]["earned_at"]
                        ).execute()
                    else:
                        database.supabase_client.table("user_trophies").insert(award_data).execute()
            except Exception as error:
                raise HTTPException(status_code=503, detail="No se pudo guardar el trofeo. La sala sigue abierta; vuelve a intentar el cierre.") from error

        members = database.supabase_client.table("game_session_members").select("user_id").eq(
            "session_id", session_id
        ).execute().data or []
        for member in members:
            database.supabase_client.table("user_room_history").upsert({
                "session_id": session_id,
                "room_name": session.get("name") or "Sala anterior",
                "user_id": member["user_id"],
                "mode": session.get("mode"),
                "started_at": session.get("created_at"),
                "finished_at": now,
                "result_summary": {},
            }, on_conflict="session_id,user_id").execute()

    session["status"] = "finished_forced" if forced else "finished_natural"
    session["finish_type"] = "forced" if forced else "natural"
    session["finished_at"] = now

    save_full_session(session)
    await manager.broadcast(session_id, {
        "event": "room_closed",
        "data": {"status": session["status"], "finish_type": session["finish_type"]},
    })
    return {"status": session["status"], "finish_type": session["finish_type"]}


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str, ticket: str):
    """
    Conexión WebSocket para una sesión.
    Maneja eventos generales de lobby (join, ready, choose_mode, leave)
    y delega eventos específicos de juego al handler del modo configurado.
    """
    ticket_data = consume_websocket_ticket(ticket, session_id)
    if not ticket_data:
        await websocket.accept()
        await websocket.send_json({"event": "error", "data": {"message": "Ticket de conexión inválido o vencido."}})
        await websocket.close(code=4001)
        return

    session = get_or_restore_session(session_id)

    if not session:
        await websocket.accept()
        await websocket.send_json({
            "event": "error",
            "data":  {"message": f"Sesión '{session_id}' no existe"}
        })
        await websocket.close(code=4004)
        return

    if session.get("status", "active") != "active":
        await websocket.accept()
        await websocket.send_json({"event": "error", "data": {"message": "La sala está cerrada."}})
        await websocket.close(code=4003)
        return

    user_id = ticket_data["user_id"]
    profile = ticket_data["profile"]
    if not _is_session_member(session_id, user_id):
        await websocket.accept()
        await websocket.close(code=4003)
        return

    username = profile["username"]

    existing_player = next((p for p in session["players"] if p.get("user_id") == user_id), None)

    if existing_player:
        username = existing_player["username"]
        existing_player["connected"] = True
        save_full_session(session)
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

        if len(session["players"]) >= session["max_players"]:
            await websocket.accept()
            await websocket.send_json({"event": "error", "data": {"message": "La sala está llena."}})
            await websocket.close(code=4003)
            return
        new_player = {
            "username": username,
            "display_name": profile["display_name"],
            "avatar_key": profile["avatar_key"],
            "user_id": user_id,
            "is_admin": profile["is_admin"],
            "ready": False,
            "connected": True,
        }
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
            touch_session(session_id)
            if session.get("status", "active") != "active":
                await websocket.close(code=4003)
                break

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
                if not can_control_room(session, username):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Solo un admin participante puede iniciar la partida."}
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
                if not can_control_room(session, username):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Solo un admin participante puede elegir el modo."}
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

        await manager.broadcast(session_id, {
            "event": "player_left",
            "data":  {
                "username": username,
                "host":     session["host"],
                "players":  session["players"],
            },
        })
