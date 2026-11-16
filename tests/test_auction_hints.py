import unittest
from backend.modes.subasta_pokemon.handler import (
    calculate_buyout_price,
    calculate_reveal_price,
    get_auction_poke_count,
    calculate_hint_thresholds,
)
from backend.modes.subasta_pokemon import poke_api


class TestAuctionHints(unittest.TestCase):

    def test_calculate_reveal_price(self):
        # 1,000,000 con 8 pokémon -> 125,000
        self.assertEqual(calculate_reveal_price(1000000, 8), 125000)
        # 1,000,000 con 6 pokémon -> 166,666 -> redondeado hacia arriba en múltiplos de 5k -> 170,000
        self.assertEqual(calculate_reveal_price(1000000, 6), 170000)
        # Mínimo 5000
        self.assertEqual(calculate_reveal_price(1000, 10), 5000)

    def test_get_auction_poke_count(self):
        subasta_state = {
            "year_pools": {
                1: {"normal": 8, "mega": 0, "legendary": 0},
                2: {"normal": 3, "mega": 3, "legendary": 0},
                3: {"normal": 3, "mega": 2, "legendary": 1},
            },
            "current_phase_quota": 2,
        }
        self.assertEqual(get_auction_poke_count(subasta_state, 1), 8)
        self.assertEqual(get_auction_poke_count(subasta_state, 2), 6)
        self.assertEqual(get_auction_poke_count(subasta_state, 3), 6)

        # Fallback si year_pools está vacío
        empty_state = {"current_phase_quota": 4}
        self.assertEqual(get_auction_poke_count(empty_state, 1), 4)

    def test_calculate_hint_thresholds(self):
        base_price = 50000
        reveal_price = 125000
        buyout_price = 250000
        thresholds = calculate_hint_thresholds(base_price, reveal_price, buyout_price)

        self.assertEqual(thresholds["primary_type"], 50000)
        self.assertGreaterEqual(thresholds["secondary_type"], 50000)
        self.assertLess(thresholds["secondary_type"], reveal_price)
        self.assertEqual(thresholds["reveal"], 125000)
        self.assertGreater(thresholds["ability"], reveal_price)
        self.assertLess(thresholds["ability"], thresholds["nature"])
        self.assertLess(thresholds["nature"], buyout_price)

    def test_hints_unlocked_step_by_step(self):
        poke_dual = {
            "name": "Bulbasaur",
            "types": ["Grass", "Poison"],
            "primary_type": "Grass",
            "ability": "Overgrow",
            "nature": "Calm",
        }
        thresholds = {
            "primary_type": 50000,
            "secondary_type": 85000,
            "reveal": 125000,
            "ability": 165000,
            "nature": 210000,
        }

        # 1. Al precio base (50K): solo tipo primario
        hints_50k = poke_api.get_auction_hints(poke_dual, 50000, thresholds)
        self.assertIn("primary_type", hints_50k)
        self.assertEqual(hints_50k["primary_type"], "Grass")
        self.assertNotIn("secondary_type", hints_50k)
        self.assertNotIn("ability", hints_50k)
        self.assertNotIn("nature", hints_50k)

        # 2. Al alcanzar segundo tipo (85K)
        hints_85k = poke_api.get_auction_hints(poke_dual, 85000, thresholds)
        self.assertEqual(hints_85k["primary_type"], "Grass")
        self.assertEqual(hints_85k["secondary_type"], "Poison")
        self.assertNotIn("ability", hints_85k)
        self.assertNotIn("nature", hints_85k)

        # 3. Al alcanzar habilidad (165K)
        hints_165k = poke_api.get_auction_hints(poke_dual, 165000, thresholds)
        self.assertEqual(hints_165k["ability"], "Overgrow")
        self.assertNotIn("nature", hints_165k)

        # 4. Al alcanzar naturaleza (210K)
        hints_210k = poke_api.get_auction_hints(poke_dual, 210000, thresholds)
        self.assertEqual(hints_210k["nature"], "Calm")

    def test_monotype_pokemon_secondary_type_is_no_tiene(self):
        poke_mono = {
            "name": "Squirtle",
            "types": ["Water"],
            "primary_type": "Water",
            "ability": "Torrent",
            "nature": "Bold",
        }
        thresholds = {
            "primary_type": 50000,
            "secondary_type": 85000,
            "reveal": 125000,
            "ability": 165000,
            "nature": 210000,
        }

        hints = poke_api.get_auction_hints(poke_mono, 90000, thresholds)
        self.assertEqual(hints["primary_type"], "Water")
        self.assertEqual(hints["secondary_type"], "No tiene")

    def test_multiplier_legacy_fallback(self):
        poke = {
            "name": "Pikachu",
            "types": ["Electric"],
            "primary_type": "Electric",
            "ability": "Static",
            "nature": "Timid",
        }
        hints_1x = poke_api.get_hints_for_multiplier(poke, 1.0)
        self.assertEqual(hints_1x.get("primary_type"), "Electric")
        self.assertNotIn("secondary_type", hints_1x)

        hints_15x = poke_api.get_hints_for_multiplier(poke, 1.5)
        self.assertEqual(hints_15x.get("secondary_type"), "No tiene")

        hints_2x = poke_api.get_hints_for_multiplier(poke, 2.0)
        self.assertEqual(hints_2x.get("ability"), "Static")

        hints_25x = poke_api.get_hints_for_multiplier(poke, 2.5)
        self.assertEqual(hints_25x.get("nature"), "Timid")


if __name__ == "__main__":
    unittest.main()
