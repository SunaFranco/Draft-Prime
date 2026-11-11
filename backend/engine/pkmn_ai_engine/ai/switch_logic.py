"""
backend/engine/pkmn_ai_engine/ai/switch_logic.py
Heurística de evaluación de cambios a la banca (Switching) para 6v6.
"""

from typing import List, Tuple, Optional
from ..core.models import PokemonState, MoveState, BattleSnapshot, Action
from ..core.damage import calculate_damage, get_effective_speed
from ..core.types import get_type_effectiveness
from .evaluator import evaluate_max_threat, DifficultyProfile


def evaluate_bench_switches(
    snapshot: BattleSnapshot,
    opponent_estimated_moves: List[MoveState],
    profile: DifficultyProfile
) -> List[Tuple[Action, float, str]]:
    """
    Evalúa cada Pokémon vivo de la banca y devuelve una lista de tuplas:
    (Action("SWITCH", poke.id), score, rationale)
    """
    if not snapshot.ai_bench or not snapshot.opponent_active:
        return []

    opp = snapshot.opponent_active
    results: List[Tuple[Action, float, str]] = []

    for candidate in snapshot.ai_bench:
        if candidate.is_fainted or candidate.current_hp <= 0:
            continue

        # 1. Daño de entrada (el rival atacará en el turno del switch)
        switch_in_dmg, _ = evaluate_max_threat(opp, candidate, opponent_estimated_moves, snapshot.weather)

        # Si el golpe de entrada mata al candidato, no es un cambio viable
        if switch_in_dmg >= candidate.current_hp:
            continue

        hp_remaining_after = candidate.current_hp - switch_in_dmg
        hp_percent_after = hp_remaining_after / max(1, candidate.max_hp)

        # 2. Potencial ofensivo del candidato contra el rival
        counter_dmg, best_counter_move = evaluate_max_threat(candidate, opp, candidate.moves, snapshot.weather)

        # 3. Comparación de velocidad del candidato
        cand_speed = get_effective_speed(candidate)
        opp_speed = get_effective_speed(opp)
        is_faster = cand_speed > opp_speed

        # 4. Cálculo del Score
        # Base: daño ofensivo proyectado normalizado
        score = float(counter_dmg)

        # Bonificación por resistencia / inmunidad a los tipos del rival
        for opp_t in opp.types:
            eff = get_type_effectiveness(opp_t, candidate.types)
            if eff == 0.0:
                score += 350.0  # Inmunidad total
            elif eff <= 0.5:
                score += 180.0  # Resistencia

        # Bono si tras entrar, puede rematar al rival siendo más rápido
        if counter_dmg >= opp.current_hp and is_faster:
            score += profile.weight_lethal_bonus * 0.85

        # Penalización por daño recibido al entrar
        damage_penalty = (switch_in_dmg / max(1, candidate.max_hp)) * 300.0
        score -= damage_penalty

        # Si la vida que le queda tras entrar es muy baja (<25%), castigo extra
        if hp_percent_after < 0.25:
            score -= 200.0

        rationale = (
            f"Switch a {candidate.species}: recibe {switch_in_dmg} dmg al entrar "
            f"({round(hp_percent_after*100)}% HP rem.), contraataca con {counter_dmg} dmg"
        )

        results.append((Action(type="SWITCH", choice=candidate.id), score, rationale))

    # Ordenar candidatos de mayor a menor score
    results.sort(key=lambda x: x[1], reverse=True)
    return results
