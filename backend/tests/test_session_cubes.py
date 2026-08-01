import pytest

from backend.routes import session


def test_get_available_cubes_only_returns_database_cubes(monkeypatch):
    monkeypatch.setattr(session, "get_all_cubes", lambda: [{"id": "db-cube-1", "title": "Supabase cube"}])

    assert session.get_available_cubes() == [{"key": "db-cube-1", "title": "Supabase cube"}]


def test_get_cube_card_pool_rejects_non_database_cube(monkeypatch):
    monkeypatch.setattr(session, "get_cube_by_id", lambda cube_id: None)
    monkeypatch.setattr(session, "get_all_cubes", lambda: [{"id": "db-cube-1", "title": "Supabase cube"}])

    with pytest.raises(ValueError, match="Cube desconocido"):
        session.get_cube_card_pool("dragon_cube")


def test_get_cube_card_pool_uses_database_card_names(monkeypatch):
    cube_cards = [f"Card {i}" for i in range(201)]
    monkeypatch.setattr(session, "resolve_cube_for_key", lambda cube_key: {"id": "cube-1", "cards": cube_cards})

    pool = session.get_cube_card_pool("cube-1")

    assert len(pool) == 201
    assert pool[0] == "Card 0"
