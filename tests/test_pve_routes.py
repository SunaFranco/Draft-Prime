"""
tests/test_pve_routes.py
Test de integración end-to-end de las rutas HTTP REST de PVE.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_pve_full_lifecycle():
    # 1. Listar presets
    res = client.get("/api/pve/presets")
    assert res.status_code == 200
    data = res.json()
    assert "presets" in data
    assert len(data["presets"]) >= 3
    brock = [p for p in data["presets"] if p["id"] == "brock-rock"][0]
    assert brock["name"] == "Líder Brock"

    # 2. Iniciar batalla contra Brock
    player_team = [
        {
            "species": "Swampert",
            "types": ["Water", "Ground"],
            "level": 50,
            "current_hp": 170,
            "max_hp": 170,
            "stats": {"hp": 170, "atk": 130, "def": 110, "spa": 105, "spd": 110, "spe": 80},
            "moves": [
                {"name": "Waterfall", "type": "Water", "category": "physical", "base_power": 80, "accuracy": 1.0},
                {"name": "Earthquake", "type": "Ground", "category": "physical", "base_power": 100, "accuracy": 1.0},
            ]
        },
        {
            "species": "Charizard",
            "types": ["Fire", "Flying"],
            "level": 50,
            "current_hp": 150,
            "max_hp": 150,
            "stats": {"hp": 150, "atk": 100, "def": 90, "spa": 130, "spd": 100, "spe": 120},
            "moves": [
                {"name": "Flamethrower", "type": "Fire", "category": "special", "base_power": 90, "accuracy": 1.0}
            ]
        }
    ]

    start_res = client.post("/api/pve/start", json={
        "preset_id": "brock-rock",
        "player_team": player_team,
    })
    assert start_res.status_code == 200
    start_data = start_res.json()
    battle_id = start_data["battle_id"]
    assert battle_id is not None
    assert start_data["status"] == "in_progress"
    assert start_data["turn"] == 1

    # 3. Consultar estado de la batalla
    get_res = client.get(f"/api/pve/battle/{battle_id}")
    assert get_res.status_code == 200
    assert get_res.json()["battle_id"] == battle_id

    # 4. Enviar un turno: Swampert usa Waterfall
    turn_res = client.post("/api/pve/turn", json={
        "battle_id": battle_id,
        "action": {
            "type": "MOVE",
            "choice": "Waterfall",
            "mega": False
        }
    })
    assert turn_res.status_code == 200
    turn_data = turn_res.json()
    assert turn_data["turn"] == 2
    assert len(turn_data["events"]) > 0
    assert "ai_action" in turn_data

    # 5. Probar surrender
    surrender_res = client.post("/api/pve/surrender", json={"battle_id": battle_id})
    assert surrender_res.status_code == 200
    assert surrender_res.json()["status"] == "surrendered"

    print("ALL PVE API ROUTE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_pve_full_lifecycle()
