"""
backend/engine/pkmn_ai_engine/core/damage.py
Cálculo oficial de daño y velocidad de Pokémon basado en Pokémon Showdown (Gen 9: sim/battle-actions.ts, sim/pokemon.ts).
Incluye críticos (ignorando etapas negativas/positivas y pantallas), climas, terrenos, habilidades, objetos y pantallas.
"""

import math
from typing import Optional, Tuple
from .models import PokemonState, MoveState, SideConditions
from .types import get_type_effectiveness, get_single_effectiveness


def get_boost_multiplier(stage: int) -> float:
    """Calcula el multiplicador para etapas de estadísticas entre -6 y +6."""
    clamped = max(-6, min(6, stage))
    if clamped >= 0:
        return (2.0 + clamped) / 2.0
    return 2.0 / (2.0 - clamped)


def get_accuracy_evasion_multiplier(acc_stage: int, eva_stage: int) -> float:
    """Calcula el multiplicador combinado de precisión y evasión según Showdown (-6 a +6)."""
    clamped = max(-6, min(6, acc_stage - eva_stage))
    if clamped >= 0:
        return (3.0 + clamped) / 3.0
    return 3.0 / (3.0 - clamped)


def get_crit_chance(crit_ratio: int) -> float:
    """Devuelve la probabilidad de golpe crítico según el ratio de Showdown Gen 9."""
    if crit_ratio <= 1:
        return 1.0 / 24.0
    if crit_ratio == 2:
        return 1.0 / 8.0
    if crit_ratio == 3:
        return 0.50
    return 1.0


def get_effective_speed(
    pokemon: PokemonState,
    side_conditions: Optional[SideConditions] = None,
    weather: Optional[str] = None,
) -> float:
    """
    Calcula la velocidad efectiva siguiendo sim/pokemon.ts (getActionSpeed):
    - Etapas de velocidad (-6 a +6)
    - Parálisis (0.5x, salvo Quick Feet que da 1.5x)
    - Choice Scarf (1.5x)
    - Tailwind (2.0x)
    - Habilidades climáticas (Swift Swim, Chlorophyll, Sand Rush, Slush Rush -> 2.0x)
    """
    speed = float(pokemon.stats.spe) * get_boost_multiplier(pokemon.boosts.spe)
    ability = (pokemon.ability or "").lower()
    item = (pokemon.item or "").lower()

    if pokemon.status == "PAR":
        if ability == "quick feet":
            speed *= 1.5
        else:
            speed *= 0.5
    elif pokemon.status is not None and ability == "quick feet":
        speed *= 1.5

    if item == "choice scarf":
        speed *= 1.5

    if side_conditions and side_conditions.tailwind_turns > 0:
        speed *= 2.0

    if weather == "Rain" and ability == "swift swim":
        speed *= 2.0
    elif weather == "Sun" and ability == "chlorophyll":
        speed *= 2.0
    elif weather == "Sandstorm" and ability == "sand rush":
        speed *= 2.0
    elif weather == "Snow" and ability == "slush rush":
        speed *= 2.0

    return math.floor(speed)


def _compute_move_effectiveness(move: MoveState, defender: PokemonState) -> Tuple[float, bool]:
    """Calcula la efectividad de tipos considerando inmunidades por habilidad, objeto y Freeze-Dry."""
    move_t = move.type.capitalize()
    def_ability = (defender.ability or "").lower()

    # Inmunidades por habilidad o suelo (Ground)
    if move_t == "Ground" and not defender.is_grounded():
        return 0.0, True
    if move_t == "Ground" and def_ability in ("levitate", "earth eater"):
        return 0.0, True
    if move_t == "Fire" and def_ability in ("flash fire", "well-baked body"):
        return 0.0, True
    if move_t == "Water" and def_ability in ("water absorb", "storm drain", "dry skin"):
        return 0.0, True
    if move_t == "Electric" and def_ability in ("volt absorb", "lightning rod", "motor drive"):
        return 0.0, True
    if move_t == "Grass" and def_ability == "sap sipper":
        return 0.0, True

    # Caso especial de Showdown: Freeze-Dry es súper eficaz (2x) contra tipo Water
    if move.id == "freeze-dry":
        total = 1.0
        for dt in defender.types:
            if not dt:
                continue
            if dt.capitalize() == "Water":
                total *= 2.0
            else:
                total *= get_single_effectiveness("Ice", dt)
        return total, (total == 0.0)

    eff = get_type_effectiveness(move_t, defender.types)
    return eff, (eff == 0.0)


def calculate_damage(
    attacker: PokemonState,
    defender: PokemonState,
    move: MoveState,
    weather: Optional[str] = None,
    terrain: Optional[str] = None,
    defender_side: Optional[SideConditions] = None,
    rng_factor: float = 1.0,
    is_critical: bool = False,
) -> Tuple[int, float, bool]:
    """
    Calcula el daño infligido siguiendo la fórmula oficial Gen 9 de Pokémon Showdown.
    Devuelve: (daño_entero, multiplicador_efectividad, fue_inmune)
    """
    if move.category == "status" or move.base_power <= 0:
        return 0, 1.0, False

    # 1. Efectividad de tipos e inmunidades
    effectiveness, is_immune = _compute_move_effectiveness(move, defender)
    if is_immune or effectiveness == 0.0:
        return 0, 0.0, True

    atk_ability = (attacker.ability or "").lower()
    def_ability = (defender.ability or "").lower()
    atk_item = (attacker.item or "").lower()
    def_item = (defender.item or "").lower()
    move_t = move.type.capitalize()

    # 2. Poder base dinámico (onBasePower en Showdown)
    base_power = float(move.base_power)

    if move.id == "hex" and defender.status is not None:
        base_power *= 2.0
    elif move.id == "acrobatics" and not attacker.item:
        base_power *= 2.0
    elif move.id == "knock-off" and defender.item:
        base_power *= 1.5
    elif move.id == "facade" and attacker.status in ("BRN", "PAR", "PSN", "TOX"):
        base_power *= 2.0
    elif move.id == "venoshock" and defender.status in ("PSN", "TOX"):
        base_power *= 2.0

    if atk_ability == "technician" and base_power <= 60:
        base_power *= 1.5
    if atk_ability == "tough claws" and move.makes_contact:
        base_power *= 1.3
    if atk_ability == "iron fist" and "punch" in move.id:
        base_power *= 1.2
    if atk_ability == "strong jaw" and move.id in ("crunch", "bite", "fire-fang", "ice-fang", "thunder-fang", "psychic-fangs"):
        base_power *= 1.5

    # Modificadores de Terreno (Gen 9: 1.3x para Electric/Grassy/Psychic, 0.5x Misty vs Dragon)
    if terrain == "Electric" and attacker.is_grounded() and move_t == "Electric":
        base_power *= 1.3
    elif terrain == "Grassy" and attacker.is_grounded() and move_t == "Grass":
        base_power *= 1.3
    elif terrain == "Psychic" and attacker.is_grounded() and move_t == "Psychic":
        base_power *= 1.3
    elif terrain == "Misty" and defender.is_grounded() and move_t == "Dragon":
        base_power *= 0.5

    if terrain == "Grassy" and defender.is_grounded() and move.id in ("earthquake", "bulldoze"):
        base_power *= 0.5

    # 3. Selección de estadísticas de Ataque y Defensa (respetando críticos y overrides como Psyshock / Body Press)
    if move.override_offensive_stat == "def":
        off_stage = max(0, attacker.boosts.def_) if is_critical else attacker.boosts.def_
        atk = float(attacker.stats.def_) * get_boost_multiplier(off_stage)
    elif move.category == "physical":
        off_stage = max(0, attacker.boosts.atk) if is_critical else attacker.boosts.atk
        atk = float(attacker.stats.atk) * get_boost_multiplier(off_stage)
        if atk_ability in ("huge power", "pure power"):
            atk *= 2.0
        elif atk_ability == "guts" and attacker.status is not None:
            atk *= 1.5
        if atk_item == "choice band":
            atk *= 1.5
    else:  # "special"
        off_stage = max(0, attacker.boosts.spa) if is_critical else attacker.boosts.spa
        atk = float(attacker.stats.spa) * get_boost_multiplier(off_stage)
        if atk_item == "choice specs":
            atk *= 1.5

    use_phys_def = (move.override_defensive_stat == "def") or (move.category == "physical" and move.override_defensive_stat != "spd")
    if use_phys_def:
        def_stage = min(0, defender.boosts.def_) if is_critical else defender.boosts.def_
        dfn = float(defender.stats.def_) * get_boost_multiplier(def_stage)
        # En Gen 9, Snow aumenta 1.5x la Defensa física de los tipo Ice
        if weather == "Snow" and "Ice" in defender.types:
            dfn *= 1.5
    else:
        def_stage = min(0, defender.boosts.spd) if is_critical else defender.boosts.spd
        dfn = float(defender.stats.spd) * get_boost_multiplier(def_stage)
        # Sandstorm aumenta 1.5x la Defensa Especial de los tipo Rock
        if weather == "Sandstorm" and "Rock" in defender.types:
            dfn *= 1.5
        if def_item == "assault vest":
            dfn *= 1.5

    if def_item == "eviolite":
        dfn *= 1.5

    if dfn <= 0:
        dfn = 1.0

    # 4. Fórmula base oficial Gen 9
    level = attacker.level
    level_factor = math.floor((2.0 * level) / 5.0) + 2
    base_dmg = math.floor((level_factor * base_power * (atk / dfn)) / 50.0) + 2

    # 5. Modificadores climáticos de poder
    weather_mult = 1.0
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

    # 6. Golpe Crítico (1.5x en Gen 9)
    crit_mult = 1.5 if is_critical else 1.0

    # 7. STAB (Same Type Attack Bonus)
    stab_mult = 1.0
    attacker_types = [t.capitalize() for t in attacker.types if t]
    if move_t in attacker_types:
        stab_mult = 2.0 if atk_ability == "adaptability" else 1.5

    # 8. Quemadura (0.5x en ataques físicos salvo Guts o Facade)
    burn_mult = 1.0
    if move.category == "physical" and attacker.status == "BRN" and atk_ability != "guts" and move.id != "facade":
        burn_mult = 0.5

    # 9. Pantallas (Reflect / Light Screen / Aurora Veil -> 0.5x si no es crítico ni Infiltrator)
    screen_mult = 1.0
    if defender_side and not is_critical and atk_ability != "infiltrator":
        if defender_side.aurora_veil_turns > 0:
            screen_mult = 0.5
        elif move.category == "physical" and defender_side.reflect_turns > 0:
            screen_mult = 0.5
        elif move.category == "special" and defender_side.light_screen_turns > 0:
            screen_mult = 0.5

    # 10. Otros modificadores (Thick Fat, Multiscale, Filter, Life Orb, Expert Belt)
    other_mult = 1.0
    if def_ability == "thick fat" and move_t in ("Fire", "Ice"):
        other_mult *= 0.5
    if def_ability in ("multiscale", "shadow shield") and defender.current_hp >= defender.max_hp:
        other_mult *= 0.5
    if def_ability in ("filter", "solid rock", "prism armor") and effectiveness > 1.0:
        other_mult *= 0.75

    if atk_item == "life orb":
        other_mult *= 1.3
    elif atk_item == "expert belt" and effectiveness > 1.0:
        other_mult *= 1.2

    # 11. Daño final
    final_dmg = (
        base_dmg
        * weather_mult
        * crit_mult
        * rng_factor
        * stab_mult
        * effectiveness
        * burn_mult
        * screen_mult
        * other_mult
    )
    final_int_dmg = max(1, math.floor(final_dmg))

    return final_int_dmg, effectiveness, False
