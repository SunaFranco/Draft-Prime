"""
backend/modes/cube_draft_yugioh/handler.py - Implementación del modo Cube Draft Yu-Gi-Oh
"""

import random
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from backend.modes.base import BaseGameMode
from backend.modes.cube_draft_yugioh.card_api import build_card_from_name
import backend.database as database
from backend.services.session_manager import get_connected_player_order


def get_available_cubes(get_all_cubes_fn: Optional[Callable] = None) -> List[dict]:
    """Devuelve los cubes disponibles en formato compatible con la UI."""
    fn = get_all_cubes_fn or database.get_all_cubes
    return [{"key": cube["id"], "title": cube["title"]} for cube in fn()]


def resolve_cube_for_key(cube_key: str, get_cube_by_id_fn: Optional[Callable] = None) -> dict | None:
    """Resuelve un cube por su ID de base de datos."""
    fn = get_cube_by_id_fn or database.get_cube_by_id
    return fn(cube_key)


def get_cube_card_pool(cube_key: str, resolve_cube_fn: Optional[Callable] = None) -> List[dict]:
    """Obtiene la lista de nombres de cartas pertenecientes a un cube."""
    resolve_fn = resolve_cube_fn or resolve_cube_for_key
    db_cube = resolve_fn(cube_key)
    if db_cube:
        cards = db_cube.get("cards", []) or []
        return cards

    raise ValueError(f"Cube desconocido: {cube_key}")


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
    cube_path = Path(__file__).resolve().parent.parent.parent / "cubes" / f"{cube_name}.txt"
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
        pack_cards = [
            {**build_card_from_name(card_name), "draft_card_key": f"round_{round_num}_pack_{idx + 1}_card_{card_idx + 1}"}
            for card_idx, card_name in enumerate(selected_names)
        ]
        draft["current_packs"][username] = {
            "pack_id": f"round_{round_num}_pack_{idx + 1}",
            "initial_owner": username,
            "cards": pack_cards,
        }


class CubeDraftYugiohMode(BaseGameMode):
    @property
    def key(self) -> str:
        return "cube_draft_yugioh"

    @property
    def name(self) -> str:
        return "Cube Draft (Yugioh)"

    @property
    def requires_cubes(self) -> bool:
        return True

    def get_public_config_options(self, session: dict) -> Dict[str, Any]:
        return {"available_cubes": get_available_cubes()}

    def get_player_sync_state(self, session: dict, username: str) -> dict:
        draft = session.get("draft")
        if not draft:
            return {}

        finished = draft.get("finished", False)
        has_picked_this_step = draft["picks_in_step"].get(username) is not None
        collection = draft["collections"].get(username, [])

        user_pack = draft["current_packs"].get(username)
        current_pack = None
        if user_pack and not has_picked_this_step and not finished:
            current_pack = {
                "pack_id": user_pack["pack_id"],
                "cards": user_pack["cards"],
            }

        picked_count = sum(1 for v in draft["picks_in_step"].values() if v is not None)
        total_players = len(draft["picker_order"])

        state = {
            "round": draft["current_round"],
            "step": draft["current_step"],
            "total_rounds": draft["pack_count"],
            "cards_per_pack": draft["cards_per_pack"],
            "collection": collection,
            "current_pack": current_pack,
            "has_picked_this_step": has_picked_this_step,
            "picked_count": picked_count,
            "total_players": total_players,
            "finished": finished,
        }

        if finished:
            state["collections"] = draft["collections"]

        return state

    def validate_config(self, message: dict) -> dict:
        cube_key = message.get("cube_key")
        pack_count = int(message.get("pack_count", 0))
        cards_per_pack = int(message.get("cards_per_pack", 0))

        if not cube_key or (not database.get_cube_by_id(cube_key) and not cube_key.startswith("custom_")):
            raise ValueError("Cube inválido.")
        if pack_count < 1 or pack_count > 4:
            raise ValueError("Cantidad de sobres inválida (1-4).")
        if cards_per_pack < 3 or cards_per_pack > 9:
            raise ValueError("Cantidad de cartas por sobre inválida (3-9).")

        return {
            "cube_key":       cube_key,
            "pack_count":     pack_count,
            "cards_per_pack": cards_per_pack,
        }

    def start_game(self, session: dict) -> None:
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

    async def handle_action(
        self,
        session: dict,
        username: str,
        action: str,
        message: dict,
        websocket: Any,
        manager: Any
    ) -> bool:
        session_id = session["id"]

        if action == "configure_mode":
            if username != session["host"]:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "Solo el host puede configurar el modo."}
                })
                return True

            try:
                config = self.validate_config(message)
            except ValueError as e:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": str(e)}
                })
                return True

            session["mode_config"] = config
            await manager.broadcast(session_id, {
                "event": "mode_configured",
                "data":  {
                    "host":        session["host"],
                    "players":     session["players"],
                    "mode":         session["mode"],
                    "mode_name":    self.name,
                    "mode_config":  session["mode_config"],
                },
            })
            return True

        elif action == "start_draft":
            if username != session["host"]:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "Solo el host puede iniciar el draft."}
                })
                return True

            if not session.get("mode_config"):
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "Falta configurar el modo de draft."}
                })
                return True

            if session["started"]:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "La partida ya ha comenzado."}
                })
                return True

            self.start_game(session)
            session["started"] = True

            await manager.broadcast(session_id, {
                "event": "draft_started",
                "data":  {
                    "host":        session["host"],
                    "players":     session["players"],
                    "mode":         session["mode"],
                    "mode_name":    self.name,
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
            return True

        elif action == "draft_pick_card":
            draft = session.get("draft")
            if not draft or draft.get("finished"):
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "No hay draft activo."}
                })
                return True

            card_name = message.get("card_name")

            if draft["picks_in_step"].get(username) is not None:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "Ya elegiste tu carta en este turno. Esperando a los demás..."}
                })
                return True

            user_pack = draft["current_packs"].get(username)
            if not user_pack:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "No tienes un sobre asignado."}
                })
                return True

            card = next((c for c in user_pack["cards"] if c["name"] == card_name), None)
            if not card:
                await manager.send_personal(websocket, {
                    "event": "error",
                    "data":  {"message": "Carta no encontrada en tu sobre."}
                })
                return True

            user_pack["cards"].remove(card)
            draft["collections"].setdefault(username, []).append(card)
            draft["picks_in_step"][username] = card

            await manager.send_personal(websocket, {
                "event": "draft_pick_confirmed",
                "data": {
                    "card":           card,
                    "round":          draft["current_round"],
                    "step":           draft["current_step"],
                    "collection":     draft["collections"][username],
                }
            })

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

            if picked_count >= total_players:
                first_user = draft["picker_order"][0]
                remaining_in_pack = len(draft["current_packs"][first_user]["cards"])

                if remaining_in_pack > 0:
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
                        draft["finished"] = True
                        await manager.broadcast(session_id, {
                            "event": "draft_complete",
                            "data": {
                                "collections": draft["collections"],
                            }
                        })
            return True

        return False
