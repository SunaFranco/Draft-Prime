"""
backend/modes/base.py - Interfaz base para todos los modos de juego
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseGameMode(ABC):
    """
    Clase base abstracta que debe ser implementada por cada modo de juego.
    """

    @property
    @abstractmethod
    def key(self) -> str:
        """Identificador único del modo de juego (ej: 'cube_draft_yugioh')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre legible del modo de juego (ej: 'Cube Draft (Yugioh)')."""
        pass

    @property
    def requires_cubes(self) -> bool:
        """Indica si el modo requiere selección de un cube."""
        return False

    def get_public_config_options(self, session: dict) -> Dict[str, Any]:
        """
        Retorna opciones de configuración públicas necesarias para la UI (ej. lista de cubes).
        """
        return {}

    @abstractmethod
    def validate_config(self, message: dict) -> dict:
        """
        Valida la configuración provista por el host en la acción 'configure_mode'.
        Retorna el diccionario de configuración procesado o lanza un ValueError en caso de error.
        """
        pass

    @abstractmethod
    def start_game(self, session: dict) -> None:
        """
        Inicializa el estado interno de la partida cuando el host ejecuta 'start_draft' o equivalente.
        """
        pass

    @abstractmethod
    async def handle_action(
        self,
        session: dict,
        username: str,
        action: str,
        message: dict,
        websocket: Any,
        manager: Any
    ) -> bool:
        """
        Maneja acciones WebSocket específicas del modo de juego.
        Retorna True si la acción fue procesada por este modo, o False si no corresponde.
        """
        pass
