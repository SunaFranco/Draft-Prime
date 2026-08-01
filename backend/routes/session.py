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


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION MANAGER (antes estaba extraído; lo dejamos en este archivo)
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


# Pequeño registro local de modos (antes estaba en backend/modes)
MODES = {
    "cube_draft_yugioh": "Cube Draft (Yugioh)",
    "subasta_pokemon": "Subasta (Pokemon)",
}


def get_available_modes() -> List[dict]:
    return [{"key": key, "name": name} for key, name in MODES.items()]


def is_valid_mode(mode: str) -> bool:
    return mode in MODES


def get_mode_name(mode: str) -> str:
    return MODES.get(mode, mode)


def mode_requires_cubes(mode: str) -> bool:
    return mode == "cube_draft_yugioh"

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
        "mode_name":     session.get("mode"),
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


# ============================================================================
# Funciones y helpers para el modo 'cube_draft_yugioh' (estaban en session.py)
# ============================================================================


def fetch_yugioh_card(name: str) -> dict:
    if name in CARD_CACHE:
        return CARD_CACHE[name]

    query = urllib.parse.urlencode({"name": name})
    url = f"{YGOPRODECK_API_URL}?{query}"
    try:
        ctx = ssl.create_default_context()
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        with urllib.request.urlopen(request, context=ctx, timeout=8) as response:
            payload = json.loads(response.read().decode())
            card_data = payload.get("data", [])[0]
            image_info = card_data.get("card_images", [{}])[0]
            card = {
                "id":         card_data.get("id", name),
                "name":       card_data.get("name", name),
                "type":       card_data.get("type", ""),
                "desc":       card_data.get("desc", ""),
                "race":       card_data.get("race", ""),
                "attribute":  card_data.get("attribute", ""),
                "level":      card_data.get("level"),
                "atk":        card_data.get("atk"),
                "def":        card_data.get("def"),
                "frameType":  card_data.get("frameType", ""),
                "archetype":  card_data.get("archetype", ""),
                "image_url":  image_info.get("image_url_small") or image_info.get("image_url") or "",
            }
    except Exception:
        card = {
            "id":        name,
            "name":      name,
            "type":      "Desconocido",
            "desc":      "No se pudo cargar la carta desde la API.",
            "image_url": "",
        }

    CARD_CACHE[name] = card
    return card


def build_card_from_name(card_name: str) -> dict:
    card = fetch_yugioh_card(card_name)
    return {**card, "name": card.get("name") or card_name}


def get_available_cubes() -> List[dict]:
    cubes = []
    for cube in get_all_cubes():
        cube_id = cube.get("id")
        if not cube_id:
            continue
        cubes.append({"key": cube_id, "title": cube.get("title", "Cube")})
    return cubes


def parse_custom_card_block(lines: List[str]) -> dict:
    card = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        normalized = key.lower()
        if normalized in ("nombre", "name", "nombre de carta", "card name"):
            normalized = "name"
        elif normalized in ("descripcion", "desc", "description", "texto"):
            normalized = "desc"
        elif normalized in ("tipo", "type", "tipo carta", "tipo de carta"):
            normalized = "type"
        elif normalized in ("nivel", "level", "estrellas", "stars"):
            normalized = "level"
        elif normalized in ("ataque", "atk", "attack"):
            normalized = "atk"
        elif normalized in ("defensa", "def", "defense"):
            normalized = "def"
        elif normalized in ("raza", "race"):
            normalized = "race"
        elif normalized in ("frame", "frametype", "tipo_marco"):
            normalized = "frameType"
        elif normalized in ("imagen", "image_url", "image", "imagen_url"):
            normalized = "image_url"
        elif normalized in ("imagen_pequeña", "image_url_small", "image_small"):
            normalized = "image_url_small"
        elif normalized in ("imagen_recortada", "image_url_cropped", "image_cropped"):
            normalized = "image_url_cropped"
        card[normalized] = value

    if "name" not in card:
        if len(lines) == 1:
            card["name"] = lines[0].strip()
        else:
            raise ValueError("Cada carta personalizada debe contener al menos un campo 'name' o una sola línea con el nombre de la carta.")

    return card


def load_custom_cube(cube_key: str) -> List[dict]:
    if not cube_key.startswith("custom_"):
        raise ValueError(f"Cube personalizado inválido: {cube_key}")

    cube_name = cube_key.replace("custom_", "")
    cube_path = Path(__file__).resolve().parent.parent / "cubes" / f"{cube_name}.txt"
    if not cube_path.exists():
        raise ValueError(f"Cube personalizado no encontrado: {cube_name}")

    raw_lines = [line.rstrip() for line in cube_path.read_text(encoding="utf-8").splitlines()]
    content_lines = [line for line in raw_lines if line.strip() and not line.strip().startswith("#")]

    if not content_lines:
        raise ValueError(f"El cube personalizado '{cube_name}' está vacío.")

    if all(":" not in line for line in content_lines):
        return [{"name": line.strip()} for line in content_lines]

    cards = []
    block = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if block:
                cards.append(parse_custom_card_block(block))
                block = []
            continue
        block.append(stripped)

    if block:
        cards.append(parse_custom_card_block(block))

    if not cards:
        raise ValueError(f"El cube personalizado '{cube_name}' no contiene cartas válidas.")

    return cards


def build_custom_card(card_def: dict) -> dict:
    card = {
        "id": card_def.get("id", card_def.get("name")),
        "name": card_def.get("name", "Carta desconocida"),
        "type": card_def.get("type", ""),
        "desc": card_def.get("desc", ""),
        "image_url": card_def.get("image_url") or card_def.get("image_url_small") or card_def.get("image_url_cropped") or "",
    }

    for field in ("level", "atk", "def", "race", "frameType"):
        if field in card_def:
            card[field] = card_def[field]

    return card


def resolve_cube_for_key(cube_key: str) -> dict | None:
    return get_cube_by_id(cube_key)


def get_cube_card_pool(cube_key: str) -> List[dict]:
    db_cube = resolve_cube_for_key(cube_key)
    if db_cube:
        cards = db_cube.get("cards", []) or []
        return cards

    raise ValueError(f"Cube desconocido: {cube_key}")



def get_connected_player_order(session: dict) -> List[str]:
    return [p["username"] for p in session["players"] if p["connected"]]


def init_draft_round(session: dict, round_num: int):
    draft = session["draft"]
    order = draft["picker_order"]
    cube_key = draft["cube_key"]
    cards_per_pack = draft["cards_per_pack"]
    pool = get_cube_card_pool(cube_key)

    draft["current_round"] = round_num
    draft["current_step"] = 1
    draft["picks_in_step"] = {u: None for u in order}
    draft["current_packs"] = {}

    for idx, username in enumerate(order):
        selected_names = random.sample(pool, k=cards_per_pack)
        pack_cards = [build_card_from_name(card_name) for card_name in selected_names]
        draft["current_packs"][username] = {
            "pack_id": f"round_{round_num}_pack_{idx + 1}",
            "initial_owner": username,
            "cards": pack_cards,
        }


def start_draft_session(session: dict):
    config = session["mode_config"]
    order = get_connected_player_order(session)

    session["draft"] = {
        "cube_key":        config["cube_key"],
        "pack_count":      config["pack_count"],
        "cards_per_pack":  config["cards_per_pack"],
        "current_round":   1,
        "current_step":    1,
        "picker_order":    order,
        "current_packs":   {},
        "picks_in_step":   {u: None for u in order},
        "collections":     {u: [] for u in order},
        "finished":        False,
    }

    init_draft_round(session, 1)











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
                # Si el host actual está marcado como desconectado, reasignarlo
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
                if not is_valid_mode(mode):
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
                        "mode_name":      get_mode_name(mode),
                        "available_cubes": get_available_cubes() if mode_requires_cubes(mode) else [],
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
                        "mode_name":    get_mode_name(session["mode"]),
                        "mode_config":  session["mode_config"],
                    },
                })

            elif action == "start_draft":
                if username != session["host"]:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Solo el host puede iniciar el draft."}
                    })
                    continue

                if session.get("mode") != "cube_draft_yugioh" or not session.get("mode_config"):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Falta configurar el modo de draft."}
                    })
                    continue

                if session["started"]:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "La partida ya ha comenzado."}
                    })
                    continue

                start_draft_session(session)
                session["started"] = True

                await manager.broadcast(session_id, {
                    "event": "draft_started",
                    "data":  {
                        "host":        session["host"],
                        "players":     session["players"],
                        "mode":         session["mode"],
                        "mode_name":    get_mode_name(session["mode"]),
                        "mode_config":  session["mode_config"],
                    },
                })

                draft = session["draft"]
                for user in draft["picker_order"]:
                    pack = draft["current_packs"][user]
                    await manager.send_personal_to_user(session_id, user, {
                        "event": "draft_open_pack",
                        "data":  {
                            "pack_id":        pack["pack_id"],
                            "cards":          pack["cards"],
                            "round":          draft["current_round"],
                            "step":           draft["current_step"],
                            "remaining":      len(pack["cards"]),
                            "total_rounds":   draft["pack_count"],
                            "cards_per_pack": draft["cards_per_pack"],
                        },
                    })

            elif action == "draft_pick_card":
                draft = session.get("draft")
                if not draft or draft.get("finished"):
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "No hay draft activo."}
                    })
                    continue

                card_name = message.get("card_name")

                if draft["picks_in_step"].get(username) is not None:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Ya elegiste tu carta en este turno. Esperando a los demás..."}
                    })
                    continue

                user_pack = draft["current_packs"].get(username)
                if not user_pack:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "No tienes un sobre asignado."}
                    })
                    continue

                card = next((c for c in user_pack["cards"] if c["name"] == card_name), None)
                if not card:
                    await manager.send_personal(websocket, {
                        "event": "error",
                        "data":  {"message": "Carta no encontrada en tu sobre."}
                    })
                    continue

                # 1. Quitar la carta del sobre y agregarla a la colección del jugador
                user_pack["cards"].remove(card)
                draft["collections"].setdefault(username, []).append(card)
                draft["picks_in_step"][username] = card

                # 2. Confirmación al jugador que eligió
                await manager.send_personal(websocket, {
                    "event": "draft_pick_confirmed",
                    "data": {
                        "card":           card,
                        "round":          draft["current_round"],
                        "step":           draft["current_step"],
                        "collection":     draft["collections"][username],
                    }
                })

                # 3. Notificar progreso del pick en la mesa
                picked_count = sum(1 for v in draft["picks_in_step"].values() if v is not None)
                total_players = len(draft["picker_order"])
                await manager.broadcast(session_id, {
                    "event": "draft_step_progress",
                    "data": {
                        "picker":        username,
                        "picked_count":  picked_count,
                        "total_players": total_players,
                        "round":         draft["current_round"],
                        "step":          draft["current_step"],
                    }
                })

                # 4. Si TODOS los jugadores de la ronda eligieron en este paso
                if picked_count >= total_players:
                    first_user = draft["picker_order"][0]
                    remaining_in_pack = len(draft["current_packs"][first_user]["cards"])

                    if remaining_in_pack > 0:
                        # ROTAR SOBRES (Rondas impares: Izquierda/Horario. Rondas pares: Derecha/Antihorario)
                        order = draft["picker_order"]
                        n = len(order)
                        new_packs = {}
                        is_odd_round = (draft["current_round"] % 2 != 0)

                        for i in range(n):
                            giver = order[i]
                            if is_odd_round:
                                receiver = order[(i + 1) % n]
                            else:
                                receiver = order[(i - 1 + n) % n]
                            new_packs[receiver] = draft["current_packs"][giver]

                        draft["current_packs"] = new_packs
                        draft["current_step"] += 1
                        draft["picks_in_step"] = {u: None for u in order}

                        # Enviar el sobre del vecino a cada jugador
                        for user in order:
                            pack = draft["current_packs"][user]
                            await manager.send_personal_to_user(session_id, user, {
                                "event": "draft_open_pack",
                                "data": {
                                    "pack_id":        pack["pack_id"],
                                    "cards":          pack["cards"],
                                    "round":          draft["current_round"],
                                    "step":           draft["current_step"],
                                    "remaining":      len(pack["cards"]),
                                    "total_rounds":   draft["pack_count"],
                                    "cards_per_pack": draft["cards_per_pack"],
                                },
                            })
                    else:
                        # Sobre agotado. Verificar si hay siguiente ronda de sobres
                        if draft["current_round"] < draft["pack_count"]:
                            next_round = draft["current_round"] + 1
                            init_draft_round(session, next_round)

                            await manager.broadcast(session_id, {
                                "event": "draft_round_start",
                                "data": {
                                    "round":        next_round,
                                    "total_rounds": draft["pack_count"],
                                }
                            })

                            for user in draft["picker_order"]:
                                pack = draft["current_packs"][user]
                                await manager.send_personal_to_user(session_id, user, {
                                    "event": "draft_open_pack",
                                    "data": {
                                        "pack_id":        pack["pack_id"],
                                        "cards":          pack["cards"],
                                        "round":          draft["current_round"],
                                        "step":           draft["current_step"],
                                        "remaining":      len(pack["cards"]),
                                        "total_rounds":   draft["pack_count"],
                                        "cards_per_pack": draft["cards_per_pack"],
                                    },
                                })
                        else:
                            # ¡DRAFT FINALIZADO COMPLETAMENTE!
                            draft["finished"] = True
                            await manager.broadcast(session_id, {
                                "event": "draft_complete",
                                "data": {
                                    "collections": draft["collections"],
                                }
                            })


            else:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": f"Acción desconocida: '{action}'"}
                })

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
