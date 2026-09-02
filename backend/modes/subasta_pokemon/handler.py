"""
backend/modes/subasta_pokemon/handler.py - Implementación completa del modo Subasta Pokémon
"""

import asyncio
import random
import time
from typing import Dict, List, Any, Optional
from backend.modes.base import BaseGameMode
from backend.modes.subasta_pokemon import poke_api, events_data, showdown
from backend.database import save_game_session, get_game_session
from backend.services.session_manager import get_connected_player_order

# Mapeo de etapas (1 a 13)
STAGE_NAMES = {
    1: "Lobby & Configuración",
    2: "Año 1: Subasta Inicial",
    3: "Año 1: Eventos de Turno",
    4: "Año 1: Exportar Equipos (Showdown)",
    5: "Año 2: Inicio & Evoluciones (Lvl 40)",
    6: "Año 2: Segunda Subasta",
    7: "Año 2: Eventos de Turno",
    8: "Año 2: Exportar Equipos (Showdown)",
    9: "Año 3: Inicio & Evoluciones (Lvl 100)",
    10: "Año 3: Última Subasta",
    11: "Año 3: Eventos de Turno",
    12: "Año 3: Exportar Equipos Definitivos",
    13: "Resultados Finales & Podio"
}

# Evoluciones simuladas para niveles 40 y 100
EVOLUTION_MAP_LVL_40 = {
    "Pikachu": "Raichu", "Charmander": "Charmeleon", "Charmeleon": "Charizard",
    "Squirtle": "Wartortle", "Wartortle": "Blastoise", "Bulbasaur": "Ivysaur",
    "Ivysaur": "Venusaur", "Gastly": "Haunter", "Haunter": "Gengar",
    "Riolu": "Lucario", "Dratini": "Dragonair", "Dragonair": "Dragonite",
    "Larvitar": "Pupitar", "Bagon": "Shelgon", "Gible": "Gabite"
}

EVOLUTION_MAP_LVL_100 = {
    "Pupitar": "Tyranitar", "Shelgon": "Salamence", "Gabite": "Garchomp",
    "Beldum": "Metagross", "Metang": "Metagross"
}


def get_year_level_cap(year: int) -> int:
    if year == 1:
        return 20
    elif year == 2:
        return 40
    return 100


def init_subasta_round(session: dict):
    """Inicializa una nueva ronda de subasta para un Pokémon."""
    subasta_state = session["subasta"]
    current_year = subasta_state["current_year"]
    level_cap = get_year_level_cap(current_year)

    tier = "normal"
    if current_year == 2:
        tier = random.choice(["normal", "mega"])
    elif current_year == 3:
        tier = random.choice(["mega", "legendary"])

    poke_data = poke_api.get_random_pokemon_from_tier(tier, year=current_year, level_cap=level_cap)

    # Determinar precio inicial base
    base_price = 1000
    if tier == "mega":
        base_price = 2000
    elif tier == "legendary":
        base_price = 3500

    order = subasta_state["player_order"]
    turn_idx = subasta_state["auction_turn_index"] % len(order)
    assigned_host_player = order[turn_idx]

    subasta_state["current_auction"] = {
        "pokemon": poke_data,
        "base_price": base_price,
        "current_bid": base_price,
        "high_bidder": assigned_host_player,
        "assigned_player": assigned_host_player,
        "folded_players": [],
        "buyout_multiplier": subasta_state.get("buyout_multiplier", 10.0),
        "buyout_price": int(base_price * subasta_state.get("buyout_multiplier", 10.0)),
        "secret_fee": subasta_state.get("secret_fee", 500),
        "hints": poke_api.get_hints_for_multiplier(poke_data, 1.0),
        "finished": False,
        "winner": None,
        "awaiting_secret_choice": False,
        "reveal_hold_until": None,
        "publicly_revealed": False
    }


def evolve_player_pokemon(player_state: dict, max_lvl: int):
    """Evoluciona los Pokémon del jugador y actualiza su nivel al máximo del año."""
    evo_map = EVOLUTION_MAP_LVL_40 if max_lvl == 40 else EVOLUTION_MAP_LVL_100
    for poke in player_state.get("pokemon", []):
        current_name = poke.get("name")
        target_name = evo_map.get(current_name, current_name)

        if target_name != current_name:
            updated = poke_api.fetch_pokemon_data(target_name, level_cap=max_lvl)
            poke.update({
                "name": updated["name"],
                "region": updated["region"],
                "types": updated["types"],
                "primary_type": updated["primary_type"],
                "abilities": updated["abilities"],
                "image_url": updated["image_url"],
                "level": max_lvl,
                "level_up_moves": updated["level_up_moves"],
                "selected_moves": updated.get("selected_moves", poke.get("selected_moves", []))
            })
        else:
            poke["level"] = max_lvl
            if "selected_moves" not in poke or not poke["selected_moves"]:
                poke["selected_moves"] = []

            current_moves = poke.get("level_up_moves") or []
            if current_moves:
                poke["level_up_moves"] = [
                    m for m in current_moves if m.get("level", 0) <= max_lvl
                ]



class SubastaPokemonMode(BaseGameMode):
    reveal_hold_seconds = 5

    @property
    def key(self) -> str:
        return "subasta_pokemon"

    async def _advance_after_reveal_delay(self, session: dict, session_id: str, manager: Any):
        await asyncio.sleep(self.reveal_hold_seconds)

        subasta_state = session.get("subasta")
        if not subasta_state:
            return

        auction = subasta_state.get("current_auction")
        if not auction:
            return

        if auction.get("winner") is None:
            return

        # Si el descanso de revelado ya terminó, se pasa a la siguiente ronda.
        target = subasta_state["pok_per_player"] * subasta_state["current_year"]
        all_done = all(len(p["pokemon"]) >= target for p in subasta_state["players"].values())

        if all_done:
            subasta_state["current_stage"] += 1
            subasta_state["current_turn"] = 1
            self._generate_turn_events(subasta_state)
        else:
            init_subasta_round(session)

        save_game_session(session_id, self.key, subasta_state)
        await self._broadcast_subasta_state(session, manager)

    @property
    def name(self) -> str:
        return "Subasta (Pokemon)"

    @property
    def requires_cubes(self) -> bool:
        return False

    def get_public_config_options(self, session: dict) -> Dict[str, Any]:
        return {
            "default_starting_money": 100000,
            "default_turns_per_year": 3,
            "default_pok_per_player": 8,
            "default_buyout_multiplier": 10.0,
            "default_secret_fee": 500,
        }

    def get_player_sync_state(self, session: dict, username: str) -> dict:
        subasta_state = session.get("subasta")
        if not subasta_state:
            return {}

        default_player_data = {
            "money": subasta_state.get("starting_money", 0),
            "pokemon": [],
            "items": [],
            "points": 0
        }
        player_data = subasta_state["players"].get(username, default_player_data)

        current_stage = subasta_state.get("current_stage", 2)
        current_year = subasta_state.get("current_year", 1)
        current_turn = subasta_state.get("current_turn", 1)
        current_auction = subasta_state.get("current_auction", {})

        # Si el Pokémon del rival es secreto, ocultar detalles a otros jugadores
        filtered_players_info = {}
        for u, p_info in subasta_state["players"].items():
            visible_pokes = []
            for p in p_info.get("pokemon", []):
                if p.get("is_hidden") and u != username:
                    visible_pokes.append({
                        "name": "🔒 Pokémon Oculto",
                        "image_url": "",
                        "level": p.get("level", 1),
                        "is_hidden": True
                    })
                else:
                    visible_pokes.append(p)

            filtered_players_info[u] = {
                "money": p_info["money"],
                "pokemon_count": len(p_info["pokemon"]),
                "pokemon": visible_pokes,
                "items": p_info.get("items", []),
                "points": p_info.get("points", 0)
            }

        # Generar export de Showdown si se encuentra en etapas de exportación
        showdown_text = ""
        if current_stage in (4, 8, 12, 13):
            showdown_text = showdown.export_team_to_showdown(
                username, player_data.get("pokemon", []), player_data.get("items", [])
            )

        return {
            "stage": current_stage,
            "stage_name": STAGE_NAMES.get(current_stage, "En Juego"),
            "current_year": current_year,
            "current_turn": current_turn,
            "max_turns": subasta_state.get("turns_per_year", 3),
            "my_data": player_data,
            "all_players": filtered_players_info,
            "current_auction": current_auction,
            "current_turn_event": subasta_state.get("current_turn_events", {}).get(username),
            "showdown_text": showdown_text,
            "standings": subasta_state.get("standings", []),
            "match_history": subasta_state.get("match_history", [])
        }

    def validate_config(self, message: dict) -> dict:
        starting_money = int(message.get("starting_money", 100000))
        turns_per_year = int(message.get("turns_per_year", 3))
        pok_per_player = int(message.get("pok_per_player", 8))
        buyout_multiplier = float(message.get("buyout_multiplier", 10.0))
        secret_fee = int(message.get("secret_fee", 500))

        return {
            "starting_money": starting_money,
            "turns_per_year": turns_per_year,
            "pok_per_player": pok_per_player,
            "buyout_multiplier": buyout_multiplier,
            "secret_fee": secret_fee
        }

    def start_game(self, session: dict) -> None:
        config = session.get("mode_config", {
            "starting_money": 100000,
            "turns_per_year": 3,
            "pok_per_player": 8,
            "buyout_multiplier": 10.0,
            "secret_fee": 500,
        })
        order = get_connected_player_order(session)

        session["subasta"] = {
            "current_stage": 2,  # Pasa directo a Año 1: Subasta Inicial
            "current_year": 1,
            "current_turn": 1,
            "starting_money": config["starting_money"],
            "turns_per_year": config["turns_per_year"],
            "pok_per_player": config["pok_per_player"],
            "buyout_multiplier": config["buyout_multiplier"],
            "secret_fee": config["secret_fee"],
            "player_order": order,
            "auction_turn_index": 0,
            "players": {
                u: {
                    "money": config["starting_money"],
                    "pokemon": [],
                    "items": [],
                    "points": 0,
                    "resolved_turn": False
                } for u in order
            },
            "current_auction": {},
            "current_turn_events": {},
            "standings": [{"username": u, "points": 0} for u in order],
            "match_history": []
        }

        init_subasta_round(session)
        save_game_session(session["id"], self.key, session["subasta"])

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
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo el host puede configurar."}})
                return True

            try:
                config = self.validate_config(message)
            except ValueError as e:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": str(e)}})
                return True

            session["mode_config"] = config
            await manager.broadcast(session_id, {
                "event": "mode_configured",
                "data": {
                    "host": session["host"],
                    "mode": session["mode"],
                    "mode_name": self.name,
                    "mode_config": config
                }
            })
            return True

        elif action == "start_draft":
            if username != session["host"]:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo el host puede iniciar."}})
                return True

            self.start_game(session)
            session["started"] = True

            await manager.broadcast(session_id, {
                "event": "draft_started",
                "data": {"message": "¡Comienza el Modo Subasta Pokémon!"}
            })
            await self._broadcast_subasta_state(session, manager)
            return True

        subasta_state = session.get("subasta")
        if not subasta_state:
            return False

        # ── Acciones de Subasta ──────────────────────────────────────────────
        if action == "subasta_bid":
            bid_amount = int(message.get("bid_amount", 0))
            auction = subasta_state.get("current_auction")
            if not auction or auction.get("finished") or auction.get("winner"):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "La subasta ya terminó."}})
                return True

            player = subasta_state["players"].get(username)
            if not player or player["money"] < bid_amount:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Fondos insuficientes."}})
                return True

            if bid_amount <= auction["current_bid"]:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": f"La puja debe superar los ${auction['current_bid']}."}})
                return True

            auction["current_bid"] = bid_amount
            auction["high_bidder"] = username

            # Actualizar pistas según multiplicador
            multiplier = bid_amount / auction["base_price"]
            auction["hints"] = poke_api.get_hints_for_multiplier(auction["pokemon"], multiplier)

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_fold":
            auction = subasta_state.get("current_auction")
            if not auction or auction.get("finished"):
                return True

            if username == auction.get("high_bidder"):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No puedes retirarte mientras eres el mayor pujador."}})
                return True

            if username not in auction["folded_players"]:
                auction["folded_players"].append(username)

            active_players = [u for u in subasta_state["player_order"] if u not in auction["folded_players"]]
            if len(active_players) <= 1 and auction.get("high_bidder") in active_players:
                winner = auction["high_bidder"]
                auction["winner"] = winner
                auction["awaiting_secret_choice"] = True

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_buyout":
            auction = subasta_state.get("current_auction")
            if not auction or auction.get("finished") or auction.get("winner"):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "La subasta ya terminó."}})
                return True

            buyout_price = auction["buyout_price"]
            player = subasta_state["players"].get(username)
            if not player or player["money"] < buyout_price:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Fondos insuficientes para compra directa."}})
                return True

            auction["current_bid"] = buyout_price
            auction["high_bidder"] = username
            auction["winner"] = username
            auction["finished"] = True
            auction["awaiting_secret_choice"] = True

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_secret_choice":
            auction = subasta_state.get("current_auction")
            if not auction or auction.get("winner") != username:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No eres el ganador de la subasta."}})
                return True

            keep_secret = bool(message.get("keep_secret", False))
            player = subasta_state["players"][username]
            cost = auction["current_bid"]

            if keep_secret:
                if player["money"] >= cost + auction["secret_fee"]:
                    cost += auction["secret_fee"]
                    won_pokemon = auction["pokemon"].copy()
                    won_pokemon["is_hidden"] = True
                    auction["pokemon"]["is_hidden"] = True
                    auction["publicly_revealed"] = False
                else:
                    won_pokemon = auction["pokemon"].copy()
                    won_pokemon["is_hidden"] = False
                    auction["pokemon"]["is_hidden"] = False
                    auction["publicly_revealed"] = True
            else:
                won_pokemon = auction["pokemon"].copy()
                won_pokemon["is_hidden"] = False
                auction["pokemon"]["is_hidden"] = False
                auction["publicly_revealed"] = True

            player["money"] -= cost
            player["pokemon"].append(won_pokemon)
            auction["finished"] = True
            auction["awaiting_secret_choice"] = False
            auction["reveal_hold_until"] = None
            subasta_state["auction_turn_index"] += 1

            # Cuando el ganador elige revelar, damos 5 segundos para que todos lo vean antes de avanzar.
            if not keep_secret:
                auction["reveal_hold_until"] = time.time() + self.reveal_hold_seconds
                auction["pokemon"]["is_hidden"] = False
                auction["publicly_revealed"] = True
                save_game_session(session_id, self.key, subasta_state)
                await self._broadcast_subasta_state(session, manager)
                asyncio.create_task(self._advance_after_reveal_delay(session, session_id, manager))
                return True

            # Verificar si todos los jugadores alcanzaron el cupo de Pokémon del año
            target = subasta_state["pok_per_player"] * subasta_state["current_year"]
            all_done = all(len(p["pokemon"]) >= target for p in subasta_state["players"].values())

            if all_done:
                # Pasar a la etapa de Eventos por Turnos
                subasta_state["current_stage"] += 1
                subasta_state["current_turn"] = 1
                self._generate_turn_events(subasta_state)
            else:
                init_subasta_round(session)

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_resolve_event":
            current_stage = subasta_state["current_stage"]
            if current_stage not in (3, 7, 11):
                return True

            player = subasta_state["players"].get(username)
            event = subasta_state["current_turn_events"].get(username)

            if player and event and not player.get("resolved_turn"):
                summary = events_data.apply_event_to_player(player, event)
                player["resolved_turn"] = True

                # Si todos resolvieron el turno actual
                if all(p.get("resolved_turn") for p in subasta_state["players"].values()):
                    if subasta_state["current_turn"] < subasta_state["turns_per_year"]:
                        subasta_state["current_turn"] += 1
                        for p in subasta_state["players"].values():
                            p["resolved_turn"] = False
                        self._generate_turn_events(subasta_state)
                    else:
                        # Finalizar turnos del año -> Pasar a Etapa de Exportación
                        subasta_state["current_stage"] += 1

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_next_stage":
            if username != session["host"]:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo el host puede avanzar de etapa."}})
                return True

            cur = subasta_state["current_stage"]
            if cur < 13:
                next_stage = cur + 1
                subasta_state["current_stage"] = next_stage

                # Transiciones especiales (Inicio de Año 2 y 3)
                if next_stage == 5:  # Inicio Año 2
                    subasta_state["current_year"] = 2
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += 5000
                        evolve_player_pokemon(p_info, 40)
                    next_stage = 6  # Salta a Subasta Año 2
                    subasta_state["current_stage"] = next_stage
                    init_subasta_round(session)

                elif next_stage == 9:  # Inicio Año 3
                    subasta_state["current_year"] = 3
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += 7500
                        evolve_player_pokemon(p_info, 100)
                    next_stage = 10  # Salta a Subasta Año 3
                    subasta_state["current_stage"] = next_stage
                    init_subasta_round(session)

                elif next_stage in (3, 7, 11):
                    subasta_state["current_turn"] = 1
                    for p in subasta_state["players"].values():
                        p["resolved_turn"] = False
                    self._generate_turn_events(subasta_state)

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_admin_submit_match":
            if username != session["host"]:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo el host puede cargar resultados."}})
                return True

            winner = message.get("winner")
            loser = message.get("loser")

            if winner in subasta_state["players"]:
                subasta_state["players"][winner]["points"] += 3
            if loser in subasta_state["players"]:
                subasta_state["players"][loser]["points"] += 1

            subasta_state.setdefault("match_history", []).append({
                "year": subasta_state["current_year"],
                "winner": winner,
                "loser": loser
            })

            # Recalcular tabla de posiciones
            sorted_standings = sorted(
                [{"username": u, "points": p["points"]} for u, p in subasta_state["players"].items()],
                key=lambda x: x["points"],
                reverse=True
            )
            subasta_state["standings"] = sorted_standings

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_select_moves":
            poke_idx = int(message.get("poke_index", 0))
            selected_moves = message.get("selected_moves", [])
            player = subasta_state["players"].get(username)

            if player and 0 <= poke_idx < len(player.get("pokemon", [])):
                poke = player["pokemon"][poke_idx]
                level_cap = get_year_level_cap(subasta_state["current_year"])
                allowed_moves = [m["name"] for m in poke.get("level_up_moves", []) if m["level"] <= level_cap]

                # Filtrar solo movimientos permitidos
                valid_moves = [m for m in selected_moves if m in allowed_moves][:4]
                if valid_moves:
                    poke["selected_moves"] = valid_moves

                save_game_session(session_id, self.key, subasta_state)
                await self._broadcast_subasta_state(session, manager)
            return True

        return False


    def _generate_turn_events(self, subasta_state: dict):
        """Genera un nuevo evento para cada jugador en el turno actual."""
        year = subasta_state["current_year"]
        subasta_state["current_turn_events"] = {
            u: events_data.get_random_event_for_year(year) for u in subasta_state["players"].keys()
        }

    async def _broadcast_subasta_state(self, session: dict, manager: Any):
        """Envía a cada jugador conectado su estado formateado."""
        session_id = session["id"]
        for user in session["subasta"]["player_order"]:
            state_for_user = self.get_player_sync_state(session, user)
            await manager.send_personal_to_user(session_id, user, {
                "event": "subasta_state_update",
                "data": state_for_user
            })
