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


ITEM_SHOP_PRICES = {
    "Capsula Habilidad": 2500,
    "MT Earthquake": 2000,
    "MT Ice Beam": 2000,
    "MT Flamethrower": 2000,
    "MT Thunderbolt": 2000,
    "MT Psychic": 2000,
    "MT Shadow Ball": 2000,
    "MT Protect": 1500,
    "MT Substitute": 2000,
    "MT Swords Dance": 2000,
    "MT Calm Mind": 2000,
    "Leftovers": 1200,
    "Life Orb": 1800,
    "Choice Band": 2000,
    "Choice Specs": 2000,
    "Choice Scarf": 2000,
    "Eviolite": 1500,
    "Rocky Helmet": 1400,
    "Heavy-Duty Boots": 1600,
    "Focus Sash": 1700,
    "Assault Vest": 1800,
    "Fire Stone": 2000,
    "Water Stone": 2000,
    "Thunder Stone": 2000,
    "Leaf Stone": 2000,
    "Moon Stone": 2000,
    "Sun Stone": 2000,
    "Shiny Stone": 2000,
    "Dusk Stone": 2000,
    "Dawn Stone": 2000,
    "Ice Stone": 2000,
}


def normalize_item_inventory(items: Any) -> Dict[str, int]:
    if items is None:
        return {}
    if isinstance(items, dict):
        return {str(k): int(v) for k, v in items.items() if int(v) > 0}
    if isinstance(items, list):
        counts: Dict[str, int] = {}
        for item in items:
            name = str(item)
            counts[name] = counts.get(name, 0) + 1
        return counts
    return {}


def add_item_to_inventory(player: dict, item_name: str, qty: int = 1):
    item_name = str(item_name)
    if not item_name:
        return
    items = normalize_item_inventory(player.get("items", {}))
    items[item_name] = items.get(item_name, 0) + qty
    player["items"] = {k: v for k, v in sorted(items.items()) if v > 0}


def remove_item_from_inventory(player: dict, item_name: str, qty: int = 1):
    item_name = str(item_name)
    if not item_name:
        return
    items = normalize_item_inventory(player.get("items", {}))
    current = items.get(item_name, 0)
    if current <= 0:
        return
    new_qty = max(0, current - qty)
    if new_qty <= 0:
        items.pop(item_name, None)
    else:
        items[item_name] = new_qty
    player["items"] = {k: v for k, v in sorted(items.items()) if v > 0}


def add_tm_to_pokemon(pokemon: dict, move_name: str) -> bool:
    """Añade permanentemente una MT al movepool del Pokémon."""
    learned_tm_moves = pokemon.setdefault("learned_tm_moves", [])
    selected_moves = pokemon.get("selected_moves") or []
    if move_name in learned_tm_moves or move_name in selected_moves:
        return False
    if move_name not in pokemon.get("tm_moves", []):
        return False

    learned_tm_moves.append(move_name)
    level_up_moves = pokemon.setdefault("level_up_moves", [])
    if not any(move.get("name") == move_name for move in level_up_moves):
        level_up_moves.append({"name": move_name, "level": 0, "source": "tm"})
    return True


def assign_item_to_pokemon(player: dict, pok_idx: int, item_name: str) -> bool:
    if item_name == "Capsula Habilidad":
        return False
    if pok_idx < 0 or pok_idx >= len(player.get("pokemon", [])):
        return False
    inventory = normalize_item_inventory(player.get("items", {}))
    if item_name not in inventory or inventory[item_name] <= 0:
        return False

    poke = player["pokemon"][pok_idx]
    current_item = poke.get("item") or poke.get("held_item")
    if current_item and current_item != item_name:
        add_item_to_inventory(player, current_item)

    if current_item == item_name:
        return True

    remove_item_from_inventory(player, item_name)
    poke["item"] = item_name
    poke["held_item"] = item_name
    return True


def remove_item_from_pokemon(player: dict, pok_idx: int) -> bool:
    if pok_idx < 0 or pok_idx >= len(player.get("pokemon", [])):
        return False

    poke = player["pokemon"][pok_idx]
    current_item = poke.get("item") or poke.get("held_item")
    if not current_item:
        return False

    add_item_to_inventory(player, current_item)
    poke["item"] = None
    poke["held_item"] = None
    return True


def init_subasta_round(session: dict):
    """Inicializa una nueva ronda de subasta para un Pokémon."""
    subasta_state = session["subasta"]
    current_year = subasta_state["current_year"]
    level_cap = get_year_level_cap(current_year)

    year_tiers = subasta_state.get("year_tiers", {1: "normal", 2: "normal", 3: "legendary"})
    tier = year_tiers.get(current_year, "normal")

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

    year_starting_money = subasta_state.get("year_starting_money", {}).get(
        current_year,
        subasta_state.get("starting_money", 10000)
    )
    pok_per_player = max(1, subasta_state.get("pok_per_player", 2))
    buyout_price = max(1000, int((year_starting_money * 2) / pok_per_player))

    subasta_state["current_auction"] = {
        "pokemon": poke_data,
        "base_price": base_price,
        "current_bid": base_price,
        "high_bidder": assigned_host_player,
        "assigned_player": assigned_host_player,
        "folded_players": [],
        "buyout_multiplier": subasta_state.get("buyout_multiplier", 10.0),
        "buyout_price": buyout_price,
        "secret_fee": subasta_state.get("secret_fee", 500),
        "hints": poke_api.get_hints_for_multiplier(poke_data, 1.0),
        "finished": False,
        "winner": None,
        "awaiting_secret_choice": False,
        "reveal_hold_until": None,
        "publicly_revealed": False
    }


def evolve_single_pokemon(poke: dict, max_lvl: int) -> bool:
    """Evoluciona un Pokémon y conserva los cuatro movimientos elegidos."""
    evo_map = EVOLUTION_MAP_LVL_40 if max_lvl == 40 else EVOLUTION_MAP_LVL_100
    current_name = poke.get("name")
    current_item = poke.get("item") or poke.get("held_item")
    current_nature = poke.get("nature")
    target_name = poke_api.get_pokemon_evolution_target(current_name, max_lvl)
    if not target_name:
        target_name = evo_map.get(current_name)

    if not target_name:
        poke["level"] = max_lvl
        return False

    updated = poke_api.fetch_pokemon_data(target_name, level_cap=max_lvl)
    previous_selected = poke.get("selected_moves", []) or []
    previous_tm_moves = poke.get("learned_tm_moves", []) or [
        move.get("name")
        for move in (poke.get("level_up_moves", []) or [])
        if move.get("source") == "tm" and move.get("name")
    ]
    previous_moves_by_name = {
        move.get("name"): move
        for move in (poke.get("level_up_moves", []) or [])
        if move.get("name")
    }
    evolution_moves = updated.get("level_up_moves", [])
    evolution_move_names = {move.get("name") for move in evolution_moves}
    inherited_moves = [
        previous_moves_by_name.get(move_name, {"name": move_name, "level": 0})
        for move_name in previous_selected
        if move_name not in evolution_move_names
    ]
    inherited_tm_moves = [
        previous_moves_by_name.get(move_name, {"name": move_name, "level": 0, "source": "tm"})
        for move_name in previous_tm_moves
        if move_name not in evolution_move_names and move_name not in previous_selected
    ]
    merged_level_up_moves = inherited_moves + inherited_tm_moves + evolution_moves
    for move in merged_level_up_moves:
        if move.get("name") in previous_tm_moves:
            move["level"] = 0
            move["source"] = "tm"

    original_abilities = poke.get("abilities") or []
    original_ability = poke.get("ability")
    original_slot = poke.get("ability_slot")
    if original_slot is None and original_ability in original_abilities:
        original_index = original_abilities.index(original_ability)
        original_slot = (poke.get("ability_slots") or [])[original_index] if original_index < len(poke.get("ability_slots") or []) else original_index + 1
    evo_abilities = updated.get("abilities") or []
    if evo_abilities:
        evo_slots = updated.get("ability_slots") or list(range(1, len(evo_abilities) + 1))
        evo_index = evo_slots.index(original_slot) if original_slot in evo_slots else 0
        updated["ability"] = evo_abilities[evo_index]
        updated["ability_slot"] = evo_slots[evo_index]

    evolution_details = poke_api.get_pokemon_evolution_details(updated["name"], max_level=max_lvl)
    next_evolution = evolution_details.get("target") if evolution_details else None
    next_level = evolution_details.get("level") if evolution_details else None
    evolution_trade = bool(evolution_details and evolution_details.get("trade"))
    received_by_trade = bool(poke.get("received_by_trade"))
    poke.clear()
    poke.update({
        "id": updated.get("id"),
        "name": updated["name"],
        "region": updated.get("region", "Desconocida"),
        "types": updated.get("types", []),
        "primary_type": updated.get("primary_type", updated.get("types", ["Normal"])[0] if updated.get("types") else "Normal"),
        "abilities": updated.get("abilities", []),
        "ability_slots": updated.get("ability_slots", []),
        "ability": updated.get("ability", updated.get("abilities", ["Desconocida"])[0]),
        "ability_slot": updated.get("ability_slot", 1),
        "nature": current_nature or updated.get("nature", "Hardy"),
        "stats": updated.get("stats", {}),
        "highest_stat": updated.get("highest_stat", "HP (50)"),
        "image_url": updated.get("image_url", ""),
        "level": max_lvl,
        "level_up_moves": merged_level_up_moves,
        "learned_tm_moves": previous_tm_moves,
        "selected_moves": previous_selected[:4] if previous_selected else updated.get("selected_moves", []),
        "item": current_item,
        "held_item": current_item,
        "can_evolve": bool(next_evolution) and (not evolution_trade or received_by_trade) and (next_level is None or next_level <= max_lvl),
        "evolution_target": next_evolution,
        "next_evolution_level": next_level,
        "evolution_item": evolution_details.get("item") if evolution_details else None,
        "evolution_trade": evolution_trade,
        "received_by_trade": received_by_trade,
    })
    return True


def refresh_pokemon_evolution_status(poke: dict, max_lvl: int):
    """Actualiza si el Pokémon puede evolucionar al cambiar de año."""
    evolution_details = poke_api.get_pokemon_evolution_details(poke.get("name"), max_level=max_lvl)
    target_name = evolution_details.get("target") if evolution_details else None
    next_level = evolution_details.get("level") if evolution_details else None
    requires_trade = bool(evolution_details and evolution_details.get("trade"))
    poke["can_evolve"] = bool(target_name) and (not requires_trade or poke.get("received_by_trade")) and (next_level is None or next_level <= max_lvl)
    poke["evolution_target"] = target_name
    poke["next_evolution_level"] = next_level
    poke["evolution_item"] = evolution_details.get("item") if evolution_details else None
    poke["evolution_trade"] = requires_trade
    return poke["can_evolve"]


def evolve_player_pokemon(player_state: dict, max_lvl: int):
    """Evoluciona los Pokémon del jugador y actualiza su nivel al máximo del año."""
    evo_map = EVOLUTION_MAP_LVL_40 if max_lvl == 40 else EVOLUTION_MAP_LVL_100
    for poke in player_state.get("pokemon", []):
        current_name = poke.get("name")
        target_name = evo_map.get(current_name, current_name)

        if target_name != current_name:
            evolve_single_pokemon(poke, max_lvl)
        else:
            poke["level"] = max_lvl
            if "selected_moves" not in poke or not poke["selected_moves"]:
                poke["selected_moves"] = []

            current_moves = poke.get("level_up_moves") or []
            if current_moves:
                poke["level_up_moves"] = [
                    m for m in current_moves if m.get("level", 0) <= max_lvl
                ]

            refresh_pokemon_evolution_status(poke, max_lvl)



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
                "items": normalize_item_inventory(p_info.get("items", {})),
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
            "match_history": subasta_state.get("match_history", []),
            "event_finished": subasta_state.get("event_finished", False),
            "trade_session": subasta_state.get("trade_session")
        }

    def validate_config(self, message: dict) -> dict:
        starting_money = int(message.get("starting_money", message.get("year_starting_money_1", 100000)))
        turns_per_year = int(message.get("turns_per_year", 3))
        pok_per_player = int(message.get("pok_per_player", 8))
        buyout_multiplier = float(message.get("buyout_multiplier", 10.0))
        secret_fee = int(message.get("secret_fee", 500))

        year_starting_money = {
            1: int(message.get("year_starting_money_1", starting_money)),
            2: int(message.get("year_starting_money_2", 5000)),
            3: int(message.get("year_starting_money_3", 7500)),
        }

        year_tiers = {
            1: str(message.get("year1_tier", message.get("year_tiers", {}).get(1, "normal"))).lower(),
            2: str(message.get("year2_tier", message.get("year_tiers", {}).get(2, "normal"))).lower(),
            3: str(message.get("year3_tier", message.get("year_tiers", {}).get(3, "legendary"))).lower(),
        }

        allowed_tiers = {"normal", "mega", "legendary"}
        for year, tier in year_tiers.items():
            if tier not in allowed_tiers:
                raise ValueError(f"El tipo de subasta del Año {year} no es válido: {tier}")

        return {
            "starting_money": starting_money,
            "turns_per_year": turns_per_year,
            "pok_per_player": pok_per_player,
            "buyout_multiplier": buyout_multiplier,
            "secret_fee": secret_fee,
            "year_starting_money": year_starting_money,
            "year_tiers": year_tiers,
            "year_starting_money_1": year_starting_money[1],
            "year_starting_money_2": year_starting_money[2],
            "year_starting_money_3": year_starting_money[3],
            "year1_tier": year_tiers[1],
            "year2_tier": year_tiers[2],
            "year3_tier": year_tiers[3],
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
            "year_starting_money": config.get("year_starting_money", {1: config["starting_money"], 2: 5000, 3: 7500}),
            "year_tiers": config.get("year_tiers", {1: "normal", 2: "normal", 3: "legendary"}),
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
            "trade_session": None,
            "standings": [{"username": u, "points": 0} for u in order],
            "match_history": [],
            "event_finished": False
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
                if event.get("granted_pokemon"):
                    granted_pokemon = poke_api.fetch_pokemon_data(
                        event["granted_pokemon"],
                        level_cap=get_year_level_cap(subasta_state.get("current_year", 1)),
                    )
                    granted_pokemon["is_hidden"] = False
                    player.setdefault("pokemon", []).append(granted_pokemon)
                    summary["pokemon_count"] = len(player["pokemon"])
                player["resolved_turn"] = True

                self._advance_after_event_resolution(subasta_state)

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_change_nature":
            current_stage = subasta_state["current_stage"]
            if current_stage not in (3, 7, 11):
                return True

            player = subasta_state["players"].get(username)
            event = subasta_state["current_turn_events"].get(username)
            poke_idx = message.get("poke_index")
            nature = message.get("nature")

            if not player or not event or player.get("resolved_turn") or event.get("type") != "nature_change":
                return True
            if not isinstance(poke_idx, int) or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido."}})
                return True
            if nature not in poke_api.POKEMON_NATURES:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona una naturaleza válida."}})
                return True

            poke = player["pokemon"][poke_idx]
            if nature == poke.get("nature"):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Elige una naturaleza distinta a la actual."}})
                return True

            poke["nature"] = nature
            player["resolved_turn"] = True
            self._advance_after_event_resolution(subasta_state)
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
                if next_stage not in (4, 8, 12, 13):
                    subasta_state["trade_session"] = None

                # Transiciones especiales (Inicio de Año 2 y 3)
                if next_stage == 5:  # Inicio Año 2
                    subasta_state["current_year"] = 2
                    year_money = subasta_state.get("year_starting_money", {}).get(2, 5000)
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 40)
                    next_stage = 6  # Salta a Subasta Año 2
                    subasta_state["current_stage"] = next_stage
                    init_subasta_round(session)

                elif next_stage == 9:  # Inicio Año 3
                    subasta_state["current_year"] = 3
                    year_money = subasta_state.get("year_starting_money", {}).get(3, 7500)
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
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

            if subasta_state["current_stage"] not in (4, 8, 12):
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

        elif action == "subasta_finalize_event":
            if username != session["host"]:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo el host puede finalizar la fase."}})
                return True

            current_stage = subasta_state["current_stage"]
            if current_stage not in (4, 8, 12):
                return True

            subasta_state["trade_session"] = None

            if current_stage == 12:
                subasta_state["current_stage"] = 13
                subasta_state["event_finished"] = True
            else:
                subasta_state["current_stage"] = current_stage + 1
                if subasta_state["current_stage"] == 5:
                    subasta_state["current_year"] = 2
                    year_money = subasta_state.get("year_starting_money", {}).get(2, 5000)
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 40)
                    subasta_state["current_stage"] = 6
                    init_subasta_round(session)
                elif subasta_state["current_stage"] == 9:
                    subasta_state["current_year"] = 3
                    year_money = subasta_state.get("year_starting_money", {}).get(3, 7500)
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 100)
                    subasta_state["current_stage"] = 10
                    init_subasta_round(session)

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_trade_start":
            if subasta_state.get("current_stage") not in (4, 8, 12, 13):
                return True
            player = subasta_state["players"].get(username)
            target_username = message.get("target_username")
            poke_idx = int(message.get("poke_index", -1))
            inventory = normalize_item_inventory(player.get("items", {})) if player else {}
            if subasta_state.get("trade_session"):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Ya hay un intercambio en curso."}})
                return True
            if not player or target_username not in subasta_state["players"] or target_username == username:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "El jugador elegido no es válido."}})
                return True
            if inventory.get("Cable Link", 0) <= 0 or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Necesitas un Cable Link y un Pokémon válido."}})
                return True
            offered = player["pokemon"][poke_idx].copy()
            subasta_state["trade_session"] = {
                "status": "selecting",
                "initiator": username,
                "target": target_username,
                "initiator_poke_index": poke_idx,
                "target_poke_index": None,
                "initiator_pokemon": offered,
                "target_pokemon": None,
                "confirms": {},
            }
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_trade_select":
            trade = subasta_state.get("trade_session")
            player = subasta_state["players"].get(username)
            poke_idx = int(message.get("poke_index", -1))
            if not trade or trade.get("status") != "selecting" or trade.get("target") != username:
                return True
            if not player or not 0 <= poke_idx < len(player.get("pokemon", [])):
                return True
            trade["target_poke_index"] = poke_idx
            trade["target_pokemon"] = player["pokemon"][poke_idx].copy()
            trade["status"] = "confirming"
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_trade_confirm":
            trade = subasta_state.get("trade_session")
            if not trade or trade.get("status") != "confirming" or username not in (trade.get("initiator"), trade.get("target")):
                return True
            trade.setdefault("confirms", {})[username] = True
            if len(trade["confirms"]) == 2:
                initiator = subasta_state["players"][trade["initiator"]]
                target = subasta_state["players"][trade["target"]]
                initiator_idx = trade["initiator_poke_index"]
                target_idx = trade["target_poke_index"]
                if (0 <= initiator_idx < len(initiator["pokemon"]) and
                        0 <= target_idx < len(target["pokemon"]) and
                        normalize_item_inventory(initiator.get("items", {})).get("Cable Link", 0) > 0):
                    initiator_pokemon = initiator["pokemon"][initiator_idx]
                    target_pokemon = target["pokemon"][target_idx]
                    initiator["pokemon"][initiator_idx], target["pokemon"][target_idx] = target_pokemon, initiator_pokemon
                    initiator["pokemon"][initiator_idx]["received_by_trade"] = True
                    target["pokemon"][target_idx]["received_by_trade"] = True
                    target_limit = get_year_level_cap(subasta_state.get("current_year", 1))
                    refresh_pokemon_evolution_status(initiator["pokemon"][initiator_idx], target_limit)
                    refresh_pokemon_evolution_status(target["pokemon"][target_idx], target_limit)
                    remove_item_from_inventory(initiator, "Cable Link")
                    trade["status"] = "completed"
                else:
                    trade["status"] = "cancelled"
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_trade_cancel":
            trade = subasta_state.get("trade_session")
            if not trade or trade.get("status") != "confirming" or username != trade.get("initiator"):
                return True

            subasta_state["trade_session"] = None
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action in ("subasta_item_assign", "subasta_item_equip"):
            item_name = message.get("item_name") or message.get("item")
            poke_idx = int(message.get("pokemon_index", message.get("poke_index", -1)))
            player = subasta_state["players"].get(username)

            if not item_name:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Debes elegir un objeto."}})
                return True
            if not player:
                return True

            if not assign_item_to_pokemon(player, poke_idx, item_name):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes ese objeto o el Pokémon es inválido."}})
                return True

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_use_ability_capsule":
            player = subasta_state["players"].get(username)
            poke_idx = message.get("poke_index")
            ability = message.get("ability")
            inventory = normalize_item_inventory(player.get("items", {})) if player else {}

            if not player or inventory.get("Capsula Habilidad", 0) <= 0:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes una Capsula Habilidad."}})
                return True
            if not isinstance(poke_idx, int) or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido."}})
                return True

            poke = player["pokemon"][poke_idx]
            abilities = poke.get("abilities") or []
            if ability not in abilities:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Esa habilidad no está disponible para este Pokémon."}})
                return True
            if ability == poke.get("ability"):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Elige una habilidad distinta a la actual."}})
                return True

            ability_index = abilities.index(ability)
            ability_slots = poke.get("ability_slots") or []
            poke["ability"] = ability
            poke["ability_slot"] = ability_slots[ability_index] if ability_index < len(ability_slots) else ability_index + 1
            remove_item_from_inventory(player, "Capsula Habilidad")
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_use_tm":
            player = subasta_state["players"].get(username)
            poke_idx = message.get("poke_index")
            item_name = message.get("item_name")
            move_name = poke_api.TM_MOVES.get(item_name)
            inventory = normalize_item_inventory(player.get("items", {})) if player else {}

            if not player or inventory.get(item_name, 0) <= 0 or not move_name:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes esa MT."}})
                return True
            if not isinstance(poke_idx, int) or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido."}})
                return True

            poke = player["pokemon"][poke_idx]
            if move_name not in (poke.get("tm_moves") or []):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Este Pokémon no puede aprender ese movimiento por MT."}})
                return True
            if not add_tm_to_pokemon(poke, move_name):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Este Pokémon ya conoce ese movimiento."}})
                return True

            remove_item_from_inventory(player, item_name)
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_item_remove":
            poke_idx = int(message.get("pokemon_index", message.get("poke_index", -1)))
            player = subasta_state["players"].get(username)

            if not player or not remove_item_from_pokemon(player, poke_idx):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "El Pokémon no tiene un objeto equipado o es inválido."}})
                return True

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_shop_buy":
            stage = subasta_state.get("current_stage")
            if stage not in (4, 8, 12, 13):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "La tienda solo está disponible en las fases de confirmación de Showdown."}})
                return True

            item_name = message.get("item_name")
            if not item_name:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Debes indicar qué objeto quieres comprar."}})
                return True

            player = subasta_state["players"].get(username)
            if not player:
                return True

            price = ITEM_SHOP_PRICES.get(item_name, 1500)
            if player["money"] < price:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes suficiente dinero para comprar ese objeto."}})
                return True

            player["money"] -= price
            add_item_to_inventory(player, item_name)
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

        elif action == "subasta_evolve_pokemon":
            poke_idx = int(message.get("poke_index", 0))
            player = subasta_state["players"].get(username)

            if player and 0 <= poke_idx < len(player.get("pokemon", [])):
                poke = player["pokemon"][poke_idx]
                current_level = poke.get("level", 1)
                target_year = subasta_state.get("current_year", 1)
                target_limit = 40 if target_year == 2 else 100
                evolution_details = poke_api.get_pokemon_evolution_details(poke.get("name"), max_level=target_limit)
                evolution_item = evolution_details.get("item") if evolution_details else None
                evolution_level = evolution_details.get("level") if evolution_details else None
                requires_trade = bool(evolution_details and evolution_details.get("trade"))
                inventory = normalize_item_inventory(player.get("items", {}))

                if not evolution_details:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": "Este Pokémon no tiene una evolución disponible."}})
                    return True
                if requires_trade and not poke.get("received_by_trade"):
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": "Este Pokémon debe llegar mediante un intercambio."}})
                    return True
                if evolution_item and inventory.get(evolution_item, 0) <= 0:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": f"Necesitas {evolution_item} para evolucionar este Pokémon."}})
                    return True
                if evolution_level is not None and current_level < evolution_level:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": f"Este Pokémon necesita llegar al nivel {evolution_level}."}})
                    return True
                if not evolution_item and current_level < target_limit:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": "Tu Pokémon aún no está listo para evolucionar."}})
                    return True

                if evolve_single_pokemon(poke, target_limit):
                    if evolution_item:
                        remove_item_from_inventory(player, evolution_item)
                    poke["selected_moves"] = (poke.get("selected_moves", []) or [])[:4]

                save_game_session(session_id, self.key, subasta_state)
                await self._broadcast_subasta_state(session, manager)
            return True

        return False


    def _generate_turn_events(self, subasta_state: dict):
        """Genera un nuevo evento para cada jugador en el turno actual."""
        year = subasta_state["current_year"]
        turn = subasta_state.get("current_turn", 1)
        subasta_state["current_turn_events"] = {
            u: events_data.get_random_event_for_year(year, turn) for u in subasta_state["players"].keys()
        }

    def _advance_after_event_resolution(self, subasta_state: dict):
        if not all(p.get("resolved_turn") for p in subasta_state["players"].values()):
            return
        if subasta_state["current_turn"] < subasta_state["turns_per_year"]:
            subasta_state["current_turn"] += 1
            for player in subasta_state["players"].values():
                player["resolved_turn"] = False
            self._generate_turn_events(subasta_state)
        else:
            subasta_state["current_stage"] += 1

    async def _broadcast_subasta_state(self, session: dict, manager: Any):
        """Envía a cada jugador conectado su estado formateado."""
        session_id = session["id"]
        for user in session["subasta"]["player_order"]:
            state_for_user = self.get_player_sync_state(session, user)
            await manager.send_personal_to_user(session_id, user, {
                "event": "subasta_state_update",
                "data": state_for_user
            })
