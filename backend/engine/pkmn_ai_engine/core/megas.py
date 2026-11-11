"""
backend/engine/pkmn_ai_engine/core/megas.py
Catálogo y reglas de Megaevolución para pkmn_ai_engine.
Permite transformar un PokemonState en su forma Mega durante el turno.
"""

from typing import Optional, Dict, Tuple
from .models import PokemonState, StatBlock

# Mapeo: Mega Stone -> { base_species, mega_name, types, stat_bonus, ability }
# stat_bonus: (atk_bonus, def_bonus, spa_bonus, spd_bonus, spe_bonus) (HP nunca cambia en megas)
MEGA_DATABASE: Dict[str, dict] = {
    "charizardite x": {
        "base": "Charizard",
        "mega_name": "Mega Charizard X",
        "types": ("Fire", "Dragon"),
        "stat_bonus": (46, 33, 21, 0, 0),
        "ability": "Tough Claws",
    },
    "charizardite y": {
        "base": "Charizard",
        "mega_name": "Mega Charizard Y",
        "types": ("Fire", "Flying"),
        "stat_bonus": (20, 0, 50, 30, 0),
        "ability": "Drought",
    },
    "blastoisinite": {
        "base": "Blastoise",
        "mega_name": "Mega Blastoise",
        "types": ("Water",),
        "stat_bonus": (20, 20, 50, 10, 0),
        "ability": "Mega Launcher",
    },
    "venusaurite": {
        "base": "Venusaur",
        "mega_name": "Mega Venusaur",
        "types": ("Grass", "Poison"),
        "stat_bonus": (18, 40, 22, 20, 0),
        "ability": "Thick Fat",
    },
    "gengarite": {
        "base": "Gengar",
        "mega_name": "Mega Gengar",
        "types": ("Ghost", "Poison"),
        "stat_bonus": (0, 20, 40, 20, 20),
        "ability": "Shadow Tag",
    },
    "lucarionite": {
        "base": "Lucario",
        "mega_name": "Mega Lucario",
        "types": ("Fighting", "Steel"),
        "stat_bonus": (35, 18, 25, 0, 22),
        "ability": "Adaptability",
    },
    "gyaradosite": {
        "base": "Gyarados",
        "mega_name": "Mega Gyarados",
        "types": ("Water", "Dark"),
        "stat_bonus": (30, 30, 10, 30, 0),
        "ability": "Mold Breaker",
    },
    "alakazite": {
        "base": "Alakazam",
        "mega_name": "Mega Alakazam",
        "types": ("Psychic",),
        "stat_bonus": (0, 20, 40, 10, 30),
        "ability": "Trace",
    },
    "tyranitarite": {
        "base": "Tyranitar",
        "mega_name": "Mega Tyranitar",
        "types": ("Rock", "Dark"),
        "stat_bonus": (30, 40, 0, 20, 10),
        "ability": "Sand Stream",
    },
    "scizorite": {
        "base": "Scizor",
        "mega_name": "Mega Scizor",
        "types": ("Bug", "Steel"),
        "stat_bonus": (20, 40, 10, 20, 10),
        "ability": "Technician",
    },
    "swampertite": {
        "base": "Swampert",
        "mega_name": "Mega Swampert",
        "types": ("Water", "Ground"),
        "stat_bonus": (40, 20, 10, 20, 10),
        "ability": "Swift Swim",
    },
    "sceptilite": {
        "base": "Sceptile",
        "mega_name": "Mega Sceptile",
        "types": ("Grass", "Dragon"),
        "stat_bonus": (25, 10, 40, 0, 25),
        "ability": "Lightning Rod",
    },
    "blazikenite": {
        "base": "Blaziken",
        "mega_name": "Mega Blaziken",
        "types": ("Fire", "Fighting"),
        "stat_bonus": (40, 10, 20, 10, 20),
        "ability": "Speed Boost",
    },
    "gardevoirite": {
        "base": "Gardevoir",
        "mega_name": "Mega Gardevoir",
        "types": ("Psychic", "Fairy"),
        "stat_bonus": (20, 0, 40, 20, 20),
        "ability": "Pixilate",
    },
    "aerodactylite": {
        "base": "Aerodactyl",
        "mega_name": "Mega Aerodactyl",
        "types": ("Rock", "Flying"),
        "stat_bonus": (30, 20, 10, 20, 20),
        "ability": "Tough Claws",
    },
    "salamencite": {
        "base": "Salamence",
        "mega_name": "Mega Salamence",
        "types": ("Dragon", "Flying"),
        "stat_bonus": (10, 50, 10, 10, 20),
        "ability": "Aerilate",
    },
    "metagrossite": {
        "base": "Metagross",
        "mega_name": "Mega Metagross",
        "types": ("Steel", "Psychic"),
        "stat_bonus": (10, 20, 10, 20, 40),
        "ability": "Tough Claws",
    },
}


def check_can_mega(pokemon: PokemonState) -> Optional[str]:
    """
    Verifica si un Pokémon tiene equipada una Mega Piedra válida para su especie.
    Devuelve la key normalizada de la piedra o None.
    """
    if pokemon.is_mega or pokemon.is_fainted:
        return None

    stone = (pokemon.mega_stone or pokemon.item or "").strip().lower()
    if stone in MEGA_DATABASE:
        mega_info = MEGA_DATABASE[stone]
        if mega_info["base"].lower() in pokemon.species.lower():
            return stone

    # Fallback buscando por nombre de especie si tiene "-mega"
    for s_name, data in MEGA_DATABASE.items():
        if data["base"].lower() in pokemon.species.lower() and (
            pokemon.mega_stone and s_name in pokemon.mega_stone.lower()
        ):
            return s_name

    return None


def trigger_mega_evolution(pokemon: PokemonState, stone_key: str) -> bool:
    """
    Transforma el PokemonState en su forma Mega in-place.
    Actualiza stats, tipos, habilidad y marca is_mega = True.
    """
    stone = stone_key.strip().lower()
    if stone not in MEGA_DATABASE:
        return False

    info = MEGA_DATABASE[stone]
    pokemon.is_mega = True
    pokemon.species = info["mega_name"]
    pokemon.types = info["types"]
    pokemon.ability = info.get("ability", pokemon.ability)

    # Actualizar stats sumando los bonus
    bonus = info["stat_bonus"]
    current_stats = pokemon.stats
    pokemon.stats = StatBlock(
        hp=current_stats.hp,
        atk=current_stats.atk + bonus[0],
        def_=current_stats.def_ + bonus[1],
        spa=current_stats.spa + bonus[2],
        spd=current_stats.spd + bonus[3],
        spe=current_stats.spe + bonus[4],
    )
    return True
