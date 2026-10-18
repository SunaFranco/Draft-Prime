import unittest
from unittest.mock import patch
from backend.modes.subasta_pokemon import events_data


class TestTrashScavengeEvent(unittest.TestCase):
    def test_berries_pool(self):
        self.assertTrue(len(events_data.BERRIES_POOL) > 0)
        self.assertIn("Oran Berry", events_data.BERRIES_POOL)
        self.assertIn("Sitrus Berry", events_data.BERRIES_POOL)
        self.assertIn("Lum Berry", events_data.BERRIES_POOL)

    def test_trash_scavenge_generation_structure(self):
        event_def = next(e for e in events_data.EVENTS_YEAR_1 if e["id"] == "e1_rebuscar_basura")
        self.assertEqual(event_def["type"], "trash_scavenge")

        with patch("backend.modes.subasta_pokemon.events_data.EVENTS_YEAR_1", [event_def]):
            ev = events_data.get_random_event_for_year(1)
            self.assertEqual(ev["id"], "e1_rebuscar_basura")
            self.assertTrue(ev["reward_is_random"])
            self.assertEqual(len(ev["granted_items"]), 3)
            for item in ev["granted_items"]:
                self.assertTrue(item == "Leftovers" or item in events_data.BERRIES_POOL)
            self.assertIn("Leftovers", ev["roulette_pool"])

    def test_trash_scavenge_odds(self):
        event_def = next(e for e in events_data.EVENTS_YEAR_1 if e["id"] == "e1_rebuscar_basura")
        # Simular tirada donde sale Leftovers (< 0.05)
        with patch("random.choice", return_value=event_def), patch("random.random", return_value=0.03):
            ev = events_data.get_random_event_for_year(1)
            self.assertEqual(ev["granted_items"], ["Leftovers", "Leftovers", "Leftovers"])

        # Simular tirada donde sale Baya (>= 0.05)
        with patch("random.choice", side_effect=[event_def, "Sitrus Berry", "Lum Berry", "Oran Berry"]), \
             patch("random.random", return_value=0.5):
            ev = events_data.get_random_event_for_year(1)
            self.assertEqual(ev["granted_items"], ["Sitrus Berry", "Lum Berry", "Oran Berry"])

    def test_apply_event_adds_items_to_player_inventory(self):
        player = {
            "money": 1000,
            "items": {"Sitrus Berry": 1},
            "pokemon": []
        }
        event = {
            "id": "e1_rebuscar_basura",
            "title": "🗑️ Rebuscar la Basura",
            "description": "Rebuscas en la basura y consigues 3 tiradas en la ruleta.",
            "granted_items": ["Leftovers", "Sitrus Berry", "Lum Berry"]
        }
        summary = events_data.apply_event_to_player(player, event)
        self.assertEqual(player["items"]["Leftovers"], 1)
        self.assertEqual(player["items"]["Sitrus Berry"], 2)
        self.assertEqual(player["items"]["Lum Berry"], 1)
        self.assertIn("Leftovers, Sitrus Berry, Lum Berry", summary["summary"])


if __name__ == "__main__":
    unittest.main()
