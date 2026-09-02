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


def clean_poke_api_name(name: str) -> str:
    """Limpia caracteres especiales para generar slugs válidos de PokeAPI."""
    s = name.lower().strip()
    s = s.replace("farfetch'd", "farfetchd").replace("sirfetch'd", "sirfetchd")
    s = s.replace("mr. mime", "mr-mime").replace("mime jr.", "mime-jr").replace("mr. rime", "mr-rime")
    s = s.replace("type: null", "type-null").replace("tapu ", "tapu-")
    s = s.replace("é", "e").replace("'", "").replace(" ", "-")
    return s


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
            abilities = [a["ability"]["name"].replace("-", " ").capitalize() for a in data.get("abilities", [])]
            stats = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}

            # Asignar HABILIDAD FIJA aleatoria entre sus habilidades disponibles
            assigned_ability = random.choice(abilities) if abilities else "Desconocida"

            highest_stat_name = max(stats, key=stats.get) if stats else "hp"
            highest_stat_val = stats.get(highest_stat_name, 50)

            sprites = data.get("sprites", {})
            image_url = (
                sprites.get("other", {}).get("official-artwork", {}).get("front_default")
                or sprites.get("front_default")
                or ""
            )

            level_up_moves = extract_level_up_moves(data.get("moves", []))
            if not level_up_moves:
                level_up_moves = [
                    {"name": "Tackle", "level": 1},
                    {"name": "Quick Attack", "level": 5},
                    {"name": "Thunderbolt", "level": 15},
                    {"name": "Iron Tail", "level": 20}
                ]

            res = {
                "id": poke_id,
                "name": name,
                "region": get_region_by_id(poke_id),
                "types": types,
                "primary_type": types[0] if types else "Normal",
                "abilities": abilities,
                "ability": assigned_ability,  # Habilidad Fija asignada en subasta
                "stats": stats,
                "highest_stat": f"{highest_stat_name.upper()} ({highest_stat_val})",
                "image_url": image_url,
                "level": level_cap,
                "level_up_moves": level_up_moves,
                "selected_moves": [m["name"] for m in level_up_moves if m["level"] <= level_cap][-4:]
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
        res = {
            "id": random.randint(1, 151),
            "name": name_clean,
            "region": "Kanto",
            "types": ["Normal"],
            "primary_type": "Normal",
            "abilities": ["Overgrow", "Chlorophyll"],
            "ability": random.choice(["Overgrow", "Chlorophyll"]),
            "stats": {"hp": 60, "attack": 75, "defense": 70, "speed": 80},
            "highest_stat": "ATTACK (75)",
            "image_url": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png",
            "level": level_cap,
            "level_up_moves": default_moves,
            "selected_moves": [m["name"] for m in default_moves if m["level"] <= level_cap][-4:]
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
      - 1.5x: Primera letra del nombre
      - 2.0x: Región de origen
      - 2.5x: Habilidad asignada
      - 3.0x: Tipo primario
      - 3.5x: Estadística base más alta
    """
    hints = {}
    name = poke_data.get("name", "???")

    if multiplier >= 1:
        hints["first_letter"] = name[0].upper() if name else "?"

    if multiplier >= 1.5:
        hints["region"] = poke_data.get("region", "Desconocida")

    if multiplier >= 2:
        hints["ability"] = poke_data.get("ability", "Desconocida")

    if multiplier >= 3:
        hints["primary_type"] = poke_data.get("primary_type", "Normal")

    if multiplier >= 5:
        hints["highest_stat"] = poke_data.get("highest_stat", "HP (50)")

    return hints
