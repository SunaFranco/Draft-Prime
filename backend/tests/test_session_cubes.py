"""
backend/tests/test_session_cubes.py - Pruebas unitarias para cubes
"""

import unittest
from unittest.mock import patch
from backend.routes import session


class TestSessionCubes(unittest.TestCase):
    def test_get_available_cubes_only_returns_database_cubes(self):
        with patch.object(session, "get_all_cubes", lambda: [{"id": "db-cube-1", "title": "Supabase cube"}]):
            self.assertEqual(session.get_available_cubes(), [{"key": "db-cube-1", "title": "Supabase cube"}])

    def test_get_cube_card_pool_rejects_non_database_cube(self):
        with patch.object(session, "get_cube_by_id", lambda cube_id: None), \
             patch.object(session, "get_all_cubes", lambda: [{"id": "db-cube-1", "title": "Supabase cube"}]):
            with self.assertRaises(ValueError):
                session.get_cube_card_pool("dragon_cube")

    def test_get_cube_card_pool_uses_database_card_names(self):
        cube_cards = [f"Card {i}" for i in range(201)]
        with patch.object(session, "resolve_cube_for_key", lambda cube_key: {"id": "cube-1", "cards": cube_cards}):
            pool = session.get_cube_card_pool("cube-1")
            self.assertEqual(len(pool), 201)
            self.assertEqual(pool[0], "Card 0")


if __name__ == "__main__":
    unittest.main()
