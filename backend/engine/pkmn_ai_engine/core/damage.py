"""
backend/engine/pkmn_ai_engine/core/damage.py
Cálculo oficial de daño de Pokémon (Gen 9) y modificadores de estadísticas en combate.
"""

import math
from typing import Optional, Tuple
from .models import PokemonState, MoveState, StatBoosts
from .types import get_type_effectiveness


def get_boost_multiplier(stage: int) -> float:
    """Calcula el multiplicador para etapas de estadísticas entre -6 y +6."""
    clamped = max(-6, min(6, stage))
    if clamped >= 0:
        return (2.0 + clamped) / 2.0
    return 2.0 / (2.0 - clamped)


def get_effective_speed(pokemon: PokemonState) -> float:
    """Calcula la velocidad efectiva considerando boosts y parálisis."""
    speed = float(pokemon.stats.spe)
    speed *= get_boost_multiplier(pokemon.boosts.spe)
    if pokemon.status == "PAR":
        speed *= 0.5
    return speed


def calculate_damage(
    attacker: PokemonState,
    defender: PokemonState,
    move: MoveState,
    weather: Optional[str] = None,
    rng_factor: float = 1.0,
    is_critical: bool = False
) -> Tuple[int, float, bool]:
    """
    Calcula el daño infligido de un ataque siguiendo la fórmula oficial Gen 9.
    Devuelve: (daño_entero, multiplicador_efectividad, fue_inmune)
    """
    if move.category == "status" or move.base_power <= 0:
        return 0, 1.0, False

    # 1. Chequeo de efectividad de tipos
    effectiveness = get_type_effectiveness(move.type, defender.types)
    if effectiveness == 0.0:
        return 0, 0.0, True

    # 2. Selección de estadísticas según categoría (Física o Especial)
    if move.category == "physical":
        atk = float(attacker.stats.atk) * get_boost_multiplier(attacker.boosts.atk)
        dfn = float(defender.stats.def_) * get_boost_multiplier(defender.boosts.def_)
        # Reducción por quemadura en atacantes físicos
        if attacker.status == "BRN" and attacker.ability != "Guts":
            atk *= 0.5
    else:  # "special"
        atk = float(attacker.stats.spa) * get_boost_multiplier(attacker.boosts.spa)
        dfn = float(defender.stats.spd) * get_boost_multiplier(defender.boosts.spd)

    if dfn <= 0:
        dfn = 1.0

    # 3. Fórmula base de daño oficial
    level = attacker.level
    level_factor = math.floor((2.0 * level) / 5.0) + 2
    base_dmg = math.floor((level_factor * move.base_power * (atk / dfn)) / 50.0) + 2

    # 4. Modificadores climáticos
    weather_mult = 1.0
    move_t = move.type.capitalize()
    if weather == "Rain":
        if move_t == "Water":
            weather_mult = 1.5
        elif move_t == "Fire":
            weather_mult = 0.5
    elif weather == "Sun":
        if move_t == "Fire":
            weather_mult = 1.5
        elif move_t == "Water":
            weather_mult = 0.5

    # 5. STAB (Same Type Attack Bonus)
    stab_mult = 1.0
    attacker_types = [t.capitalize() for t in attacker.types if t]
    if move_t in attacker_types:
        stab_mult = 2.0 if attacker.ability == "Adaptability" else 1.5

    # 6. Golpe Crítico (1.5x en Gen 9)
    crit_mult = 1.5 if is_critical else 1.0

    # 7. Daño final
    final_dmg = base_dmg * weather_mult * stab_mult * effectiveness * crit_mult * rng_factor
    final_int_dmg = max(1, math.floor(final_dmg))

    return final_int_dmg, effectiveness, False
