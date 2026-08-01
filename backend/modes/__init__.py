"""
Registry de modos de juego — mantiene metadatos y utilidades para modos.
Cada modo puede implementarse en un módulo propio bajo `backend.modes`.
"""

from typing import Dict, List

MODES: Dict[str, dict] = {
    "cube_draft_yugioh": {
        "name": "Draft cube yugioh",
        "requires_cubes": True,
    },
    "subasta_pokemon": {
        "name": "Subasta pokemon",
        "requires_cubes": False,
    },
}


def get_available_modes() -> List[dict]:
    return [{"key": k, "name": v["name"]} for k, v in MODES.items()]


def is_valid_mode(mode_key: str) -> bool:
    return mode_key in MODES


def get_mode_name(mode_key: str) -> str | None:
    return MODES.get(mode_key, {}).get("name")


def mode_requires_cubes(mode_key: str) -> bool:
    return bool(MODES.get(mode_key, {}).get("requires_cubes", False))
