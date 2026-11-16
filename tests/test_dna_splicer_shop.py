import unittest
from unittest.mock import patch
from backend.modes.subasta_pokemon.handler import (
    SubastaPokemonMode,
    get_player_shop_item_price,
)


class DummyManager:
    def __init__(self):
        self.sent_personal = []
        self.broadcasts = []

    async def send_personal(self, websocket, data):
        self.sent_personal.append((websocket, data))

    async def send_personal_to_user(self, session_id, username, data):
        self.sent_personal.append((username, data))

    async def broadcast(self, session_id, data):
        self.broadcasts.append((session_id, data))


class TestDnaSplicerShop(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mode = SubastaPokemonMode()
        self.manager = DummyManager()
        self.session = {
            "id": "test_session_dna",
            "host": "Ash",
            "mode": "subasta_pokemon",
            "players": {"Ash": {}, "Gary": {}},
            "subasta": {
                "current_stage": 4,  # Preparación Showdown Año 1
                "current_year": 1,
                "player_order": ["Ash", "Gary"],
                "trade_session": None,
                "players": {
                    "Ash": {
                        "money": 60000,
                        "items": [],
                        "pokemon": [],
                        "free_dna_splicers_claimed_years": [],
                    },
                    "Gary": {
                        "money": 0,
                        "items": [],
                        "pokemon": [],
                        "free_dna_splicers_claimed_years": [],
                    },
                },
            },
        }

    def test_get_player_shop_item_price_logic(self):
        ash = {"money": 100000, "free_dna_splicers_claimed_years": []}
        # Año 1: gratis la primera vez
        self.assertEqual(get_player_shop_item_price(ash, "DNA Splicers", 1), 0)

        # Si ya lo reclamó en año 1, vale 50000
        ash["free_dna_splicers_claimed_years"] = [1]
        self.assertEqual(get_player_shop_item_price(ash, "DNA Splicers", 1), 50000)

        # En año 2 vuelve a ser gratis
        self.assertEqual(get_player_shop_item_price(ash, "DNA Splicers", 2), 0)

        # Si ya lo reclamó en año 1 y 2, en año 2 vale 50000
        ash["free_dna_splicers_claimed_years"] = [1, 2]
        self.assertEqual(get_player_shop_item_price(ash, "DNA Splicers", 2), 50000)

        # En año 3 vuelve a ser gratis
        self.assertEqual(get_player_shop_item_price(ash, "DNA Splicers", 3), 0)

        # Otros objetos mantienen su precio normal
        self.assertEqual(get_player_shop_item_price(ash, "Sitrus Berry", 1), 50000)

    @patch("backend.modes.subasta_pokemon.handler.save_game_session")
    async def test_first_purchase_is_free_and_subsequent_costs_original_price(self, mock_save):
        # 1. Ash compra su primer DNA Splicers en Año 1
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )

        ash = self.session["subasta"]["players"]["Ash"]
        # El precio fue gratis, el dinero sigue intacto
        self.assertEqual(ash["money"], 60000)
        self.assertEqual(ash["items"].get("DNA Splicers"), 1)
        self.assertIn(1, ash["free_dna_splicers_claimed_years"])

        # 2. Ash intenta comprar un segundo DNA Splicers en Año 1
        # Ahora cuesta 50000
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )
        self.assertEqual(ash["money"], 10000)  # 60000 - 50000
        self.assertEqual(ash["items"].get("DNA Splicers"), 2)

        # 3. Ash intenta comprar un tercer DNA Splicers pero solo le quedan 10000
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )
        # Debe fallar por dinero insuficiente
        self.assertEqual(ash["money"], 10000)
        self.assertEqual(ash["items"].get("DNA Splicers"), 2)
        error_events = [
            payload["data"]["message"]
            for target, payload in self.manager.sent_personal
            if isinstance(payload, dict) and payload.get("event") == "error"
        ]
        self.assertTrue(any("No tienes suficiente dinero" in msg for msg in error_events))

    @patch("backend.modes.subasta_pokemon.handler.save_game_session")
    async def test_player_in_debt_can_claim_free_dna_splicer(self, mock_save):
        gary = self.session["subasta"]["players"]["Gary"]
        gary["money"] = -25000  # Gary está endeudado

        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_gary",
            self.manager,
        )
        self.assertEqual(gary["money"], -25000)
        self.assertEqual(gary["items"].get("DNA Splicers"), 1)
        self.assertIn(1, gary["free_dna_splicers_claimed_years"])

    @patch("backend.modes.subasta_pokemon.handler.save_game_session")
    async def test_free_dna_splicer_resets_in_new_year(self, mock_save):
        ash = self.session["subasta"]["players"]["Ash"]

        # Año 1: compra el gratis
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )
        self.assertEqual(ash["money"], 60000)
        self.assertEqual(ash["items"].get("DNA Splicers"), 1)
        self.assertIn(1, ash["free_dna_splicers_claimed_years"])

        # Avanzamos a Año 2 (Stage 8 = preparación Showdown Año 2)
        self.session["subasta"]["current_year"] = 2
        self.session["subasta"]["current_stage"] = 8

        # En Año 2, el primer DNA Splicers vuelve a ser gratis
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )
        self.assertEqual(ash["money"], 60000)
        self.assertEqual(ash["items"].get("DNA Splicers"), 2)
        self.assertIn(2, ash["free_dna_splicers_claimed_years"])

        # El segundo en Año 2 vuelve a costar 50000
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )
        self.assertEqual(ash["money"], 10000)
        self.assertEqual(ash["items"].get("DNA Splicers"), 3)

        # Avanzamos a Año 3 (Stage 12 = preparación Showdown Año 3)
        self.session["subasta"]["current_year"] = 3
        self.session["subasta"]["current_stage"] = 12

        # En Año 3, vuelve a ser gratis el primero
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_shop_buy",
            {"action": "subasta_shop_buy", "item_name": "DNA Splicers"},
            "ws_ash",
            self.manager,
        )
        self.assertEqual(ash["money"], 10000)
        self.assertEqual(ash["items"].get("DNA Splicers"), 4)
        self.assertIn(3, ash["free_dna_splicers_claimed_years"])


if __name__ == "__main__":
    unittest.main()
