"""
backend/engine/pkmn_ai_engine/resolver/combat_engine.py
Motor de combate y resolución de turnos para 6v6 Singles con Megas.
Genera la lista de eventos atómicos para el frontend.
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from ..core.models import (
    BattleSnapshot,
    PokemonState,
    MoveState,
    Action,
)
from ..core.damage import calculate_damage
from ..core.megas import check_can_mega, trigger_mega_evolution
from ..ai.tracker import OpponentTracker
from .turn_order import determine_turn_order


@dataclass
class TurnResult:
    events: List[Dict[str, Any]] = field(default_factory=list)
    new_snapshot: Optional[BattleSnapshot] = None
    battle_status: str = "in_progress"  # "in_progress", "won", "lost", "waiting_player_switch", "waiting_ai_switch"
    message: str = ""


class CombatEngine:
    """Resuelve un turno completo de combate entre el jugador y la IA."""

    def __init__(self, tracker: Optional[OpponentTracker] = None):
        self.tracker: OpponentTracker = tracker or OpponentTracker()

    def resolve_turn(
        self,
        snapshot: BattleSnapshot,
        player_action: Action,
        ai_action: Action,
    ) -> TurnResult:
        events: List[Dict[str, Any]] = []

        player_poke = snapshot.player_active
        ai_poke = snapshot.ai_active

        if not player_poke or not ai_poke:
            return TurnResult(
                events=[{"type": "ERROR", "text": "Falta un Pokémon activo en la batalla."}],
                new_snapshot=snapshot,
                battle_status="error",
            )

        # 1. Manejo de cambios forzados por KO previo (Faint Switches)
        if player_poke.is_fainted and player_action.type.upper() == "SWITCH":
            self._handle_switch("player", player_action.choice, snapshot, events)
            return TurnResult(
                events=events,
                new_snapshot=snapshot,
                battle_status=self._check_battle_status(snapshot),
            )

        if ai_poke.is_fainted and ai_action.type.upper() == "SWITCH":
            self._handle_switch("ai", ai_action.choice, snapshot, events)
            return TurnResult(
                events=events,
                new_snapshot=snapshot,
                battle_status=self._check_battle_status(snapshot),
            )

        # 2. FASE DE CAMBIOS (SWITCHES) — Prioridad absoluta sobre cualquier movimiento (+6)
        player_switched = False
        ai_switched = False

        if player_action.type.upper() == "SWITCH":
            self._handle_switch("player", player_action.choice, snapshot, events)
            player_switched = True

        if ai_action.type.upper() == "SWITCH":
            self._handle_switch("ai", ai_action.choice, snapshot, events)
            ai_switched = True

        # Si ambos cambiaron de Pokémon en el mismo turno, se concluye la fase de cambios
        if player_switched and ai_switched:
            self._apply_end_of_turn_effects(snapshot, events)
            snapshot.turn += 1
            return TurnResult(
                events=events,
                new_snapshot=snapshot,
                battle_status=self._check_battle_status(snapshot),
            )

        # Obtener los Pokémon actualmente activos tras posibles cambios
        current_player = snapshot.player_active
        current_ai = snapshot.ai_active

        # 3. Resolución de Megaevoluciones (ocurren antes de que los Pokémon ataquen)
        if not player_switched and player_action.mega and not snapshot.player_mega_used and not current_player.is_mega:
            stone = check_can_mega(current_player)
            if stone and trigger_mega_evolution(current_player, stone):
                snapshot.player_mega_used = True
                events.append({
                    "type": "MEGA_EVOLVE",
                    "side": "player",
                    "pokemon": current_player.species,
                    "text": f"¡La Mega Piedra de {current_player.species} reacciona! ¡Ha Megaevolucionado!",
                })

        if not ai_switched and ai_action.mega and not snapshot.ai_mega_used and not current_ai.is_mega:
            stone = check_can_mega(current_ai)
            if stone and trigger_mega_evolution(current_ai, stone):
                snapshot.ai_mega_used = True
                events.append({
                    "type": "MEGA_EVOLVE",
                    "side": "ai",
                    "pokemon": current_ai.species,
                    "text": f"¡La Mega Piedra de {current_ai.species} rival reacciona! ¡Ha Megaevolucionado!",
                })

        # 4. FASE DE ATAQUES
        # Caso A: El jugador cambió y la IA ataca (la IA ataca al Pokémon que acaba de entrar)
        if player_switched and not ai_switched:
            ai_move = self._find_move(current_ai, ai_action.choice)
            self._execute_action("ai", current_ai, ai_action, ai_move, current_player, "player", snapshot, events)

        # Caso B: La IA cambió y el jugador ataca (el jugador ataca al Pokémon que acaba de entrar)
        elif ai_switched and not player_switched:
            p_move = self._find_move(current_player, player_action.choice)
            self._execute_action("player", current_player, player_action, p_move, current_ai, "ai", snapshot, events)

        # Caso C: Ambos usan MOVE (se determina orden por prioridad de movimiento y velocidad)
        elif not player_switched and not ai_switched:
            p_move = self._find_move(current_player, player_action.choice)
            ai_move = self._find_move(current_ai, ai_action.choice)

            first_side, second_side = determine_turn_order(
                player_action, current_player, p_move,
                ai_action, current_ai, ai_move
            )

            if first_side == "player":
                self._execute_action("player", current_player, player_action, p_move, current_ai, "ai", snapshot, events)
                # El segundo solo ataca si sigue con vida tras el primer golpe
                if not current_ai.is_fainted and current_ai.current_hp > 0:
                    self._execute_action("ai", current_ai, ai_action, ai_move, current_player, "player", snapshot, events)
            else:
                self._execute_action("ai", current_ai, ai_action, ai_move, current_player, "player", snapshot, events)
                # El segundo solo ataca si sigue con vida tras el primer golpe
                if not current_player.is_fainted and current_player.current_hp > 0:
                    self._execute_action("player", current_player, player_action, p_move, current_ai, "ai", snapshot, events)

        # 7. Efectos de fin de turno (Daño residual por Quemadura / Veneno)
        self._apply_end_of_turn_effects(snapshot, events)

        # 8. Incrementar turno
        snapshot.turn += 1

        # 9. Evaluar estado de victoria / derrota / cambio obligado
        status = self._check_battle_status(snapshot)

        return TurnResult(
            events=events,
            new_snapshot=snapshot,
            battle_status=status,
        )

    def _execute_action(
        self,
        side: str,
        actor: PokemonState,
        action: Action,
        move: Optional[MoveState],
        defender: PokemonState,
        def_side: str,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        if action.type.upper() == "SWITCH":
            self._handle_switch(side, action.choice, snapshot, events)
            return

        if not move:
            # Fallback a Struggle si no hay movimiento
            move = MoveState(
                id="struggle",
                name="Struggle",
                type="Normal",
                category="physical",
                base_power=50,
                accuracy=1.0,
            )

        # Registrar en el tracker si el jugador usó un movimiento
        if side == "player":
            self.tracker.record_move_used(actor.species, move.name)

        events.append({
            "type": "MOVE",
            "side": side,
            "pokemon": actor.species,
            "move": move.name,
            "text": f"{actor.species} usó {move.name}!",
        })

        # Chequeo de precisión
        accuracy_roll = random.random()
        if accuracy_roll > move.accuracy:
            events.append({
                "type": "MISS",
                "side": side,
                "pokemon": actor.species,
                "text": f"¡El ataque de {actor.species} falló!",
            })
            return

        # Movimientos de estado
        if move.category == "status" or move.base_power <= 0:
            self._resolve_status_move_effects(side, actor, defender, move, events)
            return

        # Chequeo de Golpe Crítico (1/24 ≈ 4.17%)
        is_crit = random.random() < (1.0 / 24.0)

        # Roll de daño aleatorio entre 0.85 y 1.00
        rng_roll = random.uniform(0.85, 1.00)

        damage, effectiveness, is_immune = calculate_damage(
            actor, defender, move,
            weather=snapshot.weather,
            rng_factor=rng_roll,
            is_critical=is_crit,
        )

        if is_immune:
            events.append({
                "type": "IMMUNE",
                "side": def_side,
                "pokemon": defender.species,
                "text": f"No afecta a {defender.species}...",
            })
            return

        # Aplicar daño
        defender.current_hp = max(0, defender.current_hp - damage)
        hp_pct = round(defender.hp_percent, 3)

        events.append({
            "type": "DAMAGE",
            "side": def_side,
            "pokemon": defender.species,
            "damage": damage,
            "remaining_hp": defender.current_hp,
            "max_hp": defender.max_hp,
            "hp_percent": hp_pct,
            "critical": is_crit,
            "effectiveness": effectiveness,
            "text": f"¡{defender.species} recibió {damage} puntos de daño!",
        })

        if is_crit:
            events.append({"type": "MESSAGE", "text": "¡Un golpe crítico!"})

        if effectiveness >= 2.0:
            events.append({"type": "MESSAGE", "text": "¡Es súper eficaz!"})
        elif 0.0 < effectiveness < 1.0:
            events.append({"type": "MESSAGE", "text": "No es muy eficaz..."})

        # Chequeo de KO
        if defender.current_hp <= 0:
            defender.is_fainted = True
            events.append({
                "type": "FAINT",
                "side": def_side,
                "pokemon": defender.species,
                "text": f"¡{defender.species} se ha debilitado!",
            })

    def _resolve_status_move_effects(
        self,
        side: str,
        actor: PokemonState,
        defender: PokemonState,
        move: MoveState,
        events: List[Dict[str, Any]],
    ) -> None:
        m_name = move.name.lower()

        # Boosts propios (Swords Dance, Calm Mind, etc.)
        if "swords dance" in m_name:
            actor.boosts.atk = min(6, actor.boosts.atk + 2)
            events.append({"type": "BOOST", "side": side, "stat": "atk", "stages": 2, "text": f"¡El Ataque de {actor.species} subió drásticamente!"})
        elif "dragon dance" in m_name:
            actor.boosts.atk = min(6, actor.boosts.atk + 1)
            actor.boosts.spe = min(6, actor.boosts.spe + 1)
            events.append({"type": "BOOST", "side": side, "text": f"¡El Ataque y la Velocidad de {actor.species} aumentaron!"})
        elif "calm mind" in m_name:
            actor.boosts.spa = min(6, actor.boosts.spa + 1)
            actor.boosts.spd = min(6, actor.boosts.spd + 1)
            events.append({"type": "BOOST", "side": side, "text": f"¡El Ataque Esp. y Defensa Esp. de {actor.species} aumentaron!"})

        # Estados alterados al rival
        elif "thunder wave" in m_name:
            if "Ground" not in defender.types and defender.status is None:
                defender.status = "PAR"
                events.append({"type": "STATUS", "side": "def", "status": "PAR", "text": f"¡{defender.species} ha quedado paralizado! ¡Quizá no se pueda mover!"})
            else:
                events.append({"type": "MESSAGE", "text": "¡Pero falló!"})
        elif "will-o-wisp" in m_name:
            if "Fire" not in defender.types and defender.status is None:
                defender.status = "BRN"
                events.append({"type": "STATUS", "side": "def", "status": "BRN", "text": f"¡{defender.species} ha sufrido una quemadura!"})
            else:
                events.append({"type": "MESSAGE", "text": "¡Pero falló!"})
        elif "toxic" in m_name:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.status is None:
                defender.status = "PSN"
                events.append({"type": "STATUS", "side": "def", "status": "PSN", "text": f"¡{defender.species} ha sido gravemente envenenado!"})
            else:
                events.append({"type": "MESSAGE", "text": "¡Pero falló!"})

        # Recuperación de vida
        elif any(r in m_name for r in ["recover", "roost", "synthesis", "soft-boiled", "slack off"]):
            heal = math.floor(actor.max_hp * 0.5)
            actor.current_hp = min(actor.max_hp, actor.current_hp + heal)
            events.append({"type": "HEAL", "side": side, "heal_amount": heal, "text": f"¡{actor.species} recuperó salud!"})

    def _handle_switch(
        self,
        side: str,
        choice_id: str,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        bench = snapshot.player_bench if side == "player" else snapshot.ai_bench
        active = snapshot.player_active if side == "player" else snapshot.ai_active

        # Buscar el Pokémon en la banca por ID o por especie
        found_idx = -1
        for idx, p in enumerate(bench):
            if (p.id == choice_id or p.species.lower() == choice_id.lower()) and not p.is_fainted:
                found_idx = idx
                break

        if found_idx == -1:
            events.append({"type": "MESSAGE", "text": f"Cambio inválido: {choice_id} no está disponible."})
            return

        new_active = bench.pop(found_idx)
        if active:
            # Resetear boosts al cambiar a la banca
            active.boosts.atk = 0
            active.boosts.def_ = 0
            active.boosts.spa = 0
            active.boosts.spd = 0
            active.boosts.spe = 0
            bench.append(active)

        if side == "player":
            snapshot.player_active = new_active
            events.append({
                "type": "SWITCH",
                "side": "player",
                "pokemon": new_active.species,
                "text": f"¡Adelante, {new_active.species}!",
            })
        else:
            snapshot.ai_active = new_active
            events.append({
                "type": "SWITCH",
                "side": "ai",
                "pokemon": new_active.species,
                "text": f"¡El rival envió a {new_active.species}!",
            })

    def _apply_end_of_turn_effects(
        self,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        for side, poke in [("player", snapshot.player_active), ("ai", snapshot.ai_active)]:
            if not poke or poke.is_fainted or poke.current_hp <= 0:
                continue

            # Daño por Quemadura (1/16 max HP)
            if poke.status == "BRN":
                burn_dmg = max(1, math.floor(poke.max_hp / 16.0))
                poke.current_hp = max(0, poke.current_hp - burn_dmg)
                events.append({
                    "type": "STATUS_DAMAGE",
                    "side": side,
                    "pokemon": poke.species,
                    "damage": burn_dmg,
                    "status": "BRN",
                    "text": f"¡La quemadura causa daño a {poke.species}!",
                })
                if poke.current_hp <= 0:
                    poke.is_fainted = True
                    events.append({"type": "FAINT", "side": side, "pokemon": poke.species, "text": f"¡{poke.species} se ha debilitado!"})

            # Daño por Veneno (1/8 max HP)
            elif poke.status == "PSN":
                psn_dmg = max(1, math.floor(poke.max_hp / 8.0))
                poke.current_hp = max(0, poke.current_hp - psn_dmg)
                events.append({
                    "type": "STATUS_DAMAGE",
                    "side": side,
                    "pokemon": poke.species,
                    "damage": psn_dmg,
                    "status": "PSN",
                    "text": f"¡El veneno causa daño a {poke.species}!",
                })
                if poke.current_hp <= 0:
                    poke.is_fainted = True
                    events.append({"type": "FAINT", "side": side, "pokemon": poke.species, "text": f"¡{poke.species} se ha debilitado!"})

    def _check_battle_status(self, snapshot: BattleSnapshot) -> str:
        # Verificar si todo el equipo de la IA murió
        ai_alive = [p for p in ([snapshot.ai_active] + snapshot.ai_bench) if p and not p.is_fainted and p.current_hp > 0]
        if not ai_alive:
            return "won"  # Ganó el jugador

        # Verificar si todo el equipo del jugador murió
        player_alive = [p for p in ([snapshot.player_active] + snapshot.player_bench) if p and not p.is_fainted and p.current_hp > 0]
        if not player_alive:
            return "lost"  # Perdió el jugador

        # Si el activo del jugador murió pero tiene banca, debe cambiar
        if snapshot.player_active and snapshot.player_active.is_fainted:
            return "waiting_player_switch"

        # Si el activo de la IA murió pero tiene banca, la IA debe cambiar
        if snapshot.ai_active and snapshot.ai_active.is_fainted:
            return "waiting_ai_switch"

        return "in_progress"

    def _find_move(self, pokemon: PokemonState, move_id_or_name: str) -> Optional[MoveState]:
        clean = move_id_or_name.strip().lower()
        for m in pokemon.moves:
            if m.id.lower() == clean or m.name.lower() == clean:
                return m
        return pokemon.moves[0] if pokemon.moves else None
