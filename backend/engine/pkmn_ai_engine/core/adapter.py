"""
backend/engine/pkmn_ai_engine/core/adapter.py
Adaptador para transformar cualquier formato de Pokémon de Draft-Prime / Subasta
en un PokemonState oficial y totalmente jugable en el motor de combate.
"""

import math
from typing import Dict, Any, List, Optional
from .models import PokemonState, StatBlock, StatBoosts, MoveState
from .moves_db import resolve_move
from .megas import check_can_mega, MEGA_DATABASE

DEFAULT_TYPE_MOVES: Dict[str, List[str]] = {
    "Fire": ["Flamethrower", "Fire Blast", "Will-O-Wisp", "Protect"],
    "Water": ["Scald", "Hydro Pump", "Ice Beam", "Protect"],
    "Grass": ["Giga Drain", "Energy Ball", "Toxic", "Synthesis"],
    "Electric": ["Thunderbolt", "Volt Switch", "Thunder Wave", "Protect"],
    "Psychic": ["Psychic", "Psyshock", "Calm Mind", "Recover"],
    "Dragon": ["Draco Meteor", "Dragon Pulse", "Dragon Dance", "Earthquake"],
    "Ghost": ["Shadow Ball", "Will-O-Wisp", "Shadow Sneak", "Protect"],
    "Dark": ["Dark Pulse", "Knock Off", "Sucker Punch", "Taunt"],
    "Steel": ["Flash Cannon", "Iron Head", "Stealth Rock", "Roost"],
    "Fighting": ["Close Combat", "Drain Punch", "Mach Punch", "Swords Dance"],
    "Ground": ["Earthquake", "Earth Power", "Bulldoze", "Protect"],
    "Rock": ["Stone Edge", "Rock Slide", "Stealth Rock", "Earthquake"],
    "Flying": ["Air Slash", "Brave Bird", "Roost", "Protect"],
    "Ice": ["Ice Beam", "Blizzard", "Ice Shard", "Protect"],
    "Bug": ["Bug Buzz", "U-turn", "X-Scissor", "Roost"],
    "Poison": ["Sludge Bomb", "Poison Jab", "Toxic", "Protect"],
    "Fairy": ["Moonblast", "Dazzling Gleam", "Play Rough", "Protect"],
    "Normal": ["Body Slam", "Quick Attack", "Swords Dance", "Protect"],
}


def normalize_stats(raw_stats: Any, level: int = 50) -> tuple[StatBlock, int]:
    """
    Normaliza estadísticas desde PokeAPI (nombres largos como special-attack)
    o formato abreviado (spa, spd). Calcula HP real para el nivel.
    Devuelve (StatBlock, max_hp_calculado).
    """
    if not isinstance(raw_stats, dict):
        base_hp, base_atk, base_def, base_spa, base_spd, base_spe = 80, 80, 80, 80, 80, 80
    else:
        base_hp = int(raw_stats.get("hp", 80))
        base_atk = int(raw_stats.get("attack", raw_stats.get("atk", 80)))
        base_def = int(raw_stats.get("defense", raw_stats.get("def", raw_stats.get("def_", 80))))
        base_spa = int(raw_stats.get("special-attack", raw_stats.get("spa", 80)))
        base_spd = int(raw_stats.get("special-defense", raw_stats.get("spd", 80)))
        base_spe = int(raw_stats.get("speed", raw_stats.get("spe", 80)))

    # Fórmula oficial de estadísticas de Pokémon a nivel L con IVs neutros (15) y sin EVs
    # HP = floor(((2 * Base + 31) * Level) / 100) + Level + 10
    max_hp = math.floor(((2 * base_hp + 31) * level) / 100.0) + level + 10
    calc_atk = math.floor(((2 * base_atk + 31) * level) / 100.0) + 5
    calc_def = math.floor(((2 * base_def + 31) * level) / 100.0) + 5
    calc_spa = math.floor(((2 * base_spa + 31) * level) / 100.0) + 5
    calc_spd = math.floor(((2 * base_spd + 31) * level) / 100.0) + 5
    calc_spe = math.floor(((2 * base_spe + 31) * level) / 100.0) + 5

    return StatBlock(
        hp=max_hp,
        atk=calc_atk,
        def_=calc_def,
        spa=calc_spa,
        spd=calc_spd,
        spe=calc_spe,
    ), max_hp


def adapt_draft_pokemon(data: Dict[str, Any]) -> PokemonState:
    """
    Convierte un Pokémon de la subasta draft en un PokemonState listo para combate PVE.
    Garantiza que siempre tenga 4 movimientos con poder y stats coherentes.
    """
    raw_name = data.get("name") or data.get("species") or "Pikachu"
    species = str(raw_name).strip()
    slug = species.lower().replace(" ", "-")

    level = int(data.get("level", 50))

    # 1. Normalizar tipos
    raw_types = data.get("types") or [data.get("primary_type", "Normal")]
    if isinstance(raw_types, str):
        types_list = [raw_types]
    elif isinstance(raw_types, list):
        types_list = [t.capitalize() for t in raw_types if t]
    else:
        types_list = ["Normal"]

    if not types_list:
        types_list = ["Normal"]
    primary_type = types_list[0]

    # 2. Normalizar estadísticas y HP
    stat_block, calculated_hp = normalize_stats(data.get("stats"), level=level)
    max_hp = int(data.get("max_hp", calculated_hp))
    current_hp = int(data.get("current_hp", max_hp))

    # 3. Normalizar Movimientos (selected_moves de la subasta)
    raw_moves = data.get("selected_moves") or data.get("moves") or []
    if not raw_moves:
        raw_moves = DEFAULT_TYPE_MOVES.get(primary_type, DEFAULT_TYPE_MOVES["Normal"])

    resolved_moves: List[MoveState] = []
    for rm in raw_moves[:4]:
        resolved_moves.append(resolve_move(rm, fallback_type=primary_type))

    # Rellenar hasta 4 si tuviera menos
    while len(resolved_moves) < 4:
        defaults = DEFAULT_TYPE_MOVES.get(primary_type, DEFAULT_TYPE_MOVES["Normal"])
        missing_move = defaults[len(resolved_moves) % len(defaults)]
        resolved_moves.append(resolve_move(missing_move, fallback_type=primary_type))

    # 4. Normalizar Ítem y Megaevolución
    item = data.get("item") or data.get("held_item")
    is_mega = bool(data.get("is_mega", False))
    can_mega = bool(data.get("can_mega", False))
    mega_stone = data.get("mega_stone")

    # Detección inteligente de Mega Piedra
    if item and "ite" in str(item).lower():
        mega_stone = str(item)
        can_mega = True

    # 5. Imagen / Sprite oficial
    # Si viene con image_url de la subasta, usarlo directamente
    image_url = data.get("image_url") or data.get("sprite")
    if not image_url:
        clean_slug = slug.replace("mega-", "").replace("-mega", "").replace("-x", "").replace("-y", "")
        # URL oficial y confiable de Showdown gen5 sprite
        image_url = f"https://play.pokemonshowdown.com/sprites/gen5/{clean_slug}.png"

    poke_id = str(data.get("id") or f"{slug}-{data.get('acquisition_year', 1)}")

    return PokemonState(
        id=poke_id,
        species=species,
        types=tuple(types_list),
        level=level,
        current_hp=current_hp,
        max_hp=max_hp,
        stats=stat_block,
        boosts=StatBoosts.from_dict(data.get("boosts")),
        status=data.get("status"),
        item=item,
        ability=data.get("ability", "Static"),
        moves=resolved_moves,
        is_fainted=data.get("is_fainted", current_hp <= 0),
        is_mega=is_mega,
        can_mega=can_mega,
        mega_stone=mega_stone,
        image_url=image_url,
    )
