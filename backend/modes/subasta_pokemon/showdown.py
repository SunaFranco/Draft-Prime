"""
backend/modes/subasta_pokemon/showdown.py - Exportador de equipos a formato Pokémon Showdown
"""

from typing import List, Dict


def export_team_to_showdown(username: str, pokemon_list: List[dict], items_list: List[str] = None) -> str:
    """
    Convierte la lista de Pokémon de un jugador a la sintaxis estándar de Pokémon Showdown.
    """
    items = items_list or []
    lines = [f"=== [gen9anythinggoes] Equipo de {username} ===", ""]

    for idx, poke in enumerate(pokemon_list):
        name = poke.get("name", "Pikachu")
        level = poke.get("level", 40)
        ability = poke.get("ability", "Static")
        item = items[idx] if idx < len(items) else "Leftovers"
        primary_type = poke.get("primary_type", "Normal")

        lines.append(f"{name} @ {item}")
        lines.append(f"Ability: {ability}")
        lines.append(f"Level: {level}")
        lines.append(f"Tera Type: {primary_type}")

        # Usar movimientos seleccionados por el jugador por nivel
        moves = poke.get("selected_moves")
        if not moves:
            moves = get_default_moves_for_type(primary_type)

        for move in moves[:4]:
            lines.append(f"- {move}")
        lines.append("")


    return "\n".join(lines)


def get_default_moves_for_type(primary_type: str) -> List[str]:
    """Genera 4 movimientos razonables según el tipo primario."""
    t = primary_type.capitalize()
    mapping = {
        "Fire": ["Flamethrower", "Fire Blast", "Will-O-Wisp", "Protect"],
        "Water": ["Scald", "Hydro Pump", "Ice Beam", "Protect"],
        "Grass": ["Giga Drain", "Energy Ball", "Toxic", "Synthesis"],
        "Electric": ["Thunderbolt", "Volt Switch", "Thunder Wave", "Protect"],
        "Psychic": ["Psychic", "Psyshock", "Calm Mind", "Recover"],
        "Dragon": ["Draco Meteor", "Dragon Pulse", "Dragon Dance", "Earthquake"],
        "Ghost": ["Shadow Ball", "Will-O-Wisp", "Hex", "Substitue"],
        "Dark": ["Dark Pulse", "Knock Off", "Sucker Punch", "Taunt"],
        "Steel": ["Flash Cannon", "Iron Head", "Stealth Rock", "Roost"],
        "Fighting": ["Close Combat", "Drain Punch", "Mach Punch", "Swords Dance"],
    }
    return mapping.get(t, ["Return", "Quick Attack", "Protect", "Toxic"])
