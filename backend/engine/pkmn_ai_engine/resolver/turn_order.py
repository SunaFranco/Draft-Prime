"""
backend/engine/pkmn_ai_engine/resolver/turn_order.py
Determina el orden de ejecución de las acciones en un turno basado en Pokémon Showdown (sim/battle-queue.ts).
Considera:
1. Prioridad de cambio (+6)
2. Brackets de prioridad de movimiento (-7 a +5) modificados por habilidades (Prankster, Gale Wings, Triage)
3. Velocidad efectiva (etapas, parálisis, Tailwind, Choice Scarf, habilidades climáticas)
4. Inversión de velocidad bajo Trick Room (Espacio Raro)
5. Speed Tie aleatorio (50/50)
"""

import random
from typing import Optional, Tuple
from ..core.models import Action, PokemonState, MoveState, BattleSnapshot
from ..core.damage import get_effective_speed


def get_effective_priority(pokemon: PokemonState, move: Optional[MoveState]) -> int:
    """Calcula la prioridad efectiva de un movimiento considerando habilidades como Prankster, Gale Wings y Triage."""
    if not move:
        return 0
    prio = int(move.priority)
    ability = (pokemon.ability or "").lower()

    if ability == "prankster" and move.category == "status":
        prio += 1
    elif ability == "gale wings" and move.type.capitalize() == "Flying" and pokemon.current_hp >= pokemon.max_hp:
        prio += 1
    elif ability == "triage" and (move.heal_fraction > 0 or move.drain_percent > 0):
        prio += 3

    return prio


def determine_turn_order(
    player_action: Action,
    player_poke: PokemonState,
    player_move: Optional[MoveState],
    ai_action: Action,
    ai_poke: PokemonState,
    ai_move: Optional[MoveState],
    snapshot: Optional[BattleSnapshot] = None,
) -> Tuple[str, str]:
    """
    Determina si actúa primero 'player' o 'ai' según la cola de eventos de Showdown.
    Devuelve la tupla ('primero', 'segundo').
    """
    p_is_switch = player_action.type.upper() == "SWITCH"
    ai_is_switch = ai_action.type.upper() == "SWITCH"

    weather = snapshot.weather if snapshot else None
    p_side = snapshot.player_side if snapshot else None
    ai_side = snapshot.ai_side if snapshot else None
    trick_room = (snapshot.trick_room_turns > 0) if snapshot else False

    p_speed = get_effective_speed(player_poke, side_conditions=p_side, weather=weather)
    ai_speed = get_effective_speed(ai_poke, side_conditions=ai_side, weather=weather)

    # 1. Los cambios (SWITCH) tienen prioridad +6 sobre ataques
    if p_is_switch and not ai_is_switch:
        return "player", "ai"
    if ai_is_switch and not p_is_switch:
        return "ai", "player"
    if p_is_switch and ai_is_switch:
        if p_speed > ai_speed:
            return "player", "ai"
        if ai_speed > p_speed:
            return "ai", "player"
        return random.choice([("player", "ai"), ("ai", "player")])

    # 2. Ambos usan MOVE: comparar prioridad efectiva del movimiento
    p_priority = get_effective_priority(player_poke, player_move)
    ai_priority = get_effective_priority(ai_poke, ai_move)

    if p_priority > ai_priority:
        return "player", "ai"
    if ai_priority > p_priority:
        return "ai", "player"

    # 3. Igual prioridad: comparar velocidad efectiva (invertida si Trick Room está activo)
    if trick_room:
        if p_speed < ai_speed:
            return "player", "ai"
        if ai_speed < p_speed:
            return "ai", "player"
    else:
        if p_speed > ai_speed:
            return "player", "ai"
        if ai_speed > p_speed:
            return "ai", "player"

    # 4. Speed Tie exacto: 50/50 aleatorio
    return random.choice([("player", "ai"), ("ai", "player")])
