"""
backend/tests/test_subasta_pokemon.py - Pruebas unitarias para el modo Subasta Pokémon
"""

import unittest
from backend.modes.subasta_pokemon import poke_api, events_data, showdown
from backend.modes.subasta_pokemon.handler import SubastaPokemonMode, evolve_player_pokemon


class TestSubastaPokemon(unittest.TestCase):
    def test_hints_by_multiplier(self):
        poke = {
            "id": 25,
            "name": "Pikachu",
            "region": "Kanto",
            "ability": "Static",
            "primary_type": "Electric",
            "highest_stat": "SPEED (90)"
        }

        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 1.0), {})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 1.5), {"first_letter": "P"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 2.0), {"first_letter": "P", "region": "Kanto"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 2.5), {"first_letter": "P", "region": "Kanto", "ability": "Static"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 3.0), {"first_letter": "P", "region": "Kanto", "ability": "Static", "primary_type": "Electric"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 3.5), {"first_letter": "P", "region": "Kanto", "ability": "Static", "primary_type": "Electric", "highest_stat": "SPEED (90)"})

    def test_event_application(self):
        player_state = {"money": 1000, "pokemon": [{"name": "Pikachu", "level": 1}], "items": []}
        event = {"id": "e1", "title": "Test", "description": "Test desc", "type": "money_grant", "amount": 500}

        res = events_data.apply_event_to_player(player_state, event)
        self.assertEqual(player_state["money"], 1500)
        self.assertEqual(res["player_money"], 1500)

    def test_showdown_export(self):
        pokemon = [{"name": "Pikachu", "level": 40, "ability": "Static", "primary_type": "Electric"}]
        text = showdown.export_team_to_showdown("Alice", pokemon, ["Light Ball"])
        self.assertIn("=== [gen9anythinggoes] Equipo de Alice ===", text)
        self.assertIn("Pikachu @ Light Ball", text)
        self.assertIn("Ability: Static", text)

    def test_pokemon_evolution(self):
        player_state = {
            "pokemon": [
                {"name": "Pikachu", "level": 35},
                {"name": "Charmander", "level": 20}
            ]
        }
        evolve_player_pokemon(player_state, 40)
        names = [p["name"] for p in player_state["pokemon"]]
        self.assertIn("Raichu", names)
        self.assertIn("Charmeleon", names)

    def test_fixed_ability_and_moves_by_level(self):
        poke = poke_api.fetch_pokemon_data("Pikachu", level_cap=20)
        self.assertIn("ability", poke)
        self.assertIn(poke["ability"], poke["abilities"])
        self.assertLessEqual(len(poke["selected_moves"]), 4)

        # Verificar exportación con movimientos seleccionados
        text = showdown.export_team_to_showdown("Bob", [poke])
        for move in poke["selected_moves"]:
            self.assertIn(f"- {move}", text)


if __name__ == "__main__":
    unittest.main()

