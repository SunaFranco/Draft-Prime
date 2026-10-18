import unittest
from unittest.mock import AsyncMock, patch
from backend.modes.subasta_pokemon.handler import SubastaPokemonMode


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


class TestTradeMultipleTimes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mode = SubastaPokemonMode()
        self.manager = DummyManager()
        self.session = {
            "id": "test_session_1",
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
                        "money": 100000,
                        "items": {"Cable Link": 2},
                        "pokemon": [
                            {"name": "Pikachu", "level": 20, "types": ["electric"]},
                            {"name": "Charmander", "level": 20, "types": ["fire"]},
                        ],
                    },
                    "Gary": {
                        "money": 100000,
                        "items": {},
                        "pokemon": [
                            {"name": "Squirtle", "level": 20, "types": ["water"]},
                            {"name": "Bulbasaur", "level": 20, "types": ["grass"]},
                        ],
                    },
                },
            },
        }

    @patch("backend.modes.subasta_pokemon.handler.save_game_session")
    async def test_can_perform_second_trade_after_first_completed(self, mock_save):
        # 1. Ash inicia el primer intercambio
        res1 = await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_start",
            {"target_username": "Gary", "poke_index": 0},
            "ws_ash",
            self.manager,
        )
        self.assertTrue(res1)
        trade = self.session["subasta"]["trade_session"]
        self.assertIsNotNone(trade)
        self.assertEqual(trade["status"], "selecting")

        # 2. Gary selecciona a Squirtle
        res2 = await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_select",
            {"poke_index": 0},
            "ws_gary",
            self.manager,
        )
        self.assertTrue(res2)
        self.assertEqual(trade["status"], "confirming")

        # 3. Ambos confirman
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_confirm",
            {},
            "ws_ash",
            self.manager,
        )
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_confirm",
            {},
            "ws_gary",
            self.manager,
        )

        # El intercambio 1 quedó completado
        self.assertEqual(trade["status"], "completed")
        self.assertEqual(self.session["subasta"]["players"]["Ash"]["pokemon"][0]["name"], "Squirtle")
        self.assertEqual(self.session["subasta"]["players"]["Gary"]["pokemon"][0]["name"], "Pikachu")
        self.assertEqual(self.session["subasta"]["players"]["Ash"]["items"]["Cable Link"], 1)

        # 4. Ash inicia un SEGUNDO intercambio ofreciendo Charmander (index 1)
        self.manager.sent_personal.clear()
        res_trade2 = await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_start",
            {"target_username": "Gary", "poke_index": 1},
            "ws_ash",
            self.manager,
        )
        self.assertTrue(res_trade2)

        # Verificar que NO se envió mensaje de error
        error_messages = [data for _, data in self.manager.sent_personal if data.get("event") == "error"]
        self.assertEqual(error_messages, [])

        trade2 = self.session["subasta"]["trade_session"]
        self.assertEqual(trade2["status"], "selecting")
        self.assertEqual(trade2["initiator"], "Ash")
        self.assertEqual(trade2["initiator_pokemon"]["name"], "Charmander")

        # 5. Gary selecciona a Bulbasaur (index 1)
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_select",
            {"poke_index": 1},
            "ws_gary",
            self.manager,
        )
        self.assertEqual(trade2["status"], "confirming")

        # 6. Ambos confirman el segundo intercambio
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_confirm",
            {},
            "ws_ash",
            self.manager,
        )
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_confirm",
            {},
            "ws_gary",
            self.manager,
        )

        self.assertEqual(trade2["status"], "completed")
        self.assertEqual(self.session["subasta"]["players"]["Ash"]["pokemon"][1]["name"], "Bulbasaur")
        self.assertEqual(self.session["subasta"]["players"]["Gary"]["pokemon"][1]["name"], "Charmander")
        self.assertNotIn("Cable Link", self.session["subasta"]["players"]["Ash"].get("items", {}))

    @patch("backend.modes.subasta_pokemon.handler.save_game_session")
    async def test_cannot_start_trade_while_one_is_in_progress(self, mock_save):
        # Iniciar trade
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_start",
            {"target_username": "Gary", "poke_index": 0},
            "ws_ash",
            self.manager,
        )
        # Intentar iniciar otro sin finalizar el primero
        self.manager.sent_personal.clear()
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_start",
            {"target_username": "Gary", "poke_index": 1},
            "ws_ash",
            self.manager,
        )
        errors = [data for _, data in self.manager.sent_personal if data.get("event") == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("Ya hay un intercambio en curso", errors[0]["data"]["message"])

    @patch("backend.modes.subasta_pokemon.handler.save_game_session")
    async def test_cancel_trade_and_dismiss_completed(self, mock_save):
        # Iniciar trade: Ash -> Gary
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_start",
            {"target_username": "Gary", "poke_index": 0},
            "ws_ash",
            self.manager,
        )
        # El target (Gary) intenta cancelar: NO debe permitirse
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_cancel",
            {},
            "ws_gary",
            self.manager,
        )
        self.assertIsNotNone(self.session["subasta"]["trade_session"])
        self.assertEqual(self.session["subasta"]["trade_session"]["status"], "selecting")

        # El que inició (Ash) cancela: SÍ debe cancelarse
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_cancel",
            {},
            "ws_ash",
            self.manager,
        )
        self.assertIsNone(self.session["subasta"]["trade_session"])

        # Iniciar de nuevo y completar
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_start",
            {"target_username": "Gary", "poke_index": 0},
            "ws_ash",
            self.manager,
        )
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_select",
            {"poke_index": 0},
            "ws_gary",
            self.manager,
        )
        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_confirm",
            {},
            "ws_ash",
            self.manager,
        )
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_confirm",
            {},
            "ws_gary",
            self.manager,
        )
        self.assertEqual(self.session["subasta"]["trade_session"]["status"], "completed")

        # Solo el iniciador (Ash) puede cerrar el cartel
        await self.mode.handle_action(
            self.session,
            "Gary",
            "subasta_trade_cancel",
            {},
            "ws_gary",
            self.manager,
        )
        self.assertIsNotNone(self.session["subasta"]["trade_session"])

        await self.mode.handle_action(
            self.session,
            "Ash",
            "subasta_trade_cancel",
            {},
            "ws_ash",
            self.manager,
        )
        self.assertIsNone(self.session["subasta"]["trade_session"])


if __name__ == "__main__":
    unittest.main()
