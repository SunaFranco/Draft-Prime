"""
backend/modes/subasta_pokemon/poke_api.py - Integración con PokeAPI y sistema de pistas por subasta
"""

import json
import random
import ssl
import urllib.parse
import urllib.request
from typing import Dict, List, Any, Optional

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon"
POKE_CACHE: Dict[str, dict] = {}

POKEMON_NATURES = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
]

TM_MOVES = {
    "MT Earthquake": "Earthquake",
    "MT Ice Beam": "Ice Beam",
    "MT Flamethrower": "Flamethrower",
    "MT Thunderbolt": "Thunderbolt",
    "MT Psychic": "Psychic",
    "MT Shadow Ball": "Shadow Ball",
    "MT Protect": "Protect",
    "MT Substitute": "Substitute",
    "MT Swords Dance": "Swords Dance",
    "MT Calm Mind": "Calm Mind",
}

# Muestras base por Tiers para garantizar funcionamiento rápido y offline si la API no responde
SAMPLE_POKEMON_POOLS = {
    "normal": [
        "pikachu", "charizard", "blastoise", "venusaur", "gengar", "lucario", "gardevoir",
        "snorlax", "dragonite", "gyarados", "arcanine", "machamp", "scizor",
        "tyranitar", "salamence", "metagross", "garchomp", "volcarona", "greninja"
    ],
    "mega": [
        "charizard-mega-x", "charizard-mega-y", "mewtwo-mega-x", "gengar-mega",
        "lucario-mega", "gardevoir-mega", "garchomp-mega", "metagross-mega", "rayquaza-mega"
    ],
    "legendary": [
        "mewtwo", "mew", "lugia", "ho-oh", "kyogre", "groudon", "rayquaza",
        "dialga", "palkia", "giratina", "arceus", "reshiram", "zekrom", "kyurem"
    ]
}

# Mapeo aproximado de regiones por ID nacional de Pokémon
def get_region_by_id(poke_id: int) -> str:
    if 1 <= poke_id <= 151:
        return "Kanto"
    elif 152 <= poke_id <= 251:
        return "Johto"
    elif 252 <= poke_id <= 386:
        return "Hoenn"
    elif 387 <= poke_id <= 493:
        return "Sinnoh"
    elif 494 <= poke_id <= 649:
        return "Unova"
    elif 650 <= poke_id <= 721:
        return "Kalos"
    elif 722 <= poke_id <= 809:
        return "Alola"
    elif 810 <= poke_id <= 905:
        return "Galar"
    return "Paldea / Desconocida"


def extract_level_up_moves(moves_data: List[dict]) -> List[dict]:
    """Extrae únicamente los movimientos aprendidos por nivel (level-up)."""
    level_moves = []
    seen = set()

    for m in moves_data:
        move_name = m.get("move", {}).get("name", "").replace("-", " ").title()
        if not move_name:
            continue

        for detail in m.get("version_group_details", []):
            method = detail.get("move_learn_method", {}).get("name")
            level = detail.get("level_learned_at", 1)
            if method == "level-up" and move_name not in seen:
                seen.add(move_name)
                level_moves.append({"name": move_name, "level": level})

    level_moves.sort(key=lambda x: x["level"])
    return level_moves


def extract_tm_moves(moves_data: List[dict]) -> List[str]:
    """Extrae los movimientos que el Pokémon puede aprender mediante MT."""
    tm_moves = []
    seen = set()
    for move_data in moves_data:
        move_name = move_data.get("move", {}).get("name", "").replace("-", " ").title()
        if not move_name or move_name in seen:
            continue
        if any(detail.get("move_learn_method", {}).get("name") == "machine" for detail in move_data.get("version_group_details", [])):
            seen.add(move_name)
            tm_moves.append(move_name)
    return tm_moves


def clean_poke_api_name(name: str) -> str:
    """Limpia caracteres especiales para generar slugs válidos de PokeAPI."""
    s = name.lower().strip()
    s = s.replace("farfetch'd", "farfetchd").replace("sirfetch'd", "sirfetchd")
    s = s.replace("mr. mime", "mr-mime").replace("mime jr.", "mime-jr").replace("mr. rime", "mr-rime")
    s = s.replace("type: null", "type-null").replace("tapu ", "tapu-")
    s = s.replace("é", "e").replace("'", "").replace(" ", "-")
    return s


def get_pokemon_evolution_details(name_or_id: str, max_level: int = 40) -> Optional[dict]:
    """Devuelve objetivo y condiciones de la siguiente evolución aplicable."""
    try:
        slug = clean_poke_api_name(name_or_id)
        species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(slug)}"
        req = urllib.request.Request(species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=5) as resp:
            species = json.loads(resp.read().decode())
        chain_url = species.get("evolution_chain", {}).get("url")
        if not chain_url:
            return None

        chain_req = urllib.request.Request(chain_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(chain_req, context=ssl.create_default_context(), timeout=5) as chain_resp:
            evo_data = json.loads(chain_resp.read().decode())

        current = evo_data.get("chain")
        current_name = current.get("species", {}).get("name", "") if current else ""
        if not current_name:
            return None

        while current:
            species_name = current.get("species", {}).get("name", "")
            if species_name and clean_poke_api_name(species_name) == slug:
                candidates = current.get("evolves_to", [])
                for candidate in candidates:
                    details = (candidate.get("evolution_details") or [{}])[0]
                    trigger = (details.get("trigger") or {}).get("name")
                    min_level = details.get("min_level")
                    item = details.get("item") or details.get("held_item") or {}
                    item_name = item.get("name") if trigger == "use-item" else None
                    if trigger == "level-up" and item_name is None and min_level is not None and int(min_level) > int(max_level):
                        continue
                    if trigger in ("level-up", "use-item", "trade"):
                        return {
                            "target": candidate.get("species", {}).get("name"),
                            "level": int(min_level) if min_level is not None else None,
                            "item": item_name.replace("-", " ").title() if item_name else None,
                            "trade": trigger == "trade",
                        }
                break
            if current.get("evolves_to"):
                current = current["evolves_to"][0]
            else:
                break
        return None
    except Exception:
        return None


def get_pokemon_evolution_target(name_or_id: str, max_level: int = 40) -> Optional[str]:
    details = get_pokemon_evolution_details(name_or_id, max_level)
    return details.get("target") if details else None


def get_pokemon_next_evolution_level(name_or_id: str) -> Optional[int]:
    """Devuelve el nivel mínimo de la siguiente evolución por level-up del Pokémon."""
    try:
        slug = clean_poke_api_name(name_or_id)
        species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(slug)}"
        req = urllib.request.Request(species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=5) as resp:
            species = json.loads(resp.read().decode())
        chain_url = species.get("evolution_chain", {}).get("url")
        if not chain_url:
            return None

        chain_req = urllib.request.Request(chain_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(chain_req, context=ssl.create_default_context(), timeout=5) as chain_resp:
            evo_data = json.loads(chain_resp.read().decode())

        current = evo_data.get("chain")
        while current:
            species_name = current.get("species", {}).get("name", "")
            if species_name and clean_poke_api_name(species_name) == slug:
                candidates = current.get("evolves_to", [])
                for candidate in candidates:
                    details = (candidate.get("evolution_details") or [{}])[0]
                    trigger = (details.get("trigger") or {}).get("name")
                    min_level = details.get("min_level")
                    if trigger == "level-up":
                        return int(min_level) if min_level is not None else None
                return None
            if current.get("evolves_to"):
                current = current["evolves_to"][0]
            else:
                return None
        return None
    except Exception:
        return None


def fetch_pokemon_data(name_or_id: str, level_cap: int = 20) -> dict:
    """Consulta datos de Pokémon desde PokeAPI con fallback en caso de error/offline."""
    key = str(name_or_id).lower().strip()
    api_slug = clean_poke_api_name(name_or_id)
    cache_key = f"{key}_{level_cap}"
    if cache_key in POKE_CACHE:
        return POKE_CACHE[cache_key].copy()

    url = f"{POKEAPI_BASE_URL}/{urllib.parse.quote(api_slug)}"
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            poke_id = data.get("id", 1)
            name = str(name_or_id).capitalize()
            types = [t["type"]["name"].capitalize() for t in data.get("types", [])]
            ability_entries = data.get("abilities", [])
            abilities = [a["ability"]["name"].replace("-", " ").capitalize() for a in ability_entries]
            ability_slots = [a.get("slot") for a in ability_entries]
            stats = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}

            # Asignar HABILIDAD FIJA aleatoria entre sus habilidades disponibles
            assigned_index = random.randrange(len(ability_entries)) if ability_entries else None
            assigned_ability = abilities[assigned_index] if assigned_index is not None else "Desconocida"
            ability_slot = ability_entries[assigned_index].get("slot") if assigned_index is not None else None
            assigned_nature = random.choice(POKEMON_NATURES)

            highest_stat_name = max(stats, key=stats.get) if stats else "hp"
            highest_stat_val = stats.get(highest_stat_name, 50)

            sprites = data.get("sprites", {})
            other_sprites = sprites.get("other", {})
            image_url = (
                other_sprites.get("official-artwork", {}).get("front_default")
                or other_sprites.get("dream_world", {}).get("front_default")
                or sprites.get("front_default")
                or ""
            )
            shiny_image_url = (
                other_sprites.get("official-artwork", {}).get("front_shiny")
                or sprites.get("front_shiny")
                or ""
            )

            level_up_moves = extract_level_up_moves(data.get("moves", []))
            tm_moves = extract_tm_moves(data.get("moves", []))
            if not level_up_moves:
                level_up_moves = [
                    {"name": "Tackle", "level": 1},
                    {"name": "Quick Attack", "level": 5},
                    {"name": "Thunderbolt", "level": 15},
                    {"name": "Iron Tail", "level": 20}
                ]

            evolution_details = get_pokemon_evolution_details(name, max_level=level_cap)
            next_evolution = evolution_details.get("target") if evolution_details else None
            next_evolution_level = evolution_details.get("level") if evolution_details else None
            res = {
                "id": poke_id,
                "name": name,
                "region": get_region_by_id(poke_id),
                "types": types,
                "primary_type": types[0] if types else "Normal",
                "abilities": abilities,
                "ability_slots": ability_slots,
                "ability": assigned_ability,  # Habilidad Fija asignada en subasta
                "ability_slot": ability_slot,
                "nature": assigned_nature,
                "stats": stats,
                "highest_stat": f"{highest_stat_name.upper()} ({highest_stat_val})",
                "image_url": image_url,
                "shiny_image_url": shiny_image_url,
                "level": level_cap,
                "level_up_moves": level_up_moves,
                "tm_moves": tm_moves,
                "selected_moves": [m["name"] for m in level_up_moves if m["level"] <= level_cap][-4:],
                "can_evolve": bool(next_evolution),
                "evolution_target": next_evolution,
                "next_evolution_level": next_evolution_level,
                "evolution_item": evolution_details.get("item") if evolution_details else None,
                "evolution_trade": bool(evolution_details and evolution_details.get("trade")),
            }
            POKE_CACHE[cache_key] = res
            return res.copy()
    except Exception as e:
        print(f"[WARNING] No se pudo cargar '{name_or_id}' ({api_slug}) desde PokeAPI ({e}). Usando fallback local.")
        # Fallback local
        name_clean = str(name_or_id).capitalize()
        default_moves = [
            {"name": "Tackle", "level": 1},
            {"name": "Quick Attack", "level": 5},
            {"name": "Bite", "level": 12},
            {"name": "Body Slam", "level": 20},
            {"name": "Hyper Beam", "level": 40}
        ]
        evolution_details = get_pokemon_evolution_details(name_clean, max_level=level_cap)
        next_evolution = evolution_details.get("target") if evolution_details else None
        next_evolution_level = evolution_details.get("level") if evolution_details else None
        fallback_abilities = ["Overgrow", "Chlorophyll"]
        fallback_ability_index = random.randrange(len(fallback_abilities))
        res = {
            "id": random.randint(1, 151),
            "name": name_clean,
            "region": "Kanto",
            "types": ["Normal"],
            "primary_type": "Normal",
            "abilities": fallback_abilities,
            "ability": fallback_abilities[fallback_ability_index],
            "ability_slots": [1, 3],
            "ability_slot": [1, 3][fallback_ability_index],
            "nature": random.choice(POKEMON_NATURES),
            "stats": {"hp": 60, "attack": 75, "defense": 70, "speed": 80},
            "highest_stat": "ATTACK (75)",
            "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png",
            "shiny_image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/25.png",
            "level": level_cap,
            "level_up_moves": default_moves,
            "tm_moves": [],
            "selected_moves": [m["name"] for m in default_moves if m["level"] <= level_cap][-4:],
            "can_evolve": bool(next_evolution),
            "evolution_target": next_evolution,
            "next_evolution_level": next_evolution_level,
            "evolution_item": evolution_details.get("item") if evolution_details else None,
            "evolution_trade": bool(evolution_details and evolution_details.get("trade")),
        }
        POKE_CACHE[cache_key] = res
        return res.copy()


def get_random_pokemon_from_tier(tier: str = "normal", year: Optional[int] = None, level_cap: int = 20) -> dict:
    """Devuelve un Pokémon aleatorio desde la base de datos o desde el pool estático."""
    from backend import database
    db_pool = database.get_pokemon_pools_from_db(year=year, auction_type=tier)

    if db_pool:
        print(f"[OK] [DATABASE] Se cargaron {len(db_pool)} Pokémon desde Supabase (Año {year}, Tipo '{tier}').")
        chosen_name = random.choice(db_pool)
    else:
        print(f"[INFO] [LOCAL] Usando pool estático por defecto (Año {year}, Tipo '{tier}').")
        pool = SAMPLE_POKEMON_POOLS.get(tier.lower(), SAMPLE_POKEMON_POOLS["normal"])
        chosen_name = random.choice(pool)

    return fetch_pokemon_data(chosen_name, level_cap=level_cap)



def get_hints_for_multiplier(poke_data: dict, multiplier: float) -> dict:
    """
    Retorna un diccionario de pistas acumulativas en función del multiplicador del precio inicial:
      - 1.0x: Primera letra del nombre
      - 2.0x: Región de origen
      - 3.0x: Habilidad asignada
      - 5.0x: Tipo primario
      - 8.0x: Estadística base más alta
    """
    hints = {}
    name = poke_data.get("name", "???")

    if multiplier >= 1.0:
        hints["first_letter"] = name[0].upper() if name else "?"

    if multiplier >= 2.0:
        hints["region"] = poke_data.get("region", "Desconocida")

    if multiplier >= 3.0:
        hints["ability"] = poke_data.get("ability", "Desconocida")

    if multiplier >= 5.0:
        hints["primary_type"] = poke_data.get("primary_type", "Normal")

    if multiplier >= 8.0:
        hints["highest_stat"] = poke_data.get("highest_stat", "HP (50)")

    return hints
