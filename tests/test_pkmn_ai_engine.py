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


if __name__ == "__main__":
    test_type_effectiveness()
    test_damage_calculation()
    test_mega_evolution()
    test_opponent_tracker()
    test_ai_agent_lethal_decision()
    test_ai_agent_switch_decision()
    test_combat_engine_resolution()
    test_presets_loaded()
    print("ALL 8 TESTS PASSED SUCCESSFULLY!")

