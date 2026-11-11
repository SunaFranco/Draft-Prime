"""
backend/engine/pkmn_ai_engine/core/moves_db.py
Catálogo de movimientos basado en Pokémon Showdown (data/moves.ts) y sincronización con PokeAPI / Supabase.
Incluye efectos secundarios, cambios de estadísticas, climas, terrenos, hazards, pantallas, curaciones,
movimientos multi-golpe, pivots (U-turn/Volt Switch), phazing y estados volátiles.
"""

import json
import ssl
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from .models import MoveState

POPULAR_MOVES: Dict[str, dict] = {
    # =========================================================================
    # FUEGO (Fire)
    # =========================================================================
    "flamethrower": {
        "name": "Flamethrower", "type": "Fire", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.10, "status": "BRN"},
    },
    "fire-blast": {
        "name": "Fire Blast", "type": "Fire", "category": "special", "base_power": 110, "accuracy": 0.85, "pp": 5,
        "secondary": {"chance": 0.10, "status": "BRN"},
    },
    "flare-blitz": {
        "name": "Flare Blitz", "type": "Fire", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 15,
        "recoil_percent": 0.33, "makes_contact": True,
        "secondary": {"chance": 0.10, "status": "BRN"},
    },
    "fire-punch": {
        "name": "Fire Punch", "type": "Fire", "category": "physical", "base_power": 75, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.10, "status": "BRN"},
    },
    "will-o-wisp": {
        "name": "Will-O-Wisp", "type": "Fire", "category": "status", "base_power": 0, "accuracy": 0.85, "pp": 15,
        "target_status": "BRN",
    },
    "lava-plume": {
        "name": "Lava Plume", "type": "Fire", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.30, "status": "BRN"},
    },
    "overheat": {
        "name": "Overheat", "type": "Fire", "category": "special", "base_power": 130, "accuracy": 0.90, "pp": 5,
        "self_boosts": {"spa": -2},
    },
    "heat-wave": {
        "name": "Heat Wave", "type": "Fire", "category": "special", "base_power": 95, "accuracy": 0.90, "pp": 10,
        "secondary": {"chance": 0.10, "status": "BRN"},
    },
    "flame-charge": {
        "name": "Flame Charge", "type": "Fire", "category": "physical", "base_power": 50, "accuracy": 1.0, "pp": 20,
        "makes_contact": True, "self_boosts": {"spe": 1},
    },
    "sacred-fire": {
        "name": "Sacred Fire", "type": "Fire", "category": "physical", "base_power": 100, "accuracy": 0.95, "pp": 5,
        "secondary": {"chance": 0.50, "status": "BRN"},
    },
    "fire-spin": {
        "name": "Fire Spin", "type": "Fire", "category": "special", "base_power": 35, "accuracy": 0.85, "pp": 15,
        "volatile_status": "partially_trapped",
    },
    "sunny-day": {
        "name": "Sunny Day", "type": "Fire", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 5,
        "weather": "Sun",
    },

    # =========================================================================
    # AGUA (Water)
    # =========================================================================
    "surf": {
        "name": "Surf", "type": "Water", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 15,
    },
    "hydro-pump": {
        "name": "Hydro Pump", "type": "Water", "category": "special", "base_power": 110, "accuracy": 0.80, "pp": 5,
    },
    "scald": {
        "name": "Scald", "type": "Water", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.30, "status": "BRN"},
    },
    "waterfall": {
        "name": "Waterfall", "type": "Water", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.20, "flinch": True},
    },
    "liquidation": {
        "name": "Liquidation", "type": "Water", "category": "physical", "base_power": 85, "accuracy": 1.0, "pp": 10,
        "makes_contact": True, "secondary": {"chance": 0.20, "boosts": {"def": -1}},
    },
    "aqua-jet": {
        "name": "Aqua Jet", "type": "Water", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1, "pp": 20,
        "makes_contact": True,
    },
    "muddy-water": {
        "name": "Muddy Water", "type": "Water", "category": "special", "base_power": 90, "accuracy": 0.85, "pp": 10,
        "secondary": {"chance": 0.30, "boosts": {"accuracy": -1}},
    },
    "flip-turn": {
        "name": "Flip Turn", "type": "Water", "category": "physical", "base_power": 60, "accuracy": 1.0, "pp": 20,
        "makes_contact": True, "self_switch": True,
    },
    "wave-crash": {
        "name": "Wave Crash", "type": "Water", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 10,
        "recoil_percent": 0.33, "makes_contact": True,
    },
    "rain-dance": {
        "name": "Rain Dance", "type": "Water", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 5,
        "weather": "Rain",
    },

    # =========================================================================
    # PLANTA (Grass)
    # =========================================================================
    "giga-drain": {
        "name": "Giga Drain", "type": "Grass", "category": "special", "base_power": 75, "accuracy": 1.0, "pp": 10,
        "drain_percent": 0.50,
    },
    "energy-ball": {
        "name": "Energy Ball", "type": "Grass", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "boosts": {"spd": -1}},
    },
    "leaf-blade": {
        "name": "Leaf Blade", "type": "Grass", "category": "physical", "base_power": 90, "accuracy": 1.0, "pp": 15,
        "crit_ratio": 2, "makes_contact": True,
    },
    "wood-hammer": {
        "name": "Wood Hammer", "type": "Grass", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 15,
        "recoil_percent": 0.33, "makes_contact": True,
    },
    "power-whip": {
        "name": "Power Whip", "type": "Grass", "category": "physical", "base_power": 120, "accuracy": 0.85, "pp": 10,
        "makes_contact": True,
    },
    "leaf-storm": {
        "name": "Leaf Storm", "type": "Grass", "category": "special", "base_power": 130, "accuracy": 0.90, "pp": 5,
        "self_boosts": {"spa": -2},
    },
    "bullet-seed": {
        "name": "Bullet Seed", "type": "Grass", "category": "physical", "base_power": 25, "accuracy": 1.0, "pp": 30,
        "multi_hit": (2, 5),
    },
    "spore": {
        "name": "Spore", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 15,
        "target_status": "SLP",
    },
    "sleep-powder": {
        "name": "Sleep Powder", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 0.75, "pp": 15,
        "target_status": "SLP",
    },
    "stun-spore": {
        "name": "Stun Spore", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 0.75, "pp": 30,
        "target_status": "PAR",
    },
    "leech-seed": {
        "name": "Leech Seed", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 0.90, "pp": 10,
        "volatile_status": "leech_seed",
    },
    "synthesis": {
        "name": "Synthesis", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 5,
        "heal_fraction": 0.50,
    },
    "grassy-terrain": {
        "name": "Grassy Terrain", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "terrain": "Grassy",
    },

    # =========================================================================
    # ELÉCTRICO (Electric)
    # =========================================================================
    "thunderbolt": {
        "name": "Thunderbolt", "type": "Electric", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.10, "status": "PAR"},
    },
    "thunder": {
        "name": "Thunder", "type": "Electric", "category": "special", "base_power": 110, "accuracy": 0.70, "pp": 10,
        "secondary": {"chance": 0.30, "status": "PAR"},
    },
    "discharge": {
        "name": "Discharge", "type": "Electric", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.30, "status": "PAR"},
    },
    "volt-switch": {
        "name": "Volt Switch", "type": "Electric", "category": "special", "base_power": 70, "accuracy": 1.0, "pp": 20,
        "self_switch": True,
    },
    "wild-charge": {
        "name": "Wild Charge", "type": "Electric", "category": "physical", "base_power": 90, "accuracy": 1.0, "pp": 15,
        "recoil_percent": 0.25, "makes_contact": True,
    },
    "thunder-wave": {
        "name": "Thunder Wave", "type": "Electric", "category": "status", "base_power": 0, "accuracy": 0.90, "pp": 20,
        "target_status": "PAR",
    },
    "thunder-punch": {
        "name": "Thunder Punch", "type": "Electric", "category": "physical", "base_power": 75, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.10, "status": "PAR"},
    },
    "volt-tackle": {
        "name": "Volt Tackle", "type": "Electric", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 15,
        "recoil_percent": 0.33, "makes_contact": True, "secondary": {"chance": 0.10, "status": "PAR"},
    },
    "nuzzle": {
        "name": "Nuzzle", "type": "Electric", "category": "physical", "base_power": 20, "accuracy": 1.0, "pp": 20,
        "makes_contact": True, "secondary": {"chance": 1.0, "status": "PAR"},
    },
    "electric-terrain": {
        "name": "Electric Terrain", "type": "Electric", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "terrain": "Electric",
    },

    # =========================================================================
    # HIELO (Ice)
    # =========================================================================
    "ice-beam": {
        "name": "Ice Beam", "type": "Ice", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "status": "FRZ"},
    },
    "blizzard": {
        "name": "Blizzard", "type": "Ice", "category": "special", "base_power": 110, "accuracy": 0.70, "pp": 5,
        "secondary": {"chance": 0.10, "status": "FRZ"},
    },
    "ice-punch": {
        "name": "Ice Punch", "type": "Ice", "category": "physical", "base_power": 75, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.10, "status": "FRZ"},
    },
    "icicle-crash": {
        "name": "Icicle Crash", "type": "Ice", "category": "physical", "base_power": 85, "accuracy": 0.90, "pp": 10,
        "secondary": {"chance": 0.30, "flinch": True},
    },
    "ice-shard": {
        "name": "Ice Shard", "type": "Ice", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1, "pp": 30,
    },
    "freeze-dry": {
        "name": "Freeze-Dry", "type": "Ice", "category": "special", "base_power": 70, "accuracy": 1.0, "pp": 20,
        "secondary": {"chance": 0.10, "status": "FRZ"},
    },
    "icy-wind": {
        "name": "Icy Wind", "type": "Ice", "category": "special", "base_power": 55, "accuracy": 0.95, "pp": 15,
        "secondary": {"chance": 1.0, "boosts": {"spe": -1}},
    },
    "icicle-spear": {
        "name": "Icicle Spear", "type": "Ice", "category": "physical", "base_power": 25, "accuracy": 1.0, "pp": 30,
        "multi_hit": (2, 5),
    },
    "aurora-veil": {
        "name": "Aurora Veil", "type": "Ice", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "side_condition": "aurora_veil",
    },
    "snowscape": {
        "name": "Snowscape", "type": "Ice", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "weather": "Snow",
    },
    "hail": {
        "name": "Hail", "type": "Ice", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "weather": "Snow",
    },

    # =========================================================================
    # LUCHA (Fighting)
    # =========================================================================
    "close-combat": {
        "name": "Close Combat", "type": "Fighting", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 5,
        "makes_contact": True, "self_boosts": {"def": -1, "spd": -1},
    },
    "aura-sphere": {
        "name": "Aura Sphere", "type": "Fighting", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 20,
        "never_miss": True,
    },
    "drain-punch": {
        "name": "Drain Punch", "type": "Fighting", "category": "physical", "base_power": 75, "accuracy": 1.0, "pp": 10,
        "drain_percent": 0.50, "makes_contact": True,
    },
    "focus-blast": {
        "name": "Focus Blast", "type": "Fighting", "category": "special", "base_power": 120, "accuracy": 0.70, "pp": 5,
        "secondary": {"chance": 0.10, "boosts": {"spd": -1}},
    },
    "mach-punch": {
        "name": "Mach Punch", "type": "Fighting", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1, "pp": 30,
        "makes_contact": True,
    },
    "superpower": {
        "name": "Superpower", "type": "Fighting", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 5,
        "makes_contact": True, "self_boosts": {"atk": -1, "def": -1},
    },
    "body-press": {
        "name": "Body Press", "type": "Fighting", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 10,
        "makes_contact": True, "override_offensive_stat": "def",
    },
    "bulk-up": {
        "name": "Bulk Up", "type": "Fighting", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "self_boosts": {"atk": 1, "def": 1},
    },

    # =========================================================================
    # VENENO (Poison)
    # =========================================================================
    "sludge-bomb": {
        "name": "Sludge Bomb", "type": "Poison", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.30, "status": "PSN"},
    },
    "sludge-wave": {
        "name": "Sludge Wave", "type": "Poison", "category": "special", "base_power": 95, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "status": "PSN"},
    },
    "gunk-shot": {
        "name": "Gunk Shot", "type": "Poison", "category": "physical", "base_power": 120, "accuracy": 0.80, "pp": 5,
        "secondary": {"chance": 0.30, "status": "PSN"},
    },
    "poison-jab": {
        "name": "Poison Jab", "type": "Poison", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 20,
        "makes_contact": True, "secondary": {"chance": 0.30, "status": "PSN"},
    },
    "toxic": {
        "name": "Toxic", "type": "Poison", "category": "status", "base_power": 0, "accuracy": 0.90, "pp": 10,
        "target_status": "TOX",
    },
    "toxic-spikes": {
        "name": "Toxic Spikes", "type": "Poison", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "side_condition": "toxic_spikes",
    },

    # =========================================================================
    # TIERRA (Ground)
    # =========================================================================
    "earthquake": {
        "name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0, "pp": 10,
    },
    "earth-power": {
        "name": "Earth Power", "type": "Ground", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "boosts": {"spd": -1}},
    },
    "high-horsepower": {
        "name": "High Horsepower", "type": "Ground", "category": "physical", "base_power": 95, "accuracy": 0.95, "pp": 10,
        "makes_contact": True,
    },
    "bulldoze": {
        "name": "Bulldoze", "type": "Ground", "category": "physical", "base_power": 60, "accuracy": 1.0, "pp": 20,
        "secondary": {"chance": 1.0, "boosts": {"spe": -1}},
    },
    "spikes": {
        "name": "Spikes", "type": "Ground", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "side_condition": "spikes",
    },

    # =========================================================================
    # VOLADOR (Flying)
    # =========================================================================
    "air-slash": {
        "name": "Air Slash", "type": "Flying", "category": "special", "base_power": 75, "accuracy": 0.95, "pp": 15,
        "secondary": {"chance": 0.30, "flinch": True},
    },
    "brave-bird": {
        "name": "Brave Bird", "type": "Flying", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 15,
        "recoil_percent": 0.33, "makes_contact": True,
    },
    "hurricane": {
        "name": "Hurricane", "type": "Flying", "category": "special", "base_power": 110, "accuracy": 0.70, "pp": 10,
        "secondary": {"chance": 0.30, "volatile_status": "confusion"},
    },
    "aerial-ace": {
        "name": "Aerial Ace", "type": "Flying", "category": "physical", "base_power": 60, "accuracy": 1.0, "pp": 20,
        "never_miss": True, "makes_contact": True,
    },
    "dual-wingbeat": {
        "name": "Dual Wingbeat", "type": "Flying", "category": "physical", "base_power": 40, "accuracy": 0.90, "pp": 10,
        "multi_hit": (2, 2), "makes_contact": True,
    },
    "roost": {
        "name": "Roost", "type": "Flying", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "heal_fraction": 0.50,
    },
    "acrobatics": {
        "name": "Acrobatics", "type": "Flying", "category": "physical", "base_power": 55, "accuracy": 1.0, "pp": 15,
        "makes_contact": True,
    },
    "defog": {
        "name": "Defog", "type": "Flying", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 15,
        "hazard_clear": "defog", "boosts": {"evasion": -1},
    },
    "tailwind": {
        "name": "Tailwind", "type": "Flying", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 15,
        "side_condition": "tailwind",
    },

    # =========================================================================
    # PSÍQUICO (Psychic)
    # =========================================================================
    "psychic": {
        "name": "Psychic", "type": "Psychic", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "boosts": {"spd": -1}},
    },
    "psyshock": {
        "name": "Psyshock", "type": "Psychic", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 10,
        "override_defensive_stat": "def",
    },
    "zen-headbutt": {
        "name": "Zen Headbutt", "type": "Psychic", "category": "physical", "base_power": 80, "accuracy": 0.90, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.20, "flinch": True},
    },
    "calm-mind": {
        "name": "Calm Mind", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "self_boosts": {"spa": 1, "spd": 1},
    },
    "agility": {
        "name": "Agility", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 30,
        "self_boosts": {"spe": 2},
    },
    "reflect": {
        "name": "Reflect", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "side_condition": "reflect",
    },
    "light-screen": {
        "name": "Light Screen", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 30,
        "side_condition": "light_screen",
    },
    "trick-room": {
        "name": "Trick Room", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "priority": -7, "pp": 5,
        "pseudo_weather": "trick_room",
    },
    "psychic-terrain": {
        "name": "Psychic Terrain", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "terrain": "Psychic",
    },
    "rest": {
        "name": "Rest", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "heal_fraction": 1.0,
    },

    # =========================================================================
    # BICHO (Bug)
    # =========================================================================
    "bug-buzz": {
        "name": "Bug Buzz", "type": "Bug", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "boosts": {"spd": -1}},
    },
    "u-turn": {
        "name": "U-turn", "type": "Bug", "category": "physical", "base_power": 70, "accuracy": 1.0, "pp": 20,
        "makes_contact": True, "self_switch": True,
    },
    "x-scissor": {
        "name": "X-Scissor", "type": "Bug", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "makes_contact": True,
    },
    "first-impression": {
        "name": "First Impression", "type": "Bug", "category": "physical", "base_power": 90, "accuracy": 1.0, "priority": 2, "pp": 10,
        "makes_contact": True,
    },
    "quiver-dance": {
        "name": "Quiver Dance", "type": "Bug", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "self_boosts": {"spa": 1, "spd": 1, "spe": 1},
    },
    "sticky-web": {
        "name": "Sticky Web", "type": "Bug", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "side_condition": "sticky_web",
    },

    # =========================================================================
    # ROCA (Rock)
    # =========================================================================
    "stone-edge": {
        "name": "Stone Edge", "type": "Rock", "category": "physical", "base_power": 100, "accuracy": 0.80, "pp": 5,
        "crit_ratio": 2,
    },
    "rock-slide": {
        "name": "Rock Slide", "type": "Rock", "category": "physical", "base_power": 75, "accuracy": 0.90, "pp": 10,
        "secondary": {"chance": 0.30, "flinch": True},
    },
    "power-gem": {
        "name": "Power Gem", "type": "Rock", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 20,
    },
    "stealth-rock": {
        "name": "Stealth Rock", "type": "Rock", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "side_condition": "stealth_rock",
    },
    "rock-tomb": {
        "name": "Rock Tomb", "type": "Rock", "category": "physical", "base_power": 60, "accuracy": 0.95, "pp": 15,
        "secondary": {"chance": 1.0, "boosts": {"spe": -1}},
    },
    "rock-blast": {
        "name": "Rock Blast", "type": "Rock", "category": "physical", "base_power": 25, "accuracy": 0.90, "pp": 10,
        "multi_hit": (2, 5),
    },
    "sandstorm": {
        "name": "Sandstorm", "type": "Rock", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "weather": "Sandstorm",
    },

    # =========================================================================
    # FANTASMA (Ghost)
    # =========================================================================
    "shadow-ball": {
        "name": "Shadow Ball", "type": "Ghost", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.20, "boosts": {"spd": -1}},
    },
    "shadow-claw": {
        "name": "Shadow Claw", "type": "Ghost", "category": "physical", "base_power": 70, "accuracy": 1.0, "pp": 15,
        "crit_ratio": 2, "makes_contact": True,
    },
    "shadow-sneak": {
        "name": "Shadow Sneak", "type": "Ghost", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1, "pp": 30,
        "makes_contact": True,
    },
    "poltergeist": {
        "name": "Poltergeist", "type": "Ghost", "category": "physical", "base_power": 110, "accuracy": 0.90, "pp": 5,
    },
    "hex": {
        "name": "Hex", "type": "Ghost", "category": "special", "base_power": 65, "accuracy": 1.0, "pp": 10,
    },

    # =========================================================================
    # DRAGÓN (Dragon)
    # =========================================================================
    "dragon-claw": {
        "name": "Dragon Claw", "type": "Dragon", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "makes_contact": True,
    },
    "dragon-pulse": {
        "name": "Dragon Pulse", "type": "Dragon", "category": "special", "base_power": 85, "accuracy": 1.0, "pp": 10,
    },
    "draco-meteor": {
        "name": "Draco Meteor", "type": "Dragon", "category": "special", "base_power": 130, "accuracy": 0.90, "pp": 5,
        "self_boosts": {"spa": -2},
    },
    "outrage": {
        "name": "Outrage", "type": "Dragon", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 10,
        "makes_contact": True,
    },
    "dragon-dance": {
        "name": "Dragon Dance", "type": "Dragon", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "self_boosts": {"atk": 1, "spe": 1},
    },
    "dragon-tail": {
        "name": "Dragon Tail", "type": "Dragon", "category": "physical", "base_power": 60, "accuracy": 0.90, "priority": -6, "pp": 10,
        "makes_contact": True, "force_switch": True,
    },
    "scale-shot": {
        "name": "Scale Shot", "type": "Dragon", "category": "physical", "base_power": 25, "accuracy": 0.90, "pp": 20,
        "multi_hit": (2, 5), "self_boosts": {"def": -1, "spe": 1},
    },

    # =========================================================================
    # ACERO (Steel)
    # =========================================================================
    "flash-cannon": {
        "name": "Flash Cannon", "type": "Steel", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 10,
        "secondary": {"chance": 0.10, "boosts": {"spd": -1}},
    },
    "iron-head": {
        "name": "Iron Head", "type": "Steel", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.30, "flinch": True},
    },
    "meteor-mash": {
        "name": "Meteor Mash", "type": "Steel", "category": "physical", "base_power": 90, "accuracy": 0.90, "pp": 10,
        "makes_contact": True, "secondary": {"chance": 0.20, "self_boosts": {"atk": 1}},
    },
    "bullet-punch": {
        "name": "Bullet Punch", "type": "Steel", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1, "pp": 30,
        "makes_contact": True,
    },
    "iron-defense": {
        "name": "Iron Defense", "type": "Steel", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 15,
        "self_boosts": {"def": 2},
    },

    # =========================================================================
    # SINIESTRO (Dark)
    # =========================================================================
    "dark-pulse": {
        "name": "Dark Pulse", "type": "Dark", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.20, "flinch": True},
    },
    "crunch": {
        "name": "Crunch", "type": "Dark", "category": "physical", "base_power": 80, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.20, "boosts": {"def": -1}},
    },
    "knock-off": {
        "name": "Knock Off", "type": "Dark", "category": "physical", "base_power": 65, "accuracy": 1.0, "pp": 20,
        "makes_contact": True,
    },
    "sucker-punch": {
        "name": "Sucker Punch", "type": "Dark", "category": "physical", "base_power": 70, "accuracy": 1.0, "priority": 1, "pp": 5,
        "makes_contact": True,
    },
    "taunt": {
        "name": "Taunt", "type": "Dark", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "volatile_status": "taunt",
    },
    "nasty-plot": {
        "name": "Nasty Plot", "type": "Dark", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "self_boosts": {"spa": 2},
    },
    "parting-shot": {
        "name": "Parting Shot", "type": "Dark", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "boosts": {"atk": -1, "spa": -1}, "self_switch": True,
    },

    # =========================================================================
    # HADA (Fairy)
    # =========================================================================
    "moonblast": {
        "name": "Moonblast", "type": "Fairy", "category": "special", "base_power": 95, "accuracy": 1.0, "pp": 15,
        "secondary": {"chance": 0.30, "boosts": {"spa": -1}},
    },
    "dazzling-gleam": {
        "name": "Dazzling Gleam", "type": "Fairy", "category": "special", "base_power": 80, "accuracy": 1.0, "pp": 10,
    },
    "play-rough": {
        "name": "Play Rough", "type": "Fairy", "category": "physical", "base_power": 90, "accuracy": 0.90, "pp": 10,
        "makes_contact": True, "secondary": {"chance": 0.10, "boosts": {"atk": -1}},
    },
    "draining-kiss": {
        "name": "Draining Kiss", "type": "Fairy", "category": "special", "base_power": 50, "accuracy": 1.0, "pp": 10,
        "drain_percent": 0.75, "makes_contact": True,
    },
    "misty-terrain": {
        "name": "Misty Terrain", "type": "Fairy", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "terrain": "Misty",
    },

    # =========================================================================
    # NORMAL
    # =========================================================================
    "body-slam": {
        "name": "Body Slam", "type": "Normal", "category": "physical", "base_power": 85, "accuracy": 1.0, "pp": 15,
        "makes_contact": True, "secondary": {"chance": 0.30, "status": "PAR"},
    },
    "double-edge": {
        "name": "Double-Edge", "type": "Normal", "category": "physical", "base_power": 120, "accuracy": 1.0, "pp": 15,
        "recoil_percent": 0.33, "makes_contact": True,
    },
    "extreme-speed": {
        "name": "Extreme Speed", "type": "Normal", "category": "physical", "base_power": 80, "accuracy": 1.0, "priority": 2, "pp": 5,
        "makes_contact": True,
    },
    "quick-attack": {
        "name": "Quick Attack", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1, "pp": 30,
        "makes_contact": True,
    },
    "fake-out": {
        "name": "Fake Out", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 3, "pp": 10,
        "makes_contact": True, "secondary": {"chance": 1.0, "flinch": True},
    },
    "rapid-spin": {
        "name": "Rapid Spin", "type": "Normal", "category": "physical", "base_power": 50, "accuracy": 1.0, "pp": 40,
        "makes_contact": True, "hazard_clear": "rapid_spin", "self_boosts": {"spe": 1},
    },
    "hyper-voice": {
        "name": "Hyper Voice", "type": "Normal", "category": "special", "base_power": 90, "accuracy": 1.0, "pp": 10,
    },
    "hyper-beam": {
        "name": "Hyper Beam", "type": "Normal", "category": "special", "base_power": 150, "accuracy": 0.90, "pp": 5,
        "must_recharge": True,
    },
    "giga-impact": {
        "name": "Giga Impact", "type": "Normal", "category": "physical", "base_power": 150, "accuracy": 0.90, "pp": 5,
        "makes_contact": True, "must_recharge": True,
    },
    "tackle": {
        "name": "Tackle", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0, "pp": 35,
        "makes_contact": True,
    },
    "swords-dance": {
        "name": "Swords Dance", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 20,
        "self_boosts": {"atk": 2},
    },
    "shell-smash": {
        "name": "Shell Smash", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 15,
        "self_boosts": {"def": -1, "spd": -1, "atk": 2, "spa": 2, "spe": 2},
    },
    "recover": {
        "name": "Recover", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "heal_fraction": 0.50,
    },
    "soft-boiled": {
        "name": "Soft-Boiled", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "heal_fraction": 0.50,
    },
    "slack-off": {
        "name": "Slack Off", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "heal_fraction": 0.50,
    },
    "protect": {
        "name": "Protect", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "priority": 4, "pp": 10,
        "volatile_status": "protect",
    },
    "detect": {
        "name": "Detect", "type": "Fighting", "category": "status", "base_power": 0, "accuracy": 1.0, "priority": 4, "pp": 5,
        "volatile_status": "protect",
    },
    "substitute": {
        "name": "Substitute", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "pp": 10,
        "volatile_status": "substitute",
    },
    "roar": {
        "name": "Roar", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "priority": -6, "pp": 20,
        "force_switch": True, "never_miss": True,
    },
    "whirlwind": {
        "name": "Whirlwind", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0, "priority": -6, "pp": 20,
        "force_switch": True, "never_miss": True,
    },
}

_AILMENT_TO_STATUS = {
    "burn": "BRN",
    "paralysis": "PAR",
    "sleep": "SLP",
    "poison": "PSN",
    "bad-poison": "TOX",
    "freeze": "FRZ",
}

_AILMENT_TO_VOLATILE = {
    "confusion": "confusion",
    "leech-seed": "leech_seed",
    "trap": "partially_trapped",
}

_STAT_NAME_MAP = {
    "attack": "atk",
    "defense": "def",
    "special-attack": "spa",
    "special-defense": "spd",
    "speed": "spe",
    "accuracy": "accuracy",
    "evasion": "evasion",
}


def fetch_move_from_pokeapi(slug: str) -> Optional[dict]:
    """
    Consulta PokeAPI para obtener los datos oficiales de combate de un movimiento,
    incluyendo efectos secundarios, probabilidades de estado, retroceso (flinch),
    cambios de estadísticas, curación, crítico y multi-hit.
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
            never_miss = raw_acc is None and category != "status"
            accuracy = float(raw_acc) / 100.0 if raw_acc is not None else 1.0
            priority = int(data.get("priority") or 0)
            pp = int(data.get("pp") or 15)
            target_name = ((data.get("target") or {}).get("name") or "selected-pokemon").lower()

            meta = data.get("meta") or {}
            drain = int(meta.get("drain") or 0)
            drain_pct = drain / 100.0 if drain > 0 else 0.0
            recoil_pct = abs(drain) / 100.0 if drain < 0 else 0.0
            healing = int(meta.get("healing") or 0)
            heal_fraction = healing / 100.0 if healing > 0 else 0.0
            crit_rate = int(meta.get("crit_rate") or 0)
            crit_ratio = 1 + max(0, crit_rate)

            min_hits = meta.get("min_hits")
            max_hits = meta.get("max_hits")
            multi_hit = (int(min_hits), int(max_hits)) if min_hits and max_hits else None

            ailment_name = ((meta.get("ailment") or {}).get("name") or "none").lower()
            ailment_chance = int(meta.get("ailment_chance") or 0)
            flinch_chance = int(meta.get("flinch_chance") or 0)
            stat_chance = int(meta.get("stat_chance") or 0)

            stat_changes_raw = data.get("stat_changes") or []
            parsed_boosts: Dict[str, int] = {}
            for sc in stat_changes_raw:
                st_name = ((sc.get("stat") or {}).get("name") or "").lower()
                mapped_stat = _STAT_NAME_MAP.get(st_name)
                change_val = int(sc.get("change") or 0)
                if mapped_stat and change_val != 0:
                    parsed_boosts[mapped_stat] = change_val

            target_status = None
            volatile_status = None
            boosts = None
            self_boosts = None
            secondary: Dict[str, Any] = {}

            if category == "status":
                if ailment_name in _AILMENT_TO_STATUS:
                    target_status = _AILMENT_TO_STATUS[ailment_name]
                elif ailment_name in _AILMENT_TO_VOLATILE:
                    volatile_status = _AILMENT_TO_VOLATILE[ailment_name]
                if parsed_boosts:
                    if target_name in ("user", "users-field", "user-and-allies"):
                        self_boosts = parsed_boosts
                    else:
                        boosts = parsed_boosts
            else:
                # Ataque con daño: revisar efectos secundarios
                if ailment_name in _AILMENT_TO_STATUS and ailment_chance > 0:
                    secondary["chance"] = ailment_chance / 100.0
                    secondary["status"] = _AILMENT_TO_STATUS[ailment_name]
                elif ailment_name in _AILMENT_TO_VOLATILE and ailment_chance > 0:
                    secondary["chance"] = ailment_chance / 100.0
                    secondary["volatile_status"] = _AILMENT_TO_VOLATILE[ailment_name]

                if flinch_chance > 0:
                    secondary["chance"] = max(secondary.get("chance", 0.0), flinch_chance / 100.0)
                    secondary["flinch"] = True

                if parsed_boosts:
                    if stat_chance in (0, 100) and target_name == "user":
                        self_boosts = parsed_boosts
                    elif stat_chance > 0:
                        secondary["chance"] = max(secondary.get("chance", 0.0), stat_chance / 100.0)
                        if target_name == "user":
                            secondary["self_boosts"] = parsed_boosts
                        else:
                            secondary["boosts"] = parsed_boosts

            display_name = clean_slug.replace("-", " ").title()
            for n_entry in data.get("names", []):
                lang = (n_entry.get("language") or {}).get("name")
                if lang == "en" and n_entry.get("name"):
                    display_name = n_entry["name"]
                    break

            result = {
                "slug": clean_slug,
                "name": display_name,
                "type": move_type,
                "category": category,
                "base_power": power,
                "accuracy": accuracy,
                "never_miss": never_miss,
                "priority": priority,
                "pp": pp,
                "drain_percent": drain_pct,
                "recoil_percent": recoil_pct,
                "heal_fraction": heal_fraction,
                "crit_ratio": crit_ratio,
            }
            if multi_hit:
                result["multi_hit"] = multi_hit
            if boosts:
                result["boosts"] = boosts
            if self_boosts:
                result["self_boosts"] = self_boosts
            if target_status:
                result["target_status"] = target_status
            if volatile_status:
                result["volatile_status"] = volatile_status
            if secondary:
                result["secondary"] = secondary
            return result
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


def _merge_popular_and_effect_data(base_dict: dict, slug: str) -> dict:
    """Combina los datos base de la DB con effect_data y con POPULAR_MOVES para preservar todos los efectos."""
    merged = dict(POPULAR_MOVES.get(slug, {}))
    merged.update(base_dict)
    effect_data = base_dict.get("effect_data")
    if isinstance(effect_data, dict):
        merged.update(effect_data)
    merged["id"] = base_dict.get("slug") or base_dict.get("id") or slug
    return merged


def ensure_move_in_db(
    move_name_or_dict: Any,
    fallback_type: str = "Normal",
    sync_db: bool = True
) -> MoveState:
    """
    Verifica si un movimiento está en la tabla 'pokemon_moves' de Supabase.
    Si no está, obtiene sus datos de combate (catálogo Showdown o PokeAPI) y lo inserta en la tabla.
    """
    if isinstance(move_name_or_dict, dict):
        if "base_power" in move_name_or_dict or "category" in move_name_or_dict:
            slug_key = str(move_name_or_dict.get("id") or move_name_or_dict.get("slug") or move_name_or_dict.get("name") or "tackle").lower().replace(" ", "-")
            enriched = _merge_popular_and_effect_data(move_name_or_dict, slug_key)
            ms = MoveState.from_dict(enriched)
            if sync_db:
                try:
                    from backend.database import get_pokemon_move_from_db, save_pokemon_move_to_db
                    if not get_pokemon_move_from_db(ms.id):
                        save_pokemon_move_to_db({**ms.to_dict(), "slug": ms.id})
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
            from backend.database import get_pokemon_move_from_db
            existing = get_pokemon_move_from_db(slug)
            if existing:
                merged = _merge_popular_and_effect_data(existing, slug)
                return MoveState.from_dict(merged)
        except Exception:
            pass

    # 2. Si no está en la tabla, obtener sus datos de combate
    move_dict: Optional[dict] = None

    if slug in POPULAR_MOVES:
        d = POPULAR_MOVES[slug]
        move_dict = {"slug": slug, "id": slug, **d}
    else:
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

    return MoveState.from_dict(move_dict)


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
