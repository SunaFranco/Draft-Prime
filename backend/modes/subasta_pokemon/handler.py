"""
backend/modes/subasta_pokemon/handler.py - Stub inicial para el modo Subasta Pokémon
"""

from typing import Dict, Any
from backend.modes.base import BaseGameMode


class SubastaPokemonMode(BaseGameMode):
    @property
    def key(self) -> str:
        return "subasta_pokemon"

    @property
    def name(self) -> str:
        return "Subasta (Pokemon)"

    @property
    def requires_cubes(self) -> bool:
        return False

    def get_public_config_options(self, session: dict) -> Dict[str, Any]:
        return {}

    def validate_config(self, message: dict) -> dict:
        return {}

    def start_game(self, session: dict) -> None:
        session["subasta"] = {
            "finished": False,
            "items": [],
        }

    async def handle_action(
        self,
        session: dict,
        username: str,
        action: str,
        message: dict,
        websocket: Any,
        manager: Any
    ) -> bool:
        # Stub preparado para futuras acciones de subasta pokemon (ej: 'bid_pokemon', 'nominate_pokemon')
        return False
