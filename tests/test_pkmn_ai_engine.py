"""
tests/test_pkmn_ai_engine.py
Tests unitarios exhaustivos para el motor modular pkmn_ai_engine.
"""

import sys
from backend.engine.pkmn_ai_engine import (
    get_type_effectiveness,
    calculate_damage,
    PokemonState,
    MoveState,
    StatBlock,
    BattleSnapshot,
    Action,
    check_can_mega,
    trigger_mega_evolution,
    OpponentTracker,
    PokemonAIAgent,
    CombatEngine,
    PVE_PRESETS,
    get_preset_by_id,
)


def test_type_effectiveness():
    # Inmunidades
    assert get_type_effectiveness("Electric", ["Ground"]) == 0.0
    assert get_type_effectiveness("Dragon", ["Fairy"]) == 0.0
    assert get_type_effectiveness("Normal", ["Ghost"]) == 0.0
    assert get_type_effectiveness("Poison", ["Steel"]) == 0.0
    assert get_type_effectiveness("Psychic", ["Dark"]) == 0.0

    # Súper eficaz simple
    assert get_type_effectiveness("Water", ["Fire"]) == 2.0
    assert get_type_effectiveness("Fire", ["Grass"]) == 2.0

    # Súper eficaz cuádruple (4x)
    assert get_type_effectiveness("Rock", ["Fire", "Flying"]) == 4.0
    assert get_type_effectiveness("Electric", ["Water", "Flying"]) == 4.0

    # Resistencias (0.5x y 0.25x)
    assert get_type_effectiveness("Fire", ["Water"]) == 0.5
    assert get_type_effectiveness("Grass", ["Fire", "Flying"]) == 0.25


def test_damage_calculation():
    charizard = PokemonState(
        id="charizard",
        species="Charizard",
        types=("Fire", "Flying"),
        level=50,
        current_hp=150,
        max_hp=150,
        stats=StatBlock(hp=150, atk=100, def_=100, spa=150, spd=100, spe=120)
    )

    venusaur = PokemonState(
        id="venusaur",
        species="Venusaur",
        types=("Grass", "Poison"),
        level=50,
        current_hp=150,
        max_hp=150,
        stats=StatBlock(hp=150, atk=100, def_=100, spa=120, spd=120, spe=100)
    )

    flamethrower = MoveState(
        id="flamethrower",
        name="Flamethrower",
        type="Fire",
        category="special",
        base_power=90,
        accuracy=1.0,
    )

    dmg, eff, is_immune = calculate_damage(charizard, venusaur, flamethrower, rng_factor=1.0)
    assert not is_immune
    assert eff == 2.0
    assert dmg > 90  # Con STAB (1.5x) y debilidad (2.0x), el daño debe ser contundente


def test_mega_evolution():
    charizard = PokemonState(
        id="charizard",
        species="Charizard",
        types=("Fire", "Flying"),
        current_hp=150,
        max_hp=150,
        item="Charizardite X",
        mega_stone="Charizardite X",
        can_mega=True,
        stats=StatBlock(hp=150, atk=100, def_=100, spa=130, spd=100, spe=120),
    )

    stone = check_can_mega(charizard)
    assert stone == "charizardite x"

    success = trigger_mega_evolution(charizard, stone)
    assert success is True
    assert charizard.is_mega is True
    assert charizard.species == "Mega Charizard X"
    assert charizard.types == ("Fire", "Dragon")  # Cambio oficial de tipo
    assert charizard.stats.atk == 146             # +46 Atk


def test_opponent_tracker():
    tracker = OpponentTracker()
    tracker.record_move_used("Gengar", "Shadow Ball")

    tracked = tracker.get_or_create("Gengar")
    assert "Shadow Ball" in tracked.revealed_moves

    dummy_gengar = PokemonState(
        id="gengar",
        species="Gengar",
        types=("Ghost", "Poison"),
        stats=StatBlock(hp=120, atk=80, def_=80, spa=150, spd=95, spe=130),
        moves=[MoveState(id="shadow-ball", name="Shadow Ball", type="Ghost", category="special", base_power=80)]
    )

    estimated = tracked.get_estimated_moves(dummy_gengar)
    assert len(estimated) == 4
    # El primer movimiento es el revelado
    assert estimated[0].name == "Shadow Ball"
    # El segundo movimiento deducido debe tener el tipo Poison
    assert any(m.type == "Poison" for m in estimated)


def test_ai_agent_lethal_decision():
    # IA tiene a Jolteon (rápido y con Thunderbolt)
    ai_jolteon = PokemonState(
        id="jolteon",
        species="Jolteon",
        types=("Electric",),
        level=50,
        current_hp=130,
        max_hp=130,
        stats=StatBlock(hp=130, atk=80, def_=80, spa=140, spd=110, spe=160),
        moves=[
            MoveState(id="thunderbolt", name="Thunderbolt", type="Electric", category="special", base_power=90),
            MoveState(id="tackle", name="Tackle", type="Normal", category="physical", base_power=40),
        ]
    )

    # Rival es un Gyarados debilitado (Water/Flying con 30 HP restantes)
    player_gyarados = PokemonState(
        id="gyarados",
        species="Gyarados",
        types=("Water", "Flying"),
        level=50,
        current_hp=30,
        max_hp=160,
        stats=StatBlock(hp=160, atk=140, def_=100, spa=80, spd=120, spe=100),
    )

    snapshot = BattleSnapshot(
        turn=1,
        ai_active=ai_jolteon,
        opponent_active=player_gyarados,
    )

    agent = PokemonAIAgent(difficulty="hard")
    decision = agent.decide_action(snapshot)

    assert decision.action.type == "MOVE"
    assert decision.action.choice == "thunderbolt"
    assert "LETAL" in decision.debug_rationale


def test_ai_agent_switch_decision():
    # IA tiene activo a un Charizard casi muerto (10 HP) frente a un Blastoise rival con Surf
    ai_charizard = PokemonState(
        id="charizard",
        species="Charizard",
        types=("Fire", "Flying"),
        current_hp=10,
        max_hp=150,
        stats=StatBlock(hp=150, atk=100, def_=90, spa=130, spd=100, spe=120),
        moves=[MoveState(id="scratch", name="Scratch", type="Normal", category="physical", base_power=40)]
    )

    # En la banca la IA tiene a Venusaur con 100% HP y Giga Drain (counter perfecto para Blastoise)
    ai_venusaur = PokemonState(
        id="venusaur",
        species="Venusaur",
        types=("Grass", "Poison"),
        current_hp=160,
        max_hp=160,
        stats=StatBlock(hp=160, atk=100, def_=100, spa=130, spd=120, spe=100),
        moves=[MoveState(id="giga-drain", name="Giga Drain", type="Grass", category="special", base_power=75)]
    )

    player_blastoise = PokemonState(
        id="blastoise",
        species="Blastoise",
        types=("Water",),
        current_hp=160,
        max_hp=160,
        stats=StatBlock(hp=160, atk=100, def_=120, spa=105, spd=120, spe=90),
        moves=[MoveState(id="surf", name="Surf", type="Water", category="special", base_power=90)]
    )

    snapshot = BattleSnapshot(
        turn=1,
        ai_active=ai_charizard,
        ai_bench=[ai_venusaur],
        opponent_active=player_blastoise,
    )

    tracker = OpponentTracker()
    tracker.record_move_used("Blastoise", "Surf")

    agent = PokemonAIAgent(difficulty="hard", tracker=tracker)
    decision = agent.decide_action(snapshot)

    # Ante la muerte inminente y teniendo a Venusaur en banca, la IA debe cambiar
    assert decision.action.type == "SWITCH"
    assert decision.action.choice == "venusaur"


def test_combat_engine_resolution():
    # Pikachu (rápido) contra Squirtle
    pikachu = PokemonState(
        id="pikachu",
        species="Pikachu",
        types=("Electric",),
        current_hp=100,
        max_hp=100,
        stats=StatBlock(hp=100, atk=80, def_=60, spa=80, spd=70, spe=130),
        moves=[MoveState(id="thunder-shock", name="Thunder Shock", type="Electric", category="special", base_power=40)]
    )

    squirtle = PokemonState(
        id="squirtle",
        species="Squirtle",
        types=("Water",),
        current_hp=100,
        max_hp=100,
        stats=StatBlock(hp=100, atk=70, def_=90, spa=70, spd=90, spe=60),
        moves=[MoveState(id="water-gun", name="Water Gun", type="Water", category="special", base_power=40)]
    )

    snapshot = BattleSnapshot(
        turn=1,
        player_active=pikachu,
        ai_active=squirtle,
    )

    engine = CombatEngine()
    player_act = Action(type="MOVE", choice="thunder-shock")
    ai_act = Action(type="MOVE", choice="water-gun")

    result = engine.resolve_turn(snapshot, player_act, ai_act)

    assert len(result.events) > 0
    # Como Pikachu es más rápido, el primer evento de movimiento debe ser Pikachu
    move_events = [e for e in result.events if e.get("type") == "MOVE"]
    assert len(move_events) >= 1
    assert move_events[0]["pokemon"] == "Pikachu"
    # El snapshot debe haberse incrementado a turno 2
    assert result.new_snapshot.turn == 2


def test_presets_loaded():
    assert len(PVE_PRESETS) >= 3
    brock = get_preset_by_id("brock-rock")
    assert brock is not None
    assert len(brock["team"]) == 6
    # Aerodactyl de Brock tiene Aerodactylite
    aero = [p for p in brock["team"] if p["species"] == "Aerodactyl"][0]
    assert aero["mega_stone"] == "Aerodactylite"
    assert aero["can_mega"] is True


def test_adapt_draft_pokemon_conversion():
    from backend.engine.pkmn_ai_engine.core.adapter import adapt_draft_pokemon

    # Simular exactamente el dict que genera la subasta para un Pokémon
    raw_subasta_poke = {
        "name": "Charizard",
        "level": 35,
        "types": ["Fire", "Flying"],
        "stats": {
            "hp": 78,
            "attack": 84,
            "defense": 78,
            "special-attack": 109,
            "special-defense": 85,
            "speed": 100
        },
        "selected_moves": ["Flamethrower", "Air Slash", "Dragon Claw", "Protect"],
        "item": "Charizardite X",
        "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/6.png"
    }

    adapted = adapt_draft_pokemon(raw_subasta_poke)
    assert adapted.species == "Charizard"
    assert adapted.level == 35
    assert adapted.types == ("Fire", "Flying")
    assert adapted.max_hp > 100  # HP calculado a nivel 35
    assert adapted.current_hp == adapted.max_hp
    assert adapted.can_mega is True
    assert adapted.mega_stone == "Charizardite X"
    assert adapted.image_url == "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/6.png"

    # Verificar que los movimientos sean MoveState reales con poder y tipo
    assert len(adapted.moves) == 4
    flamethrower = [m for m in adapted.moves if m.name == "Flamethrower"][0]
    assert flamethrower.type == "Fire"
    assert flamethrower.category == "special"
    assert flamethrower.base_power == 90

    # Caso borde: Pokémon sin selected_moves (debe rellenar con 4 movimientos por defecto)
    empty_poke = {"name": "Blastoise", "types": ["Water"], "level": 20}
    adapted_empty = adapt_draft_pokemon(empty_poke)
    assert len(adapted_empty.moves) == 4
    assert any(m.type == "Water" for m in adapted_empty.moves)


def test_switch_priority_over_moves():
    """Verifica que cambiar de Pokémon (SWITCH) tiene prioridad máxima (+6) sobre cualquier ataque."""
    pikachu = PokemonState(
        id="pikachu",
        species="Pikachu",
        types=("Electric",),
        current_hp=100, max_hp=100,
        stats=StatBlock(hp=100, atk=80, def_=60, spa=80, spd=70, spe=130),
        moves=[MoveState(id="thunderbolt", name="Thunderbolt", type="Electric", category="special", base_power=90)]
    )

    charizard = PokemonState(
        id="charizard",
        species="Charizard",
        types=("Fire", "Flying"),
        current_hp=150, max_hp=150,
        stats=StatBlock(hp=150, atk=100, def_=90, spa=130, spd=100, spe=120),
        moves=[MoveState(id="flamethrower", name="Flamethrower", type="Fire", category="special", base_power=90)]
    )

    squirtle = PokemonState(
        id="squirtle",
        species="Squirtle",
        types=("Water",),
        current_hp=100, max_hp=100,
        stats=StatBlock(hp=100, atk=70, def_=90, spa=70, spd=90, spe=60),
        moves=[MoveState(id="water-gun", name="Water Gun", type="Water", category="special", base_power=40)]
    )

    snapshot = BattleSnapshot(
        turn=1,
        player_active=pikachu,
        player_bench=[charizard],
        ai_active=squirtle,
    )

    engine = CombatEngine()
    # Jugador cambia a Charizard, la IA intenta atacar con Water Gun
    player_act = Action(type="SWITCH", choice="charizard")
    ai_act = Action(type="MOVE", choice="water-gun")

    result = engine.resolve_turn(snapshot, player_act, ai_act)

    # 1. El primer evento DEBE ser el cambio de Pokémon
    assert result.events[0]["type"] == "SWITCH"
    assert result.events[0]["pokemon"] == "Charizard"

    # 2. El nuevo Pokémon activo debe ser Charizard
    assert result.new_snapshot.player_active.species == "Charizard"

    # 3. El ataque de la IA debe golpear al Pokémon recién entrado (Charizard)
    dmg_events = [e for e in result.events if e.get("type") == "DAMAGE"]
    assert len(dmg_events) == 1
    assert dmg_events[0]["pokemon"] == "Charizard"
    assert dmg_events[0]["side"] == "player"


def test_dynamic_moves_db_population():
    """Verifica que al asignar un movimiento a un Pokémon, se verifique y agregue a la tabla de datos."""
    from backend.engine.pkmn_ai_engine.core.moves_db import ensure_move_in_db, ensure_moves_registered
    from backend.database import POKEMON_MOVES_LOCAL, get_pokemon_move_from_db

    # Limpiamos un movimiento específico de la caché local para simular que no estaba
    POKEMON_MOVES_LOCAL.pop("flamethrower", None)

    move_state = ensure_move_in_db("Flamethrower", fallback_type="Fire")
    assert move_state.id == "flamethrower"
    assert move_state.type == "Fire"
    assert move_state.category == "special"
    assert move_state.base_power == 90

    # Debe haber quedado guardado en la base de datos / tabla pokemon_moves
    stored = get_pokemon_move_from_db("flamethrower")
    assert stored is not None
    assert stored["slug"] == "flamethrower"
    assert stored["base_power"] == 90
    assert stored["category"] == "special"

    # Probar con una lista de movimientos asignados a un Pokémon
    registered = ensure_moves_registered(["Thunderbolt", "Ice Beam", "Earthquake"], fallback_type="Electric")
    assert len(registered) == 3
    assert get_pokemon_move_from_db("thunderbolt") is not None
    assert get_pokemon_move_from_db("ice-beam") is not None
    assert get_pokemon_move_from_db("earthquake") is not None


if __name__ == "__main__":
    test_type_effectiveness()
    test_damage_calculation()
    test_mega_evolution()
    test_opponent_tracker()
    test_ai_agent_lethal_decision()
    test_ai_agent_switch_decision()
    test_combat_engine_resolution()
    test_presets_loaded()
    test_adapt_draft_pokemon_conversion()
    test_switch_priority_over_moves()
    test_dynamic_moves_db_population()
    print("ALL 11 TESTS PASSED SUCCESSFULLY!")

