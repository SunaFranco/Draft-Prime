"""
backend/modes/subasta_pokemon/handler.py - Implementación completa del modo Subasta Pokémon
"""

import asyncio
import copy
import math
import random
import time
from typing import Dict, List, Any, Optional
from backend.modes.base import BaseGameMode
from backend.modes.subasta_pokemon import poke_api, events_data, showdown
from backend.database import save_game_session, save_full_session, get_game_session
from backend.services.session_manager import get_connected_player_order

_PENDING_BID_SAVES: dict[str, dict] = {}
_BID_SAVE_TASKS: dict[str, asyncio.Task] = {}


def queue_bid_session_save(session: dict) -> None:
    session_id = session["id"]
    _PENDING_BID_SAVES[session_id] = session
    task = _BID_SAVE_TASKS.get(session_id)
    if task is None or task.done():
        _BID_SAVE_TASKS[session_id] = asyncio.create_task(_flush_bid_session_saves(session_id))


async def _flush_bid_session_saves(session_id: str) -> None:
    while True:
        await asyncio.sleep(0.35)
        session = _PENDING_BID_SAVES.pop(session_id, None)
        if session is None:
            _BID_SAVE_TASKS.pop(session_id, None)
            return

        try:
            snapshot = copy.deepcopy(session)
            await asyncio.to_thread(save_full_session, snapshot)
        except Exception as error:
            print(f"[WARNING] No se pudo persistir la puja de la sesión {session_id}: {error}")

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
    "Pikachu": "Raichu"
}

EVOLUTION_MAP_LVL_100 = {
    "Pupitar": "Tyranitar"
}


def get_year_level_cap(year: int) -> int:
    if year == 1:
        return 20
    elif year == 2:
        return 40
    return 100


MIN_BID_INCREMENT = 5000


def calculate_buyout_price(starting_money: int, phase_quota: int) -> int:
    price = max(5000, int((starting_money * 2) / max(1, phase_quota)))
    return ((price + MIN_BID_INCREMENT - 1) // MIN_BID_INCREMENT) * MIN_BID_INCREMENT


def get_pokemon_sell_value(pokemon: dict, subasta_state: dict) -> int:
    buyout_price = pokemon.get("instant_purchase_price")
    if buyout_price is None:
        year = int(pokemon.get("acquisition_year", subasta_state.get("current_year", 1)))
        tier = pokemon.get("acquisition_tier") or ("mega" if poke_api.is_mega_pokemon(pokemon) else "normal")
        year_pools = subasta_state.get("year_pools", {})
        year_pool = year_pools.get(year) or year_pools.get(str(year)) or {}
        phase_quota = year_pool.get(tier) or subasta_state.get("current_phase_quota", 1)
        year_money = subasta_state.get("year_starting_money", {})
        starting_money = year_money.get(year) or year_money.get(str(year)) or subasta_state.get("starting_money", 100000)
        buyout_price = calculate_buyout_price(int(starting_money), int(phase_quota))
    return int(int(buyout_price) * 0.25)

ITEM_SHOP_PRICES = {
    "Caja Misteriosa I": 100000,
    "Caja Misteriosa 1": 100000,
    "Regalo del Primo jeque": 250000,
    "Eviolite": 100000,
    "Sitrus Berry": 50000,
    "MT Fire Punch": 30000,
    "MT Thunder Punch": 30000,
    "MT Ice Punch": 30000,
    "Capsula Habilidad": 150000,
    "Silk Scarf": 50000,
    "Water Stone": 100000,
    "Fire Stone": 100000,
    "Leaf Stone": 100000,
    "Ice Stone": 100000,
    "Thunder Stone": 100000,
    "Moon Stone": 100000,
    "Sun Stone": 100000,
    "Dusk Stone": 100000,
    "Dawn Stone": 100000,
    "Shiny Stone": 100000,
    "Cambia Formas": 75000,
    "Ruleta Plates": 20000,
    "Ruleta Piedras": 20000,
    "Flame Orb": 50000,
    "MT Toxic": 100000,
    "MT Protect": 20000,
    "Life Orb": 100000,
    "Leftovers": 200000,
    "Ruleta Mentas": 30000,
    "Ruleta Choice": 150000,
    "Ruleta MT OP": 100000,
}

PLATE_ITEMS = [
    "Fist Plate",
    "Sky Plate",
    "Flame Plate",
    "Splash Plate",
    "Zap Plate",
    "Meadow Plate",
    "Icicle Plate",
    "Toxic Plate",
    "Earth Plate",
    "Mind Plate",
    "Insect Plate",
    "Stone Plate",
    "Spooky Plate",
    "Draco Plate",
    "Dread Plate",
    "Iron Plate",
    "Pixie Plate",
]

EVOLUTION_STONE_ITEMS = [
    "Fire Stone",
    "Water Stone",
    "Thunder Stone",
    "Leaf Stone",
    "Moon Stone",
    "Sun Stone",
    "Shiny Stone",
    "Dusk Stone",
    "Dawn Stone",
    "Ice Stone",
]

MINT_ITEMS = [
    "Adamant Mint",
    "Bashful Mint",
    "Bold Mint",
    "Brave Mint",
    "Calm Mint",
    "Careful Mint",
    "Docile Mint",
    "Gentle Mint",
    "Hardy Mint",
    "Hasty Mint",
    "Impish Mint",
    "Jolly Mint",
    "Lax Mint",
    "Lonely Mint",
    "Mild Mint",
    "Modest Mint",
    "Naive Mint",
    "Naughty Mint",
    "Quiet Mint",
    "Quirky Mint",
    "Rash Mint",
    "Relaxed Mint",
    "Sassy Mint",
    "Serious Mint",
    "Timid Mint",
]

CHOICE_ITEM_REWARDS = [
    "Choice Scarf",
    "Choice Band",
    "Choice Specs",
]

OVERPOWERED_TM_ITEMS = [
    "MT Earthquake",
    "MT Ice Beam",
    "MT Flamethrower",
    "MT Thunderbolt",
    "MT Shadow Ball",
    "MT Stone Edge",
    "MT U-turn",
    "MT Close Combat",
    "MT Energy Ball",
    "MT Dark Pulse",
    "MT Sludge Bomb",
    "MT Knock Off",
]

YEAR_SHOP_ROULETTES = {
    "Ruleta Plates": PLATE_ITEMS,
    "Ruleta Piedras": EVOLUTION_STONE_ITEMS,
    "Ruleta Mentas": MINT_ITEMS,
    "Ruleta Choice": CHOICE_ITEM_REWARDS,
    "Ruleta MT OP": OVERPOWERED_TM_ITEMS,
}

YEAR_SHOP_ITEMS = {
    1: [
        "Caja Misteriosa I",
        "Regalo del Primo jeque",
        "Eviolite",
        "Sitrus Berry",
        "MT Fire Punch",
        "MT Thunder Punch",
        "MT Ice Punch",
        "Capsula Habilidad",
        "Cambia Formas",
        "Silk Scarf",
        "Water Stone",
        "Fire Stone",
        "Leaf Stone",
        
    ],
    2: [
        "Ruleta Plates",
        "Capsula Habilidad",
        "Cambia Formas",
        "Flame Orb",
        "Sitrus Berry",
        "MT Toxic",
        "MT Protect",
        "Ruleta Piedras",
    ],
    3: [
        "Life Orb",
        "Capsula Habilidad",
        "Ruleta Mentas",
        "Leftovers",
        "Ruleta Choice",
        "Ruleta MT OP",
    ],
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
    poke = player["pokemon"][pok_idx]
    if poke_api.is_mega_pokemon(poke):
        return False
    inventory = normalize_item_inventory(player.get("items", {}))
    if item_name not in inventory or inventory[item_name] <= 0:
        return False

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
    if poke_api.is_mega_pokemon(poke):
        return False
    current_item = poke.get("item") or poke.get("held_item")
    if not current_item:
        return False

    add_item_to_inventory(player, current_item)
    poke["item"] = None
    poke["held_item"] = None
    return True


def get_year_active_phases(year_pools: dict, year: int) -> List[dict]:
    pools = year_pools.get(year) or year_pools.get(str(year)) or {"normal": 2, "mega": 0, "legendary": 0}
    phases = []
    for tier in ("normal", "mega", "legendary"):
        cnt = int(pools.get(tier, 0))
        if cnt > 0:
            phases.append({"tier": tier, "count": cnt})
    return phases


def setup_year_auction_phases(subasta_state: dict, year: int) -> bool:
    """Configura las sub-fases de pools para el año dado. Retorna True si hay fases activas, False si no hay."""
    active_phases = get_year_active_phases(subasta_state.get("year_pools", {}), year)
    subasta_state["current_year_phases"] = active_phases
    subasta_state["current_pool_phase_index"] = 0
    all_players = subasta_state.get("player_order", list(subasta_state.get("players", {}).keys()))

    if not active_phases:
        subasta_state["current_phase_tier"] = "normal"
        subasta_state["current_phase_quota"] = 0
        subasta_state["phase_pokemon_won"] = {u: 0 for u in all_players}
        return False

    first_phase = active_phases[0]
    subasta_state["current_phase_tier"] = first_phase["tier"]
    subasta_state["current_phase_quota"] = first_phase["count"]
    subasta_state["phase_pokemon_won"] = {u: 0 for u in all_players}
    return True


async def init_subasta_round(session: dict):
    """Inicializa una nueva ronda de subasta para un Pokémon."""
    subasta_state = session["subasta"]
    current_year = subasta_state["current_year"]
    level_cap = get_year_level_cap(current_year)

    tier = subasta_state.get("current_phase_tier", "normal")

    poke_data = await asyncio.to_thread(
        poke_api.get_random_pokemon_from_tier,
        tier,
        current_year,
        level_cap,
    )
    poke_data["is_shiny"] = random.random() < 0.01
    if poke_data["is_shiny"] and poke_data.get("shiny_image_url"):
        poke_data["image_url"] = poke_data["shiny_image_url"]

    # Determinar precio inicial base en múltiplos de 5k
    base_price = 50000
    if tier == "mega":
        base_price = 80000
    elif tier == "legendary":
        base_price = 100000

    order = subasta_state["player_order"]
    turn_idx = subasta_state["auction_turn_index"] % len(order)
    assigned_host_player = order[turn_idx]

    year_starting_money = subasta_state.get("year_starting_money", {}).get(
        current_year,
        subasta_state.get("starting_money", 100000)
    )
    phase_quota = max(1, subasta_state.get("current_phase_quota", 2))
    buyout_price = calculate_buyout_price(year_starting_money, phase_quota)

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
        "publicly_revealed": False,
        "phase_tier": tier,
        "phase_quota": phase_quota,
    }


def evolve_single_pokemon(poke: dict, max_lvl: int, target_name: Optional[str] = None) -> bool:
    """Evoluciona un Pokémon y conserva los cuatro movimientos elegidos."""
    evo_map = EVOLUTION_MAP_LVL_40 if max_lvl == 40 else EVOLUTION_MAP_LVL_100
    current_name = poke.get("name")
    current_item = poke.get("item") or poke.get("held_item")
    current_nature = poke.get("nature")
    was_shiny = bool(poke.get("is_shiny"))
    if not target_name:
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

    evolution_options = poke_api.get_pokemon_all_evolution_options(updated["name"], max_level=100)
    formatted_options = [
        {
            "target": opt["target"].capitalize() if opt.get("target") else "",
            "level": opt.get("level"),
            "item": opt.get("item"),
            "trade": bool(opt.get("trade")),
            "friendship": bool(opt.get("friendship")),
        }
        for opt in evolution_options
    ]
    evolution_details = evolution_options[0] if evolution_options else None
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
        "shiny_image_url": updated.get("shiny_image_url", ""),
        "is_shiny": was_shiny,
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
        "evolution_options": formatted_options,
        "received_by_trade": received_by_trade,
    })
    if was_shiny and poke.get("shiny_image_url"):
        poke["image_url"] = poke["shiny_image_url"]
    return True


def refresh_pokemon_evolution_status(poke: dict, max_lvl: int):
    """Actualiza si el Pokémon puede evolucionar al cambiar de año."""
    evolution_options = poke_api.get_pokemon_all_evolution_options(poke.get("name"), max_level=max_lvl)
    evolution_details = evolution_options[0] if evolution_options else None
    target_name = evolution_details.get("target") if evolution_details else None
    next_level = evolution_details.get("level") if evolution_details else None
    requires_trade = bool(evolution_details and evolution_details.get("trade"))
    poke["can_evolve"] = bool(target_name) and (not requires_trade or poke.get("received_by_trade")) and (next_level is None or next_level <= max_lvl)
    poke["evolution_target"] = target_name
    poke["next_evolution_level"] = next_level
    poke["evolution_item"] = evolution_details.get("item") if evolution_details else None
    poke["evolution_trade"] = requires_trade
    poke["evolution_options"] = [
        {
            "target": opt["target"].capitalize() if opt.get("target") else "",
            "level": opt.get("level"),
            "item": opt.get("item"),
            "trade": bool(opt.get("trade")),
            "friendship": bool(opt.get("friendship")),
        }
        for opt in evolution_options
    ]
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

    def _phase_is_completed(self, subasta_state: dict) -> bool:
        quota = int(subasta_state.get("current_phase_quota", 1) or 1)
        phase_won = subasta_state.get("phase_pokemon_won", {}) or {}
        players = list(subasta_state.get("players", {}).keys())

        if quota <= 0:
            return True

        # La fase solo termina cuando todos los jugadores cumplen el mínimo de Pokémon
        # requerido para esa pool actual. Si alguien queda corto, la subasta no avanza.
        return all(phase_won.get(player, 0) >= quota for player in players)

    async def _advance_auction_flow(self, session: dict):
        subasta_state = session["subasta"]
        quota = subasta_state.get("current_phase_quota", 1)
        phase_won = subasta_state.setdefault("phase_pokemon_won", {})
        all_players = list(subasta_state["players"].keys())

        phase_done = self._phase_is_completed(subasta_state)

        if phase_done:
            current_phases = subasta_state.get("current_year_phases", [])
            next_idx = int(subasta_state.get("current_pool_phase_index", 0)) + 1

            if next_idx < len(current_phases):
                # Avanzar a la siguiente sub-fase de pool del año (ej. de Normal a Mega)
                subasta_state["current_pool_phase_index"] = next_idx
                next_phase = current_phases[next_idx]
                subasta_state["current_phase_tier"] = next_phase["tier"]
                subasta_state["current_phase_quota"] = max(1, int(next_phase.get("count", 1)))
                subasta_state["phase_pokemon_won"] = {u: 0 for u in all_players}
                subasta_state["current_auction"] = {}
                await init_subasta_round(session)
            else:
                # Todas las sub-fases del año concluyeron: dejar la subasta y entrar a eventos.
                subasta_state["current_auction"] = {}
                subasta_state["current_stage"] = max(3, int(subasta_state.get("current_stage", 2)) + 1)
                subasta_state["current_turn"] = 1
                for player in subasta_state["players"].values():
                    player["resolved_turn"] = False
                self._generate_turn_events(subasta_state)
                subasta_state["phase_pokemon_won"] = {u: 0 for u in all_players}
        else:
            # Si no llegó a la cuota, sigue con otra subasta de la misma fase.
            subasta_state["current_auction"] = {}
            await init_subasta_round(session)

    async def _advance_after_reveal_delay(self, session: dict, session_id: str, manager: Any):
        await asyncio.sleep(self.reveal_hold_seconds)

        subasta_state = session.get("subasta")
        if not subasta_state:
            return

        auction = subasta_state.get("current_auction")
        if not auction or auction.get("winner") is None:
            return

        await self._advance_auction_flow(session)

        await asyncio.to_thread(save_game_session, session_id, self.key, subasta_state)
        await self._broadcast_subasta_state(session, manager)

    @property
    def name(self) -> str:
        return "Subasta (Pokemon)"

    @property
    def requires_cubes(self) -> bool:
        return False

    def get_public_config_options(self, session: dict) -> Dict[str, Any]:
        return {
            "default_starting_money": 1000000,
            "default_turns_per_year": 3,
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

        for p in player_data.get("pokemon", []):
            if isinstance(p, dict):
                if "regional_form_options" not in p:
                    p["regional_form_options"] = poke_api.get_pokemon_regional_form_options(p)
                p["sell_value"] = get_pokemon_sell_value(p, subasta_state)

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

        current_year_phases = subasta_state.get("current_year_phases", [])
        current_pool_phase_index = subasta_state.get("current_pool_phase_index", 0)
        current_phase_tier = subasta_state.get("current_phase_tier", "normal")
        current_phase_quota = subasta_state.get("current_phase_quota", 1)
        phase_pokemon_won = subasta_state.get("phase_pokemon_won", {})
        solvency = {
            "positive_player_count": sum(1 for p in subasta_state["players"].values() if p.get("money", 0) > 0),
            "total_player_count": len(subasta_state["players"]),
            "negative_players": [u for u, p in subasta_state["players"].items() if p.get("money", 0) < 0],
        }

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
            "trade_session": subasta_state.get("trade_session"),
            "year_pools": subasta_state.get("year_pools", {}),
            "current_phase_tier": current_phase_tier,
            "current_phase_quota": current_phase_quota,
            "current_pool_phase_index": current_pool_phase_index,
            "current_year_phases": current_year_phases,
            "phase_pokemon_won": phase_pokemon_won,
            "my_phase_pokemon_won": phase_pokemon_won.get(username, 0),
            **solvency,
        }

    def validate_config(self, message: dict) -> dict:
        starting_money = int(message.get("starting_money", message.get("yearly_money", message.get("year_starting_money_1", 1000000))))
        turns_per_year = int(message.get("turns_per_year", 3))
        buyout_multiplier = float(message.get("buyout_multiplier", 10.0))
        secret_fee = int(message.get("secret_fee", 500))

        year_starting_money = {
            1: int(message.get("year_starting_money_1", message.get("year1_money", starting_money))),
            2: int(message.get("year_starting_money_2", message.get("year2_money", starting_money))),
            3: int(message.get("year_starting_money_3", message.get("year3_money", starting_money))),
        }

        # Configuración de pools por año (rondas de cada pool por año)
        year_pools_raw = message.get("year_pools", {})
        year_pools = {}
        for y in (1, 2, 3):
            yp = year_pools_raw.get(y) or year_pools_raw.get(str(y)) or {}
            normal_cnt = int(message.get(f"year{y}_normal", yp.get("normal", 2 if y <= 2 else 0)))
            mega_cnt = int(message.get(f"year{y}_mega", yp.get("mega", 1 if y >= 2 else 0)))
            leg_cnt = int(message.get(f"year{y}_legendary", yp.get("legendary", 2 if y == 3 else 0)))

            year_pools[y] = {
                "normal": max(0, min(10, normal_cnt)),
                "mega": max(0, min(10, mega_cnt)),
                "legendary": max(0, min(10, leg_cnt)),
            }

        return {
            "starting_money": starting_money,
            "yearly_money": starting_money,
            "turns_per_year": turns_per_year,
            "buyout_multiplier": buyout_multiplier,
            "secret_fee": secret_fee,
            "year_starting_money": year_starting_money,
            "year_pools": year_pools,
            "year_starting_money_1": year_starting_money[1],
            "year_starting_money_2": year_starting_money[2],
            "year_starting_money_3": year_starting_money[3],
            "year1_normal": year_pools[1]["normal"],
            "year1_mega": year_pools[1]["mega"],
            "year1_legendary": year_pools[1]["legendary"],
            "year2_normal": year_pools[2]["normal"],
            "year2_mega": year_pools[2]["mega"],
            "year2_legendary": year_pools[2]["legendary"],
            "year3_normal": year_pools[3]["normal"],
            "year3_mega": year_pools[3]["mega"],
            "year3_legendary": year_pools[3]["legendary"],
        }

    def start_game(self, session: dict) -> None:
        config = session.get("mode_config", {
            "starting_money": 1000000,
            "yearly_money": 1000000,
            "turns_per_year": 3,
            "buyout_multiplier": 10.0,
            "secret_fee": 500,
            "year_pools": {
                1: {"normal": 8, "mega": 0, "legendary": 0},
                2: {"normal": 3, "mega": 3, "legendary": 0},
                3: {"normal": 3, "mega": 2, "legendary": 1},
            },
            "year_starting_money": {1: 1000000, 2: 1000000, 3: 1000000},
        })
        order = get_connected_player_order(session)

        year_pools = config.get("year_pools", {
            1: {"normal": 8, "mega": 0, "legendary": 0},
            2: {"normal": 3, "mega": 3, "legendary": 0},
            3: {"normal": 3, "mega": 2, "legendary": 1},
        })
        starting_money = config.get("starting_money", 1000000)
        year_starting_money = config.get("year_starting_money", {1: starting_money, 2: starting_money, 3: starting_money})

        subasta_state = {
            "current_stage": 2,  # Pasa directo a Año 1: Subasta Inicial
            "current_year": 1,
            "current_turn": 1,
            "starting_money": starting_money,
            "turns_per_year": config.get("turns_per_year", 3),
            "buyout_multiplier": config.get("buyout_multiplier", 10.0),
            "secret_fee": config.get("secret_fee", 500),
            "year_starting_money": year_starting_money,
            "year_pools": year_pools,
            "player_order": order,
            "auction_turn_index": 0,
            "players": {
                u: {
                    "money": year_starting_money.get(1, starting_money),
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

        has_phases = setup_year_auction_phases(subasta_state, 1)
        session["subasta"] = subasta_state

        if not has_phases:
            subasta_state["current_stage"] = 3
            self._generate_turn_events(subasta_state)

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
            if session["subasta"].get("current_phase_quota", 0) > 0:
                await init_subasta_round(session)
            await asyncio.to_thread(save_game_session, session["id"], self.key, session["subasta"])

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

            if auction.get("high_bidder") == username:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Ya eres el mayor pujador de esta subasta."}})
                return True

            if bid_amount % MIN_BID_INCREMENT != 0:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": f"La puja debe ser múltiplo de ${MIN_BID_INCREMENT}."}})
                return True

            player = subasta_state["players"].get(username)
            if not player:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Fondos insuficientes."}})
                return True

            minimum_valid_bid = auction["current_bid"] + MIN_BID_INCREMENT
            if bid_amount < minimum_valid_bid:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": f"La puja debe superar los ${auction['current_bid']} en múltiplos de ${MIN_BID_INCREMENT}."}})
                return True

            auction["current_bid"] = bid_amount
            auction["high_bidder"] = username

            # Actualizar pistas según multiplicador
            multiplier = bid_amount / auction["base_price"]
            auction["hints"] = poke_api.get_hints_for_multiplier(auction["pokemon"], multiplier)

            queue_bid_session_save(session)
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

            if not auction.get("awaiting_secret_choice") or auction.get("awarded"):
                return True

            auction["awaiting_secret_choice"] = False
            auction["awarded"] = True

            keep_secret = bool(message.get("keep_secret", False))
            player = subasta_state["players"][username]
            cost = auction["current_bid"]

            if keep_secret:
                secret_cost = math.ceil(auction["current_bid"] * 0.1)
                if player["money"] >= cost + secret_cost:
                    cost += secret_cost
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
            won_pokemon["instant_purchase_price"] = int(auction.get("buyout_price", cost))
            won_pokemon["acquisition_year"] = int(subasta_state.get("current_year", 1))
            won_pokemon["acquisition_tier"] = auction.get("phase_tier", "normal")
            player["pokemon"].append(won_pokemon)
            auction["finished"] = True
            auction["reveal_hold_until"] = None
            subasta_state["auction_turn_index"] += 1

            # Incrementar el contador de pokémon ganados en la fase actual
            phase_won = subasta_state.setdefault("phase_pokemon_won", {})
            phase_won[username] = phase_won.get(username, 0) + 1

            # Cuando el ganador elige revelar, damos 5 segundos para que todos lo vean antes de avanzar.
            if not keep_secret:
                auction["reveal_hold_until"] = time.time() + self.reveal_hold_seconds
                auction["pokemon"]["is_hidden"] = False
                auction["publicly_revealed"] = True
                save_game_session(session_id, self.key, subasta_state)
                await self._broadcast_subasta_state(session, manager)
                asyncio.create_task(self._advance_after_reveal_delay(session, session_id, manager))
                return True

            await self._advance_auction_flow(session)
            await asyncio.to_thread(save_game_session, session_id, self.key, subasta_state)
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

        elif action == "subasta_pokemon_traffic":
            current_stage = subasta_state["current_stage"]
            if current_stage not in (3, 7, 11):
                return True

            player = subasta_state["players"].get(username)
            event = subasta_state["current_turn_events"].get(username)

            if not player or not event or player.get("resolved_turn") or event.get("type") != "pokemon_traffic":
                return True

            poke_idx = message.get("poke_index")

            # Rechazar la oferta (poke_index = -1)
            if poke_idx is None or poke_idx == -1:
                player["resolved_turn"] = True
                self._advance_after_event_resolution(subasta_state)
                save_game_session(session_id, self.key, subasta_state)
                await self._broadcast_subasta_state(session, manager)
                return True

            if not isinstance(poke_idx, int) or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido."}})
                return True

            # Eliminar el Pokémon y dar el dinero
            player["pokemon"].pop(poke_idx)
            traffic_amount = event.get("traffic_amount", 0)
            player["money"] += traffic_amount
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
                    year_money = subasta_state.get("year_starting_money", {}).get(2, subasta_state.get("starting_money", 1000000))
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 40)
                    has_phases = setup_year_auction_phases(subasta_state, 2)
                    if has_phases:
                        subasta_state["current_stage"] = 6  # Salta a Subasta Año 2
                        await init_subasta_round(session)
                    else:
                        subasta_state["current_stage"] = 7  # Salta a Eventos Año 2
                        subasta_state["current_turn"] = 1
                        for p in subasta_state["players"].values():
                            p["resolved_turn"] = False
                        self._generate_turn_events(subasta_state)

                elif next_stage == 9:  # Inicio Año 3
                    subasta_state["current_year"] = 3
                    year_money = subasta_state.get("year_starting_money", {}).get(3, subasta_state.get("starting_money", 1000000))
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 100)
                    has_phases = setup_year_auction_phases(subasta_state, 3)
                    if has_phases:
                        subasta_state["current_stage"] = 10  # Salta a Subasta Año 3
                        await init_subasta_round(session)
                    else:
                        subasta_state["current_stage"] = 11  # Salta a Eventos Año 3
                        subasta_state["current_turn"] = 1
                        for p in subasta_state["players"].values():
                            p["resolved_turn"] = False
                        self._generate_turn_events(subasta_state)

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
                next_stage = current_stage + 1
                subasta_state["current_stage"] = next_stage
                if next_stage == 5:
                    subasta_state["current_year"] = 2
                    year_money = subasta_state.get("year_starting_money", {}).get(2, subasta_state.get("starting_money", 1000000))
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 40)
                    has_phases = setup_year_auction_phases(subasta_state, 2)
                    if has_phases:
                        subasta_state["current_stage"] = 6
                        await init_subasta_round(session)
                    else:
                        subasta_state["current_stage"] = 7
                        subasta_state["current_turn"] = 1
                        for p in subasta_state["players"].values():
                            p["resolved_turn"] = False
                        self._generate_turn_events(subasta_state)
                elif next_stage == 9:
                    subasta_state["current_year"] = 3
                    year_money = subasta_state.get("year_starting_money", {}).get(3, subasta_state.get("starting_money", 1000000))
                    for p_info in subasta_state["players"].values():
                        p_info["money"] += year_money
                        evolve_player_pokemon(p_info, 100)
                    has_phases = setup_year_auction_phases(subasta_state, 3)
                    if has_phases:
                        subasta_state["current_stage"] = 10
                        await init_subasta_round(session)
                    else:
                        subasta_state["current_stage"] = 11
                        subasta_state["current_turn"] = 1
                        for p in subasta_state["players"].values():
                            p["resolved_turn"] = False
                        self._generate_turn_events(subasta_state)

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
            current_trade = subasta_state.get("trade_session")
            if current_trade and current_trade.get("status") in ("selecting", "confirming"):
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
            if not trade or username != trade.get("initiator"):
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

            if 0 <= poke_idx < len(player.get("pokemon", [])):
                poke = player["pokemon"][poke_idx]
                if poke_api.is_mega_pokemon(poke):
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": "Los Pokémon Mega no pueden equipar objetos."}})
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

        elif action == "subasta_use_mint":
            player = subasta_state["players"].get(username)
            poke_idx = message.get("poke_index")
            item_name = message.get("item_name")
            mint_nature = item_name[:-5] if isinstance(item_name, str) and item_name.endswith(" Mint") else None
            inventory = normalize_item_inventory(player.get("items", {})) if player else {}

            if not player or not mint_nature or item_name not in MINT_ITEMS or inventory.get(item_name, 0) <= 0:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes esa Menta."}})
                return True
            if mint_nature not in poke_api.POKEMON_NATURES:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Esa Menta no corresponde a una naturaleza válida."}})
                return True
            if not isinstance(poke_idx, int) or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido."}})
                return True

            poke = player["pokemon"][poke_idx]
            if poke.get("nature") == mint_nature:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Esa Menta no cambiaría la naturaleza actual del Pokémon."}})
                return True

            poke["nature"] = mint_nature
            remove_item_from_inventory(player, item_name)
            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_use_tm":
            player = subasta_state["players"].get(username)
            poke_idx = message.get("poke_index")
            item_name = message.get("item_name")
            move_name = poke_api.TM_MOVES.get(item_name) or (item_name[3:].strip() if isinstance(item_name, str) and item_name.startswith("MT ") else None)
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

        elif action == "subasta_use_form_change":
            player = subasta_state["players"].get(username)
            poke_idx = message.get("poke_index")
            target_form = message.get("target_form")
            inventory = normalize_item_inventory(player.get("items", {})) if player else {}

            if not player or inventory.get("Cambia Formas", 0) <= 0:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes el ítem Cambia Formas."}})
                return True
            if not isinstance(poke_idx, int) or not 0 <= poke_idx < len(player.get("pokemon", [])):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido."}})
                return True

            poke = player["pokemon"][poke_idx]
            form_options = poke_api.get_pokemon_regional_form_options(poke)
            if not form_options:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Este Pokémon no tiene formas regionales disponibles."}})
                return True

            if target_form is None:
                target_form = form_options[0].get("target_name")

            valid_targets = {opt.get("target_name"): opt for opt in form_options}
            selected_option = valid_targets.get(str(target_form).lower()) or valid_targets.get(str(target_form))
            if not selected_option:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Esa forma regional no está disponible para este Pokémon."}})
                return True

            if not poke_api.apply_regional_form(poke, selected_option["target_name"]):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No se pudo cambiar la forma regional del Pokémon."}})
                return True

            remove_item_from_inventory(player, "Cambia Formas")
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

            current_year = int(subasta_state.get("current_year", 1))
            year_shop_items = YEAR_SHOP_ITEMS.get(current_year, YEAR_SHOP_ITEMS[1])
            if item_name == "Caja Misteriosa 1" and "Caja Misteriosa I" in year_shop_items:
                item_name = "Caja Misteriosa I"

            if item_name not in year_shop_items:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": f"Ese objeto no está disponible en la tienda del Año {current_year}."}})
                return True

            price = ITEM_SHOP_PRICES.get(item_name, 1500)
            if player["money"] < price:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "No tienes suficiente dinero para comprar ese objeto."}})
                return True

            player["money"] -= price

            if item_name in ("Caja Misteriosa I", "Caja Misteriosa 1"):
                roll = random.random()
                reward_info = {}

                box_pool_preview = [
                    {"name": "Oran Berry", "display": "Oran Berry (x1)", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/oran-berry.png"},
                    {"name": "MT Earthquake", "display": "MT Earthquake", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png"},
                    {"name": "MT Flamethrower", "display": "MT Flamethrower", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png"},
                    {"name": "MT Shadow Ball", "display": "MT Shadow Ball", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png"},
                    {"name": "Capsula Habilidad", "display": "Cápsula Habilidad", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/ability-capsule.png"},
                    {"name": "Porygon + Mejora", "display": "Porygon + Objeto Mejora", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/137.png"},
                    {"name": "$500,000", "display": "$500,000 en efectivo", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/big-nugget.png"},
                    {"name": "Pokémon Shiny ✨", "display": "Pokémon Shiny Random ✨", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/shiny-stone.png"},
                ]

                if roll < 0.75:
                    add_item_to_inventory(player, "Oran Berry")
                    reward_info = {
                        "type": "item",
                        "name": "Oran Berry",
                        "display": "Oran Berry (x1)",
                        "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/oran-berry.png",
                    }
                elif roll < 0.80:
                    add_item_to_inventory(player, "MT Earthquake")
                    reward_info = {
                        "type": "item",
                        "name": "MT Earthquake",
                        "display": "MT Earthquake",
                        "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png",
                    }
                elif roll < 0.85:
                    add_item_to_inventory(player, "MT Flamethrower")
                    reward_info = {
                        "type": "item",
                        "name": "MT Flamethrower",
                        "display": "MT Flamethrower",
                        "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png",
                    }
                elif roll < 0.90:
                    add_item_to_inventory(player, "MT Shadow Ball")
                    reward_info = {
                        "type": "item",
                        "name": "MT Shadow Ball",
                        "display": "MT Shadow Ball",
                        "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-normal.png",
                    }
                elif roll < 0.95:
                    add_item_to_inventory(player, "Capsula Habilidad")
                    reward_info = {
                        "type": "item",
                        "name": "Capsula Habilidad",
                        "display": "Cápsula Habilidad",
                        "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/ability-capsule.png",
                    }
                elif roll < 0.98:
                    porygon_data = poke_api.fetch_pokemon_data("Porygon", level_cap=20)
                    player.setdefault("pokemon", []).append(porygon_data)
                    add_item_to_inventory(player, "Up-Grade")
                    nature_str = porygon_data.get("nature", "Hardy")
                    ability_str = porygon_data.get("ability", "Trace")
                    reward_info = {
                        "type": "porygon",
                        "name": "Porygon + Mejora",
                        "display": f"¡Porygon ({nature_str} / {ability_str}) + Objeto Mejora (Up-Grade)!",
                        "image": porygon_data.get("image_url") or "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/137.png",
                        "pokemon": porygon_data,
                    }
                elif roll < 0.99:
                    player["money"] = player.get("money", 0) + 500000
                    reward_info = {
                        "type": "money",
                        "name": "$500,000",
                        "display": "¡$500,000 en efectivo!",
                        "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/big-nugget.png",
                    }
                else:
                    from backend import database
                    chosen_poke = database.get_random_pokemon_from_db(year=1, auction_type="normal")
                    if not chosen_poke:
                        chosen_poke = random.choice(poke_api.SAMPLE_POKEMON_POOLS.get("normal", ["Pikachu", "Eevee", "Charmander", "Squirtle", "Bulbasaur"]))
                    shiny_data = poke_api.fetch_pokemon_data(chosen_poke, level_cap=20)
                    shiny_data["is_shiny"] = True
                    if shiny_data.get("shiny_image_url"):
                        shiny_data["image_url"] = shiny_data["shiny_image_url"]
                    player.setdefault("pokemon", []).append(shiny_data)
                    nature_str = shiny_data.get("nature", "Hardy")
                    ability_str = shiny_data.get("ability", "Static")
                    reward_info = {
                        "type": "shiny_pokemon",
                        "name": f"{shiny_data['name']} Shiny ✨",
                        "display": f"¡{shiny_data['name']} Shiny ✨ ({nature_str} / {ability_str})!",
                        "image": shiny_data.get("shiny_image_url") or shiny_data.get("image_url"),
                        "pokemon": shiny_data,
                    }

                await manager.send_personal(websocket, {
                    "event": "subasta_mystery_box_result",
                    "data": {
                        "box_name": "Caja Misteriosa I",
                        "reward": reward_info,
                        "pool": box_pool_preview,
                    },
                })
            elif item_name in YEAR_SHOP_ROULETTES:
                rewards = YEAR_SHOP_ROULETTES[item_name]
                chosen_reward = random.choice(rewards)
                add_item_to_inventory(player, chosen_reward)
                await manager.send_personal(websocket, {
                    "event": "subasta_mystery_box_result",
                    "data": {
                        "box_name": item_name,
                        "store_title": f"TIENDA AÑO {current_year}",
                        "reward": {
                            "type": "item",
                            "name": chosen_reward,
                            "display": chosen_reward,
                        },
                        "pool": rewards,
                    },
                })
            elif item_name == "Regalo del Primo jeque":
                jeque_pool_preview = [
                    {"name": "Galvantula", "display": "Galvantula", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/596.png"},
                    {"name": "Scolipede", "display": "Scolipede", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/545.png"},
                    {"name": "Sawk", "display": "Sawk", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/539.png"},
                    {"name": "Gardevoir", "display": "Gardevoir", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/282.png"},
                ]
                chosen_species = random.choice(["Galvantula", "Scolipede", "Sawk", "Gardevoir"])
                poke_data = poke_api.fetch_pokemon_data(chosen_species, level_cap=20)
                player.setdefault("pokemon", []).append(poke_data)
                nature_str = poke_data.get("nature", "Hardy")
                ability_str = poke_data.get("ability", "")
                reward_info = {
                    "type": "pokemon",
                    "name": poke_data["name"],
                    "display": f"¡{poke_data['name']} ({nature_str} / {ability_str})!",
                    "image": poke_data.get("image_url") or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_data.get('id', 1)}.png",
                    "pokemon": poke_data,
                }
                await manager.send_personal(websocket, {
                    "event": "subasta_mystery_box_result",
                    "data": {
                        "box_name": "Regalo del Primo jeque",
                        "reward": reward_info,
                        "pool": jeque_pool_preview,
                    },
                })
            else:
                add_item_to_inventory(player, item_name)

            save_game_session(session_id, self.key, subasta_state)
            await self._broadcast_subasta_state(session, manager)
            return True

        elif action == "subasta_sell_pokemon":
            if subasta_state.get("current_stage") not in (4, 8, 12):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo puedes vender Pokémon durante la preparación de Showdown."}})
                return True

            player = subasta_state["players"].get(username)
            if not player or player.get("money", 0) >= 0:
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Solo puedes vender Pokémon mientras tu saldo sea negativo."}})
                return True

            pokemon_index = int(message.get("pokemon_index", -1))
            pokemon = player.get("pokemon", [])
            if not 0 <= pokemon_index < len(pokemon):
                await manager.send_personal(websocket, {"event": "error", "data": {"message": "Selecciona un Pokémon válido para vender."}})
                return True

            sold_pokemon = pokemon.pop(pokemon_index)
            sell_value = get_pokemon_sell_value(sold_pokemon, subasta_state)
            equipped_item = sold_pokemon.get("item") or sold_pokemon.get("held_item")
            if equipped_item:
                add_item_to_inventory(player, equipped_item)
            player["money"] += sell_value

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
            requested_target = message.get("target_name") or message.get("target_species")
            player = subasta_state["players"].get(username)

            if player and 0 <= poke_idx < len(player.get("pokemon", [])):
                poke = player["pokemon"][poke_idx]
                target_year = int(subasta_state.get("current_year", 1))
                target_limit = 20 if target_year == 1 else (40 if target_year == 2 else 100)
                current_level = int(poke.get("level", target_limit))
                all_options = poke_api.get_pokemon_all_evolution_options(poke.get("name"), max_level=100)

                if not all_options:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": "Este Pokémon no tiene una evolución disponible."}})
                    return True

                candidate_options = [
                    opt for opt in all_options
                    if not requested_target or opt.get("target", "").lower() == str(requested_target).lower()
                ]

                if not candidate_options:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": f"'{requested_target}' no es una evolución válida para este Pokémon."}})
                    return True

                inventory = normalize_item_inventory(player.get("items", {}))
                satisfied_option = None
                first_error = ""

                for opt in candidate_options:
                    opt_item = opt.get("item")
                    opt_trade = bool(opt.get("trade"))
                    opt_friendship = bool(opt.get("friendship"))
                    opt_level = opt.get("level")
                    t_name = (opt.get("target") or "este Pokémon").capitalize()

                    has_req_item = True
                    if opt_item:
                        has_req_item = inventory.get(opt_item, 0) > 0
                        if not has_req_item and opt_item.lower().replace("-", " ") in ("up grade", "upgrade"):
                            has_req_item = any(inventory.get(k, 0) > 0 for k in ("Up-Grade", "Up Grade", "Mejora", "Objeto Mejora"))
                        if not has_req_item:
                            if not first_error:
                                first_error = f"Necesitas {opt_item} para evolucionar a {t_name}."
                            continue

                    if opt_trade and not opt_item and not poke.get("received_by_trade"):
                        if not first_error:
                            first_error = "Este Pokémon debe haber sido recibido mediante intercambio."
                        continue

                    if opt_friendship and target_year < 2:
                        if not first_error:
                            first_error = "La evolución por amistad está disponible a partir del Año 2."
                        continue

                    if target_year == 1 and not opt_item:
                        if not first_error:
                            first_error = "En el Año 1 solo se permiten evoluciones mediante objetos o piedras evolutivas."
                        continue

                    if opt_level is not None and current_level < opt_level:
                        if not first_error:
                            first_error = f"Este Pokémon necesita alcanzar el nivel {opt_level}."
                        continue

                    satisfied_option = opt
                    break

                if not satisfied_option:
                    await manager.send_personal(websocket, {"event": "error", "data": {"message": first_error or "No cumples los requisitos para esta evolución."}})
                    return True

                selected_option = satisfied_option
                target_species = selected_option.get("target")
                evolution_item = selected_option.get("item")

                if evolve_single_pokemon(poke, target_limit, target_name=target_species):
                    if evolution_item:
                        item_to_remove = evolution_item
                        if evolution_item.lower().replace("-", " ") in ("up grade", "upgrade") and inventory.get(evolution_item, 0) <= 0:
                            for alias in ("Up-Grade", "Up Grade", "Mejora", "Objeto Mejora"):
                                if inventory.get(alias, 0) > 0:
                                    item_to_remove = alias
                                    break
                        remove_item_from_inventory(player, item_to_remove)
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
