"""
backend/modes/subasta_pokemon/poke_api.py - Integración con PokeAPI y sistema de pistas por subasta
"""

import json
import random
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Dict, List, Any, Optional

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon"
MAX_POKE_CACHE = 150
POKE_CACHE: OrderedDict[str, dict] = OrderedDict()

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
    "MT Surf": "Surf",
    "MT Dragon Claw": "Dragon Claw",
    "MT Stone Edge": "Stone Edge",
    "MT U-turn": "U Turn",
    "MT Volt Switch": "Volt Switch",
    "MT Stealth Rock": "Stealth Rock",
    "MT Spikes": "Spikes",
    "MT Toxic": "Toxic",
    "MT Roost": "Roost",
    "MT Iron Head": "Iron Head",
    "MT Close Combat": "Close Combat",
    "MT Dazzling Gleam": "Dazzling Gleam",
    "MT Energy Ball": "Energy Ball",
    "MT Dark Pulse": "Dark Pulse",
    "MT Sludge Bomb": "Sludge Bomb",
    "MT Focus Blast": "Focus Blast",
    "MT Thunder Wave": "Thunder Wave",
    "MT Will-O-Wisp": "Will O Wisp",
    "MT Taunt": "Taunt",
    "MT Trick Room": "Trick Room",
    "MT Giga Drain": "Giga Drain",
    "MT Brick Break": "Brick Break",
    "MT Knock Off": "Knock Off",
    "MT Ice Spinner": "Ice Spinner",
}

# Mapeo completo de Pokémon Mega / Primigenios a su especie base y Mega Piedra / Objeto
MEGA_DATA = {
    "venusaur-mega": ("Venusaur", "Venusaurite"),
    "charizard-mega-x": ("Charizard", "Charizardite X"),
    "charizard-mega-y": ("Charizard", "Charizardite Y"),
    "blastoise-mega": ("Blastoise", "Blastoisinite"),
    "beedrill-mega": ("Beedrill", "Beedrillite"),
    "pidgeot-mega": ("Pidgeot", "Pidgeotite"),
    "alakazam-mega": ("Alakazam", "Alakazite"),
    "slowbro-mega": ("Slowbro", "Slowbronite"),
    "gengar-mega": ("Gengar", "Gengarite"),
    "kangaskhan-mega": ("Kangaskhan", "Kangaskhanite"),
    "pinsir-mega": ("Pinsir", "Pinsirite"),
    "gyarados-mega": ("Gyarados", "Gyaradosite"),
    "aerodactyl-mega": ("Aerodactyl", "Aerodactylite"),
    "mewtwo-mega-x": ("Mewtwo", "Mewtwonite X"),
    "mewtwo-mega-y": ("Mewtwo", "Mewtwonite Y"),
    "ampharos-mega": ("Ampharos", "Ampharosite"),
    "steelix-mega": ("Steelix", "Steelixite"),
    "scizor-mega": ("Scizor", "Scizorite"),
    "heracross-mega": ("Heracross", "Heracronite"),
    "houndoom-mega": ("Houndoom", "Houndoominite"),
    "tyranitar-mega": ("Tyranitar", "Tyranitarite"),
    "sceptile-mega": ("Sceptile", "Sceptilite"),
    "blaziken-mega": ("Blaziken", "Blazikenite"),
    "swampert-mega": ("Swampert", "Swampertite"),
    "gardevoir-mega": ("Gardevoir", "Gardevoirite"),
    "sableye-mega": ("Sableye", "Sablenite"),
    "mawile-mega": ("Mawile", "Mawilite"),
    "aggron-mega": ("Aggron", "Aggronite"),
    "medicham-mega": ("Medicham", "Medichamite"),
    "manectric-mega": ("Manectric", "Manectite"),
    "sharpedo-mega": ("Sharpedo", "Sharpedonite"),
    "camerupt-mega": ("Camerupt", "Cameruptite"),
    "altaria-mega": ("Altaria", "Altarianite"),
    "banette-mega": ("Banette", "Banettite"),
    "absol-mega": ("Absol", "Absolite"),
    "glalie-mega": ("Glalie", "Glalitite"),
    "salamence-mega": ("Salamence", "Salamencite"),
    "metagross-mega": ("Metagross", "Metagrossite"),
    "latias-mega": ("Latias", "Latiasite"),
    "latios-mega": ("Latios", "Latiosite"),
    "kyogre-primal": ("Kyogre", "Blue Orb"),
    "groudon-primal": ("Groudon", "Red Orb"),
    "rayquaza-mega": ("Rayquaza", "Life Orb"),
    "lopunny-mega": ("Lopunny", "Lopunnite"),
    "garchomp-mega": ("Garchomp", "Garchompite"),
    "lucario-mega": ("Lucario", "Lucarionite"),
    "abomasnow-mega": ("Abomasnow", "Abomasite"),
    "gallade-mega": ("Gallade", "Galladite"),
    "audino-mega": ("Audino", "Audinite"),
    "diancie-mega": ("Diancie", "Diancite"),
}


def normalize_mega_slug(name: str) -> str:
    import re
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(name).strip().lower()).strip('-')
    if slug.startswith("mega-"):
        parts = slug.split("-")
        if len(parts) == 2:
            slug = f"{parts[1]}-mega"
        elif len(parts) >= 3:
            slug = f"{parts[1]}-mega-{'-'.join(parts[2:])}"
    elif slug.startswith("primal-"):
        parts = slug.split("-")
        if len(parts) >= 2:
            slug = f"{parts[1]}-primal"
    return slug


def get_mega_info(poke_or_name: Any) -> Optional[Dict[str, Any]]:
    if not poke_or_name:
        return None
    if isinstance(poke_or_name, dict):
        if poke_or_name.get("is_mega") and poke_or_name.get("base_species") and poke_or_name.get("mega_stone"):
            return {
                "is_mega": True,
                "base_name": poke_or_name["base_species"],
                "mega_stone": poke_or_name["mega_stone"]
            }
        name = poke_or_name.get("name", "")
    else:
        name = str(poke_or_name or "")

    slug = normalize_mega_slug(name)
    if slug in MEGA_DATA:
        base_name, stone = MEGA_DATA[slug]
        return {
            "is_mega": True,
            "base_name": base_name,
            "mega_stone": stone
        }

    if "-mega" in slug or "mega-" in slug:
        clean_base = slug.replace("-mega", "").replace("mega-", "").replace("-", " ").title()
        return {
            "is_mega": True,
            "base_name": clean_base,
            "mega_stone": f"{clean_base}ite"
        }

    return None


def is_mega_pokemon(poke_or_name: Any) -> bool:
    return get_mega_info(poke_or_name) is not None


def find_chain_node(chain_node: Optional[dict], target_slug: str) -> Optional[dict]:
    if not chain_node:
        return None
    sp_name = clean_poke_api_name((chain_node.get("species") or {}).get("name", ""))
    if sp_name == target_slug:
        return chain_node
    for child in chain_node.get("evolves_to", []):
        res = find_chain_node(child, target_slug)
        if res:
            return res
    return None


def get_pokemon_regional_form_options(poke_or_name: Any) -> List[Dict[str, str]]:
    """Devuelve las formas disponibles para un Pokémon (incluyendo la normal y variantes regionales), excluyendo la forma actual."""
    import re
    if isinstance(poke_or_name, dict):
        raw_name = poke_or_name.get("name") or ""
        base_name = poke_or_name.get("base_species") or raw_name
    else:
        raw_name = str(poke_or_name or "")
        base_name = raw_name

    raw_slug = clean_poke_api_name(raw_name)
    base_slug = clean_poke_api_name(base_name)
    current_form_slug = raw_slug or base_slug
    if not current_form_slug:
        return []

    reg_match = re.match(r'^(.*?)-(alola|galar|hisui|paldea|paldean)$', current_form_slug)
    if reg_match:
        species_slug = reg_match.group(1)
    else:
        base_reg_match = re.match(r'^(.*?)-(alola|galar|hisui|paldea|paldean)$', base_slug)
        species_slug = base_reg_match.group(1) if base_reg_match else base_slug

    species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(species_slug)}"

    try:
        req = urllib.request.Request(species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=5) as resp:
                species = json.loads(resp.read().decode())
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            pokemon_url = f"{POKEAPI_BASE_URL}/{urllib.parse.quote(current_form_slug)}"
            pokemon_req = urllib.request.Request(pokemon_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
            with urllib.request.urlopen(pokemon_req, context=ssl.create_default_context(), timeout=5) as resp:
                pokemon_data = json.loads(resp.read().decode())
            species_slug = (pokemon_data.get("species") or {}).get("name") or species_slug
            species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(species_slug)}"
            species_req = urllib.request.Request(species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
            with urllib.request.urlopen(species_req, context=ssl.create_default_context(), timeout=5) as resp:
                species = json.loads(resp.read().decode())

        options: List[Dict[str, str]] = []
        seen = set()
        base_title = species_slug.replace("-", " ").title()

        for variety in species.get("varieties", []):
            variant_name = (variety.get("pokemon", {}) or {}).get("name", "")
            if not variant_name:
                continue

            variant_key = variant_name.lower()
            if variant_key == current_form_slug.lower():
                continue

            if variant_key == species_slug.lower():
                # Forma Normal disponible si actualmente se tiene una forma regional
                if variant_key not in seen:
                    seen.add(variant_key)
                    options.append({
                        "target_name": variant_name,
                        "display_name": f"{base_title} (Normal)",
                        "form_name": "normal",
                        "slug": variant_name,
                    })
                continue

            form_name = None
            if "-" in variant_key:
                form_name = variant_key.rsplit("-", 1)[1]
            if form_name not in {"alola", "galar", "hisui", "paldea", "paldean"}:
                continue

            if variant_key in seen:
                continue
            seen.add(variant_key)
            options.append({
                "target_name": variant_name,
                "display_name": f"{base_title} {form_name.capitalize()}",
                "form_name": form_name,
                "slug": variant_name,
            })
        return options
    except Exception:
        return []


def apply_regional_form(poke: Dict[str, Any], target_name: str) -> bool:
    """Cambia la forma de un Pokémon (regional o normal) conservando datos del jugador."""
    if not poke or not target_name:
        return False

    target_key = clean_poke_api_name(target_name)
    current_key = clean_poke_api_name(poke.get("name") or poke.get("base_species") or "")
    if not target_key or target_key == current_key:
        return False

    level = int(poke.get("level", 20))
    try:
        updated = fetch_pokemon_data(target_key, level_cap=level)
    except Exception:
        return False

    current_item = poke.get("item") or poke.get("held_item")
    current_nature = poke.get("nature")
    current_slot = poke.get("ability_slot", 1)
    is_shiny = bool(poke.get("is_shiny"))
    received_by_trade = bool(poke.get("received_by_trade"))
    is_hidden = bool(poke.get("is_hidden"))
    selected_moves = poke.get("selected_moves", [])
    learned_tm_moves = poke.get("learned_tm_moves", [])

    new_abilities = updated.get("abilities", [])
    new_slots = updated.get("ability_slots", [])
    if current_slot in new_slots:
        slot_idx = new_slots.index(current_slot)
        assigned_ability = new_abilities[slot_idx] if slot_idx < len(new_abilities) else (new_abilities[0] if new_abilities else "Desconocida")
        assigned_slot = current_slot
    else:
        assigned_ability = updated.get("ability") or (new_abilities[0] if new_abilities else "Desconocida")
        assigned_slot = updated.get("ability_slot") or 1

    updated["level"] = level
    updated["is_shiny"] = is_shiny
    if is_shiny and updated.get("shiny_image_url"):
        updated["image_url"] = updated["shiny_image_url"]
    updated["nature"] = current_nature or updated.get("nature", "Hardy")
    updated["ability"] = assigned_ability
    updated["ability_slot"] = assigned_slot
    updated["item"] = current_item
    updated["held_item"] = current_item
    updated["received_by_trade"] = received_by_trade
    updated["is_hidden"] = is_hidden
    updated["learned_tm_moves"] = learned_tm_moves

    new_valid_moves = [m["name"] for m in updated.get("level_up_moves", []) if m.get("level", 0) <= level] + learned_tm_moves
    valid_selected = [m for m in selected_moves if m in new_valid_moves]
    if len(valid_selected) == 4:
        updated["selected_moves"] = valid_selected
    else:
        updated["selected_moves"] = [m["name"] for m in updated.get("level_up_moves", []) if m.get("level", 0) <= level][-4:]

    updated["base_species"] = updated.get("base_species") or updated.get("name") or target_name
    updated["regional_form"] = target_name
    updated["regional_form_options"] = get_pokemon_regional_form_options(updated)
    poke.clear()
    poke.update(updated)
    return True


# Muestras base por Tiers para garantizar funcionamiento rápido y offline si la API no responde
SAMPLE_POKEMON_POOLS = {
    "normal": [
        "pikachu", "charizard", "blastoise", "venusaur", "gengar", "lucario", "gardevoir",
        "snorlax", "dragonite", "gyarados", "arcanine", "machamp", "scizor",
        "tyranitar", "salamence", "metagross", "garchomp", "volcarona", "greninja"
    ],
    "mega": [
        "venusaur-mega", "charizard-mega-x", "charizard-mega-y", "blastoise-mega",
        "beedrill-mega", "pidgeot-mega", "alakazam-mega", "slowbro-mega",
        "gengar-mega", "kangaskhan-mega", "pinsir-mega", "gyarados-mega",
        "aerodactyl-mega", "ampharos-mega", "steelix-mega", "scizor-mega",
        "heracross-mega", "houndoom-mega", "tyranitar-mega", "sceptile-mega",
        "blaziken-mega", "swampert-mega", "gardevoir-mega", "sableye-mega",
        "mawile-mega", "aggron-mega", "medicham-mega", "manectric-mega",
        "sharpedo-mega", "camerupt-mega", "altaria-mega", "banette-mega",
        "absol-mega", "glalie-mega", "salamence-mega", "metagross-mega",
        "lopunny-mega", "garchomp-mega", "lucario-mega", "abomasnow-mega",
        "gallade-mega", "audino-mega"
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


def get_pokemon_all_evolution_options(name_or_id: str, max_level: int = 100) -> list:
    """Devuelve todas las opciones de evolución aplicables para el Pokémon, deduplicadas."""
    import re
    options = []
    seen = set()
    try:
        slug = clean_poke_api_name(name_or_id)
        reg_match = re.match(r'^(.*?)-(alola|galar|hisui|paldea|paldean)$', slug)
        if reg_match:
            base_species_slug = reg_match.group(1)
            regional_form = reg_match.group(2)
            if regional_form == "paldean":
                regional_form = "paldea"
        else:
            base_species_slug = slug
            regional_form = None

        species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(base_species_slug)}"
        req = urllib.request.Request(species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=5) as resp:
                species = json.loads(resp.read().decode())
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise

            pokemon_url = f"{POKEAPI_BASE_URL}/{urllib.parse.quote(slug)}"
            pokemon_req = urllib.request.Request(pokemon_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
            with urllib.request.urlopen(pokemon_req, context=ssl.create_default_context(), timeout=5) as resp:
                pokemon_data = json.loads(resp.read().decode())
            base_species_slug = (pokemon_data.get("species") or {}).get("name") or base_species_slug
            if not regional_form and slug.startswith(f"{base_species_slug}-"):
                regional_form = slug[len(base_species_slug) + 1:]
                if regional_form == "paldean":
                    regional_form = "paldea"
            species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(base_species_slug)}"
            species_req = urllib.request.Request(species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
            with urllib.request.urlopen(species_req, context=ssl.create_default_context(), timeout=5) as resp:
                species = json.loads(resp.read().decode())

        chain_url = species.get("evolution_chain", {}).get("url")
        if not chain_url:
            return options

        chain_req = urllib.request.Request(chain_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(chain_req, context=ssl.create_default_context(), timeout=5) as chain_resp:
            evo_data = json.loads(chain_resp.read().decode())

        current = find_chain_node(evo_data.get("chain"), base_species_slug)
        if not current:
            return options

        candidates = current.get("evolves_to", [])
        any_candidate_matches_regional = False
        if regional_form:
            for cand in candidates:
                for d in (cand.get("evolution_details") or []):
                    req_name = (d.get("required_pokemon_form") or {}).get("name")
                    if req_name and (regional_form in req_name or slug == req_name):
                        any_candidate_matches_regional = True
                        break

        for candidate in candidates:
            target_name = candidate.get("species", {}).get("name")
            if not target_name:
                continue

            details_list = candidate.get("evolution_details") or [{}]
            cand_has_regional_match = any(
                regional_form and (d.get("required_pokemon_form") or {}).get("name") and (
                    regional_form in (d.get("required_pokemon_form") or {}).get("name") or
                    slug == (d.get("required_pokemon_form") or {}).get("name")
                )
                for d in details_list
            )

            for details in details_list:
                req_form = (details.get("required_pokemon_form") or {}).get("name")
                evolved_form = (details.get("evolved_pokemon_form") or {}).get("name")

                if regional_form:
                    if req_form:
                        if regional_form not in req_form and req_form != slug:
                            continue
                    else:
                        if cand_has_regional_match:
                            continue
                        if any_candidate_matches_regional and not evolved_form:
                            continue
                else:
                    if req_form:
                        continue

                target_slug = evolved_form or target_name
                if regional_form and not evolved_form:
                    regional_target_slug = f"{target_name}-{regional_form}"
                    target_species_url = f"https://pokeapi.co/api/v2/pokemon-species/{urllib.parse.quote(target_name)}"
                    target_species_req = urllib.request.Request(target_species_url, headers={"User-Agent": "DraftPrimeApp/1.0"})
                    try:
                        with urllib.request.urlopen(target_species_req, context=ssl.create_default_context(), timeout=5) as resp:
                            target_species = json.loads(resp.read().decode())
                        varieties = {
                            (variety.get("pokemon") or {}).get("name")
                            for variety in target_species.get("varieties", [])
                        }
                        if regional_target_slug in varieties:
                            target_slug = regional_target_slug
                    except Exception:
                        pass

                trigger = (details.get("trigger") or {}).get("name")
                min_level = details.get("min_level")
                item = details.get("item") or details.get("held_item") or {}
                item_name = item.get("name") if item else None
                is_trade = (trigger == "trade") or bool(details.get("trade_species"))
                is_friendship = bool(details.get("min_happiness") or details.get("min_affection"))

                formatted_item = item_name.replace("-", " ").title() if item_name else None

                opt_key = (
                    target_slug.lower(),
                    (formatted_item or "").lower(),
                    bool(is_trade),
                    bool(is_friendship),
                    min_level if min_level is not None else 0,
                )
                if opt_key not in seen:
                    seen.add(opt_key)
                    options.append({
                        "target": target_slug,
                        "level": int(min_level) if min_level is not None else None,
                        "item": formatted_item,
                        "trade": is_trade,
                        "friendship": is_friendship,
                    })

        return options
    except Exception:
        return options


def get_pokemon_evolution_details(name_or_id: str, max_level: int = 40) -> Optional[dict]:
    """Devuelve objetivo y condiciones de la primera evolución aplicable."""
    options = get_pokemon_all_evolution_options(name_or_id, max_level)
    return options[0] if options else None


def get_pokemon_evolution_target(name_or_id: str, max_level: int = 40) -> Optional[str]:
    details = get_pokemon_evolution_details(name_or_id, max_level)
    return details.get("target") if details else None


def get_pokemon_next_evolution_level(name_or_id: str) -> Optional[int]:
    """Devuelve el nivel mínimo de la siguiente evolución por level-up del Pokémon."""
    options = get_pokemon_all_evolution_options(name_or_id, max_level=100)
    for opt in options:
        if opt.get("level") is not None:
            return opt.get("level")
    return None


def fetch_pokemon_data(name_or_id: str, level_cap: int = 20) -> dict:
    """Consulta datos de Pokémon desde PokeAPI con fallback en caso de error/offline."""
    key = str(name_or_id).lower().strip()
    api_slug = clean_poke_api_name(name_or_id)
    cache_key = f"{key}_{level_cap}"
    if cache_key in POKE_CACHE:
        POKE_CACHE.move_to_end(cache_key)
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

            evolution_options = get_pokemon_all_evolution_options(name, max_level=100)
            evolution_details = evolution_options[0] if evolution_options else None
            next_evolution = evolution_details.get("target") if evolution_details else None
            next_evolution_level = evolution_details.get("level") if evolution_details else None
            formatted_options = [
                {
                    "target": opt["target"].capitalize() if opt.get("target") else "",
                    "level": opt.get("level"),
                    "item": opt.get("item"),
                    "trade": bool(opt.get("trade")),
                    "friendship": bool(opt.get("friendship")),
                }
                for opt in evolution_options
            ]
            mega_info = get_mega_info(name_or_id) or get_mega_info(name)
            is_mega = bool(mega_info)
            base_species = mega_info["base_name"] if mega_info else name
            mega_stone = mega_info["mega_stone"] if mega_info else None

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
                "can_evolve": bool(next_evolution) if not is_mega else False,
                "evolution_target": next_evolution if not is_mega else None,
                "next_evolution_level": next_evolution_level if not is_mega else None,
                "evolution_item": evolution_details.get("item") if (evolution_details and not is_mega) else None,
                "evolution_trade": bool(evolution_details and evolution_details.get("trade")) if not is_mega else False,
                "evolution_options": formatted_options if not is_mega else [],
                "is_mega": is_mega,
                "base_species": base_species,
                "mega_stone": mega_stone,
                "item": None,
                "held_item": None,
            }
            if len(POKE_CACHE) >= MAX_POKE_CACHE:
                POKE_CACHE.popitem(last=False)
            POKE_CACHE[cache_key] = res
            return res.copy()
    except Exception as e:
        print(f"[WARNING] No se pudo cargar '{name_or_id}' ({api_slug}) desde PokeAPI ({e}). Usando fallback local.")
        # Fallback local
        name_clean = str(name_or_id).capitalize()
        mega_info = get_mega_info(name_or_id) or get_mega_info(name_clean)
        is_mega = bool(mega_info)
        base_species = mega_info["base_name"] if mega_info else name_clean
        mega_stone = mega_info["mega_stone"] if mega_info else None

        default_moves = [
            {"name": "Tackle", "level": 1},
            {"name": "Quick Attack", "level": 5},
            {"name": "Bite", "level": 12},
            {"name": "Body Slam", "level": 20},
            {"name": "Hyper Beam", "level": 40}
        ]
        evolution_options = get_pokemon_all_evolution_options(name_clean, max_level=100)
        evolution_details = evolution_options[0] if evolution_options else None
        next_evolution = evolution_details.get("target") if evolution_details else None
        next_evolution_level = evolution_details.get("level") if evolution_details else None
        formatted_options = [
            {
                "target": opt["target"].capitalize() if opt.get("target") else "",
                "level": opt.get("level"),
                "item": opt.get("item"),
                "trade": bool(opt.get("trade")),
                "friendship": bool(opt.get("friendship")),
            }
            for opt in evolution_options
        ]
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
            "can_evolve": bool(next_evolution) if not is_mega else False,
            "evolution_target": next_evolution if not is_mega else None,
            "next_evolution_level": next_evolution_level if not is_mega else None,
            "evolution_item": evolution_details.get("item") if (evolution_details and not is_mega) else None,
            "evolution_trade": bool(evolution_details and evolution_details.get("trade")) if not is_mega else False,
            "evolution_options": formatted_options if not is_mega else [],
            "is_mega": is_mega,
            "base_species": base_species,
            "mega_stone": mega_stone,
            "item": None,
            "held_item": None,
        }
        if len(POKE_CACHE) >= MAX_POKE_CACHE:
            POKE_CACHE.popitem(last=False)
        POKE_CACHE[cache_key] = res
        return res.copy()


def get_random_pokemon_form_choice(base_name: str) -> str:
    """Elige entre la forma normal y sus variantes regionales con probabilidad igual entre todas las opciones."""
    variants = get_pokemon_regional_form_options(base_name)
    if not variants:
        return str(base_name)

    options = [str(base_name)]
    options.extend(option["target_name"] for option in variants)
    return random.choice(options)


def get_random_pokemon_from_tier(tier: str = "normal", year: Optional[int] = None, level_cap: int = 20) -> dict:
    """Devuelve un Pokémon aleatorio desde la base de datos o desde el pool estático, incluyendo forma regional con probabilidad uniforme."""
    from backend import database
    chosen_base_name = database.get_random_pokemon_from_db(year=year, auction_type=tier)

    if chosen_base_name:
        print(f"[OK] [DATABASE] Pokémon aleatorio obtenido desde Supabase (Año {year}, Tipo '{tier}').")
    else:
        print(f"[INFO] [LOCAL] Usando pool estático por defecto (Año {year}, Tipo '{tier}').")
        pool = SAMPLE_POKEMON_POOLS.get(tier.lower(), SAMPLE_POKEMON_POOLS["normal"])
        chosen_base_name = random.choice(pool)

    chosen_name = get_random_pokemon_form_choice(chosen_base_name)
    return fetch_pokemon_data(chosen_name, level_cap=level_cap)



def get_hints_for_multiplier(poke_data: dict, multiplier: float) -> dict:
    """
    Retorna un diccionario de pistas acumulativas en función del multiplicador del precio inicial:
      - 1.0x: Primera letra del nombre
      - 2.0x: Región de origen
      - 3.0x: Estadística base más alta
      - 5.0x: Tipo primario
      - 8.0x: Habilidad asignada 
    """
    hints = {}
    name = poke_data.get("name", "???")

    if multiplier >= 1.0:
        hints["first_letter"] = name[0].upper() if name else "?"

    if multiplier >= 2.0:
        hints["region"] = poke_data.get("region", "Desconocida")

    if multiplier >= 3.0:
        hints["highest_stat"] = poke_data.get("highest_stat", "HP (50)")

    if multiplier >= 5.0:
        hints["primary_type"] = poke_data.get("primary_type", "Normal")

    if multiplier >= 8.0:
        hints["ability"] = poke_data.get("ability", "Desconocida")

    return hints
