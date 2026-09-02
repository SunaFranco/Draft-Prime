"""
backend/tests/test_subasta_pokemon.py - Pruebas unitarias para el modo Subasta Pokémon
"""

import asyncio
import unittest
from unittest.mock import patch
from backend.modes.subasta_pokemon import poke_api, events_data, showdown
from backend.modes.subasta_pokemon.handler import SubastaPokemonMode, evolve_player_pokemon, evolve_single_pokemon


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

        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 1.0), {"first_letter": "P"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 1.5), {"first_letter": "P"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 2.0), {"first_letter": "P", "region": "Kanto"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 2.5), {"first_letter": "P", "region": "Kanto"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 3.0), {"first_letter": "P", "region": "Kanto", "ability": "Static"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 5.0), {"first_letter": "P", "region": "Kanto", "ability": "Static", "primary_type": "Electric"})
        self.assertEqual(poke_api.get_hints_for_multiplier(poke, 8.0), {"first_letter": "P", "region": "Kanto", "ability": "Static", "primary_type": "Electric", "highest_stat": "SPEED (90)"})

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

    def test_evolution_updates_all_pokemon_to_year_cap(self):
        player_state = {
            "pokemon": [
                {"name": "Pikachu", "level": 20},
                {"name": "Bulbasaur", "level": 20},
                {"name": "Gengar", "level": 35},
                {"name": "Pupitar", "level": 80}
            ]
        }

        evolve_player_pokemon(player_state, 40)
        self.assertTrue(all(p["level"] == 40 for p in player_state["pokemon"]))

        player_state = {
            "pokemon": [
                {"name": "Pikachu", "level": 40},
                {"name": "Bulbasaur", "level": 40},
                {"name": "Gengar", "level": 40},
                {"name": "Pupitar", "level": 90}
            ]
        }

        evolve_player_pokemon(player_state, 100)
        self.assertTrue(all(p["level"] == 100 for p in player_state["pokemon"]))

    def test_gothita_evolution_uses_next_min_level_gate(self):
        poke = poke_api.fetch_pokemon_data("Gothita", level_cap=40)
        self.assertEqual(poke.get("evolution_target"), "gothorita")
        self.assertEqual(poke.get("next_evolution_level"), 32)
        self.assertTrue(poke.get("can_evolve"))

    def test_evolution_replaces_species_and_keeps_ability_slot(self):
        original = {
            "name": "Charmander",
            "level": 35,
            "ability": "Blaze",
            "abilities": ["Blaze", "Solar Power"],
            "image_url": "old-sprite.png",
            "selected_moves": ["Ember"],
            "level_up_moves": [
                {"name": "Ember", "level": 1},
                {"name": "Flame Burst", "level": 15},
                {"name": "Flare Blitz", "level": 35}
            ]
        }

        evolved_data = {
            "name": "Charmeleon",
            "region": "Kanto",
            "types": ["Fire"],
            "primary_type": "Fire",
            "abilities": ["Blaze", "Solar Power"],
            "ability": "Solar Power",
            "image_url": "new-sprite.png",
            "level_up_moves": [
                {"name": "Ember", "level": 1},
                {"name": "Flame Burst", "level": 15},
                {"name": "Flare Blitz", "level": 20},
                {"name": "Dragon Claw", "level": 25}
            ]
        }

        with patch("backend.modes.subasta_pokemon.handler.poke_api.fetch_pokemon_data", return_value=evolved_data), \
             patch("backend.modes.subasta_pokemon.handler.poke_api.get_pokemon_evolution_target", return_value="charmeleon"):
            result = evolve_single_pokemon(original, 40)

        self.assertTrue(result)
        self.assertEqual(original["name"], "Charmeleon")
        self.assertEqual(original["image_url"], "new-sprite.png")
        self.assertEqual(original["ability"], "Solar Power")
        self.assertIn("Solar Power", original["abilities"])
        self.assertGreaterEqual(len(original["selected_moves"]), 1)

    def test_buyout_immediately_finishes_round(self):
        class DummyManager:
            def __init__(self):
                self.messages = []

            async def broadcast(self, *args, **kwargs):
                pass

            async def send_personal(self, websocket, payload):
                self.messages.append(payload)

            async def send_personal_to_user(self, session_id, username, payload):
                self.messages.append({"user": username, "payload": payload})

        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 2,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "player_order": ["Alice", "Bob"],
                "players": {
                    "Alice": {"money": 5000, "pokemon": [], "items": []},
                    "Bob": {"money": 15000, "pokemon": [], "items": []}
                },
                "current_auction": {
                    "base_price": 1000,
                    "current_bid": 1000,
                    "high_bidder": "Alice",
                    "buyout_price": 10000,
                    "secret_fee": 500,
                    "pokemon": {"name": "Pikachu"},
                    "finished": False,
                    "winner": None,
                    "awaiting_secret_choice": False,
                    "folded_players": []
                }
            }
        }

        manager = DummyManager()
        mode = SubastaPokemonMode()

        asyncio.run(mode.handle_action(session, "Bob", "subasta_buyout", {}, None, manager))

        self.assertTrue(session["subasta"]["current_auction"]["finished"])
        self.assertEqual(session["subasta"]["current_auction"]["winner"], "Bob")

        asyncio.run(mode.handle_action(session, "Alice", "subasta_bid", {"bid_amount": 2000}, None, manager))
        self.assertTrue(manager.messages[-1]["event"] == "error")
        self.assertEqual(manager.messages[-1]["data"]["message"], "La subasta ya terminó.")

    def test_revealed_auction_waits_before_next_round(self):
        class DummyManager:
            def __init__(self):
                self.messages = []

            async def broadcast(self, *args, **kwargs):
                pass

            async def send_personal(self, websocket, payload):
                self.messages.append(payload)

            async def send_personal_to_user(self, session_id, username, payload):
                self.messages.append({"user": username, "payload": payload})

        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 2,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "pok_per_player": 8,
                "player_order": ["Alice", "Bob"],
                "players": {
                    "Alice": {"money": 5000, "pokemon": [], "items": []},
                    "Bob": {"money": 15000, "pokemon": [], "items": []}
                },
                "auction_turn_index": 0,
                "current_auction": {
                    "base_price": 1000,
                    "current_bid": 1500,
                    "high_bidder": "Alice",
                    "buyout_price": 10000,
                    "secret_fee": 500,
                    "pokemon": {"name": "Pikachu", "image_url": "img.png", "is_hidden": True},
                    "finished": False,
                    "winner": "Alice",
                    "awaiting_secret_choice": True,
                    "folded_players": []
                }
            }
        }

        mode = SubastaPokemonMode()
        mode.reveal_hold_seconds = 0.1

        asyncio.run(mode.handle_action(session, "Alice", "subasta_secret_choice", {"keep_secret": False}, None, DummyManager()))

        self.assertFalse(session["subasta"]["current_auction"]["awaiting_secret_choice"])
        self.assertTrue(session["subasta"]["current_auction"]["finished"])
        self.assertIsNotNone(session["subasta"]["current_auction"]["winner"])
        self.assertFalse(session["subasta"]["current_auction"]["pokemon"]["is_hidden"])

        asyncio.run(asyncio.sleep(0.2))

    def test_secret_choice_updates_shared_auction_visibility(self):
        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 2,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "pok_per_player": 8,
                "buyout_multiplier": 10.0,
                "player_order": ["Alice", "Bob"],
                "players": {
                    "Alice": {"money": 5000, "pokemon": [], "items": []},
                    "Bob": {"money": 15000, "pokemon": [], "items": []}
                },
                "auction_turn_index": 0,
                "current_auction": {
                    "base_price": 1000,
                    "current_bid": 1500,
                    "high_bidder": "Alice",
                    "buyout_price": 10000,
                    "secret_fee": 500,
                    "pokemon": {"name": "Pikachu", "image_url": "img.png", "is_hidden": True},
                    "finished": False,
                    "winner": "Alice",
                    "awaiting_secret_choice": True,
                    "folded_players": []
                }
            }
        }

        class AsyncManager:
            async def send_personal(self, websocket, payload):
                return None

            async def send_personal_to_user(self, session_id, username, payload):
                return None

        mode = SubastaPokemonMode()
        manager = AsyncManager()

        asyncio.run(mode.handle_action(session, "Alice", "subasta_secret_choice", {"keep_secret": False}, None, manager))
        self.assertFalse(session["subasta"]["current_auction"]["pokemon"]["is_hidden"])
        self.assertTrue(session["subasta"]["current_auction"]["publicly_revealed"])

        session["subasta"]["current_auction"]["pokemon"]["is_hidden"] = True
        session["subasta"]["current_auction"]["publicly_revealed"] = False
        asyncio.run(mode.handle_action(session, "Alice", "subasta_secret_choice", {"keep_secret": True}, None, manager))
        self.assertIn("pokemon", session["subasta"]["current_auction"])
        self.assertFalse(session["subasta"]["current_auction"].get("publicly_revealed", True))
        self.assertIn("name", session["subasta"]["current_auction"]["pokemon"])

    def test_fold_when_all_others_fold_finishes_round_and_high_bidder_cannot_fold(self):
        class DummyManager:
            def __init__(self):
                self.messages = []

            async def broadcast(self, *args, **kwargs):
                pass

            async def send_personal(self, websocket, payload):
                self.messages.append(payload)

            async def send_personal_to_user(self, session_id, username, payload):
                self.messages.append({"user": username, "payload": payload})

        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 2,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "pok_per_player": 8,
                "buyout_multiplier": 10.0,
                "secret_fee": 500,
                "player_order": ["Alice", "Bob"],
                "players": {
                    "Alice": {"money": 5000, "pokemon": [], "items": []},
                    "Bob": {"money": 15000, "pokemon": [], "items": []}
                },
                "current_auction": {
                    "base_price": 1000,
                    "current_bid": 1500,
                    "high_bidder": "Alice",
                    "winner": None,
                    "awaiting_secret_choice": False,
                    "finished": False,
                    "folded_players": [],
                    "pokemon": {"name": "Pikachu", "image_url": "img.png"}
                }
            }
        }

        mode = SubastaPokemonMode()
        manager = DummyManager()

        asyncio.run(mode.handle_action(session, "Bob", "subasta_fold", {}, None, manager))

        self.assertEqual(session["subasta"]["current_auction"]["winner"], "Alice")
        self.assertTrue(session["subasta"]["current_auction"]["awaiting_secret_choice"])

        self.assertTrue(session["subasta"]["players"]["Alice"]["money"] >= 0)

    def test_high_bidder_cannot_fold_and_round_finishes_when_others_fold(self):
        class DummyManager:
            def __init__(self):
                self.messages = []

            async def broadcast(self, *args, **kwargs):
                pass

            async def send_personal(self, websocket, payload):
                self.messages.append(payload)

            async def send_personal_to_user(self, session_id, username, payload):
                self.messages.append({"user": username, "payload": payload})

        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 2,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "pok_per_player": 8,
                "buyout_multiplier": 10.0,
                "secret_fee": 500,
                "player_order": ["Alice", "Bob", "Cara"],
                "players": {
                    "Alice": {"money": 5000, "pokemon": [], "items": []},
                    "Bob": {"money": 15000, "pokemon": [], "items": []},
                    "Cara": {"money": 12000, "pokemon": [], "items": []}
                },
                "current_auction": {
                    "base_price": 1000,
                    "current_bid": 1500,
                    "high_bidder": "Alice",
                    "winner": None,
                    "awaiting_secret_choice": False,
                    "finished": False,
                    "folded_players": [],
                    "pokemon": {"name": "Pikachu", "image_url": "img.png"}
                }
            }
        }

        mode = SubastaPokemonMode()
        manager = DummyManager()

        asyncio.run(mode.handle_action(session, "Bob", "subasta_fold", {}, None, manager))
        self.assertFalse(session["subasta"]["current_auction"]["finished"])
        self.assertIn("Bob", session["subasta"]["current_auction"]["folded_players"])

        asyncio.run(mode.handle_action(session, "Cara", "subasta_fold", {}, None, manager))
        self.assertEqual(session["subasta"]["current_auction"]["winner"], "Alice")
        self.assertTrue(session["subasta"]["current_auction"]["awaiting_secret_choice"])

        asyncio.run(mode.handle_action(session, "Alice", "subasta_fold", {}, None, manager))
        self.assertEqual(manager.messages[-1]["data"]["message"], "No puedes retirarte mientras eres el mayor pujador.")

    def test_item_backpack_and_equip_flow(self):
        class DummyManager:
            def __init__(self):
                self.messages = []

            async def send_personal(self, websocket, payload):
                self.messages.append(payload)

            async def send_personal_to_user(self, session_id, username, payload):
                self.messages.append({"user": username, "payload": payload})

            async def broadcast(self, *args, **kwargs):
                pass

        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 4,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "pok_per_player": 2,
                "player_order": ["Alice"],
                "players": {
                    "Alice": {
                        "money": 12000,
                        "pokemon": [{"name": "Pikachu", "level": 20, "item": "Leftovers"}],
                        "items": {"Leftovers": 1, "Life Orb": 2},
                        "points": 0,
                        "resolved_turn": False,
                    }
                },
                "current_auction": {},
                "current_turn_events": {}
            }
        }

        mode = SubastaPokemonMode()
        manager = DummyManager()

        asyncio.run(mode.handle_action(session, "Alice", "subasta_item_assign", {"pokemon_index": 0, "item_name": "Life Orb"}, None, manager))
        self.assertEqual(session["subasta"]["players"]["Alice"]["pokemon"][0]["item"], "Life Orb")
        self.assertEqual(session["subasta"]["players"]["Alice"]["items"]["Life Orb"], 1)

    def test_shop_buy_available_only_in_showdown_confirmation_stages(self):
        class DummyManager:
            def __init__(self):
                self.messages = []

            async def send_personal(self, websocket, payload):
                self.messages.append(payload)

            async def send_personal_to_user(self, session_id, username, payload):
                self.messages.append({"user": username, "payload": payload})

            async def broadcast(self, *args, **kwargs):
                pass

        session = {
            "id": "s1",
            "host": "Alice",
            "mode": "subasta_pokemon",
            "subasta": {
                "starting_money": 10000,
                "current_stage": 2,
                "current_year": 1,
                "current_turn": 1,
                "turns_per_year": 3,
                "pok_per_player": 2,
                "player_order": ["Alice"],
                "players": {
                    "Alice": {"money": 5000, "pokemon": [], "items": {}, "points": 0, "resolved_turn": False}
                },
                "current_auction": {},
                "current_turn_events": {}
            }
        }

        mode = SubastaPokemonMode()
        manager = DummyManager()

        result = asyncio.run(mode.handle_action(session, "Alice", "subasta_shop_buy", {"item_name": "Leftovers"}, None, manager))
        self.assertTrue(result)
        self.assertEqual(session["subasta"]["players"]["Alice"]["items"].get("Leftovers", 0), 0)

        session["subasta"]["current_stage"] = 4
        result = asyncio.run(mode.handle_action(session, "Alice", "subasta_shop_buy", {"item_name": "Leftovers"}, None, manager))
        self.assertTrue(result)
        self.assertGreaterEqual(session["subasta"]["players"]["Alice"]["items"].get("Leftovers", 0), 1)

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

