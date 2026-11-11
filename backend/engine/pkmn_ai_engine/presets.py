"""
backend/engine/pkmn_ai_engine/presets.py
Equipos prefabricados de Entrenadores PVE (Líderes de Gimnasio y Campeones).
Totalmente balanceados para combates 6v6 Singles con Megaevolución.
"""

from typing import List, Dict, Any

PVE_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "brock-rock",
        "name": "Líder Brock",
        "title": "Líder de Gimnasio Plateada",
        "difficulty": "easy",
        "avatar_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainers/brock.png",
        "description": "Especialista en Pokémon de tipo Roca y Tierra. Resistente y contundente.",
        "team": [
            {
                "species": "Geodude",
                "types": ["Rock", "Ground"],
                "level": 50,
                "current_hp": 130, "max_hp": 130,
                "stats": {"hp": 130, "atk": 110, "def": 130, "spa": 50, "spd": 50, "spe": 40},
                "item": "Hard Stone",
                "moves": [
                    {"name": "Rock Slide", "type": "Rock", "category": "physical", "base_power": 75, "accuracy": 0.90},
                    {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
                    {"name": "Tackle", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0},
                    {"name": "Defense Curl", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},
                ]
            },
            {
                "species": "Onix",
                "types": ["Rock", "Ground"],
                "level": 50,
                "current_hp": 125, "max_hp": 125,
                "stats": {"hp": 125, "atk": 75, "def": 180, "spa": 50, "spd": 65, "spe": 90},
                "item": "Leftovers",
                "moves": [
                    {"name": "Rock Tomb", "type": "Rock", "category": "physical", "base_power": 60, "accuracy": 0.95},
                    {"name": "Slam", "type": "Normal", "category": "physical", "base_power": 80, "accuracy": 0.75},
                    {"name": "Iron Tail", "type": "Steel", "category": "physical", "base_power": 100, "accuracy": 0.75},
                    {"name": "Stealth Rock", "type": "Rock", "category": "status", "base_power": 0, "accuracy": 1.0},
                ]
            },
            {
                "species": "Golem",
                "types": ["Rock", "Ground"],
                "level": 50,
                "current_hp": 160, "max_hp": 160,
                "stats": {"hp": 160, "atk": 140, "def": 150, "spa": 75, "spd": 85, "spe": 65},
                "item": "Muscle Band",
                "moves": [
                    {"name": "Stone Edge", "type": "Rock", "category": "physical", "base_power": 100, "accuracy": 0.80},
                    {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
                    {"name": "Heavy Slam", "type": "Steel", "category": "physical", "base_power": 80, "accuracy": 1.0},
                    {"name": "Explosion", "type": "Normal", "category": "physical", "base_power": 250, "accuracy": 1.0},
                ]
            },
            {
                "species": "Kabutops",
                "types": ["Rock", "Water"],
                "level": 50,
                "current_hp": 145, "max_hp": 145,
                "stats": {"hp": 145, "atk": 135, "def": 125, "spa": 85, "spd": 90, "spe": 100},
                "item": "Mystic Water",
                "moves": [
                    {"name": "Liquidation", "type": "Water", "category": "physical", "base_power": 85, "accuracy": 1.0},
                    {"name": "Aqua Jet", "type": "Water", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
                    {"name": "Stone Edge", "type": "Rock", "category": "physical", "base_power": 100, "accuracy": 0.80},
                    {"name": "Swords Dance", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},
                ]
            },
            {
                "species": "Omastar",
                "types": ["Rock", "Water"],
                "level": 50,
                "current_hp": 150, "max_hp": 150,
                "stats": {"hp": 150, "atk": 80, "def": 145, "spa": 135, "spd": 90, "spe": 75},
                "item": "Expert Belt",
                "moves": [
                    {"name": "Hydro Pump", "type": "Water", "category": "special", "base_power": 110, "accuracy": 0.80},
                    {"name": "Ancient Power", "type": "Rock", "category": "special", "base_power": 60, "accuracy": 1.0},
                    {"name": "Ice Beam", "type": "Ice", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Shell Smash", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},
                ]
            },
            {
                "species": "Aerodactyl",
                "types": ["Rock", "Flying"],
                "level": 50,
                "current_hp": 160, "max_hp": 160,
                "stats": {"hp": 160, "atk": 125, "def": 85, "spa": 80, "spd": 95, "spe": 150},
                "item": "Aerodactylite",
                "mega_stone": "Aerodactylite",
                "can_mega": True,
                "moves": [
                    {"name": "Stone Edge", "type": "Rock", "category": "physical", "base_power": 100, "accuracy": 0.80},
                    {"name": "Wing Attack", "type": "Flying", "category": "physical", "base_power": 60, "accuracy": 1.0},
                    {"name": "Crunch", "type": "Dark", "category": "physical", "base_power": 80, "accuracy": 1.0},
                    {"name": "Iron Head", "type": "Steel", "category": "physical", "base_power": 80, "accuracy": 1.0},
                ]
            }
        ]
    },
    {
        "id": "cynthia-sinnoh",
        "name": "Campeona Cynthia",
        "title": "Campeona de Sinnoh",
        "difficulty": "hard",
        "avatar_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainers/cynthia.png",
        "description": "Una de las entrenadoras más temidas. Equipo balanceado, cobertura perfecta y un Lucario devastador.",
        "team": [
            {
                "species": "Spiritomb",
                "types": ["Ghost", "Dark"],
                "level": 50,
                "current_hp": 135, "max_hp": 135,
                "stats": {"hp": 135, "atk": 112, "def": 128, "spa": 112, "spd": 128, "spe": 55},
                "item": "Leftovers",
                "moves": [
                    {"name": "Shadow Ball", "type": "Ghost", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Dark Pulse", "type": "Dark", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Psychic", "type": "Psychic", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Will-O-Wisp", "type": "Fire", "category": "status", "base_power": 0, "accuracy": 0.85},
                ]
            },
            {
                "species": "Roserade",
                "types": ["Grass", "Poison"],
                "level": 50,
                "current_hp": 140, "max_hp": 140,
                "stats": {"hp": 140, "atk": 90, "def": 85, "spa": 145, "spd": 125, "spe": 110},
                "item": "Life Orb",
                "moves": [
                    {"name": "Giga Drain", "type": "Grass", "category": "special", "base_power": 75, "accuracy": 1.0},
                    {"name": "Sludge Bomb", "type": "Poison", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Shadow Ball", "type": "Ghost", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Dazzling Gleam", "type": "Fairy", "category": "special", "base_power": 80, "accuracy": 1.0},
                ]
            },
            {
                "species": "Togekiss",
                "types": ["Fairy", "Flying"],
                "level": 50,
                "current_hp": 165, "max_hp": 165,
                "stats": {"hp": 165, "atk": 70, "def": 115, "spa": 140, "spd": 135, "spe": 100},
                "item": "King's Rock",
                "moves": [
                    {"name": "Air Slash", "type": "Flying", "category": "special", "base_power": 75, "accuracy": 0.95},
                    {"name": "Dazzling Gleam", "type": "Fairy", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Aura Sphere", "type": "Fighting", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Thunder Wave", "type": "Electric", "category": "status", "base_power": 0, "accuracy": 0.90},
                ]
            },
            {
                "species": "Milotic",
                "types": ["Water"],
                "level": 50,
                "current_hp": 175, "max_hp": 175,
                "stats": {"hp": 175, "atk": 80, "def": 99, "spa": 120, "spd": 145, "spe": 101},
                "item": "Flame Orb",
                "moves": [
                    {"name": "Scald", "type": "Water", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Ice Beam", "type": "Ice", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Recover", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},
                    {"name": "Dragon Pulse", "type": "Dragon", "category": "special", "base_power": 85, "accuracy": 1.0},
                ]
            },
            {
                "species": "Garchomp",
                "types": ["Dragon", "Ground"],
                "level": 50,
                "current_hp": 188, "max_hp": 188,
                "stats": {"hp": 188, "atk": 150, "def": 115, "spa": 100, "spd": 105, "spe": 122},
                "item": "Yache Berry",
                "moves": [
                    {"name": "Dragon Claw", "type": "Dragon", "category": "physical", "base_power": 80, "accuracy": 1.0},
                    {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
                    {"name": "Stone Edge", "type": "Rock", "category": "physical", "base_power": 100, "accuracy": 0.80},
                    {"name": "Swords Dance", "type": "Normal", "category": "status", "base_power": 0, "accuracy": 1.0},
                ]
            },
            {
                "species": "Lucario",
                "types": ["Fighting", "Steel"],
                "level": 50,
                "current_hp": 150, "max_hp": 150,
                "stats": {"hp": 150, "atk": 130, "def": 90, "spa": 135, "spd": 90, "spe": 110},
                "item": "Lucarionite",
                "mega_stone": "Lucarionite",
                "can_mega": True,
                "moves": [
                    {"name": "Close Combat", "type": "Fighting", "category": "physical", "base_power": 120, "accuracy": 1.0},
                    {"name": "Flash Cannon", "type": "Steel", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Extreme Speed", "type": "Normal", "category": "physical", "base_power": 80, "accuracy": 1.0, "priority": 2},
                    {"name": "Aura Sphere", "type": "Fighting", "category": "special", "base_power": 80, "accuracy": 1.0},
                ]
            }
        ]
    },
    {
        "id": "red-kanto",
        "name": "Entrenador Red",
        "title": "Leyenda de Kanto",
        "difficulty": "hard",
        "avatar_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainers/red.png",
        "description": "El mítico entrenador del Monte Plateado con su Mega Charizard X.",
        "team": [
            {
                "species": "Pikachu",
                "types": ["Electric"],
                "level": 50,
                "current_hp": 120, "max_hp": 120,
                "stats": {"hp": 120, "atk": 115, "def": 60, "spa": 110, "spd": 70, "spe": 120},
                "item": "Light Ball",
                "moves": [
                    {"name": "Volt Tackle", "type": "Electric", "category": "physical", "base_power": 120, "accuracy": 1.0},
                    {"name": "Iron Tail", "type": "Steel", "category": "physical", "base_power": 100, "accuracy": 0.75},
                    {"name": "Quick Attack", "type": "Normal", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
                    {"name": "Thunder Wave", "type": "Electric", "category": "status", "base_power": 0, "accuracy": 0.90},
                ]
            },
            {
                "species": "Lapras",
                "types": ["Water", "Ice"],
                "level": 50,
                "current_hp": 210, "max_hp": 210,
                "stats": {"hp": 210, "atk": 105, "def": 100, "spa": 105, "spd": 115, "spe": 80},
                "item": "Leftovers",
                "moves": [
                    {"name": "Surf", "type": "Water", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Ice Beam", "type": "Ice", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Thunderbolt", "type": "Electric", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Body Slam", "type": "Normal", "category": "physical", "base_power": 85, "accuracy": 1.0},
                ]
            },
            {
                "species": "Snorlax",
                "types": ["Normal"],
                "level": 50,
                "current_hp": 240, "max_hp": 240,
                "stats": {"hp": 240, "atk": 130, "def": 85, "spa": 85, "spd": 130, "spe": 50},
                "item": "Chesto Berry",
                "moves": [
                    {"name": "Body Slam", "type": "Normal", "category": "physical", "base_power": 85, "accuracy": 1.0},
                    {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
                    {"name": "Rest", "type": "Psychic", "category": "status", "base_power": 0, "accuracy": 1.0},
                    {"name": "Crunch", "type": "Dark", "category": "physical", "base_power": 80, "accuracy": 1.0},
                ]
            },
            {
                "species": "Venusaur",
                "types": ["Grass", "Poison"],
                "level": 50,
                "current_hp": 160, "max_hp": 160,
                "stats": {"hp": 160, "atk": 102, "def": 103, "spa": 120, "spd": 120, "spe": 100},
                "item": "Black Sludge",
                "moves": [
                    {"name": "Giga Drain", "type": "Grass", "category": "special", "base_power": 75, "accuracy": 1.0},
                    {"name": "Sludge Bomb", "type": "Poison", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Sleep Powder", "type": "Grass", "category": "status", "base_power": 0, "accuracy": 0.75},
                    {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
                ]
            },
            {
                "species": "Blastoise",
                "types": ["Water"],
                "level": 50,
                "current_hp": 159, "max_hp": 159,
                "stats": {"hp": 159, "atk": 103, "def": 120, "spa": 105, "spd": 125, "spe": 98},
                "item": "Mystic Water",
                "moves": [
                    {"name": "Hydro Pump", "type": "Water", "category": "special", "base_power": 110, "accuracy": 0.80},
                    {"name": "Ice Beam", "type": "Ice", "category": "special", "base_power": 90, "accuracy": 1.0},
                    {"name": "Flash Cannon", "type": "Steel", "category": "special", "base_power": 80, "accuracy": 1.0},
                    {"name": "Aqua Jet", "type": "Water", "category": "physical", "base_power": 40, "accuracy": 1.0, "priority": 1},
                ]
            },
            {
                "species": "Charizard",
                "types": ["Fire", "Flying"],
                "level": 50,
                "current_hp": 158, "max_hp": 158,
                "stats": {"hp": 158, "atk": 104, "def": 98, "spa": 129, "spd": 105, "spe": 120},
                "item": "Charizardite X",
                "mega_stone": "Charizardite X",
                "can_mega": True,
                "moves": [
                    {"name": "Flare Blitz", "type": "Fire", "category": "physical", "base_power": 120, "accuracy": 1.0},
                    {"name": "Dragon Claw", "type": "Dragon", "category": "physical", "base_power": 80, "accuracy": 1.0},
                    {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
                    {"name": "Dragon Dance", "type": "Dragon", "category": "status", "base_power": 0, "accuracy": 1.0},
                ]
            }
        ]
    }
]


def get_preset_by_id(preset_id: str) -> Dict[str, Any] | None:
    for p in PVE_PRESETS:
        if p["id"].lower() == preset_id.lower():
            return p
    return None
