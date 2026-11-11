"""
backend/engine/pkmn_ai_engine/ai/evaluator.py
Evaluador heurístico de estado de combate y perfiles de dificultad.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from ..core.models import PokemonState, MoveState, BattleSnapshot
from ..core.damage import calculate_damage, get_effective_speed


@dataclass(slots=True)
class DifficultyProfile:
    name: str
    weight_lethal_bonus: float = 1000.0   # Bono cuando un ataque noquea al rival
    weight_speed_priority: float = 400.0  # Bono por tener iniciativa en turnos críticos
    weight_material: float = 300.0        # Valor de conservar piezas vivas
    weight_hp_preservation: float = 150.0 # Valor de conservar porcentaje de HP
    switch_danger_threshold: float = 0.85 # Vida restante por debajo de la cual se evalúa switch
    noise_factor: float = 0.0             # 0.0 (impecable) a 0.30 (comete errores novatos)


# Perfiles estándar de dificultad
PROFILES = {
    "easy": DifficultyProfile(
        name="easy",
        weight_lethal_bonus=300.0,
        weight_speed_priority=100.0,
        weight_material=100.0,
        weight_hp_preservation=50.0,
        switch_danger_threshold=0.30,
        noise_factor=0.25,  # 25% de error o jugadas sub-óptimas
    ),
    "medium": DifficultyProfile(
        name="medium",
        weight_lethal_bonus=700.0,
        weight_speed_priority=250.0,
        weight_material=200.0,
        weight_hp_preservation=100.0,
        switch_danger_threshold=0.60,
        noise_factor=0.08,
    ),
    "hard": DifficultyProfile(
        name="hard",
        weight_lethal_bonus=1200.0,
        weight_speed_priority=500.0,
        weight_material=350.0,
        weight_hp_preservation=200.0,
        switch_danger_threshold=0.85,
        noise_factor=0.0,   # Cero errores, precisión competitiva
    ),
}


def get_profile(difficulty: str) -> DifficultyProfile:
    return PROFILES.get(difficulty.lower(), PROFILES["medium"])


def evaluate_max_threat(
    attacker: PokemonState,
    defender: PokemonState,
    moves: List[MoveState],
    weather: Optional[str] = None
) -> Tuple[int, Optional[MoveState]]:
    """
    Calcula el mayor daño que el atacante puede infligir al defensor entre los movimientos dados.
    Devuelve (daño_máximo, mejor_movimiento).
    """
    max_dmg = 0
    best_move = None
    for m in moves:
        if m.category == "status" or m.base_power <= 0:
            continue
        dmg, _, is_immune = calculate_damage(attacker, defender, m, weather=weather, rng_factor=1.0)
        if not is_immune and dmg > max_dmg:
            max_dmg = dmg
            best_move = m

    return max_dmg, best_move


def is_ai_in_critical_danger(
    ai_active: PokemonState,
    opponent_active: PokemonState,
    opponent_moves: List[MoveState],
    weather: Optional[str] = None
) -> Tuple[bool, int]:
    """
    Determina si el Pokémon activo de la IA corre peligro de ser debilitado (OHKO o 2HKO con rival más rápido).
    """
    threat_dmg, _ = evaluate_max_threat(opponent_active, ai_active, opponent_moves, weather)
    ai_speed = get_effective_speed(ai_active)
    opp_speed = get_effective_speed(opponent_active)

    # Si el rival ataca primero y el golpe es letal
    if opp_speed >= ai_speed and threat_dmg >= ai_active.current_hp:
        return True, threat_dmg

    # Si el golpe le quita más del 70% de vida restante
    if threat_dmg >= (ai_active.current_hp * 0.70):
        return True, threat_dmg

    return False, threat_dmg
