"""
backend/routes/pve.py
Rutas HTTP REST para combates PVE contra la Inteligencia Artificial.
Stateless, ligero y persistido en Supabase JSONB.
"""

import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.database import (
    create_pve_battle,
    get_pve_battle,
    update_pve_battle,
)
from backend.engine.pkmn_ai_engine import (
    BattleSnapshot,
    PokemonState,
    MoveState,
    Action,
    PokemonAIAgent,
    CombatEngine,
    OpponentTracker,
    PVE_PRESETS,
    get_preset_by_id,
)
from backend.engine.pkmn_ai_engine.core.adapter import adapt_draft_pokemon

router = APIRouter()


class PlayerActionSchema(BaseModel):
    type: str = Field(..., description="'MOVE' o 'SWITCH'")
    choice: str = Field(..., description="Nombre/ID del ataque o del Pokémon de banca")
    mega: bool = Field(False, description="¿Activa Megaevolución en este turno?")


class StartPVEBattleRequest(BaseModel):
    preset_id: str = Field(..., description="ID del rival prefabricado (ej: 'brock-rock', 'cynthia-sinnoh')")
    player_team: List[Dict[str, Any]] = Field(..., description="Lista de hasta 6 Pokémon del jugador")
    user_id: Optional[str] = None


class TurnPVEBattleRequest(BaseModel):
    battle_id: str
    action: PlayerActionSchema


class SurrenderRequest(BaseModel):
    battle_id: str


@router.get("/presets")
async def list_pve_presets():
    """Devuelve la lista de entrenadores prefabricados para el modo PVE."""
    presets_summary = []
    for p in PVE_PRESETS:
        presets_summary.append({
            "id": p["id"],
            "name": p["name"],
            "title": p.get("title", ""),
            "difficulty": p.get("difficulty", "medium"),
            "avatar_url": p.get("avatar_url", ""),
            "description": p.get("description", ""),
            "team_size": len(p.get("team", [])),
        })
    return {"presets": presets_summary}


@router.post("/start")
async def start_pve_battle(req: StartPVEBattleRequest):
    """Inicia una nueva batalla 6v6 PVE contra un entrenador IA."""
    preset = get_preset_by_id(req.preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{req.preset_id}' no encontrado.")

    if not req.player_team:
        raise HTTPException(status_code=400, detail="El equipo del jugador no puede estar vacío.")

    # Convertir Pokémon del jugador usando el adaptador inteligente
    parsed_player_team: List[PokemonState] = [adapt_draft_pokemon(p) for p in req.player_team[:6]]

    # Convertir Pokémon de la IA usando el adaptador inteligente
    parsed_ai_team: List[PokemonState] = [adapt_draft_pokemon(p) for p in preset["team"][:6]]

    player_active = parsed_player_team[0]
    player_bench = parsed_player_team[1:]

    ai_active = parsed_ai_team[0]
    ai_bench = parsed_ai_team[1:]

    initial_snapshot = BattleSnapshot(
        turn=1,
        player_active=player_active,
        player_bench=player_bench,
        ai_active=ai_active,
        ai_bench=ai_bench,
    )

    state_dict = initial_snapshot.to_dict()
    state_dict["difficulty"] = preset.get("difficulty", "medium")
    state_dict["preset_id"] = preset["id"]
    state_dict["preset_name"] = preset["name"]
    state_dict["opponent_tracker"] = {}

    battle_id = str(uuid.uuid4())
    record = create_pve_battle(
        battle_id=battle_id,
        user_id=req.user_id,
        preset_id=preset["id"],
        state=state_dict,
    )

    return {
        "battle_id": battle_id,
        "status": "in_progress",
        "turn": 1,
        "trainer": {
            "name": preset["name"],
            "title": preset.get("title", ""),
            "difficulty": preset.get("difficulty", "medium"),
            "avatar_url": preset.get("avatar_url", ""),
        },
        "state": state_dict,
    }


@router.post("/turn")
async def process_pve_turn(req: TurnPVEBattleRequest):
    """Procesa el turno enviado por el jugador, decide la jugada de la IA y resuelve el combate."""
    battle = get_pve_battle(req.battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Batalla PVE no encontrada.")

    current_status = battle.get("status", "in_progress")
    if current_status in ["won", "lost", "surrendered"]:
        return {
            "events": [{"type": "MESSAGE", "text": "Esta batalla ya ha finalizado."}],
            "state": battle.get("state"),
            "battle_status": current_status,
        }

    raw_state = battle.get("state", {})
    snapshot = BattleSnapshot.from_dict(raw_state)

    # Reconstruir Tracker de la IA
    tracker_data = raw_state.get("opponent_tracker", {})
    tracker = OpponentTracker(tracker_data)

    # Decisión de la IA
    difficulty = raw_state.get("difficulty", "medium")
    agent = PokemonAIAgent(difficulty=difficulty, tracker=tracker)
    ai_decision = agent.decide_action(snapshot)

    # Acción del jugador
    player_action = Action(
        type=req.action.type.upper(),
        choice=req.action.choice,
        mega=req.action.mega,
    )

    # Resolver el turno
    engine = CombatEngine(tracker=tracker)
    turn_result = engine.resolve_turn(
        snapshot=snapshot,
        player_action=player_action,
        ai_action=ai_decision.action,
    )

    # Si el Pokémon activo de la IA cayó pero le queda banca, la IA envía su reemplazo automáticamente
    safety_loops = 0
    while turn_result.battle_status == "waiting_ai_switch" and safety_loops < 6:
        safety_loops += 1
        faint_decision = agent.decide_action(turn_result.new_snapshot)
        if faint_decision.action.type.upper() != "SWITCH" or faint_decision.action.choice == "none":
            break
        faint_res = engine.resolve_turn(
            snapshot=turn_result.new_snapshot,
            player_action=Action(type="WAIT", choice="none"),
            ai_action=faint_decision.action,
        )
        turn_result.events.extend(faint_res.events)
        turn_result.new_snapshot = faint_res.new_snapshot
        turn_result.battle_status = faint_res.battle_status

    # Actualizar estado serializable
    updated_state_dict = turn_result.new_snapshot.to_dict()
    updated_state_dict["difficulty"] = difficulty
    updated_state_dict["preset_id"] = raw_state.get("preset_id")
    updated_state_dict["preset_name"] = raw_state.get("preset_name")
    updated_state_dict["opponent_tracker"] = tracker.to_dict()

    new_status = turn_result.battle_status
    update_pve_battle(
        battle_id=req.battle_id,
        state=updated_state_dict,
        status=new_status,
        turn_number=turn_result.new_snapshot.turn,
    )

    return {
        "battle_id": req.battle_id,
        "turn": turn_result.new_snapshot.turn,
        "events": turn_result.events,
        "state": updated_state_dict,
        "battle_status": new_status,
        "ai_action": {
            "type": ai_decision.action.type,
            "choice": ai_decision.action.choice,
            "mega": ai_decision.action.mega,
            "rationale": ai_decision.debug_rationale,
        },
    }


@router.get("/battle/{battle_id}")
async def get_pve_battle_status(battle_id: str):
    """Consulta el estado actual de una batalla PVE."""
    battle = get_pve_battle(battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Batalla PVE no encontrada.")

    return {
        "battle_id": battle["id"],
        "status": battle.get("status", "in_progress"),
        "turn_number": battle.get("turn_number", 1),
        "state": battle.get("state", {}),
    }


@router.post("/surrender")
async def surrender_pve_battle(req: SurrenderRequest):
    """Permite al jugador rendirse y finalizar la batalla PVE."""
    battle = get_pve_battle(req.battle_id)
    if not battle:
        raise HTTPException(status_code=404, detail="Batalla PVE no encontrada.")

    state = battle.get("state", {})
    update_pve_battle(
        battle_id=req.battle_id,
        state=state,
        status="surrendered",
        turn_number=battle.get("turn_number", 1),
    )

    return {
        "battle_id": req.battle_id,
        "status": "surrendered",
        "message": "Te has rendido de la batalla.",
    }
