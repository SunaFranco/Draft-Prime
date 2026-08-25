"""
backend/modes/registry.py - Registro dinámico de modos de juego
"""

from typing import Dict, List, Optional
from backend.modes.base import BaseGameMode
from backend.modes.cube_draft_yugioh.handler import CubeDraftYugiohMode
from backend.modes.subasta_pokemon.handler import SubastaPokemonMode

# Registro de handlers instanciados de modos de juego
_REGISTERED_MODES: Dict[str, BaseGameMode] = {}


def register_mode(mode_handler: BaseGameMode):
    """Registra una instancia de modo de juego."""
    _REGISTERED_MODES[mode_handler.key] = mode_handler


# Registrar los modos iniciales
register_mode(CubeDraftYugiohMode())
register_mode(SubastaPokemonMode())


def get_available_modes() -> List[dict]:
    """Retorna la lista de modos disponibles para enviar al cliente."""
    return [
        {"key": handler.key, "name": handler.name}
        for handler in _REGISTERED_MODES.values()
    ]


def is_valid_mode(mode_key: str) -> bool:
    """Indica si una clave de modo está registrada."""
    return mode_key in _REGISTERED_MODES


def get_mode_name(mode_key: str) -> str:
    """Devuelve el nombre legible de un modo."""
    handler = _REGISTERED_MODES.get(mode_key)
    return handler.name if handler else mode_key


def mode_requires_cubes(mode_key: str) -> bool:
    """Indica si el modo especificado requiere la selección de un cube."""
    handler = _REGISTERED_MODES.get(mode_key)
    return handler.requires_cubes if handler else False


def get_mode_handler(mode_key: str) -> Optional[BaseGameMode]:
    """Retorna el handler asociado a la clave de modo."""
    return _REGISTERED_MODES.get(mode_key)
