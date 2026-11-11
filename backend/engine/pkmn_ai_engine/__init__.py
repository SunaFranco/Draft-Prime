"""
backend/engine/pkmn_ai_engine/__init__.py
Módulo independiente de IA y Combate Pokémon (pkmn_ai_engine).
"""

from .core.types import (
    TYPE_CHART,
    POKEMON_TYPES,
    get_type_effectiveness,
    get_single_effectiveness,
)
from .core.models import (
    StatBlock,
    StatBoosts,
    MoveState,
    PokemonState,
    Action,
    DecisionResult,
    BattleSnapshot,
)
from .core.damage import (
    calculate_damage,
    get_effective_speed,
    get_boost_multiplier,
)
from .core.megas import (
    MEGA_DATABASE,
    check_can_mega,
    trigger_mega_evolution,
)
from .ai.tracker import OpponentTracker, TrackedOpponentPokemon
from .ai.evaluator import DifficultyProfile, PROFILES, get_profile
from .ai.agent import PokemonAIAgent
from .resolver.turn_order import determine_turn_order
from .resolver.combat_engine import CombatEngine, TurnResult
from .presets import PVE_PRESETS, get_preset_by_id

__version__ = "1.0.0"

__all__ = [
    "TYPE_CHART",
    "POKEMON_TYPES",
    "get_type_effectiveness",
    "get_single_effectiveness",
    "StatBlock",
    "StatBoosts",
    "MoveState",
    "PokemonState",
    "Action",
    "DecisionResult",
    "BattleSnapshot",
    "calculate_damage",
    "get_effective_speed",
    "get_boost_multiplier",
    "MEGA_DATABASE",
    "check_can_mega",
    "trigger_mega_evolution",
    "OpponentTracker",
    "TrackedOpponentPokemon",
    "DifficultyProfile",
    "PROFILES",
    "get_profile",
    "PokemonAIAgent",
    "determine_turn_order",
    "CombatEngine",
    "TurnResult",
    "PVE_PRESETS",
    "get_preset_by_id",
]
