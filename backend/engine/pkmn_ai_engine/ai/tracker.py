"""
backend/engine/pkmn_ai_engine/ai/tracker.py
Rastreador de información imperfecta del rival (OpponentTracker).
Registra lo que el jugador revela en combate e infiere movimientos no revelados.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ..core.models import MoveState, PokemonState


@dataclass
class TrackedOpponentPokemon:
    species: str
    revealed_moves: List[str] = field(default_factory=list)
    revealed_item: Optional[str] = None
    revealed_ability: Optional[str] = None

    def record_move(self, move_name: str) -> None:
        clean = move_name.strip()
        if clean and clean not in self.revealed_moves:
            self.revealed_moves.append(clean)

    def record_item(self, item_name: str) -> None:
        if item_name:
            self.revealed_item = item_name

    def record_ability(self, ability_name: str) -> None:
        if ability_name:
            self.revealed_ability = ability_name

    def get_estimated_moves(self, pokemon: PokemonState) -> List[MoveState]:
        """
        Devuelve la lista de movimientos conocidos + movimientos deducidos
        según los tipos del Pokémon para las ranuras no reveladas.
        """
        # 1. Movimientos reales ya conocidos que coincidan con los de pokemon.moves
        known: List[MoveState] = []
        for m in pokemon.moves:
            if m.name in self.revealed_moves or m.id in [x.lower() for x in self.revealed_moves]:
                known.append(m)

        # 2. Rellenar las ranuras desconocidas con estimaciones STAB de poder 80
        remaining_slots = max(0, 4 - len(known))
        if remaining_slots > 0:
            for idx, p_type in enumerate(pokemon.types):
                if remaining_slots <= 0:
                    break
                # Asume un ataque genérico físico o especial según las stats del rival
                category = "physical" if pokemon.stats.atk >= pokemon.stats.spa else "special"
                known.append(
                    MoveState(
                        id=f"estimated-{p_type.lower()}-{idx}",
                        name=f"Estimated {p_type}",
                        type=p_type,
                        category=category,
                        base_power=80,
                        accuracy=1.0,
                    )
                )
                remaining_slots -= 1

        # Si aún sobran ranuras (ej: monotipo), agregar Normal o cobertura neutra
        while len(known) < 4:
            category = "physical" if pokemon.stats.atk >= pokemon.stats.spa else "special"
            known.append(
                MoveState(
                    id=f"estimated-normal-{len(known)}",
                    name="Estimated Normal",
                    type="Normal",
                    category=category,
                    base_power=70,
                    accuracy=1.0,
                )
            )

        return known


class OpponentTracker:
    """Mantiene el estado de deducción de todo el equipo rival a lo largo del combate."""

    def __init__(self, data: Optional[Dict[str, dict]] = None):
        self.pokemon_map: Dict[str, TrackedOpponentPokemon] = {}
        if data:
            for spec, pdata in data.items():
                self.pokemon_map[spec] = TrackedOpponentPokemon(
                    species=spec,
                    revealed_moves=pdata.get("revealed_moves", []),
                    revealed_item=pdata.get("revealed_item"),
                    revealed_ability=pdata.get("revealed_ability"),
                )

    def get_or_create(self, species: str) -> TrackedOpponentPokemon:
        if species not in self.pokemon_map:
            self.pokemon_map[species] = TrackedOpponentPokemon(species=species)
        return self.pokemon_map[species]

    def record_move_used(self, species: str, move_name: str) -> None:
        self.get_or_create(species).record_move(move_name)

    def record_item_triggered(self, species: str, item_name: str) -> None:
        self.get_or_create(species).record_item(item_name)

    def to_dict(self) -> Dict[str, dict]:
        return {
            spec: {
                "revealed_moves": tracked.revealed_moves,
                "revealed_item": tracked.revealed_item,
                "revealed_ability": tracked.revealed_ability,
            }
            for spec, tracked in self.pokemon_map.items()
        }
