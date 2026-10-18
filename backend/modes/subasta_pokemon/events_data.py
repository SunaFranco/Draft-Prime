"""
backend/modes/subasta_pokemon/events_data.py - Eventos aleatorios por turno para los Años 1, 2 y 3
"""

import random
from typing import Dict, List, Any
from backend.modes.subasta_pokemon.poke_api import TM_MOVES

ITEMS_POOL = [
    "Leftovers", "Life Orb", "Choice Band", "Choice Specs", "Choice Scarf",
    "Focus Sash", "Assault Vest", "Heavy-Duty Boots", "Eviolite", "Rocky Helmet"
]

BERRIES_POOL = [
    "Oran Berry", "Sitrus Berry", "Lum Berry", "Cheri Berry", "Chesto Berry",
    "Pecha Berry", "Rawst Berry", "Aspear Berry", "Leppa Berry", "Persim Berry",
    "Figy Berry", "Wiki Berry", "Mago Berry", "Aguav Berry", "Iapapa Berry",
    "Liechi Berry", "Ganlon Berry", "Salac Berry", "Petaya Berry", "Apicot Berry",
    "Custap Berry", "Occa Berry", "Passho Berry", "Wacan Berry", "Rindo Berry",
    "Yache Berry", "Chople Berry", "Shuca Berry", "Coba Berry", "Haban Berry",
    "Colbur Berry", "Babiri Berry", "Roseli Berry",
]

CABLE_LINK_ITEM = "Cable Link"
ABILITY_CAPSULE_ITEM = "Capsula Habilidad"
TM_BOOSTER_PACK_SIZE = 2

EVENTS_YEAR_1 = [
    {
        "id": "e1_cable_link",
        "title": "🔗 Cable Link",
        "description": "Encontraste un Cable Link. Puedes usarlo para intercambiar un Pokémon en la fase de preparación.",
        "type": "item_grant",
        "granted_item": CABLE_LINK_ITEM,
    },
    {
        "id": "e1_objeto",
        "title": "🎁 Hallazgo de Objeto",
        "description": "Encontraste un objeto competitivo tirado en la ruta.",
        "type": "item_grant",
    },
    {
        "id": "e1_cambio_naturaleza",
        "title": "🌿 Cambio de Naturaleza",
        "description": "Un cuidador experto puede cambiar la naturaleza de uno de tus Pokémon.",
        "type": "nature_change",
    },
    {
        "id": "e2_capsula_habilidad",
        "title": "💊 Capsula Habilidad",
        "description": "Encontraste una Capsula Habilidad. Puedes usarla para cambiar la habilidad de uno de tus Pokémon.",
        "type": "item_grant",
        "granted_item": ABILITY_CAPSULE_ITEM,
    },
    {
        "id": "e1_mt_booster_pack",
        "title": "MT BOOSTER PACK",
        "description": "Encontraste un MT BOOSTER PACK con 4 MTs aleatorias.",
        "type": "tm_booster_pack",
    },
    {
        "id": "e1_rebuscar_basura",
        "title": "🗑️ Rebuscar la Basura",
        "description": "Rebuscas en la basura y consigues 3 tiradas en la ruleta (5% Leftovers, 95% Baya aleatoria).",
        "type": "trash_scavenge",
    },
    {
        "id": "e1_trafico_pokemon",
        "title": "🕶️ Tráfico Pokémon",
        "description": "Un tipo sospechoso te ofrece dinero por uno de tus Pokémon. Perderás el Pokémon y ganarás entre $0 y $125,000 — cuanto más suba, más probable es que se detenga.",
        "type": "pokemon_traffic",
    },
]

EVENTS_YEAR_2 = [
    {
        "id": "e2_feria",
        "title": "🎡 Subasta Relámpago en la Feria",
        "description": "Recibes una bonificación de $2,000 de presupuesto.",
        "type": "money_grant",
        "amount": 50000,
    },
    {
        "id": "e2_cambio_naturaleza",
        "title": "🌿 Cambio de Naturaleza",
        "description": "Un cuidador experto puede cambiar la naturaleza de uno de tus Pokémon.",
        "type": "nature_change",
    },
    {
        "id": "e2_capsula_habilidad",
        "title": "💊 Capsula Habilidad",
        "description": "Encontraste una Capsula Habilidad. Puedes usarla para cambiar la habilidad de uno de tus Pokémon.",
        "type": "item_grant",
        "granted_item": ABILITY_CAPSULE_ITEM,
    },
    {
        "id": "e2_mt_booster_pack",
        "title": "MT BOOSTER PACK",
        "description": "Encontraste un MT BOOSTER PACK con 4 MTs aleatorias.",
        "type": "tm_booster_pack",
    },
]

EVENTS_YEAR_3 = [
    {
        "id": "e3_cambio_naturaleza",
        "title": "🌿 Cambio de Naturaleza",
        "description": "Un cuidador experto puede cambiar la naturaleza de uno de tus Pokémon.",
        "type": "nature_change",
    },
    {
        "id": "e3_mt_booster_pack",
        "title": "MT BOOSTER PACK",
        "description": "Encontraste un MT BOOSTER PACK con 4 MTs aleatorias.",
        "type": "tm_booster_pack",
    },
]


def get_random_event_for_year(year: int, turn: int = 1) -> dict:
    """Devuelve un evento aleatorio según el año actual."""
    if year == 1:
        pool = EVENTS_YEAR_1
    elif year == 2:
        pool = EVENTS_YEAR_2
    else:
        pool = EVENTS_YEAR_3

    event = random.choice(pool).copy()
    if event.get("type") == "pokemon_traffic":
        event["traffic_amount"] = _generate_traffic_amount()
    elif event.get("type") == "trash_scavenge":
        spins = 3
        granted = []
        for _ in range(spins):
            if random.random() < 0.05:
                granted.append("Leftovers")
            else:
                granted.append(random.choice(BERRIES_POOL))
        event["granted_items"] = granted
        event["reward_is_random"] = True
        event["roulette_pool"] = ["Leftovers"] + BERRIES_POOL
    elif event.get("type") == "tm_booster_pack":
        event["granted_items"] = random.sample(list(TM_MOVES), min(TM_BOOSTER_PACK_SIZE, len(TM_MOVES)))
        event["reward_is_random"] = True
    elif event.get("type") in ("item_grant", "mixed_grant") and not event.get("granted_item"):
        event["granted_item"] = random.choice(ITEMS_POOL)
        event["reward_is_random"] = True

    return event


def _generate_traffic_amount() -> int:
    """Genera un monto entre 0 y 125,000 con probabilidad creciente de parada."""
    amount = 0
    step = 5000
    max_amount = 125000
    while amount < max_amount:
        # A medida que el monto sube, más probable que se detenga
        stop_chance = (amount + step) / (max_amount + step)
        if random.random() < stop_chance:
            return amount
        amount += step
    return max_amount


def normalize_item_counts(items) -> dict:
    """Normaliza el inventario a un diccionario item -> cantidad."""
    if items is None:
        return {}
    if isinstance(items, dict):
        return {str(k): int(v) for k, v in items.items() if int(v) > 0}
    if isinstance(items, list):
        counts = {}
        for item in items:
            if item:
                counts[str(item)] = counts.get(str(item), 0) + 1
        return counts
    return {}


def apply_event_to_player(player_state: dict, event: dict) -> dict:
    """Aplica los efectos de un evento al estado del jugador y retorna un resumen del impacto."""
    event_type = event.get("type")
    msg_parts = [event["description"]]

    if "amount" in event:
        player_state["money"] += event["amount"]
        msg_parts.append(f"+${event['amount']} agregados a tus fondos (Saldo: ${player_state['money']}).")

    if event.get("granted_item"):
        item = event["granted_item"]
        items = normalize_item_counts(player_state.setdefault("items", {}))
        items[item] = items.get(item, 0) + 1
        player_state["items"] = items
        msg_parts.append(f"Objeto obtenido: {item}.")

    if event.get("granted_items"):
        items = normalize_item_counts(player_state.setdefault("items", {}))
        for item in event["granted_items"]:
            items[item] = items.get(item, 0) + 1
        player_state["items"] = items
        msg_parts.append(f"Objetos obtenidos: {', '.join(event['granted_items'])}.")

    if event.get("granted_pokemon"):
        poke_name = event["granted_pokemon"]
        from backend.modes.subasta_pokemon import poke_api
        new_poke = poke_api.fetch_pokemon_data(poke_name, level_cap=20)
        player_state.setdefault("pokemon", []).append(new_poke)
        msg_parts.append(f"Pokémon obtenido: {new_poke.get('name', poke_name)}.")

    return {
        "event_id": event["id"],
        "title": event["title"],
        "summary": " ".join(msg_parts),
        "player_money": player_state["money"],
        "pokemon_count": len(player_state.get("pokemon", []))
    }
