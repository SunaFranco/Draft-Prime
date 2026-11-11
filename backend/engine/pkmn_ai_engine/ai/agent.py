"""
backend/engine/pkmn_ai_engine/ai/agent.py
Agente Heurístico Principal de Combate (PokemonAIAgent).
Orquesta la toma de decisiones competitivas para 6v6 Singles con Megas.
"""

import random
from typing import Optional, List, Tuple
from ..core.models import (
    BattleSnapshot,
    DecisionResult,
    Action,
    MoveState,
    PokemonState,
)
from ..core.damage import calculate_damage, get_effective_speed
from ..core.megas import check_can_mega
from ..core.types import get_type_effectiveness
from .tracker import OpponentTracker
from .evaluator import (
    get_profile,
    DifficultyProfile,
    evaluate_max_threat,
    is_ai_in_critical_danger,
)
from .switch_logic import evaluate_bench_switches


class PokemonAIAgent:
    """Agente de combate PVE modular y configurable por dificultad."""

    def __init__(self, difficulty: str = "medium", tracker: Optional[OpponentTracker] = None):
        self.difficulty = difficulty.lower()
        self.profile: DifficultyProfile = get_profile(self.difficulty)
        self.tracker: OpponentTracker = tracker or OpponentTracker()

    def decide_action(self, snapshot: BattleSnapshot) -> DecisionResult:
        """
        Punto de entrada principal: analiza el snapshot y devuelve la mejor acción.
        """
        ai = snapshot.ai_active
        opp = snapshot.opponent_active

        # Caso borde: si el activo está muerto o no existe, forzar cambio
        if not ai or ai.is_fainted or ai.current_hp <= 0:
            return self._force_faint_switch(snapshot)

        # Si no hay rival activo (partida terminada o error), acción neutra
        if not opp or opp.is_fainted or opp.current_hp <= 0:
            first_move = ai.moves[0].id if ai.moves else "struggle"
            return DecisionResult(
                action=Action(type="MOVE", choice=first_move),
                score=100.0,
                debug_rationale="Rival no activo, ataque directo.",
            )

        # 1. Obtener movimientos estimados del rival a través del tracker
        tracked_opp = self.tracker.get_or_create(opp.species)
        opp_estimated_moves = tracked_opp.get_estimated_moves(opp)

        # 2. Verificar si la IA puede y debe megaevolucionar en este turno
        wants_mega = False
        stone_key = check_can_mega(ai)
        if stone_key and not snapshot.ai_mega_used and not ai.is_mega:
            # En combate competitivo, si la Mega está lista y se va a atacar, se activa siempre
            wants_mega = True

        # 3. Evaluar opciones de ataque del Pokémon activo
        move_candidates: List[Tuple[Action, float, str]] = []
        scores_map: dict[str, float] = {}

        ai_speed = get_effective_speed(ai)
        opp_speed = get_effective_speed(opp)

        for move in ai.moves:
            score, rationale = self._evaluate_move(
                ai, opp, move, wants_mega, ai_speed, opp_speed, snapshot.weather
            )
            scores_map[move.name] = round(score, 1)
            action = Action(type="MOVE", choice=move.id, mega=wants_mega)
            move_candidates.append((action, score, rationale))

        # 4. Evaluar opciones de cambio a la banca (Switch)
        switch_candidates: List[Tuple[Action, float, str]] = []
        in_danger, threat_dmg = is_ai_in_critical_danger(ai, opp, opp_estimated_moves, snapshot.weather)

        # Evaluamos banca si estamos en peligro o si tenemos poca efectividad ofensiva
        best_attack_dmg = max([c[1] for c in move_candidates] or [0])
        needs_switch_check = in_danger or (best_attack_dmg < opp.max_hp * 0.18 and snapshot.ai_bench)

        if needs_switch_check and snapshot.ai_bench:
            switches = evaluate_bench_switches(snapshot, opp_estimated_moves, self.profile)
            for act, sc, rat in switches:
                scores_map[f"SWITCH_{act.choice}"] = round(sc, 1)
                switch_candidates.append((act, sc, rat))

        # 5. Consolidar todas las opciones
        all_candidates = move_candidates + switch_candidates
        if not all_candidates:
            # Fallback seguro
            first_move_id = ai.moves[0].id if ai.moves else "struggle"
            return DecisionResult(
                action=Action(type="MOVE", choice=first_move_id),
                score=50.0,
                debug_rationale="Fallback sin candidatos válidos.",
            )

        # 6. Aplicar factor de ruido según dificultad
        if self.profile.noise_factor > 0.0:
            for i in range(len(all_candidates)):
                act, sc, rat = all_candidates[i]
                noise = random.uniform(-self.profile.noise_factor, self.profile.noise_factor) * abs(sc)
                all_candidates[i] = (act, sc + noise, rat)

        # 7. Seleccionar la mejor opción
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        best_action, best_score, best_rationale = all_candidates[0]

        return DecisionResult(
            action=best_action,
            score=best_score,
            debug_rationale=best_rationale,
            scores_evaluated=scores_map,
        )

    def _evaluate_move(
        self,
        ai: PokemonState,
        opp: PokemonState,
        move: MoveState,
        wants_mega: bool,
        ai_speed: float,
        opp_speed: float,
        weather: Optional[str]
    ) -> Tuple[float, str]:
        """Calcula el puntaje heurístico para un movimiento individual."""
        if move.category == "status" or move.base_power <= 0:
            return self._evaluate_status_move(ai, opp, move)

        # Cálculo de daño considerando precisión
        predicted_dmg, effectiveness, is_immune = calculate_damage(
            ai, opp, move, weather=weather, rng_factor=1.0
        )

        if is_immune or effectiveness == 0.0:
            return -500.0, f"{move.name}: Inmune (0x daño)."

        score = float(predicted_dmg) * move.accuracy

        # Bono letal: el ataque garantiza noquear al rival
        is_lethal = predicted_dmg >= opp.current_hp
        is_faster = ai_speed > opp_speed or move.priority > 0

        if is_lethal:
            score += self.profile.weight_lethal_bonus
            if is_faster:
                # Si es más rápido y letal, la jugada es prácticamente perfecta
                score += self.profile.weight_speed_priority

        # Bono de prioridad si la IA es más lenta pero está a punto de caer
        if move.priority > 0 and ai_speed <= opp_speed:
            score += 150.0

        rationale = (
            f"{move.name}: {predicted_dmg} daño ({effectiveness}x) "
            f"precisión={move.accuracy*100}%"
            + (" [LETAL]" if is_lethal else "")
            + (" [PRIMERO]" if is_faster else "")
        )
        return score, rationale

    def _evaluate_status_move(
        self,
        ai: PokemonState,
        opp: PokemonState,
        move: MoveState
    ) -> Tuple[float, str]:
        """Puntúa movimientos de estado (Danza Espada, Tóxico, Onda Trueno, etc.)."""
        m_name = move.name.lower()
        # Movimientos de Boost (ej: Swords Dance, Nasty Plot, Dragon Dance)
        if any(b in m_name for b in ["dance", "plot", "boost", "curse", "calm mind", "growth"]):
            if ai.hp_percent >= 0.70:
                return 220.0, f"{move.name}: Boost viable con salud alta ({round(ai.hp_percent*100)}% HP)."
            return 30.0, f"{move.name}: Boost arriesgado por vida baja."

        # Movimientos de alteración de estado (Thunder Wave, Will-O-Wisp, Toxic)
        if any(s in m_name for s in ["wave", "toxic", "spore", "wisp", "powder"]):
            if opp.status is None:
                # Chequeo de inmunidades básicas por tipo
                if "wave" in m_name and "Ground" in opp.types:
                    return -500.0, f"{move.name}: Ineficaz contra tipo Tierra."
                if "wisp" in m_name and "Fire" in opp.types:
                    return -500.0, f"{move.name}: Ineficaz contra tipo Fuego."
                return 260.0, f"{move.name}: Aplica estado alterado valioso al rival activo."
            return -200.0, f"{move.name}: Rival ya tiene estado {opp.status}."

        # Movimientos de recuperación (Recover, Roost, Synthesis)
        if any(r in m_name for r in ["recover", "roost", "rest", "synthesis", "soft-boiled", "slack off"]):
            if ai.hp_percent <= 0.50:
                return 320.0, f"{move.name}: Recuperación crucial de HP."
            return 10.0, f"{move.name}: Salud suficiente, recuperación innecesaria."

        return 50.0, f"{move.name}: Movimiento de estado genérico."

    def _force_faint_switch(self, snapshot: BattleSnapshot) -> DecisionResult:
        """Elige obligatoriamente el mejor reemplazo de la banca cuando el activo cayó."""
        if not snapshot.ai_bench:
            return DecisionResult(
                action=Action(type="MOVE", choice="none"),
                score=0.0,
                debug_rationale="Sin reemplazos disponibles.",
            )

        alive_bench = [p for p in snapshot.ai_bench if not p.is_fainted and p.current_hp > 0]
        if not alive_bench:
            return DecisionResult(
                action=Action(type="MOVE", choice="none"),
                score=0.0,
                debug_rationale="Todo el equipo está debilitado.",
            )

        # Si hay rival activo, buscamos el mejor matchup
        opp = snapshot.opponent_active
        if opp and not opp.is_fainted:
            tracked_opp = self.tracker.get_or_create(opp.species)
            opp_moves = tracked_opp.get_estimated_moves(opp)
            switches = evaluate_bench_switches(snapshot, opp_moves, self.profile)
            if switches:
                best_sw = switches[0]
                return DecisionResult(
                    action=best_sw[0],
                    score=best_sw[1],
                    debug_rationale=f"Reemplazo por KO: {best_sw[2]}",
                )

        # Fallback al primer miembro vivo
        first_alive = alive_bench[0]
        return DecisionResult(
            action=Action(type="SWITCH", choice=first_alive.id),
            score=100.0,
            debug_rationale=f"Reemplazo por KO de emergencia: {first_alive.species}",
        )
