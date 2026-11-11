"""
backend/engine/pkmn_ai_engine/core/__init__.py
"""

from .types import (
    TYPE_CHART,
    POKEMON_TYPES,
    get_type_effectiveness,
    get_single_effectiveness,
    normalize_type_name,
)
from .models import (
    StatBlock,
    StatBoosts,
    MoveState,
    PokemonState,
    Action,
    DecisionResult,
    BattleSnapshot,
)
from .megas import (
    MEGA_DATABASE,
    check_can_mega,
    trigger_mega_evolution,
)
from .damage import (
    calculate_damage,
    get_effective_speed,
    get_boost_multiplier,
)

__all__ = [
    "TYPE_CHART",
    "POKEMON_TYPES",
    "get_type_effectiveness",
    "get_single_effectiveness",
    "normalize_type_name",
    "StatBlock",
    "StatBoosts",
    "MoveState",
    "PokemonState",
    "Action",
    "DecisionResult",
    "BattleSnapshot",
    "MEGA_DATABASE",
    "check_can_mega",
    "trigger_mega_evolution",
    "calculate_damage",
    "get_effective_speed",
    "get_boost_multiplier",
]
