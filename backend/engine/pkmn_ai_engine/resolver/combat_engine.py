"""
backend/engine/pkmn_ai_engine/resolver/combat_engine.py
Motor de combate y resolución de turnos para 6v6 Singles (Gen 9 + Megas) basado en Pokémon Showdown:
- sim/battle.ts (orden de fases: Cambios -> Entry Hazards/Abilities -> Megas -> Movimientos -> Residuales)
- sim/battle-actions.ts (precisión/evasión, Protect, Sustituto, multi-hit, secundario, drain/recoil, phazing, pivot)
- sim/conditions.ts (estados BRN, PAR, PSN, TOX progresivo, SLP, FRZ y volátiles flinch, confusion, leech_seed, taunt)
- sim/field.ts (Climas, Terrenos, Trick Room, Stealth Rock, Spikes, Toxic Spikes, Sticky Web, Pantallas y Tailwind)
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from ..core.models import (
    BattleSnapshot,
    PokemonState,
    MoveState,
    SideConditions,
    Action,
)
from ..core.damage import (
    calculate_damage,
    get_effective_speed,
    get_accuracy_evasion_multiplier,
    get_crit_chance,
)
from ..core.types import get_type_effectiveness
from ..core.megas import check_can_mega, trigger_mega_evolution
from ..core.text_es import get_move_text_es
from ..ai.tracker import OpponentTracker
from .turn_order import determine_turn_order, get_effective_priority


STAT_LABELS_ES = {
    "atk": "Ataque",
    "def": "Defensa",
    "def_": "Defensa",
    "spa": "Ataque Esp.",
    "spd": "Defensa Esp.",
    "spe": "Velocidad",
    "accuracy": "Precisión",
    "evasion": "Evasión",
}


@dataclass
class TurnResult:
    events: List[Dict[str, Any]] = field(default_factory=list)
    new_snapshot: Optional[BattleSnapshot] = None
    battle_status: str = "in_progress"  # "in_progress", "won", "lost", "waiting_player_switch", "waiting_ai_switch"
    message: str = ""


class CombatEngine:
    """Resuelve un turno completo de combate entre el jugador y la IA siguiendo el ciclo de Pokémon Showdown."""

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

        player_poke.revealed = True
        ai_poke.revealed = True

        # 1. Reemplazos obligatorios tras debilitarse en el turno previo (Faint Switches)
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

        # 2. FASE DE CAMBIOS (SWITCHES) — Prioridad +6 sobre cualquier movimiento
        player_switched = False
        ai_switched = False

        p_wants_switch = player_action.type.upper() == "SWITCH"
        ai_wants_switch = ai_action.type.upper() == "SWITCH"

        if p_wants_switch and ai_wants_switch:
            first_sw, _ = determine_turn_order(
                player_action, player_poke, None,
                ai_action, ai_poke, None,
                snapshot=snapshot,
            )
            if first_sw == "player":
                self._handle_switch("player", player_action.choice, snapshot, events)
                self._handle_switch("ai", ai_action.choice, snapshot, events)
            else:
                self._handle_switch("ai", ai_action.choice, snapshot, events)
                self._handle_switch("player", player_action.choice, snapshot, events)
            player_switched = True
            ai_switched = True
        elif p_wants_switch:
            self._handle_switch("player", player_action.choice, snapshot, events)
            player_switched = True
        elif ai_wants_switch:
            self._handle_switch("ai", ai_action.choice, snapshot, events)
            ai_switched = True

        # Si ambos cambiaron de Pokémon en el mismo turno, pasamos directo a los efectos de fin de turno
        if player_switched and ai_switched:
            self._apply_end_of_turn_effects(snapshot, events)
            snapshot.turn += 1
            return TurnResult(
                events=events,
                new_snapshot=snapshot,
                battle_status=self._check_battle_status(snapshot),
            )

        current_player = snapshot.player_active
        current_ai = snapshot.ai_active

        # 3. FASE DE MEGAEVOLUCIÓN (Antes de ejecutar movimientos)
        if (
            not player_switched
            and current_player
            and not current_player.is_fainted
            and player_action.mega
            and not snapshot.player_mega_used
            and not current_player.is_mega
        ):
            stone = check_can_mega(current_player)
            if stone and trigger_mega_evolution(current_player, stone):
                snapshot.player_mega_used = True
                events.append({
                    "type": "MEGA_EVOLVE",
                    "side": "player",
                    "pokemon": current_player.species,
                    "text": f"¡La Mega Piedra de {current_player.species} reacciona! ¡Ha Megaevolucionado!",
                })
                self._trigger_entry_ability("player", current_player, current_ai, snapshot, events)

        if (
            not ai_switched
            and current_ai
            and not current_ai.is_fainted
            and ai_action.mega
            and not snapshot.ai_mega_used
            and not current_ai.is_mega
        ):
            stone = check_can_mega(current_ai)
            if stone and trigger_mega_evolution(current_ai, stone):
                snapshot.ai_mega_used = True
                events.append({
                    "type": "MEGA_EVOLVE",
                    "side": "ai",
                    "pokemon": current_ai.species,
                    "text": f"¡La Mega Piedra de {current_ai.species} rival reacciona! ¡Ha Megaevolucionado!",
                })
                self._trigger_entry_ability("ai", current_ai, current_player, snapshot, events)

        # 4. FASE DE ATAQUES
        if player_switched and not ai_switched:
            if current_ai and not current_ai.is_fainted and current_player and not current_player.is_fainted:
                ai_move = self._find_move(current_ai, ai_action.choice)
                self._execute_action("ai", current_ai, ai_action, ai_move, snapshot.player_active, "player", snapshot, events)

        elif ai_switched and not player_switched:
            if current_player and not current_player.is_fainted and current_ai and not current_ai.is_fainted:
                p_move = self._find_move(current_player, player_action.choice)
                self._execute_action("player", current_player, player_action, p_move, snapshot.ai_active, "ai", snapshot, events)

        elif not player_switched and not ai_switched:
            p_move = self._find_move(current_player, player_action.choice)
            ai_move = self._find_move(current_ai, ai_action.choice)

            first_side, _ = determine_turn_order(
                player_action, current_player, p_move,
                ai_action, current_ai, ai_move,
                snapshot=snapshot,
            )

            if first_side == "player":
                if current_player and not current_player.is_fainted and snapshot.ai_active and not snapshot.ai_active.is_fainted:
                    self._execute_action("player", current_player, player_action, p_move, snapshot.ai_active, "ai", snapshot, events)
                # El segundo solo actúa si sigue siendo el activo y sigue con vida
                if (
                    snapshot.ai_active is current_ai
                    and not current_ai.is_fainted
                    and current_ai.current_hp > 0
                    and snapshot.player_active
                    and not snapshot.player_active.is_fainted
                ):
                    self._execute_action("ai", current_ai, ai_action, ai_move, snapshot.player_active, "player", snapshot, events)
            else:
                if current_ai and not current_ai.is_fainted and snapshot.player_active and not snapshot.player_active.is_fainted:
                    self._execute_action("ai", current_ai, ai_action, ai_move, snapshot.player_active, "player", snapshot, events)
                # El segundo solo actúa si sigue siendo el activo y sigue con vida
                if (
                    snapshot.player_active is current_player
                    and not current_player.is_fainted
                    and current_player.current_hp > 0
                    and snapshot.ai_active
                    and not snapshot.ai_active.is_fainted
                ):
                    self._execute_action("player", current_player, player_action, p_move, snapshot.ai_active, "ai", snapshot, events)

        # 5. FASE RESIDUAL DE FIN DE TURNO (runResiduals en Showdown)
        self._apply_end_of_turn_effects(snapshot, events)

        # 6. Incrementar contador de turno
        snapshot.turn += 1

        # 7. Evaluar estado de la batalla
        status = self._check_battle_status(snapshot)

        return TurnResult(
            events=events,
            new_snapshot=snapshot,
            battle_status=status,
        )

    # =========================================================================
    # CHEQUEOS PRE-MOVIMIENTO (BeforeMove: Sueño, Hielo, Flinch, Parálisis, Confusión, Mofa, Recarga)
    # =========================================================================

    def _can_execute_move(
        self,
        side: str,
        actor: PokemonState,
        move: MoveState,
        events: List[Dict[str, Any]],
    ) -> bool:
        # 1. Recarga obligatoria (Hyper Beam / Giga Impact)
        if actor.volatiles.get("must_recharge"):
            actor.volatiles.pop("must_recharge", None)
            events.append({
                "type": "MESSAGE",
                "side": side,
                "pokemon": actor.species,
                "text": f"¡{actor.species} debe recuperar energías!",
            })
            return False

        # 2. Sueño (SLP)
        if actor.status == "SLP":
            if actor.sleep_turns <= 0:
                actor.sleep_turns = random.randint(1, 3)
            actor.sleep_turns -= 1
            if actor.sleep_turns <= 0:
                actor.status = None
                events.append({
                    "type": "STATUS_CURE",
                    "side": side,
                    "pokemon": actor.species,
                    "status": "SLP",
                    "text": f"¡{actor.species} se despertó!",
                })
            else:
                events.append({
                    "type": "MESSAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "text": f"¡{actor.species} está profundamente dormido!",
                })
                return False

        # 3. Congelación (FRZ): 20% de descongelarse por turno o uso de movimientos de fuego
        if actor.status == "FRZ":
            thaw_moves = ("flare-blitz", "scald", "sacred-fire", "flame-wheel", "fusion-flare", "steam-eruption")
            if move.id in thaw_moves or move.type.capitalize() == "Fire" or random.random() < 0.20:
                actor.status = None
                events.append({
                    "type": "STATUS_CURE",
                    "side": side,
                    "pokemon": actor.species,
                    "status": "FRZ",
                    "text": f"¡{actor.species} se descongeló!",
                })
            else:
                events.append({
                    "type": "MESSAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "text": f"¡{actor.species} está congelado y no puede moverse!",
                })
                return False

        # 4. Retroceso (Flinch)
        if actor.volatiles.pop("flinch", None):
            if (actor.ability or "").lower() != "inner focus":
                events.append({
                    "type": "MESSAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "text": f"¡{actor.species} retrocedió y no pudo atacar!",
                })
                return False

        # 5. Mofa (Taunt): impide movimientos de categoría status
        if actor.volatiles.get("taunt", 0) > 0 and move.category == "status":
            events.append({
                "type": "MESSAGE",
                "side": side,
                "pokemon": actor.species,
                "text": f"¡{actor.species} no puede usar {move.name} por la Mofa!",
            })
            return False

        # 6. Confusión (Confusion): dura 1-4 turnos; 33% de golpearse a sí mismo (40 BP físico sin tipo)
        if "confusion" in actor.volatiles:
            actor.volatiles["confusion"] = int(actor.volatiles["confusion"]) - 1
            if actor.volatiles["confusion"] <= 0:
                actor.volatiles.pop("confusion", None)
                events.append({
                    "type": "MESSAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "text": f"¡{actor.species} ya no está confuso!",
                })
            else:
                events.append({
                    "type": "MESSAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "text": f"¡{actor.species} está confuso!",
                })
                if random.random() < 0.33:
                    conf_move = MoveState(id="confusion-hit", name="Confusión", type="Normal", category="physical", base_power=40)
                    self_dmg, _, _ = calculate_damage(actor, actor, conf_move, rng_factor=random.uniform(0.85, 1.0))
                    # Sin STAB ni efectividad en el autodaño por confusión
                    self_dmg = max(1, math.floor(self_dmg / 1.5)) if "Normal" in actor.types else max(1, self_dmg)
                    actor.current_hp = max(0, actor.current_hp - self_dmg)
                    events.append({
                        "type": "DAMAGE",
                        "side": side,
                        "pokemon": actor.species,
                        "damage": self_dmg,
                        "remaining_hp": actor.current_hp,
                        "max_hp": actor.max_hp,
                        "hp_percent": round(actor.hp_percent, 3),
                        "text": f"¡Está tan confuso que se hirió a sí mismo ({self_dmg} PS)!",
                    })
                    self._check_and_emit_faint(side, actor, events)
                    return False

        # 7. Parálisis (PAR): 25% de probabilidad de no poder moverse
        if actor.status == "PAR":
            if random.random() < 0.25:
                events.append({
                    "type": "MESSAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "text": f"¡{actor.species} está paralizado! ¡No se puede mover!",
                })
                return False

        return True

    # =========================================================================
    # EJECUCIÓN DE MOVIMIENTO (Showdown runMove)
    # =========================================================================

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
            move = MoveState(
                id="struggle",
                name="Struggle",
                type="Normal",
                category="physical",
                base_power=50,
                accuracy=1.0,
                never_miss=True,
                recoil_percent=0.25,
            )

        # Chequeos previos al movimiento (Sueño, Congelación, Retroceso, Confusión, Parálisis, Mofa, Recarga)
        if not self._can_execute_move(side, actor, move, events):
            actor.protect_counter = 0
            return

        if move.volatile_status != "protect":
            actor.protect_counter = 0

        # Descontar PP
        if move.pp > 0:
            move.pp -= 1

        if side == "player":
            self.tracker.record_move_used(actor.species, move.name)

        move_es = move.name_es or get_move_text_es(move.name)["es"]
        events.append({
            "type": "MOVE",
            "side": side,
            "pokemon": actor.species,
            "move": move.name,
            "move_es": move_es,
            "text": f"¡{actor.species} usó {move_es}!",
        })

        # Fake Out / First Impression solo funcionan en el primer turno activo del Pokémon en el campo
        if move.id in ("fake-out", "first-impression") and actor.active_turns > 0:
            events.append({"type": "MESSAGE", "text": "¡Pero falló! (Solo funciona al entrar al campo)"})
            return

        # Sucker Punch falla si el objetivo no iba a atacar o ya actuó
        # Protección (Protect / Detect)
        if move.volatile_status == "protect":
            chance = 1.0 / (3 ** actor.protect_counter)
            if random.random() <= chance:
                actor.volatiles["protect"] = True
                actor.protect_counter += 1
                events.append({
                    "type": "VOLATILE",
                    "side": side,
                    "pokemon": actor.species,
                    "volatile": "protect",
                    "text": f"¡{actor.species} se protegió!",
                })
            else:
                actor.protect_counter = 0
                events.append({"type": "MESSAGE", "text": "¡Pero falló!"})
            return

        targets_opponent = self._move_targets_opponent(move)

        # Bloqueo por Campo Psíquico (Psychic Terrain bloquea movimientos con prioridad > 0 contra rivales en tierra)
        eff_prio = get_effective_priority(actor, move)
        if targets_opponent and snapshot.terrain == "Psychic" and defender.is_grounded() and eff_prio > 0:
            events.append({
                "type": "MESSAGE",
                "text": f"¡El Campo Psíquico protege a {defender.species} de ataques con prioridad!",
            })
            return

        # Inmunidad de tipo Siniestro (Dark) a movimientos potenciados por Bromista (Prankster)
        if (
            targets_opponent
            and (actor.ability or "").lower() == "prankster"
            and move.category == "status"
            and "Dark" in defender.types
        ):
            events.append({
                "type": "IMMUNE",
                "side": def_side,
                "pokemon": defender.species,
                "text": f"No afecta a {defender.species} (inmune a Bromista)...",
            })
            return

        # Chequeo de Protect en el defensor
        if targets_opponent and defender.volatiles.get("protect"):
            events.append({
                "type": "PROTECTED",
                "side": def_side,
                "pokemon": defender.species,
                "text": f"¡{defender.species} se protegió del ataque!",
            })
            return

        # Chequeo de precisión y evasión (con overrides climáticos de Showdown)
        if targets_opponent and not self._check_move_accuracy(actor, defender, move, snapshot.weather):
            events.append({
                "type": "MISS",
                "side": side,
                "pokemon": actor.species,
                "text": f"¡El ataque de {actor.species} falló!",
            })
            return

        # Movimientos de estado (Categoría "status" o sin potencia)
        if move.category == "status" or move.base_power <= 0:
            self._resolve_status_move_effects(side, actor, def_side, defender, move, snapshot, events)
            return

        # =====================================================================
        # MOVIMIENTOS DE DAÑO (Físicos / Especiales, incluyendo Multi-Hit)
        # =====================================================================
        defender_side = snapshot.player_side if def_side == "player" else snapshot.ai_side

        # Demolición (Brick Break) y Psicocolmillo (Psychic Fangs): destruyen pantallas antes de calcular el daño (salvo inmunidad)
        if move.id in ("brick-break", "brickbreak", "psychic-fangs", "psychicfangs"):
            eff_check = get_type_effectiveness(move.type, defender.types)
            if eff_check > 0.0:
                cleared_scr = defender_side.clear_screens()
                if cleared_scr:
                    events.append({
                        "type": "FIELD",
                        "side": def_side,
                        "text": f"¡{actor.species} destruyó las barreras ({', '.join(cleared_scr)}) del campo rival!",
                    })

        num_hits = self._determine_num_hits(actor, move)

        total_damage_dealt = 0
        hit_count_actual = 0
        hit_substitute = False

        for _ in range(num_hits):
            if defender.is_fainted or defender.current_hp <= 0:
                break

            is_crit = random.random() < get_crit_chance(move.crit_ratio)
            rng_roll = random.uniform(0.85, 1.00)

            damage, effectiveness, is_immune = calculate_damage(
                actor,
                defender,
                move,
                weather=snapshot.weather,
                terrain=snapshot.terrain,
                defender_side=defender_side,
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

            hit_count_actual += 1

            # Verificar si el defensor tiene un Sustituto activo (salvo habilidad Infiltrator)
            if defender.substitute_hp > 0 and (actor.ability or "").lower() != "infiltrator":
                hit_substitute = True
                sub_dmg = min(defender.substitute_hp, damage)
                defender.substitute_hp -= sub_dmg
                total_damage_dealt += sub_dmg
                if defender.substitute_hp <= 0:
                    defender.substitute_hp = 0
                    defender.volatiles.pop("substitute", None)
                    events.append({
                        "type": "VOLATILE_END",
                        "side": def_side,
                        "pokemon": defender.species,
                        "volatile": "substitute",
                        "text": f"¡El sustituto de {defender.species} recibió el golpe y se rompió!",
                    })
                else:
                    events.append({
                        "type": "MESSAGE",
                        "side": def_side,
                        "pokemon": defender.species,
                        "text": f"¡El sustituto absorbió el daño por {defender.species}!",
                    })
            else:
                # Chequeo de Focus Sash y Sturdy (sobrevivir con 1 PS si estaba con vida máxima)
                was_full_hp = defender.current_hp >= defender.max_hp
                actual_dmg = min(defender.current_hp, damage)

                if was_full_hp and damage >= defender.current_hp and defender.max_hp > 1:
                    if (defender.item or "").lower() == "focus sash":
                        actual_dmg = defender.current_hp - 1
                        defender.item = None
                        events.append({
                            "type": "ITEM",
                            "side": def_side,
                            "pokemon": defender.species,
                            "text": f"¡{defender.species} resistió el golpe usando su Focus Sash!",
                        })
                    elif (defender.ability or "").lower() == "sturdy":
                        actual_dmg = defender.current_hp - 1
                        events.append({
                            "type": "ABILITY",
                            "side": def_side,
                            "pokemon": defender.species,
                            "text": f"¡{defender.species} resistió el golpe gracias a Sturdy!",
                        })

                defender.current_hp = max(0, defender.current_hp - actual_dmg)
                total_damage_dealt += actual_dmg
                hp_pct = round(defender.hp_percent, 3)

                events.append({
                    "type": "DAMAGE",
                    "side": def_side,
                    "pokemon": defender.species,
                    "damage": actual_dmg,
                    "remaining_hp": defender.current_hp,
                    "max_hp": defender.max_hp,
                    "hp_percent": hp_pct,
                    "critical": is_crit,
                    "effectiveness": effectiveness,
                    "text": f"¡{defender.species} recibió {actual_dmg} puntos de daño!",
                })

                if is_crit:
                    events.append({"type": "MESSAGE", "text": "¡Un golpe crítico!"})

                if hit_count_actual == 1:
                    if effectiveness >= 2.0:
                        events.append({"type": "MESSAGE", "text": "¡Es súper eficaz!"})
                    elif 0.0 < effectiveness < 1.0:
                        events.append({"type": "MESSAGE", "text": "No es muy eficaz..."})

                # Si tenía Air Balloon, explota al recibir daño
                if (defender.item or "").lower() == "air balloon" and actual_dmg > 0:
                    defender.item = None
                    events.append({
                        "type": "MESSAGE",
                        "text": f"¡El Globo Helio de {defender.species} explotó!",
                    })

                # Knock Off: elimina el objeto del defensor (salvo Mega Piedra)
                if move.id == "knock-off" and defender.item and not defender.can_mega and actual_dmg > 0:
                    lost_item = defender.item
                    defender.item = None
                    events.append({
                        "type": "ITEM",
                        "side": def_side,
                        "pokemon": defender.species,
                        "text": f"¡{actor.species} desarmó el {lost_item} de {defender.species}!",
                    })

                # Efectos de contacto (Rocky Helmet, Rough Skin, Iron Barbs, Static, Flame Body)
                if move.makes_contact and not actor.is_fainted and actor.current_hp > 0:
                    self._apply_contact_punishment(side, actor, def_side, defender, events)

                self._check_and_emit_faint(def_side, defender, events)

        if num_hits > 1 and hit_count_actual > 0:
            events.append({
                "type": "MESSAGE",
                "text": f"¡Golpeó {hit_count_actual} veces!",
            })

        # Drenaje de vida (Giga Drain, Drain Punch, Draining Kiss)
        if move.drain_percent > 0 and total_damage_dealt > 0 and not actor.is_fainted and actor.current_hp > 0:
            heal_amt = max(1, math.floor(total_damage_dealt * move.drain_percent))
            actor.current_hp = min(actor.max_hp, actor.current_hp + heal_amt)
            events.append({
                "type": "HEAL",
                "side": side,
                "pokemon": actor.species,
                "heal_amount": heal_amt,
                "remaining_hp": actor.current_hp,
                "max_hp": actor.max_hp,
                "hp_percent": round(actor.hp_percent, 3),
                "text": f"¡{actor.species} drenó energía de {defender.species} (+{heal_amt} PS)!",
            })

        # Daño de retroceso (Flare Blitz, Brave Bird, Wood Hammer, Wild Charge, Double-Edge)
        if move.recoil_percent > 0 and total_damage_dealt > 0 and not actor.is_fainted and actor.current_hp > 0:
            if (actor.ability or "").lower() not in ("rock head", "magic guard"):
                recoil_dmg = max(1, math.floor(total_damage_dealt * move.recoil_percent))
                actor.current_hp = max(0, actor.current_hp - recoil_dmg)
                events.append({
                    "type": "DAMAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "damage": recoil_dmg,
                    "remaining_hp": actor.current_hp,
                    "max_hp": actor.max_hp,
                    "hp_percent": round(actor.hp_percent, 3),
                    "text": f"¡{actor.species} sufrió {recoil_dmg} PS de daño por retroceso!",
                })
                self._check_and_emit_faint(side, actor, events)

        # Daño de Life Orb (10% del max HP del atacante)
        if (
            (actor.item or "").lower() == "life orb"
            and total_damage_dealt > 0
            and not actor.is_fainted
            and actor.current_hp > 0
            and (actor.ability or "").lower() != "magic guard"
        ):
            lo_dmg = max(1, math.floor(actor.max_hp * 0.10))
            actor.current_hp = max(0, actor.current_hp - lo_dmg)
            events.append({
                "type": "DAMAGE",
                "side": side,
                "pokemon": actor.species,
                "damage": lo_dmg,
                "remaining_hp": actor.current_hp,
                "max_hp": actor.max_hp,
                "hp_percent": round(actor.hp_percent, 3),
                "text": f"¡{actor.species} perdió salud por su Vidasfera (-{lo_dmg} PS)!",
            })
            self._check_and_emit_faint(side, actor, events)

        # Limpieza de Hazards con golpe (Rapid Spin / Mortal Spin)
        if move.hazard_clear == "rapid_spin" and not actor.is_fainted:
            own_side = snapshot.player_side if side == "player" else snapshot.ai_side
            cleared = own_side.clear_hazards()
            actor.volatiles.pop("leech_seed", None)
            actor.volatiles.pop("partially_trapped", None)
            if cleared:
                events.append({
                    "type": "FIELD",
                    "side": side,
                    "text": f"¡{actor.species} eliminó {', '.join(cleared)} de su campo!",
                })

        # Niebla Clara (Clear Smog): elimina todos los cambios de características del objetivo al golpear
        if move.id in ("clear-smog", "clearsmog") and hit_count_actual > 0 and not defender.is_fainted and not hit_substitute:
            defender.boosts.reset()
            events.append({
                "type": "CLEAR_BOOST",
                "side": def_side,
                "pokemon": defender.species,
                "boosts": defender.boosts.to_dict(),
                "text": f"¡Se eliminaron todos los cambios de características de {defender.species}!",
            })

        # Cambios de estadísticas propios tras golpear (Close Combat, Draco Meteor, Flame Charge, Rapid Spin)
        if move.self_boosts and not actor.is_fainted:
            self._apply_stat_boosts(side, actor, move.self_boosts, events)

        # Cambios de estadísticas primarios al objetivo
        if move.boosts and not defender.is_fainted and not hit_substitute:
            self._apply_stat_boosts(def_side, defender, move.boosts, events)

        # Estado volátil primario en movimiento de daño (ej. Fire Spin -> partially_trapped)
        if move.volatile_status and not defender.is_fainted and not hit_substitute:
            self._inflict_volatile(def_side, defender, move.volatile_status, events)

        # Efectos secundarios (Secondary: probabilidad de quemar, paralizar, congelar, retroceder, bajar stats)
        if move.secondary and not defender.is_fainted and defender.current_hp > 0:
            self._resolve_secondary_effects(side, actor, def_side, defender, move.secondary, hit_substitute, snapshot, events)

        # Recarga en el siguiente turno (Hyper Beam / Giga Impact)
        if move.must_recharge and not actor.is_fainted:
            actor.volatiles["must_recharge"] = True

        # Phazing (Dragon Tail / Circle Throw): fuerza al rival a cambiar a un Pokémon aleatorio de su banca
        if move.force_switch and not defender.is_fainted and defender.current_hp > 0 and not hit_substitute:
            self._force_random_switch(def_side, snapshot, events)

        # Pivot (U-turn / Volt Switch / Flip Turn): el atacante vuelve a la banca tras golpear
        if move.self_switch and not actor.is_fainted and actor.current_hp > 0:
            self._auto_pivot_switch(side, snapshot, events)

    # =========================================================================
    # EFECTOS DE MOVIMIENTOS DE ESTADO Y CAMPO
    # =========================================================================

    def _resolve_status_move_effects(
        self,
        side: str,
        actor: PokemonState,
        def_side: str,
        defender: PokemonState,
        move: MoveState,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        own_side = snapshot.player_side if side == "player" else snapshot.ai_side
        opp_side = snapshot.player_side if def_side == "player" else snapshot.ai_side

        # 0. Movimientos especiales de estado (Curse, Belly Drum, Haze)
        if move.id == "curse":
            if "Ghost" in actor.types:
                if defender.volatiles.get("curse") or defender.is_fainted:
                    events.append({"type": "MESSAGE", "text": "¡Pero falló!"})
                    return
                cost = max(1, math.floor(actor.max_hp / 2.0))
                actor.current_hp = max(0, actor.current_hp - cost)
                defender.volatiles["curse"] = True
                events.append({
                    "type": "DAMAGE",
                    "side": side,
                    "pokemon": actor.species,
                    "damage": cost,
                    "remaining_hp": actor.current_hp,
                    "max_hp": actor.max_hp,
                    "hp_percent": round(actor.hp_percent, 3),
                    "text": f"¡{actor.species} redujo sus PS a la mitad y maldijo a {defender.species}!",
                })
                events.append({
                    "type": "VOLATILE",
                    "side": def_side,
                    "pokemon": defender.species,
                    "volatile": "curse",
                    "text": f"¡{defender.species} está bajo los efectos de una Maldición!",
                })
                self._check_and_emit_faint(side, actor, events)
                return
            else:
                self._apply_stat_boosts(side, actor, {"spe": -1, "atk": 1, "def": 1}, events)
                return

        if move.id in ("belly-drum", "bellydrum"):
            cost = math.floor(actor.max_hp / 2.0)
            if actor.current_hp <= cost or actor.boosts.atk >= 6:
                events.append({"type": "MESSAGE", "text": "¡Pero no tiene suficientes PS para usar Tambor!"})
                return
            actor.current_hp -= cost
            events.append({
                "type": "DAMAGE",
                "side": side,
                "pokemon": actor.species,
                "damage": cost,
                "remaining_hp": actor.current_hp,
                "max_hp": actor.max_hp,
                "hp_percent": round(actor.hp_percent, 3),
                "text": f"¡{actor.species} redujo sus PS a la mitad y maximizó su Ataque!",
            })
            self._apply_stat_boosts(side, actor, {"atk": 12}, events)
            return

        if move.id == "haze":
            actor.boosts.reset()
            defender.boosts.reset()
            events.append({
                "type": "CLEAR_BOOST",
                "side": "both",
                "player_boosts": snapshot.player_active.boosts.to_dict() if snapshot.player_active else {},
                "ai_boosts": snapshot.ai_active.boosts.to_dict() if snapshot.ai_active else {},
                "text": "¡Se han eliminado todos los cambios de características en el combate!",
            })
            return

        # 1. Clima (Sunny Day, Rain Dance, Sandstorm, Snowscape)
        if move.weather:
            snapshot.weather = move.weather
            snapshot.weather_turns = 5
            weather_names = {
                "Sun": "¡El sol empezó a brillar con fuerza!",
                "Rain": "¡Empezó a llover intensamente!",
                "Sandstorm": "¡Se ha desatado una tormenta de arena!",
                "Snow": "¡Empezó a nevar!",
            }
            events.append({
                "type": "WEATHER",
                "weather": move.weather,
                "turns": 5,
                "text": weather_names.get(move.weather, f"¡El clima cambió a {move.weather}!"),
            })

        # 2. Terrenos (Electric, Grassy, Psychic, Misty Terrain)
        if move.terrain:
            snapshot.terrain = move.terrain
            snapshot.terrain_turns = 5
            terrain_names = {
                "Electric": "¡Se ha creado un Campo Eléctrico en el terreno de combate!",
                "Grassy": "¡El terreno de combate se cubrió de hierba (Campo de Hierba)!",
                "Psychic": "¡Una extraña energía psíquica envuelve el terreno (Campo Psíquico)!",
                "Misty": "¡La niebla envuelve el terreno de combate (Campo de Niebla)!",
            }
            events.append({
                "type": "TERRAIN",
                "terrain": move.terrain,
                "turns": 5,
                "text": terrain_names.get(move.terrain, f"¡El terreno cambió a {move.terrain}!"),
            })

        # 3. Espacio Raro (Trick Room)
        if move.pseudo_weather == "trick_room":
            if snapshot.trick_room_turns > 0:
                snapshot.trick_room_turns = 0
                events.append({
                    "type": "FIELD",
                    "text": "¡Se han restaurado las dimensiones alteradas del Espacio Raro!",
                })
            else:
                snapshot.trick_room_turns = 5
                events.append({
                    "type": "FIELD",
                    "text": f"¡{actor.species} alteró las dimensiones! ¡Los Pokémon más lentos se moverán primero!",
                })

        # 4. Condiciones de lado: Hazards y Pantallas / Tailwind
        if move.side_condition:
            sc = move.side_condition
            if sc == "stealth_rock":
                if not opp_side.stealth_rock:
                    opp_side.stealth_rock = True
                    events.append({"type": "SIDE_CONDITION", "side": def_side, "condition": sc, "text": "¡Rocas afiladas flotan en el campo rival (Trampa Rocas)!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡Pero ya había Trampa Rocas en el campo rival!"})
            elif sc == "spikes":
                if opp_side.spikes < 3:
                    opp_side.spikes += 1
                    events.append({"type": "SIDE_CONDITION", "side": def_side, "condition": sc, "layers": opp_side.spikes, "text": f"¡Se esparcieron Púas en el campo rival (Capa {opp_side.spikes}/3)!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡No se pueden colocar más capas de Púas!"})
            elif sc == "toxic_spikes":
                if opp_side.toxic_spikes < 2:
                    opp_side.toxic_spikes += 1
                    events.append({"type": "SIDE_CONDITION", "side": def_side, "condition": sc, "layers": opp_side.toxic_spikes, "text": f"¡Se esparcieron Púas Tóxicas en el campo rival (Capa {opp_side.toxic_spikes}/2)!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡No se pueden colocar más Púas Tóxicas!"})
            elif sc == "sticky_web":
                if not opp_side.sticky_web:
                    opp_side.sticky_web = True
                    events.append({"type": "SIDE_CONDITION", "side": def_side, "condition": sc, "text": "¡Una Red Viscosa se extendió a los pies del equipo rival!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡Pero ya había una Red Viscosa!"})
            elif sc == "reflect":
                if own_side.reflect_turns == 0:
                    turns = 8 if (actor.item or "").lower() == "light clay" else 5
                    own_side.reflect_turns = turns
                    events.append({"type": "SIDE_CONDITION", "side": side, "condition": sc, "text": "¡Reflejo aumentó la defensa física del equipo!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡Pero Reflejo ya está activo!"})
            elif sc == "light_screen":
                if own_side.light_screen_turns == 0:
                    turns = 8 if (actor.item or "").lower() == "light clay" else 5
                    own_side.light_screen_turns = turns
                    events.append({"type": "SIDE_CONDITION", "side": side, "condition": sc, "text": "¡Pantalla de Luz aumentó la defensa especial del equipo!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡Pero Pantalla de Luz ya está activa!"})
            elif sc == "aurora_veil":
                if snapshot.weather == "Snow" and own_side.aurora_veil_turns == 0:
                    turns = 8 if (actor.item or "").lower() == "light clay" else 5
                    own_side.aurora_veil_turns = turns
                    events.append({"type": "SIDE_CONDITION", "side": side, "condition": sc, "text": "¡Velo Aurora protege al equipo contra ataques físicos y especiales!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡Pero Velo Aurora falló (requiere Nieve)!"})
            elif sc == "tailwind":
                if own_side.tailwind_turns == 0:
                    own_side.tailwind_turns = 4
                    events.append({"type": "SIDE_CONDITION", "side": side, "condition": sc, "text": "¡El Viento Afín sopla a favor del equipo duplicando su Velocidad!"})
                else:
                    events.append({"type": "MESSAGE", "text": "¡El Viento Afín ya está activo!"})

        # 5. Despejar Hazards y Pantallas (Defog)
        if move.hazard_clear == "defog":
            c_opp_h = opp_side.clear_hazards()
            c_opp_s = opp_side.clear_screens()
            c_own_h = own_side.clear_hazards()
            snapshot.terrain = None
            snapshot.terrain_turns = 0
            all_cleared = c_opp_h + c_opp_s + c_own_h
            events.append({
                "type": "FIELD",
                "text": f"¡{actor.species} despejó el campo de batalla ({', '.join(all_cleared) if all_cleared else 'niebla despejada'})!",
            })

        # 6. Curación directa (Recover, Roost, Synthesis, Soft-Boiled, Slack Off, Rest)
        if move.heal_fraction > 0:
            if actor.current_hp >= actor.max_hp:
                events.append({"type": "MESSAGE", "text": f"¡Los PS de {actor.species} ya están al máximo!"})
            else:
                frac = move.heal_fraction
                if move.id == "synthesis":
                    if snapshot.weather == "Sun":
                        frac = 0.667
                    elif snapshot.weather in ("Rain", "Sandstorm", "Snow"):
                        frac = 0.25
                heal_amt = max(1, math.floor(actor.max_hp * frac))
                actor.current_hp = min(actor.max_hp, actor.current_hp + heal_amt)
                if move.id == "rest":
                    actor.status = "SLP"
                    actor.sleep_turns = 2
                    actor.status_counter = 0
                    events.append({
                        "type": "STATUS",
                        "side": side,
                        "pokemon": actor.species,
                        "status": "SLP",
                        "text": f"¡{actor.species} se durmió y recuperó toda su salud!",
                    })
                events.append({
                    "type": "HEAL",
                    "side": side,
                    "pokemon": actor.species,
                    "heal_amount": heal_amt,
                    "remaining_hp": actor.current_hp,
                    "max_hp": actor.max_hp,
                    "hp_percent": round(actor.hp_percent, 3),
                    "text": f"¡{actor.species} recuperó {heal_amt} PS!",
                })

        # 7. Sustituto (Substitute)
        if move.volatile_status == "substitute":
            sub_cost = math.floor(actor.max_hp * 0.25)
            if actor.substitute_hp > 0:
                events.append({"type": "MESSAGE", "text": f"¡{actor.species} ya tiene un sustituto!"})
            elif actor.current_hp <= sub_cost or sub_cost <= 0:
                events.append({"type": "MESSAGE", "text": "¡Pero no tiene suficiente salud para crear un sustituto!"})
            else:
                actor.current_hp -= sub_cost
                actor.substitute_hp = sub_cost
                actor.volatiles["substitute"] = True
                events.append({
                    "type": "VOLATILE",
                    "side": side,
                    "pokemon": actor.species,
                    "volatile": "substitute",
                    "remaining_hp": actor.current_hp,
                    "hp_percent": round(actor.hp_percent, 3),
                    "text": f"¡{actor.species} creó un sustituto ({sub_cost} PS)!",
                })

        # 8. Otros estados volátiles al rival (Leech Seed, Taunt, Confusion)
        elif move.volatile_status and move.volatile_status != "protect":
            if defender.substitute_hp > 0:
                events.append({"type": "MESSAGE", "text": "¡Pero el sustituto bloqueó el efecto!"})
            else:
                self._inflict_volatile(def_side, defender, move.volatile_status, events, move_type=move.type)

        # 9. Estados alterados no volátiles al objetivo (Will-O-Wisp, Thunder Wave, Toxic, Spore, Sleep Powder)
        if move.target_status:
            if defender.substitute_hp > 0:
                events.append({"type": "MESSAGE", "text": "¡Pero el sustituto bloqueó el estado!"})
            else:
                applied = self._try_inflict_status(
                    def_side,
                    defender,
                    move.target_status,
                    snapshot,
                    events,
                    move_type=move.type,
                    is_powder=("powder" in move.id or "spore" in move.id),
                )
                if not applied:
                    events.append({"type": "MESSAGE", "text": f"¡No afectó a {defender.species}!"})

        # 10. Boosts propios (Swords Dance, Dragon Dance, Calm Mind, Nasty Plot, Quiver Dance, Bulk Up, Shell Smash, Growth)
        if move.self_boosts:
            boosts_to_apply = dict(move.self_boosts)
            if move.id == "growth" and snapshot.weather == "Sun":
                boosts_to_apply = {"atk": 2, "spa": 2}
            self._apply_stat_boosts(side, actor, boosts_to_apply, events)

        # 11. Boosts / drops al objetivo (Defog, Parting Shot, Charm, Scary Face)
        if move.boosts:
            if defender.substitute_hp > 0 and move.hazard_clear != "defog":
                events.append({"type": "MESSAGE", "text": "¡El sustituto de " + defender.species + " evitó la reducción!"})
            else:
                self._apply_stat_boosts(def_side, defender, move.boosts, events)

        # 12. Phazing (Roar / Whirlwind)
        if move.force_switch and not defender.is_fainted:
            self._force_random_switch(def_side, snapshot, events)

        # 13. Pivot de estado (Parting Shot / Teleport)
        if move.self_switch and not actor.is_fainted:
            self._auto_pivot_switch(side, snapshot, events)

    # =========================================================================
    # CAMBIOS (SWITCHES), ENTRY HAZARDS Y HABILIDADES DE ENTRADA
    # =========================================================================

    def _handle_switch(
        self,
        side: str,
        choice_id: str,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        bench = snapshot.player_bench if side == "player" else snapshot.ai_bench
        active = snapshot.player_active if side == "player" else snapshot.ai_active

        found_idx = -1
        for idx, p in enumerate(bench):
            if (p.id == choice_id or p.species.lower() == choice_id.lower()) and not p.is_fainted and p.current_hp > 0:
                found_idx = idx
                break

        if found_idx == -1:
            events.append({"type": "MESSAGE", "text": f"Cambio inválido: {choice_id} no está disponible."})
            return

        prev_species = active.species if active else None
        new_active = bench.pop(found_idx)
        if active:
            # Habilidades al salir del campo (Regenerator / Natural Cure)
            out_ability = (active.ability or "").lower()
            if not active.is_fainted and active.current_hp > 0:
                if out_ability == "regenerator":
                    regen = max(1, math.floor(active.max_hp / 3.0))
                    active.current_hp = min(active.max_hp, active.current_hp + regen)
                elif out_ability == "natural cure" and active.status is not None:
                    active.status = None
                    active.status_counter = 0
                    active.sleep_turns = 0

            active.clear_volatile_state_on_switch()
            bench.append(active)

        new_active.active_turns = 0
        new_active.revealed = True
        if side == "player":
            snapshot.player_active = new_active
            events.append({
                "type": "SWITCH",
                "side": "player",
                "pokemon": new_active.species,
                "previous_pokemon": prev_species,
                "pokemon_state": new_active.to_dict(),
                "text": f"¡Adelante, {new_active.species}!",
            })
        else:
            snapshot.ai_active = new_active
            events.append({
                "type": "SWITCH",
                "side": "ai",
                "pokemon": new_active.species,
                "previous_pokemon": prev_species,
                "pokemon_state": new_active.to_dict(),
                "text": f"¡El rival envió a {new_active.species}!",
            })

        # Aplicar Entry Hazards al entrar al campo
        self._apply_switch_in_hazards(side, new_active, snapshot, events)

        # Si sobrevivió a las hazards, activar habilidades de entrada (Intimidate, Drizzle, Drought, etc.)
        if not new_active.is_fainted and new_active.current_hp > 0:
            opp_poke = snapshot.ai_active if side == "player" else snapshot.player_active
            self._trigger_entry_ability(side, new_active, opp_poke, snapshot, events)

    def _apply_switch_in_hazards(
        self,
        side: str,
        pokemon: PokemonState,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        side_cond = snapshot.player_side if side == "player" else snapshot.ai_side
        item_low = (pokemon.item or "").lower()
        ability_low = (pokemon.ability or "").lower()

        # Heavy-Duty Boots ignora todas las hazards de entrada
        if item_low == "heavy-duty boots":
            return

        # 1. Stealth Rock (afecta a todos salvo Magic Guard)
        if side_cond.stealth_rock and ability_low != "magic guard":
            eff = get_type_effectiveness("Rock", pokemon.types)
            sr_dmg = max(1, math.floor(pokemon.max_hp * 0.125 * eff))
            pokemon.current_hp = max(0, pokemon.current_hp - sr_dmg)
            events.append({
                "type": "HAZARD_DAMAGE",
                "side": side,
                "pokemon": pokemon.species,
                "damage": sr_dmg,
                "remaining_hp": pokemon.current_hp,
                "max_hp": pokemon.max_hp,
                "hp_percent": round(pokemon.hp_percent, 3),
                "text": f"¡Las rocas afiladas hirieron a {pokemon.species} (-{sr_dmg} PS)!",
            })
            if self._check_and_emit_faint(side, pokemon, events):
                return

        # Las siguientes hazards solo afectan a Pokémon que tocan el suelo (is_grounded)
        if not pokemon.is_grounded():
            return

        # 2. Spikes (1 capa = 1/8, 2 capas = 1/6, 3 capas = 1/4)
        if side_cond.spikes > 0 and ability_low != "magic guard":
            frac_map = {1: 1.0 / 8.0, 2: 1.0 / 6.0, 3: 1.0 / 4.0}
            sp_dmg = max(1, math.floor(pokemon.max_hp * frac_map.get(side_cond.spikes, 0.125)))
            pokemon.current_hp = max(0, pokemon.current_hp - sp_dmg)
            events.append({
                "type": "HAZARD_DAMAGE",
                "side": side,
                "pokemon": pokemon.species,
                "damage": sp_dmg,
                "remaining_hp": pokemon.current_hp,
                "max_hp": pokemon.max_hp,
                "hp_percent": round(pokemon.hp_percent, 3),
                "text": f"¡{pokemon.species} sufrió daño por las Púas (-{sp_dmg} PS)!",
            })
            if self._check_and_emit_faint(side, pokemon, events):
                return

        # 3. Toxic Spikes (Veneno en tierra las absorbe; 1 capa = PSN, 2 capas = TOX)
        if side_cond.toxic_spikes > 0:
            if "Poison" in pokemon.types:
                side_cond.toxic_spikes = 0
                events.append({
                    "type": "FIELD",
                    "side": side,
                    "text": f"¡{pokemon.species} absorbió las Púas Tóxicas del campo!",
                })
            elif "Steel" not in pokemon.types and pokemon.status is None:
                st_to_apply = "TOX" if side_cond.toxic_spikes >= 2 else "PSN"
                self._try_inflict_status(side, pokemon, st_to_apply, snapshot, events)

        # 4. Sticky Web (-1 Velocidad al entrar)
        if side_cond.sticky_web:
            events.append({
                "type": "MESSAGE",
                "side": side,
                "text": f"¡{pokemon.species} cayó en la Red Viscosa!",
            })
            self._apply_stat_boosts(side, pokemon, {"spe": -1}, events)

    def _trigger_entry_ability(
        self,
        side: str,
        pokemon: PokemonState,
        opponent: Optional[PokemonState],
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        ability = (pokemon.ability or "").lower()
        if not ability:
            return

        opp_side = "ai" if side == "player" else "player"

        if ability == "intimidate" and opponent and not opponent.is_fainted and opponent.substitute_hp <= 0:
            opp_ab = (opponent.ability or "").lower()
            if opp_ab not in ("clear body", "white smoke", "hyper cutter", "inner focus", "oblivious", "scrappy"):
                events.append({
                    "type": "ABILITY",
                    "side": side,
                    "pokemon": pokemon.species,
                    "ability": "Intimidate",
                    "text": f"¡Intimidación de {pokemon.species} bajó el Ataque de {opponent.species}!",
                })
                self._apply_stat_boosts(opp_side, opponent, {"atk": -1}, events)

        elif ability in ("drizzle", "drought", "sand stream", "snow warning"):
            w_map = {
                "drizzle": ("Rain", "¡Llovizna de " + pokemon.species + " hizo que empezara a llover!"),
                "drought": ("Sun", "¡Sequía de " + pokemon.species + " intensificó los rayos del sol!"),
                "sand stream": ("Sandstorm", "¡Chorro Arena de " + pokemon.species + " desató una tormenta de arena!"),
                "snow warning": ("Snow", "¡Nevada de " + pokemon.species + " hizo que empezara a nevar!"),
            }
            w_type, w_text = w_map[ability]
            if snapshot.weather != w_type:
                snapshot.weather = w_type
                snapshot.weather_turns = 5
                events.append({"type": "WEATHER", "weather": w_type, "turns": 5, "text": w_text})

        elif ability in ("electric surge", "grassy surge", "psychic surge", "misty surge"):
            t_map = {
                "electric surge": ("Electric", f"¡Electrogénesis de {pokemon.species} creó un Campo Eléctrico!"),
                "grassy surge": ("Grassy", f"¡Herbogénesis de {pokemon.species} creó un Campo de Hierba!"),
                "psychic surge": ("Psychic", f"¡Psicogénesis de {pokemon.species} creó un Campo Psíquico!"),
                "misty surge": ("Misty", f"¡Nebulogénesis de {pokemon.species} creó un Campo de Niebla!"),
            }
            t_type, t_text = t_map[ability]
            if snapshot.terrain != t_type:
                snapshot.terrain = t_type
                snapshot.terrain_turns = 5
                events.append({"type": "TERRAIN", "terrain": t_type, "turns": 5, "text": t_text})

    # =========================================================================
    # EFECTOS DE FIN DE TURNO (Showdown runResiduals)
    # =========================================================================

    def _apply_end_of_turn_effects(
        self,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        # 1. Limpiar volátiles de 1 turno (Protect / Flinch) e incrementar active_turns
        for poke in (snapshot.player_active, snapshot.ai_active):
            if poke and not poke.is_fainted and poke.current_hp > 0:
                poke.volatiles.pop("protect", None)
                poke.volatiles.pop("flinch", None)
                poke.active_turns += 1

        # 2. Clima: Daño residual de Tormenta de Arena y contador de turnos
        if snapshot.weather:
            if snapshot.weather == "Sandstorm":
                for side, poke in self._get_speed_ordered_actives(snapshot):
                    if not poke or poke.is_fainted or poke.current_hp <= 0:
                        continue
                    ab = (poke.ability or "").lower()
                    item = (poke.item or "").lower()
                    if (
                        not any(t in poke.types for t in ("Rock", "Ground", "Steel"))
                        and ab not in ("magic guard", "overcoat", "sand rush", "sand force", "sand veil")
                        and item != "safety goggles"
                    ):
                        sand_dmg = max(1, math.floor(poke.max_hp / 16.0))
                        poke.current_hp = max(0, poke.current_hp - sand_dmg)
                        events.append({
                            "type": "WEATHER_DAMAGE",
                            "side": side,
                            "pokemon": poke.species,
                            "damage": sand_dmg,
                            "remaining_hp": poke.current_hp,
                            "max_hp": poke.max_hp,
                            "hp_percent": round(poke.hp_percent, 3),
                            "text": f"¡La tormenta de arena zarandea a {poke.species} (-{sand_dmg} PS)!",
                        })
                        self._check_and_emit_faint(side, poke, events)

            if snapshot.weather_turns > 0:
                snapshot.weather_turns -= 1
                if snapshot.weather_turns <= 0:
                    old_w = snapshot.weather
                    snapshot.weather = None
                    events.append({"type": "WEATHER_END", "text": f"¡El efecto climático ({old_w}) se ha disipado!"})

        # 3. Terreno: Curación de Campo de Hierba (Grassy Terrain) y contador de turnos
        if snapshot.terrain:
            if snapshot.terrain == "Grassy":
                for side, poke in self._get_speed_ordered_actives(snapshot):
                    if poke and not poke.is_fainted and 0 < poke.current_hp < poke.max_hp and poke.is_grounded():
                        gt_heal = max(1, math.floor(poke.max_hp / 16.0))
                        poke.current_hp = min(poke.max_hp, poke.current_hp + gt_heal)
                        events.append({
                            "type": "HEAL",
                            "side": side,
                            "pokemon": poke.species,
                            "heal_amount": gt_heal,
                            "remaining_hp": poke.current_hp,
                            "max_hp": poke.max_hp,
                            "hp_percent": round(poke.hp_percent, 3),
                            "text": f"¡El Campo de Hierba restauró la salud de {poke.species} (+{gt_heal} PS)!",
                        })

            if snapshot.terrain_turns > 0:
                snapshot.terrain_turns -= 1
                if snapshot.terrain_turns <= 0:
                    old_t = snapshot.terrain
                    snapshot.terrain = None
                    events.append({"type": "TERRAIN_END", "text": f"¡El {old_t} Terrain desapareció del campo!"})

        # 4. Contador de Trick Room
        if snapshot.trick_room_turns > 0:
            snapshot.trick_room_turns -= 1
            if snapshot.trick_room_turns <= 0:
                events.append({"type": "FIELD", "text": "¡Se han restaurado las dimensiones alteradas del Espacio Raro!"})

        # 5. Contadores de Pantallas y Tailwind en ambos lados
        for side_label, sc in (("player", snapshot.player_side), ("ai", snapshot.ai_side)):
            if sc.reflect_turns > 0:
                sc.reflect_turns -= 1
                if sc.reflect_turns == 0:
                    events.append({"type": "FIELD", "side": side_label, "text": f"¡El Reflejo del lado {'jugador' if side_label == 'player' else 'rival'} se disipó!"})
            if sc.light_screen_turns > 0:
                sc.light_screen_turns -= 1
                if sc.light_screen_turns == 0:
                    events.append({"type": "FIELD", "side": side_label, "text": f"¡La Pantalla de Luz del lado {'jugador' if side_label == 'player' else 'rival'} se disipó!"})
            if sc.aurora_veil_turns > 0:
                sc.aurora_veil_turns -= 1
                if sc.aurora_veil_turns == 0:
                    events.append({"type": "FIELD", "side": side_label, "text": f"¡El Velo Aurora del lado {'jugador' if side_label == 'player' else 'rival'} se disipó!"})
            if sc.tailwind_turns > 0:
                sc.tailwind_turns -= 1
                if sc.tailwind_turns == 0:
                    events.append({"type": "FIELD", "side": side_label, "text": f"¡El Viento Afín del lado {'jugador' if side_label == 'player' else 'rival'} cesó!"})

        # 6. Efectos residuales individuales en orden de velocidad (Objetos, Leech Seed, BRN, PSN, TOX, Trapped, Speed Boost)
        for side, poke in self._get_speed_ordered_actives(snapshot):
            if not poke or poke.is_fainted or poke.current_hp <= 0:
                continue

            opp_side = "ai" if side == "player" else "player"
            opp_poke = snapshot.ai_active if side == "player" else snapshot.player_active
            ability = (poke.ability or "").lower()
            item = (poke.item or "").lower()

            # 6a. Leftovers / Black Sludge
            if item == "leftovers" and poke.current_hp < poke.max_hp:
                heal = max(1, math.floor(poke.max_hp / 16.0))
                poke.current_hp = min(poke.max_hp, poke.current_hp + heal)
                events.append({
                    "type": "HEAL",
                    "side": side,
                    "pokemon": poke.species,
                    "heal_amount": heal,
                    "remaining_hp": poke.current_hp,
                    "max_hp": poke.max_hp,
                    "hp_percent": round(poke.hp_percent, 3),
                    "text": f"¡{poke.species} recuperó un poco de salud con sus Restos (+{heal} PS)!",
                })
            elif item == "black sludge":
                if "Poison" in poke.types:
                    if poke.current_hp < poke.max_hp:
                        heal = max(1, math.floor(poke.max_hp / 16.0))
                        poke.current_hp = min(poke.max_hp, poke.current_hp + heal)
                        events.append({
                            "type": "HEAL",
                            "side": side,
                            "pokemon": poke.species,
                            "heal_amount": heal,
                            "remaining_hp": poke.current_hp,
                            "max_hp": poke.max_hp,
                            "hp_percent": round(poke.hp_percent, 3),
                            "text": f"¡{poke.species} recuperó salud con su Lodo Negro (+{heal} PS)!",
                        })
                elif ability != "magic guard":
                    sludge_dmg = max(1, math.floor(poke.max_hp / 8.0))
                    poke.current_hp = max(0, poke.current_hp - sludge_dmg)
                    events.append({
                        "type": "DAMAGE",
                        "side": side,
                        "pokemon": poke.species,
                        "damage": sludge_dmg,
                        "text": f"¡El Lodo Negro dañó a {poke.species} (-{sludge_dmg} PS)!",
                    })
                    if self._check_and_emit_faint(side, poke, events):
                        continue

            # 6b. Drenadoras (Leech Seed: drena 1/8 de vida y cura al oponente activo)
            if poke.volatiles.get("leech_seed") and ability != "magic guard":
                if opp_poke and not opp_poke.is_fainted and opp_poke.current_hp > 0:
                    seed_dmg = max(1, math.floor(poke.max_hp / 8.0))
                    actual_drain = min(poke.current_hp, seed_dmg)
                    poke.current_hp = max(0, poke.current_hp - actual_drain)
                    opp_poke.current_hp = min(opp_poke.max_hp, opp_poke.current_hp + actual_drain)
                    events.append({
                        "type": "DAMAGE",
                        "side": side,
                        "pokemon": poke.species,
                        "damage": actual_drain,
                        "remaining_hp": poke.current_hp,
                        "max_hp": poke.max_hp,
                        "hp_percent": round(poke.hp_percent, 3),
                        "text": f"¡Las Drenadoras restaron salud a {poke.species} (-{actual_drain} PS)!",
                    })
                    if self._check_and_emit_faint(side, poke, events):
                        continue

            # 6c. Quemadura (BRN: 1/16 max HP en Gen 9)
            if poke.status == "BRN" and ability != "magic guard":
                burn_dmg = max(1, math.floor(poke.max_hp / 16.0))
                poke.current_hp = max(0, poke.current_hp - burn_dmg)
                events.append({
                    "type": "STATUS_DAMAGE",
                    "side": side,
                    "pokemon": poke.species,
                    "damage": burn_dmg,
                    "remaining_hp": poke.current_hp,
                    "max_hp": poke.max_hp,
                    "hp_percent": round(poke.hp_percent, 3),
                    "status": "BRN",
                    "text": f"¡La quemadura causa daño a {poke.species} (-{burn_dmg} PS)!",
                })
                if self._check_and_emit_faint(side, poke, events):
                    continue

            # 6d. Veneno normal (PSN: 1/8 max HP, o cura 1/8 con Poison Heal)
            elif poke.status == "PSN":
                if ability == "poison heal":
                    if poke.current_hp < poke.max_hp:
                        ph_heal = max(1, math.floor(poke.max_hp / 8.0))
                        poke.current_hp = min(poke.max_hp, poke.current_hp + ph_heal)
                        events.append({"type": "HEAL", "side": side, "pokemon": poke.species, "heal_amount": ph_heal, "text": f"¡Antídoto restauró salud a {poke.species} (+{ph_heal} PS)!"})
                elif ability != "magic guard":
                    psn_dmg = max(1, math.floor(poke.max_hp / 8.0))
                    poke.current_hp = max(0, poke.current_hp - psn_dmg)
                    events.append({
                        "type": "STATUS_DAMAGE",
                        "side": side,
                        "pokemon": poke.species,
                        "damage": psn_dmg,
                        "remaining_hp": poke.current_hp,
                        "max_hp": poke.max_hp,
                        "hp_percent": round(poke.hp_percent, 3),
                        "status": "PSN",
                        "text": f"¡El veneno causa daño a {poke.species} (-{psn_dmg} PS)!",
                    })
                    if self._check_and_emit_faint(side, poke, events):
                        continue

            # 6e. Veneno grave progresivo (TOX: N/16 max HP, incrementando N cada turno)
            elif poke.status == "TOX":
                if poke.status_counter <= 0:
                    poke.status_counter = 1
                if ability == "poison heal":
                    if poke.current_hp < poke.max_hp:
                        ph_heal = max(1, math.floor(poke.max_hp / 8.0))
                        poke.current_hp = min(poke.max_hp, poke.current_hp + ph_heal)
                        events.append({"type": "HEAL", "side": side, "pokemon": poke.species, "heal_amount": ph_heal, "text": f"¡Antídoto restauró salud a {poke.species} (+{ph_heal} PS)!"})
                elif ability != "magic guard":
                    tox_dmg = max(1, math.floor(poke.max_hp * poke.status_counter / 16.0))
                    poke.current_hp = max(0, poke.current_hp - tox_dmg)
                    events.append({
                        "type": "STATUS_DAMAGE",
                        "side": side,
                        "pokemon": poke.species,
                        "damage": tox_dmg,
                        "remaining_hp": poke.current_hp,
                        "max_hp": poke.max_hp,
                        "hp_percent": round(poke.hp_percent, 3),
                        "status": "TOX",
                        "text": f"¡El veneno grave daña a {poke.species} (-{tox_dmg} PS)!",
                    })
                    poke.status_counter = min(15, poke.status_counter + 1)
                    if self._check_and_emit_faint(side, poke, events):
                        continue

            # 6f. Daño por atrapamiento parcial (Fire Spin / Whirlpool / Magma Storm: 1/8 max HP)
            if "partially_trapped" in poke.volatiles and ability != "magic guard":
                trap_dmg = max(1, math.floor(poke.max_hp / 8.0))
                poke.current_hp = max(0, poke.current_hp - trap_dmg)
                events.append({
                    "type": "DAMAGE",
                    "side": side,
                    "pokemon": poke.species,
                    "damage": trap_dmg,
                    "remaining_hp": poke.current_hp,
                    "max_hp": poke.max_hp,
                    "hp_percent": round(poke.hp_percent, 3),
                    "text": f"¡{poke.species} sufre daño en el vórtice (-{trap_dmg} PS)!",
                })
                poke.volatiles["partially_trapped"] = int(poke.volatiles["partially_trapped"]) - 1
                if poke.volatiles["partially_trapped"] <= 0:
                    poke.volatiles.pop("partially_trapped", None)
                    events.append({"type": "MESSAGE", "text": f"¡{poke.species} se liberó del vórtice!"})
                if self._check_and_emit_faint(side, poke, events):
                    continue

            # 6f2. Daño por Maldición de tipo Fantasma (Curse: 1/4 max HP)
            if poke.volatiles.get("curse") and ability != "magic guard":
                curse_dmg = max(1, math.floor(poke.max_hp / 4.0))
                poke.current_hp = max(0, poke.current_hp - curse_dmg)
                events.append({
                    "type": "DAMAGE",
                    "side": side,
                    "pokemon": poke.species,
                    "damage": curse_dmg,
                    "remaining_hp": poke.current_hp,
                    "max_hp": poke.max_hp,
                    "hp_percent": round(poke.hp_percent, 3),
                    "text": f"¡La maldición resta salud a {poke.species} (-{curse_dmg} PS)!",
                })
                if self._check_and_emit_faint(side, poke, events):
                    continue

            # 6g. Contador de Mofa (Taunt)
            if "taunt" in poke.volatiles:
                poke.volatiles["taunt"] = int(poke.volatiles["taunt"]) - 1
                if poke.volatiles["taunt"] <= 0:
                    poke.volatiles.pop("taunt", None)
                    events.append({"type": "MESSAGE", "side": side, "text": f"¡El efecto de la Mofa sobre {poke.species} terminó!"})

            # 6h. Activación de Flame Orb / Toxic Orb al final del turno
            if item == "flame orb" and poke.status is None:
                self._try_inflict_status(side, poke, "BRN", snapshot, events)
            elif item == "toxic orb" and poke.status is None:
                self._try_inflict_status(side, poke, "TOX", snapshot, events)

            # 6i. Habilidad Impulso (Speed Boost)
            if ability == "speed boost" and poke.active_turns > 0:
                events.append({"type": "ABILITY", "side": side, "pokemon": poke.species, "text": f"¡Impulso de {poke.species} aumentó su Velocidad!"})
                self._apply_stat_boosts(side, poke, {"spe": 1}, events)

    # =========================================================================
    # MÉTODOS AUXILIARES DE ESTADOS, BOOSTS, SECUNDARIOS Y PRECISIÓN
    # =========================================================================

    def _move_targets_opponent(self, move: MoveState) -> bool:
        """Determina si el movimiento apunta al Pokémon oponente (y por tanto está sujeto a Protect/Precisión)."""
        if move.category in ("physical", "special") and move.base_power > 0:
            return True
        if move.target_status or move.boosts or move.force_switch:
            return True
        if move.volatile_status in ("leech_seed", "taunt", "confusion", "partially_trapped"):
            return True
        return False

    def _check_move_accuracy(
        self,
        actor: PokemonState,
        defender: PokemonState,
        move: MoveState,
        weather: Optional[str],
    ) -> bool:
        if move.never_miss or move.accuracy > 1.0:
            return True
        if (actor.ability or "").lower() == "no guard" or (defender.ability or "").lower() == "no guard":
            return True

        base_acc = float(move.accuracy)

        # Reglas climáticas de Showdown para Thunder, Hurricane y Blizzard
        if move.id in ("thunder", "hurricane"):
            if weather == "Rain":
                return True
            if weather == "Sun":
                base_acc = 0.50
        elif move.id == "blizzard" and weather == "Snow":
            return True

        stage_mult = get_accuracy_evasion_multiplier(actor.boosts.accuracy, defender.boosts.evasion)
        final_acc = base_acc * stage_mult
        return random.random() <= final_acc

    def _determine_num_hits(self, actor: PokemonState, move: MoveState) -> int:
        if not move.multi_hit:
            return 1
        min_h, max_h = move.multi_hit
        if min_h == max_h:
            return min_h
        if (actor.ability or "").lower() == "skill link":
            return max_h
        if (actor.item or "").lower() == "loaded dice":
            return random.randint(max(min_h, 4), max_h)
        if (min_h, max_h) == (2, 5):
            # Distribución oficial de Showdown: 35% 2 golpes, 35% 3 golpes, 15% 4 golpes, 15% 5 golpes
            return random.choices([2, 3, 4, 5], weights=[35, 35, 15, 15], k=1)[0]
        return random.randint(min_h, max_h)

    def _apply_stat_boosts(
        self,
        side: str,
        target: PokemonState,
        changes: Dict[str, int],
        events: List[Dict[str, Any]],
    ) -> None:
        # Habilidad Contrary invierte las subidas y bajadas de estadísticas
        effective_changes = dict(changes)
        if (target.ability or "").lower() == "contrary":
            effective_changes = {k: -v for k, v in effective_changes.items()}

        applied = target.boosts.apply_boosts(effective_changes)
        current_boosts = target.boosts.to_dict()
        for stat_key, delta in applied.items():
            stat_label = STAT_LABELS_ES.get(stat_key, stat_key.upper())
            if delta > 0:
                adverb = "drásticamente" if delta >= 2 else ""
                events.append({
                    "type": "BOOST",
                    "side": side,
                    "pokemon": target.species,
                    "stat": stat_key,
                    "stages": delta,
                    "boosts": dict(current_boosts),
                    "text": f"¡{stat_label} de {target.species} subió {adverb}!".replace("  ", " ").replace(" !", "!"),
                })
            elif delta < 0:
                adverb = "drásticamente" if delta <= -2 else ""
                events.append({
                    "type": "UNBOOST",
                    "side": side,
                    "pokemon": target.species,
                    "stat": stat_key,
                    "stages": delta,
                    "boosts": dict(current_boosts),
                    "text": f"¡{stat_label} de {target.species} bajó {adverb}!".replace("  ", " ").replace(" !", "!"),
                })
            else:
                req_delta = effective_changes.get(stat_key, 0)
                if req_delta != 0:
                    verb = "subir" if req_delta > 0 else "bajar"
                    events.append({
                        "type": "MESSAGE",
                        "side": side,
                        "pokemon": target.species,
                        "text": f"¡{stat_label} de {target.species} ya no puede {verb} más!",
                    })

    def _try_inflict_status(
        self,
        side: str,
        target: PokemonState,
        status_code: str,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
        move_type: Optional[str] = None,
        is_powder: bool = False,
    ) -> bool:
        if target.status is not None or target.is_fainted or target.current_hp <= 0:
            return False

        st = status_code.upper()
        t_types = [t.capitalize() for t in target.types if t]
        ability = (target.ability or "").lower()

        # Inmunidad de tipo Grass o Overcoat/Safety Goggles a movimientos de polvo/esporas
        if is_powder and ("Grass" in t_types or ability == "overcoat" or (target.item or "").lower() == "safety goggles"):
            return False

        # Inmunidades por Terreno (Campo de Niebla bloquea cualquier estado; Campo Eléctrico bloquea Sueño)
        if snapshot.terrain == "Misty" and target.is_grounded():
            return False
        if snapshot.terrain == "Electric" and st == "SLP" and target.is_grounded():
            return False

        # Inmunidades elementales de Showdown
        if st == "BRN" and ("Fire" in t_types or ability == "water veil"):
            return False
        if st == "PAR":
            if "Electric" in t_types or ability == "limber":
                return False
            if move_type and move_type.capitalize() == "Electric" and "Ground" in t_types:
                return False
        if st in ("PSN", "TOX") and ("Poison" in t_types or "Steel" in t_types or ability == "immunity"):
            return False
        if st == "FRZ" and ("Ice" in t_types or snapshot.weather == "Sun" or ability == "magma armor"):
            return False
        if st == "SLP" and ability in ("insomnia", "vital spirit"):
            return False
        if ability in ("purifying salt", "comatose", "good as gold"):
            return False

        target.status = st
        if st == "TOX":
            target.status_counter = 1
        elif st == "SLP":
            target.sleep_turns = random.randint(1, 3)

        status_texts = {
            "BRN": f"¡{target.species} ha sufrido una quemadura!",
            "PAR": f"¡{target.species} ha quedado paralizado! ¡Quizá no se pueda mover!",
            "PSN": f"¡{target.species} ha sido envenenado!",
            "TOX": f"¡{target.species} ha sido gravemente envenenado!",
            "SLP": f"¡{target.species} se quedó dormido!",
            "FRZ": f"¡{target.species} se ha congelado!",
        }
        events.append({
            "type": "STATUS",
            "side": side,
            "pokemon": target.species,
            "status": st,
            "text": status_texts.get(st, f"¡{target.species} sufrió {st}!"),
        })
        return True

    def _inflict_volatile(
        self,
        side: str,
        target: PokemonState,
        volatile: str,
        events: List[Dict[str, Any]],
        move_type: Optional[str] = None,
    ) -> bool:
        if target.is_fainted or target.current_hp <= 0:
            return False

        if volatile == "leech_seed":
            if "Grass" in target.types or "leech_seed" in target.volatiles:
                events.append({"type": "MESSAGE", "text": f"¡No afectó a {target.species}!"})
                return False
            target.volatiles["leech_seed"] = True
            events.append({"type": "VOLATILE", "side": side, "pokemon": target.species, "volatile": "leech_seed", "text": f"¡{target.species} fue infectado por Drenadoras!"})
            return True

        if volatile == "taunt":
            target.volatiles["taunt"] = 3
            events.append({"type": "VOLATILE", "side": side, "pokemon": target.species, "volatile": "taunt", "text": f"¡{target.species} cayó en la Mofa!"})
            return True

        if volatile == "confusion":
            if "confusion" in target.volatiles or (target.ability or "").lower() == "own tempo":
                return False
            target.volatiles["confusion"] = random.randint(2, 5)
            events.append({"type": "VOLATILE", "side": side, "pokemon": target.species, "volatile": "confusion", "text": f"¡{target.species} se ha confundido!"})
            return True

        if volatile == "partially_trapped":
            if "partially_trapped" not in target.volatiles:
                target.volatiles["partially_trapped"] = random.randint(4, 5)
                events.append({"type": "VOLATILE", "side": side, "pokemon": target.species, "volatile": "partially_trapped", "text": f"¡{target.species} quedó atrapado en el vórtice!"})
                return True

        return False

    def _resolve_secondary_effects(
        self,
        atk_side: str,
        actor: PokemonState,
        def_side: str,
        defender: PokemonState,
        secondary: Dict[str, Any],
        hit_substitute: bool,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        chance = float(secondary.get("chance", 1.0))
        if (actor.ability or "").lower() == "serene grace":
            chance = min(1.0, chance * 2.0)

        # Habilidad Sheer Force anula efectos secundarios a cambio de potencia
        if (actor.ability or "").lower() == "sheer force":
            return

        if random.random() > chance:
            return

        # Self boosts del efecto secundario (ej. Meteor Mash +1 Atk, Fiery Dance +1 SpA) ocurren aunque golpee un sustituto
        if secondary.get("self_boosts") and not actor.is_fainted:
            self._apply_stat_boosts(atk_side, actor, secondary["self_boosts"], events)

        # El resto de efectos secundarios sobre el defensor son bloqueados por Sustituto o Shield Dust / Covert Cloak
        if hit_substitute:
            return
        if (defender.ability or "").lower() == "shield dust" or (defender.item or "").lower() == "covert cloak":
            return

        if secondary.get("status"):
            self._try_inflict_status(def_side, defender, secondary["status"], snapshot, events)

        if secondary.get("volatile_status"):
            self._inflict_volatile(def_side, defender, secondary["volatile_status"], events)

        if secondary.get("flinch"):
            defender.volatiles["flinch"] = True

        if secondary.get("boosts"):
            self._apply_stat_boosts(def_side, defender, secondary["boosts"], events)

    def _apply_contact_punishment(
        self,
        atk_side: str,
        actor: PokemonState,
        def_side: str,
        defender: PokemonState,
        events: List[Dict[str, Any]],
    ) -> None:
        if (actor.item or "").lower() == "protective pads":
            return

        def_item = (defender.item or "").lower()
        def_ab = (defender.ability or "").lower()

        if def_item == "rocky helmet" and (actor.ability or "").lower() != "magic guard":
            rh_dmg = max(1, math.floor(actor.max_hp / 6.0))
            actor.current_hp = max(0, actor.current_hp - rh_dmg)
            events.append({
                "type": "DAMAGE",
                "side": atk_side,
                "pokemon": actor.species,
                "damage": rh_dmg,
                "remaining_hp": actor.current_hp,
                "max_hp": actor.max_hp,
                "hp_percent": round(actor.hp_percent, 3),
                "text": f"¡{actor.species} se hirió con el Casco Dentado de {defender.species} (-{rh_dmg} PS)!",
            })
            self._check_and_emit_faint(atk_side, actor, events)

        if def_ab in ("rough skin", "iron barbs") and not actor.is_fainted and (actor.ability or "").lower() != "magic guard":
            ab_dmg = max(1, math.floor(actor.max_hp / 8.0))
            actor.current_hp = max(0, actor.current_hp - ab_dmg)
            events.append({
                "type": "DAMAGE",
                "side": atk_side,
                "pokemon": actor.species,
                "damage": ab_dmg,
                "remaining_hp": actor.current_hp,
                "max_hp": actor.max_hp,
                "hp_percent": round(actor.hp_percent, 3),
                "text": f"¡La habilidad de {defender.species} hirió a {actor.species} al contacto (-{ab_dmg} PS)!",
            })
            self._check_and_emit_faint(atk_side, actor, events)

    def _force_random_switch(
        self,
        target_side: str,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        bench = snapshot.player_bench if target_side == "player" else snapshot.ai_bench
        alive_bench = [p for p in bench if not p.is_fainted and p.current_hp > 0]
        if not alive_bench:
            return
        chosen = random.choice(alive_bench)
        self._handle_switch(target_side, chosen.id, snapshot, events)

    def _auto_pivot_switch(
        self,
        side: str,
        snapshot: BattleSnapshot,
        events: List[Dict[str, Any]],
    ) -> None:
        bench = snapshot.player_bench if side == "player" else snapshot.ai_bench
        alive_bench = [p for p in bench if not p.is_fainted and p.current_hp > 0]
        if not alive_bench:
            return
        chosen = alive_bench[0]
        self._handle_switch(side, chosen.id, snapshot, events)

    def _get_speed_ordered_actives(self, snapshot: BattleSnapshot) -> List[Tuple[str, Optional[PokemonState]]]:
        p = snapshot.player_active
        ai = snapshot.ai_active
        p_spd = get_effective_speed(p, snapshot.player_side, snapshot.weather) if p else 0
        ai_spd = get_effective_speed(ai, snapshot.ai_side, snapshot.weather) if ai else 0

        if snapshot.trick_room_turns > 0:
            if p_spd <= ai_spd:
                return [("player", p), ("ai", ai)]
            return [("ai", ai), ("player", p)]

        if p_spd >= ai_spd:
            return [("player", p), ("ai", ai)]
        return [("ai", ai), ("player", p)]

    def _check_and_emit_faint(
        self,
        side: str,
        pokemon: PokemonState,
        events: List[Dict[str, Any]],
    ) -> bool:
        if pokemon.current_hp <= 0 and not pokemon.is_fainted:
            pokemon.current_hp = 0
            pokemon.is_fainted = True
            events.append({
                "type": "FAINT",
                "side": side,
                "pokemon": pokemon.species,
                "text": f"¡{pokemon.species} se ha debilitado!",
            })
            return True
        return pokemon.is_fainted

    def _check_battle_status(self, snapshot: BattleSnapshot) -> str:
        ai_alive = [p for p in ([snapshot.ai_active] + snapshot.ai_bench) if p and not p.is_fainted and p.current_hp > 0]
        if not ai_alive:
            return "won"

        player_alive = [p for p in ([snapshot.player_active] + snapshot.player_bench) if p and not p.is_fainted and p.current_hp > 0]
        if not player_alive:
            return "lost"

        if snapshot.player_active and snapshot.player_active.is_fainted:
            return "waiting_player_switch"

        if snapshot.ai_active and snapshot.ai_active.is_fainted:
            return "waiting_ai_switch"

        return "in_progress"

    def _find_move(self, pokemon: PokemonState, move_id_or_name: str) -> Optional[MoveState]:
        clean = move_id_or_name.strip().lower()
        for m in pokemon.moves:
            if m.id.lower() == clean or m.name.lower() == clean:
                return m
        return pokemon.moves[0] if pokemon.moves else None
