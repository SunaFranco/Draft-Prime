import json
import random
import secrets
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from backend.database import get_cube_by_id

YGOPRODECK_API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
CARD_CACHE: Dict[str, dict] = {}

def fetch_yugioh_card(name: str) -> dict:
    """Obtiene datos básicos de una carta desde la API YGOPRODeck."""
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
                "id":        card_data.get("id", name),
                "name":      card_data.get("name", name),
                "type":      card_data.get("type", ""),
                "desc":      card_data.get("desc", ""),
                "image_url": image_info.get("image_url_small") or image_info.get("image_url") or "",
                "atk":       card_data.get("atk"),
                "def":       card_data.get("def"),
                "level":     card_data.get("level"),
                "race":      card_data.get("race"),
                "attribute": card_data.get("attribute"),
                "archetype": card_data.get("archetype"),
            }
    except Exception:
        card = {
            "id":        name,
            "name":      name,
            "type":      "Desconocido",
            "desc":      "No se pudo cargar la carta desde la API.",
            "image_url": "",
            "atk":       None,
            "def":       None,
            "level":     None,
            "race":      None,
            "attribute": None,
            "archetype": None,
        }

    CARD_CACHE[name] = card
    return card


def build_card_from_name(card_name: str) -> dict:
    card = fetch_yugioh_card(card_name)
    return {
        **card,
        "name": card.get("name") or card_name,
    }


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
        elif normalized in ("atributo", "attribute"):
            normalized = "attribute"
        elif normalized in ("arquetipo", "archetype"):
            normalized = "archetype"
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

    for field in ("level", "atk", "def", "race", "frameType", "attribute", "archetype"):
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


def start_draft_session(session: dict, order: List[str]):
    config = session["mode_config"]

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


async def handle_action(session: dict, username: str, message: dict, manager, websocket):
    action = message.get("action")
    session_id = session["id"]

    if action == "start_draft":
        if username != session["host"]:
            await manager.send_personal(websocket, {
                "event": "error",
                "data":  {"message": "Solo el host puede iniciar el draft."}
            })
            return

        if session.get("mode") != "cube_draft_yugioh" or not session.get("mode_config"):
            await manager.send_personal(websocket, {
                "event": "error",
                "data":  {"message": "Falta configurar el modo de draft."}
            })
            return

        if session["started"]:
            await manager.send_personal(websocket, {
                "event": "error",
                "data":  {"message": "La partida ya ha comenzado."}
            })
            return

        order = [p["username"] for p in session["players"] if p["connected"]]
        start_draft_session(session, order)
        session["started"] = True

        from backend.routes.session import MODE_NAMES
        await manager.broadcast(session_id, {
            "event": "draft_started",
            "data":  {
                "host":        session["host"],
                "players":     session["players"],
                "mode":         session["mode"],
                "mode_name":    MODE_NAMES[session["mode"]],
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
            return

        card_name = message.get("card_name")

        if draft["picks_in_step"].get(username) is not None:
            await manager.send_personal(websocket, {
                "event": "error",
                "data":  {"message": "Ya elegiste tu carta en este turno. Esperando a los demás..."}
            })
            return

        user_pack = draft["current_packs"].get(username)
        if not user_pack:
            await manager.send_personal(websocket, {
                "event": "error",
                "data":  {"message": "No tienes un sobre asignado."}
            })
            return

        card = next((c for c in user_pack["cards"] if c["name"] == card_name), None)
        if not card:
            await manager.send_personal(websocket, {
                "event": "error",
                "data":  {"message": "Carta no encontrada en tu sobre."}
            })
            return

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
