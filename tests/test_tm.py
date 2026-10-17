import unittest
from backend.modes.subasta_pokemon import poke_api
from backend.modes.subasta_pokemon.handler import add_tm_to_pokemon


class TestTMCompatibility(unittest.TestCase):
    def test_tm_moves_dict_contains_punches_and_common_tms(self):
        self.assertIn("MT Earthquake", poke_api.TM_MOVES)
        self.assertEqual(poke_api.TM_MOVES["MT Earthquake"], "Earthquake")
        self.assertIn("MT Fire Punch", poke_api.TM_MOVES)
        self.assertEqual(poke_api.TM_MOVES["MT Fire Punch"], "Fire Punch")
        self.assertIn("MT Thunder Punch", poke_api.TM_MOVES)
        self.assertIn("MT Ice Punch", poke_api.TM_MOVES)

    def test_add_tm_to_pokemon_success(self):
        poke = {
            "name": "Snorlax",
            "tm_moves": ["Earthquake", "Body Slam", "Rest"],
            "learned_tm_moves": [],
            "selected_moves": ["Tackle"],
            "level_up_moves": [{"name": "Tackle", "level": 1}]
        }
        # Snorlax learns Earthquake
        success = add_tm_to_pokemon(poke, "Earthquake")
        self.assertTrue(success)
        self.assertIn("Earthquake", poke["learned_tm_moves"])
        self.assertTrue(any(m["name"] == "Earthquake" for m in poke["level_up_moves"]))

    def test_add_tm_to_pokemon_incompatible(self):
        poke = {
            "name": "Caterpie",
            "tm_moves": ["Snore", "Bug Bite"],
            "learned_tm_moves": [],
            "selected_moves": ["Tackle"],
            "level_up_moves": [{"name": "Tackle", "level": 1}]
        }
        # Caterpie cannot learn Earthquake
        success = add_tm_to_pokemon(poke, "Earthquake")
        self.assertFalse(success)
        self.assertNotIn("Earthquake", poke.get("learned_tm_moves", []))

    def test_add_tm_to_pokemon_already_known(self):
        poke = {
            "name": "Gengar",
            "tm_moves": ["Shadow Ball"],
            "learned_tm_moves": ["Shadow Ball"],
            "selected_moves": [],
            "level_up_moves": [{"name": "Shadow Ball", "level": 0, "source": "tm"}]
        }
        # Already learned
        success = add_tm_to_pokemon(poke, "Shadow Ball")
        self.assertFalse(success)

        poke2 = {
            "name": "Gengar",
            "tm_moves": ["Shadow Ball"],
            "learned_tm_moves": [],
            "selected_moves": ["Shadow Ball"],
            "level_up_moves": [{"name": "Shadow Ball", "level": 25}]
        }
        # In selected moves
        success2 = add_tm_to_pokemon(poke2, "Shadow Ball")
        self.assertFalse(success2)


if __name__ == "__main__":
    unittest.main()
