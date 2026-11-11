"""
backend/engine/pkmn_ai_engine/core/types.py
Matriz oficial de efectividades de tipos de Pokémon (Generación 9).
Ultra-ligero en memoria, optimizado para consultas O(1) inmutables.
"""

from typing import Sequence, Union

POKEMON_TYPES: tuple[str, ...] = (
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Steel", "Dark", "Fairy"
)

# Diccionario de efectividades atacante -> {defensor: multiplicador}
# Si no está en el diccionario, el multiplicador neutro es 1.0.
TYPE_CHART: dict[str, dict[str, float]] = {
    "Normal": {
        "Rock": 0.5, "Ghost": 0.0, "Steel": 0.5
    },
    "Fire": {
        "Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0,
        "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0
    },
    "Water": {
        "Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0,
        "Rock": 2.0, "Dragon": 0.5
    },
    "Grass": {
        "Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5,
        "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0,
        "Dragon": 0.5, "Steel": 0.5
    },
    "Electric": {
        "Water": 2.0, "Grass": 0.5, "Electric": 0.5, "Ground": 0.0,
        "Flying": 2.0, "Dragon": 0.5
    },
    "Ice": {
        "Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5,
        "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5
    },
    "Fighting": {
        "Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5,
        "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0,
        "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5
    },
    "Poison": {
        "Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5,
        "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0
    },
    "Ground": {
        "Fire": 2.0, "Grass": 0.5, "Electric": 2.0, "Poison": 2.0,
        "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0
    },
    "Flying": {
        "Grass": 2.0, "Electric": 0.5, "Fighting": 2.0, "Bug": 2.0,
        "Rock": 0.5, "Steel": 0.5
    },
    "Psychic": {
        "Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Steel": 0.5,
        "Dark": 0.0
    },
    "Bug": {
        "Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5,
        "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Steel": 0.5,
        "Fairy": 0.5
    },
    "Rock": {
        "Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5,
        "Flying": 2.0, "Bug": 2.0, "Steel": 0.5
    },
    "Ghost": {
        "Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5
    },
    "Dragon": {
        "Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0
    },
    "Steel": {
        "Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0,
        "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0
    },
    "Dark": {
        "Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5,
        "Fairy": 0.5
    },
    "Fairy": {
        "Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0,
        "Dark": 2.0, "Steel": 0.5
    }
}


def normalize_type_name(t: str) -> str:
    """Normaliza el nombre del tipo capitalizando la primera letra."""
    if not t:
        return "Normal"
    return t.strip().capitalize()


def get_single_effectiveness(attack_type: str, defend_type: str) -> float:
    """Devuelve el multiplicador de un tipo atacante contra un único tipo defensor."""
    atk = normalize_type_name(attack_type)
    dfn = normalize_type_name(defend_type)
    return TYPE_CHART.get(atk, {}).get(dfn, 1.0)


def get_type_effectiveness(attack_type: str, defend_types: Sequence[str]) -> float:
    """
    Calcula la efectividad contra un Pokémon defensor de uno o dos tipos (ej: 0.0, 0.25, 0.5, 1.0, 2.0, 4.0).
    """
    multiplier = 1.0
    for dt in defend_types:
        if dt:
            multiplier *= get_single_effectiveness(attack_type, dt)
    return multiplier
