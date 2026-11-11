"""
backend/engine/pkmn_ai_engine/resolver/turn_order.py
Determina el orden de ejecución de las acciones en un turno (Prioridades y Velocidad).
"""

import random
from typing import Tuple
from ..core.models import Action, PokemonState, MoveState
from ..core.damage import get_effective_speed


def determine_turn_order(
    player_action: Action,
    player_poke: PokemonState,
    player_move: MoveState | None,
    ai_action: Action,
    ai_poke: PokemonState,
    ai_move: MoveState | None
) -> Tuple[str, str]:
    """
    Determina si actúa primero 'player' o 'ai'.
    Devuelve la tupla ('primero', 'segundo').
    """
    # 1. Los cambios a la banca (SWITCH) tienen prioridad máxima (+6)
    p_is_switch = player_action.type.upper() == "SWITCH"
    ai_is_switch = ai_action.type.upper() == "SWITCH"

    if p_is_switch and not ai_is_switch:
        return "player", "ai"
    if ai_is_switch and not p_is_switch:
        return "ai", "player"
    if p_is_switch and ai_is_switch:
        # Si ambos cambian, el jugador va primero (o aleatorio)
        return "player", "ai"

    # 2. Ambos usan MOVE: comparar prioridad del movimiento
    p_priority = player_move.priority if player_move else 0
    ai_priority = ai_move.priority if ai_move else 0

    if p_priority > ai_priority:
        return "player", "ai"
    if ai_priority > p_priority:
        return "ai", "player"

    # 3. Igual prioridad: comparar velocidad efectiva
    p_speed = get_effective_speed(player_poke)
    ai_speed = get_effective_speed(ai_poke)

    if p_speed > ai_speed:
        return "player", "ai"
    if ai_speed > p_speed:
        return "ai", "player"

    # 4. Speed Tie exacto: 50/50 aleatorio
    return random.choice([("player", "ai"), ("ai", "player")])
