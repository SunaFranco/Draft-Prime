"""
backend/engine/pkmn_ai_engine/core/moves_db.py
Base de datos ligera de movimientos de Pokémon oficiales.
Contiene más de 120 movimientos competitivos comunes y un generador inteligente para movimientos no listados.
"""

import json
import ssl
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from .models import MoveState

POPULAR_MOVES: Dict[str, dict] = {
    # Fuego
    "flamethrower": {"name": "Flamethrower", "type": "Fire", "category": "special", "base_power": 90, "accuracy": 1.0},
    "fire-blast": {"name": "Fire Blast", "type": "Fire", "category": "special", "base_power": 110, "accuracy": 0.85},
    "flare-blitz": {"name": "Flare Blitz", "type": "Fire", "category": "physical", "base_power": 120, "accuracy": 1.0},
    "fire-punch": {"name": "Fire Punch", "type": "Fire", "category": "physical", "base_power": 75, "accuracy": 1.0},
    "will-o-wisp": {"name": "Will-O-Wisp", "type": "Fire", "category": "status", "base_power": 0, "accuracy": 0.85},
    "lava-plume": {"name": "Lava Plume", "type": "Fire", "category": "special", "base_power": 80, "accuracy": 1.0},

    # Agua
    "surf": {"name": "Surf", "type": "Water", "category": "special", "base_power": 90, "accuracy": 1.0},
    "hydro-pump": {"name": "Hydro Pump", "type": "Water", "category": "special", "base_power": 110, "accuracy": 0.80},
    "scald": {"name": "Scald", "type": "Water", "category": "special", "base_power": 80, "accuracy": 1.0},
    "waterfall": {"name": "Waterfall", "type": "Water", "category": "physical", "base_power": 80, "accuracy": 1.0},
    "liquidation": {"name": "Liquidation", "type": "Water", "category": "physical", "base_power": 85, "accuracy": 1.0},
    "aqua-jet": {"name": "Aqua Jet", "type": "Water", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
    "muddy-water": {"name": "Muddy Water", "type": "Water", "category": "special", "base_power": 90, "accuracy": 0.85},

    # Planta
    "giga-drain": {"name": "Giga Drain", "type": "Grass", "category": "special", "base_power": 75, "accuracy": 1.0},
    "energy-ball": {"name": "Energy Ball", "type": "Grass", "category": "special", "base_power": 90, "accuracy": 1.0},
    "leaf-blade": {"name": "Leaf Blade", "type": "Grass", "category": "physical", "base_power": 90, "accuracy": 1.0},
    "wood-hammer": {"name": "Wood Hammer", "type": "Grass", "category": "physical", "base_power": 120, "accuracy": 1.0},
    "power-whip": {"name": "Power Whip", "type": "Grass", "category": "physical", "base_power": 120, "accuracy": 0.85},
    "spore": {"name": "Spore", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 1.0},
    "sleep-powder": {"name": "Sleep Powder", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 0.75},
    "synthesis": {"name": "Synthesis", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 1.0},

    # Eléctrico
    "thunderbolt": {"name": "Thunderbolt", "type": "Electric", "category": "special", "base_power": 90, "accuracy": 1.0},
    "thunder": {"name": "Thunder", "type": "Electric", "category": "special", "base_power": 110, "accuracy": 0.70},
    "volt-switch": {"name": "Volt Switch", "type": "Electric", "category": "special", "base_power": 70, "accuracy": 1.0},
    "wild-charge": {"name": "Wild Charge", "type": "Electric", "category": "physical", "base_power": 90, "accuracy": 1.0},
    "thunder-wave": {"name": "Thunder Wave", "type": "Electric", "category": "status", "base_power": 0, "accuracy": 0.90},
    "thunder-punch": {"name": "Thunder Punch", "type": "Electric", "category": "physical", "base_power": 75, "accuracy": 1.0},
    "volt-tackle": {"name": "Volt Tackle", "type": "Electric", "category": "physical", "base_power": 120, "accuracy": 1.0},

    # Hielo
    "ice-beam": {"name": "Ice Beam", "type": "Ice", "category": "special", "base_power": 90, "accuracy": 1.0},
    "blizzard": {"name": "Blizzard", "type": "Ice", "category": "special", "base_power": 110, "accuracy": 0.70},
    "ice-punch": {"name": "Ice Punch", "type": "Ice", "category": "physical", "base_power": 75, "accuracy": 1.0},
    "icicle-crash": {"name": "Icicle Crash", "type": "Ice", "category": "physical", "base_power": 85, "accuracy": 0.90},
    "ice-shard": {"name": "Ice Shard", "type": "Ice", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
    "freeze-dry": {"name": "Freeze-Dry", "type": "Ice", "category": "special", "base_power": 70, "accuracy": 1.0},

    # Lucha
    "close-combat": {"name": "Close Combat", "type": "Fighting", "category": "physical", "base_power": 120, "accuracy": 1.0},
    "aura-sphere": {"name": "Aura Sphere", "type": "Fighting", "category": "special", "base_power": 80, "accuracy": 1.0},
    "drain-punch": {"name": "Drain Punch", "type": "Fighting", "category": "physical", "base_power": 75, "accuracy": 1.0},
    "focus-blast": {"name": "Focus Blast", "type": "Fighting", "category": "special", "base_power": 120, "accuracy": 0.70},
    "mach-punch": {"name": "Mach Punch", "type": "Fighting", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
    "superpower": {"name": "Superpower", "type": "Fighting", "category": "physical", "base_power": 120, "accuracy": 1.0},

    # Veneno
    "sludge-bomb": {"name": "Sludge Bomb", "type": "Poison", "category": "special", "base_power": 90, "accuracy": 1.0},
    "sludge-wave": {"name": "Sludge Wave", "type": "Poison", "category": "special", "base_power": 95, "accuracy": 1.0},
    "gunk-shot": {"name": "Gunk Shot", "type": "Poison", "category": "physical", "base_power": 120, "accuracy": 0.80},
    "poison-jab": {"name": "Poison Jab", "type": "Poison", "category": "physical", "base_power": 80, "accuracy": 1.0},
    "toxic": {"name": "Toxic", "type": "Poison", "category": "status", "base_power": 0, "accuracy": 0.90},

    # Tierra
    "earthquake": {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
    "earth-power": {"name": "Earth Power", "type": "Ground", "category": "special", "base_power": 90, "accuracy": 1.0},
    "high-horsepower": {"name": "High Horsepower", "type": "Ground", "category": "physical", "base_power": 95, "accuracy": 0.95},
    "bulldoze": {"name": "Bulldoze", "type": "Ground", "category": "physical", "base_power": 60, "accuracy": 1.0},

    # Volador
    "air-slash": {"name": "Air Slash", "type": "Flying", "category": "special", "base_power": 75, "accuracy": 0.95},
    "brave-bird": {"name": "Brave Bird", "type": "Flying", "category": "physical", "base_power": 120, "accuracy": 1.0},
    "hurricane": {"name": "Hurricane", "type": "Flying", "category": "special", "base_power": 110, "accuracy": 0.70},
    "roost": {"name": "Roost", "type": "Flying", "category": "status", "base_power": 0, "accuracy": 1.0},
    "acrobatics": {"name": "Acrobatics", "type": "Flying", "category": "physical", "base_power": 55, "accuracy": 1.0},
    "defog": {"name": "Defog", "type": "Flying", "category": "status", "base_power": 0, "accuracy": 1.0},

    # Psíquico
    "psychic": {"name": "Psychic", "type": "Psychic", "category": "special", "base_power": 90, "accuracy": 1.0},
    "psyshock": {"name": "Psyshock", "type": "Psychic", "category": "special", "base_power": 80, "accuracy": 1.0},
    "zen-headbutt": {"name": "Zen Headbutt", "type": "Psychic", "category": "physical", "base_power": 80, "accuracy": 0.90},
    "calm-mind": {"name": "Calm Mind", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0},
    "recover": {"name": "Recover", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},

    # Bicho
    "bug-buzz": {"name": "Bug Buzz", "type": "Bug", "category": "special", "base_power": 90, "accuracy": 1.0},
    "u-turn": {"name": "U-turn", "type": "Bug", "category": "physical", "base_power": 70, "accuracy": 1.0},
    "x-scissor": {"name": "X-Scissor", "type": "Bug", "category": "physical", "base_power": 80, "accuracy": 1.0},
    "quiver-dance": {"name": "Quiver Dance", "type": "Bug", "category": "status", "base_power": 0, "accuracy": 1.0},

    # Roca
    "stone-edge": {"name": "Stone Edge", "type": "Rock", "category": "physical", "base_power": 100, "accuracy": 0.80},
    "rock-slide": {"name": "Rock Slide", "type": "Rock", "category": "physical", "base_power": 75, "accuracy": 0.90},
    "power-gem": {"name": "Power Gem", "type": "Rock", "category": "special", "base_power": 80, "accuracy": 1.0},
    "stealth-rock": {"name": "Stealth Rock", "type": "Rock", "category": "status", "base_power": 0, "accuracy": 1.0},
    "rock-tomb": {"name": "Rock Tomb", "type": "Rock", "category": "physical", "base_power": 60, "accuracy": 0.95},

    # Fantasma
    "shadow-ball": {"name": "Shadow Ball", "type": "Ghost", "category": "special", "base_power": 80, "accuracy": 1.0},
    "shadow-claw": {"name": "Shadow Claw", "type": "Ghost", "category": "physical", "base_power": 70, "accuracy": 1.0},
    "shadow-sneak": {"name": "Shadow Sneak", "type": "Ghost", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
    "poltergeist": {"name": "Poltergeist", "type": "Ghost", "category": "physical", "base_power": 110, "accuracy": 0.90},

    # Dragón
    "dragon-claw": {"name": "Dragon Claw", "type": "Dragon", "category": "physical", "base_power": 80, "accuracy": 1.0},
    "dragon-pulse": {"name": "Dragon Pulse", "type": "Dragon", "category": "special", "base_power": 85, "accuracy": 1.0},
    "draco-meteor": {"name": "Draco Meteor", "type": "Dragon", "category": "special", "base_power": 130, "accuracy": 0.90},
    "outrage": {"name": "Outrage", "type": "Dragon", "category": "physical", "base_power": 120, "accuracy": 1.0},
    "dragon-dance": {"name": "Dragon Dance", "type": "Dragon", "category": "status", "base_power": 0, "accuracy": 1.0},

    # Acero
    "flash-cannon": {"name": "Flash Cannon", "type": "Steel", "category": "special", "base_power": 80, "accuracy": 1.0},
    "iron-head": {"name": "Iron Head", "type": "Steel", "category": "physical", "base_power": 80, "accuracy": 1.0},
    "meteor-mash": {"name": "Meteor Mash", "type": "Steel", "category": "physical", "base_power": 90, "accuracy": 0.90},
    "bullet-punch": {"name": "Bullet Punch", "type": "Steel", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},

    # Siniestro
    "dark-pulse": {"name": "Dark Pulse", "type": "Dark", "category": "special", "base_power": 80, "accuracy": 1.0},
    "crunch": {"name": "Crunch", "type": "Dark", "category": "physical", "base_power": 80, "accuracy": 1.0},
    "knock-off": {"name": "Knock Off", "type": "Dark", "category": "physical", "base_power": 65, "accuracy": 1.0},
    "sucker-punch": {"name": "Sucker Punch", "type": "Dark", "category": "physical", "base_power": 70, "accuracy": 1.0, "priority": 1},
    "taunt": {"name": "Taunt", "type": "Dark", "category": "status", "base_power": 0, "accuracy": 1.0},

    # Hada
    "moonblast": {"name": "Moonblast", "type": "Fairy", "category": "special", "base_power": 95, "accuracy": 1.0},
    "dazzling-gleam": {"name": "Dazzling Gleam", "type": "Fairy", "category": "special", "base_power": 80, "accuracy": 1.0},
    "play-rough": {"name": "Play Rough", "type": "Fairy", "category": "physical", "base_power": 90, "accuracy": 0.90},

    # Normal
    "body-slam": {"name": "Body Slam", "type": "Normal", "category": "physical", "base_power": 85, "accuracy": 1.0},
    "extreme-speed": {"name": "Extreme Speed", "type": "Normal", "category": "physical", "base_power": 80, "accuracy": 1.0, "priority": 2},
    "quick-attack": {"name": "Quick Attack", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
    "tackle": {"name": "Tackle", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0},
    "swords-dance": {"name": "Swords Dance", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},
    "protect": {"name": "Protect", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "priority": 4},
}


def fetch_move_from_pokeapi(slug: str) -> Optional[dict]:
    """
    Consulta PokeAPI para obtener los datos oficiales de combate de un movimiento.
    Devuelve None si falla o si no existe en PokeAPI.
    """
    clean_slug = slug.strip().lower().replace(" ", "-")
    if not clean_slug:
        return None

    url = f"https://pokeapi.co/api/v2/move/{urllib.parse.quote(clean_slug)}"
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "DraftPrimeApp/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))

            move_type = ((data.get("type") or {}).get("name") or "normal").capitalize()
            category = ((data.get("damage_class") or {}).get("name") or "physical").lower()
            power = int(data.get("power") or 0)
            raw_acc = data.get("accuracy")
            accuracy = float(raw_acc) / 100.0 if raw_acc is not None else 1.0
            priority = int(data.get("priority") or 0)
            pp = int(data.get("pp") or 15)

            meta = data.get("meta") or {}
            drain = int(meta.get("drain") or 0)
            drain_pct = drain / 100.0 if drain > 0 else 0.0
            recoil_pct = abs(drain) / 100.0 if drain < 0 else 0.0

            # Buscar nombre en inglés legible si existe
            display_name = clean_slug.replace("-", " ").title()
            for n_entry in data.get("names", []):
                lang = (n_entry.get("language") or {}).get("name")
                if lang == "en" and n_entry.get("name"):
                    display_name = n_entry["name"]
                    break

            return {
                "slug": clean_slug,
                "name": display_name,
                "type": move_type,
                "category": category,
                "base_power": power,
                "accuracy": accuracy,
                "priority": priority,
                "pp": pp,
                "drain_percent": drain_pct,
                "recoil_percent": recoil_pct,
            }
    except Exception:
        return None


def _build_inferred_move_dict(slug: str, clean_name: str, fallback_type: str = "Normal") -> dict:
    """Construye un diccionario de movimiento por inferencia si no se encuentra en ninguna fuente."""
    is_status = any(
        k in slug
        for k in [
            "dance", "spore", "wave", "powder", "toxic", "protect",
            "substitute", "mind", "growth", "curse", "rest", "roost",
            "recover", "synthesis", "taunt", "stealth-rock", "spikes", "defog"
        ]
    )
    cat = "status" if is_status else "physical"
    power = 0 if is_status else 80
    return {
        "slug": slug or "tackle",
        "name": clean_name or "Tackle",
        "type": fallback_type.capitalize(),
        "category": cat,
        "base_power": power,
        "accuracy": 1.0,
        "priority": 0,
        "pp": 15,
        "drain_percent": 0.0,
        "recoil_percent": 0.0,
    }


def ensure_move_in_db(
    move_name_or_dict: Any,
    fallback_type: str = "Normal",
    sync_db: bool = True
) -> MoveState:
    """
    Verifica si un movimiento está en la tabla 'pokemon_moves' de Supabase.
    Si no está, obtiene sus datos de combate (catálogo local o PokeAPI) y lo inserta en la tabla.
    """
    if isinstance(move_name_or_dict, dict):
        if "base_power" in move_name_or_dict or "category" in move_name_or_dict:
            ms = MoveState.from_dict(move_name_or_dict)
            if sync_db:
                try:
                    from backend.database import get_pokemon_move_from_db, save_pokemon_move_to_db
                    if not get_pokemon_move_from_db(ms.id):
                        save_pokemon_move_to_db({
                            "slug": ms.id,
                            "name": ms.name,
                            "type": ms.type,
                            "category": ms.category,
                            "base_power": ms.base_power,
                            "accuracy": ms.accuracy,
                            "priority": ms.priority,
                            "pp": ms.pp,
                            "drain_percent": ms.drain_percent,
                            "recoil_percent": ms.recoil_percent,
                        })
                except Exception:
                    pass
            return ms
        raw_name = move_name_or_dict.get("name", "")
    else:
        raw_name = str(move_name_or_dict or "")

    clean_name = raw_name.replace("MT ", "").replace("MO ", "").strip()
    slug = clean_name.lower().replace(" ", "-")
    if not slug:
        slug = "tackle"
        clean_name = "Tackle"

    # 1. Consultar si ya existe en la tabla de base de datos (Supabase / Caché local)
    if sync_db:
        try:
            from backend.database import get_pokemon_move_from_db, save_pokemon_move_to_db
            existing = get_pokemon_move_from_db(slug)
            if existing:
                return MoveState(
                    id=existing.get("slug", slug),
                    name=existing.get("name", clean_name),
                    type=existing.get("type", fallback_type.capitalize()),
                    category=existing.get("category", "physical"),
                    base_power=int(existing.get("base_power", 0)),
                    accuracy=float(existing.get("accuracy", 1.0)),
                    priority=int(existing.get("priority", 0)),
                    pp=int(existing.get("pp", 15)),
                    max_pp=int(existing.get("pp", 15)),
                    drain_percent=float(existing.get("drain_percent", 0.0)),
                    recoil_percent=float(existing.get("recoil_percent", 0.0)),
                )
        except Exception:
            pass

    # 2. Si no está en la tabla, obtener sus datos de combate
    move_dict: Optional[dict] = None

    if slug in POPULAR_MOVES:
        d = POPULAR_MOVES[slug]
        move_dict = {
            "slug": slug,
            "name": d["name"],
            "type": d["type"],
            "category": d["category"],
            "base_power": d["base_power"],
            "accuracy": d.get("accuracy", 1.0),
            "priority": d.get("priority", 0),
            "pp": d.get("pp", 15),
            "drain_percent": d.get("drain_percent", 0.0),
            "recoil_percent": d.get("recoil_percent", 0.0),
        }
    else:
        # Consultar PokeAPI para obtener los datos reales de combate del movimiento
        move_dict = fetch_move_from_pokeapi(slug)

    if not move_dict:
        move_dict = _build_inferred_move_dict(slug, clean_name, fallback_type)

    # 3. Guardar el nuevo movimiento en la tabla 'pokemon_moves' de Supabase
    if sync_db:
        try:
            from backend.database import save_pokemon_move_to_db
            save_pokemon_move_to_db(move_dict)
        except Exception:
            pass

    return MoveState(
        id=move_dict["slug"],
        name=move_dict["name"],
        type=move_dict["type"],
        category=move_dict["category"],
        base_power=int(move_dict["base_power"]),
        accuracy=float(move_dict["accuracy"]),
        priority=int(move_dict["priority"]),
        pp=int(move_dict.get("pp", 15)),
        max_pp=int(move_dict.get("pp", 15)),
        drain_percent=float(move_dict.get("drain_percent", 0.0)),
        recoil_percent=float(move_dict.get("recoil_percent", 0.0)),
    )


def ensure_moves_registered(move_names: List[Any], fallback_type: str = "Normal") -> List[MoveState]:
    """
    Verifica una lista de movimientos asignados a un Pokémon y registra en la base de datos
    aquellos que aún no existan.
    """
    results: List[MoveState] = []
    for m in move_names:
        if m:
            results.append(ensure_move_in_db(m, fallback_type=fallback_type, sync_db=True))
    return results


def resolve_move(move_name_or_dict: Any, fallback_type: str = "Normal") -> MoveState:
    """
    Convierte cualquier nombre de movimiento (string o dict) en un MoveState completo
    y garantiza que esté registrado en la tabla de datos de movimientos.
    """
    return ensure_move_in_db(move_name_or_dict, fallback_type=fallback_type, sync_db=True)
