"""
backend/modes/subasta_pokemon/events_data.py - Eventos aleatorios por turno para los Años 1, 2 y 3
"""

import random
from typing import Dict, List, Any

ITEMS_POOL = [
    "Leftovers", "Life Orb", "Choice Band", "Choice Specs", "Choice Scarf",
    "Focus Sash", "Assault Vest", "Heavy-Duty Boots", "Eviolite", "Rocky Helmet"
]

CABLE_LINK_ITEM = "Cable Link"

EVENTS_YEAR_1 = [
    {
        "id": "e1_objeto",
        "title": "🎁 Hallazgo de Objeto",
        "description": "Encontraste un objeto competitivo tirado en la ruta.",
        "type": "item_grant",
    },
    {
        "id": "e1_patrocinio",
        "title": "💰 Patrocinio Local",
        "description": "Un patrocinador local apoya tu campaña con $1,000 de presupuesto extra.",
        "type": "money_grant",
        "amount": 1000,
    },
]

EVENTS_YEAR_2 = [
    {
        "id": "e2_gimnasio",
        "title": "🏟️ Reto de Gimnasio",
        "description": "Superaste una prueba intensa. Tu equipo recibe +10 niveles distribuibles y $1,500.",
        "type": "gym_win",
        "xp_bonus": 10,
        "amount": 1500,
    },
    {
        "id": "e2_megapiedra",
        "title": "💎 Hallazgo de Mega-Piedra / Z-Crystal",
        "description": "Obtienes un objeto de potenciación avanzada.",
        "type": "item_grant",
    },
    {
        "id": "e2_feria",
        "title": "🎡 Subasta Relámpago en la Feria",
        "description": "Recibes una bonificación de $2,000 de presupuesto.",
        "type": "money_grant",
        "amount": 2000,
    },
]

EVENTS_YEAR_3 = [
    {
        "id": "e3_alto_mando",
        "title": "👑 Entrenamiento del Alto Mando",
        "description": "Entrenamiento supremo antes de la liga. Todos tus Pokémon ganan +15 niveles.",
        "type": "xp_boost",
        "xp_bonus": 15,
    },
    {
        "id": "e3_artefacto",
        "title": "⚡ Artefacto Legendario",
        "description": "Obtienes $3,000 extra para la subasta final y un objeto premium.",
        "type": "mixed_grant",
        "amount": 3000,
    },
]


def get_random_event_for_year(year: int, turn: int = 1) -> dict:
    """Devuelve un evento aleatorio según el año actual."""
    if year == 1 and turn == 1:
        return {
            "id": "e1_cable_link",
            "title": "🔗 Cable Link",
            "description": "Encontraste un Cable Link. Puedes usarlo para intercambiar un Pokémon en la fase de preparación.",
            "type": "item_grant",
            "granted_item": CABLE_LINK_ITEM,
        }

    if year == 1:
        pool = EVENTS_YEAR_1
    elif year == 2:
        pool = EVENTS_YEAR_2
    else:
        pool = EVENTS_YEAR_3

    event = random.choice(pool).copy()
    if event.get("type") in ("item_grant", "mixed_grant"):
        event["granted_item"] = random.choice(ITEMS_POOL)

    return event


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

    if "xp_bonus" in event and player_state.get("pokemon"):
        bonus = event["xp_bonus"]
        target = min(player_state["pokemon"], key=lambda p: p.get("level", 1))
        target["level"] += bonus
        msg_parts.append(f"{target['name']} subió a Nivel {target['level']} (+{bonus} Nv).")

    return {
        "event_id": event["id"],
        "title": event["title"],
        "summary": " ".join(msg_parts),
        "player_money": player_state["money"],
        "pokemon_count": len(player_state.get("pokemon", []))
    }
