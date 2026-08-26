from backend.services.session_manager import session_public_state, sessions
from backend.modes.registry import get_mode_handler

def test_session_reconnect_draft_state():
    # Setup mock session
    session_id = "test-reconnect-session"
    sessions[session_id] = {
        "id": session_id,
        "host": "Player1",
        "players": [
            {"username": "Player1", "ready": True, "connected": True},
            {"username": "Player2", "ready": True, "connected": True},
        ],
        "max_players": 4,
        "started": True,
        "mode": "cube_draft_yugioh",
        "mode_config": {
            "cube_key": "custom_default",
            "pack_count": 3,
            "cards_per_pack": 5,
        },
        "created_at": "2026-08-26T00:00:00Z",
    }

    session = sessions[session_id]
    
    # Initialize Yu-Gi-Oh draft handler mode and start the game in the session
    handler = get_mode_handler("cube_draft_yugioh")
    
    # Mock resolve_cube_for_key and get_cube_card_pool
    # Let's mock the load of card pool
    import backend.modes.cube_draft_yugioh.handler as yugioh_handler
    original_get_pool = yugioh_handler.get_cube_card_pool
    yugioh_handler.get_cube_card_pool = lambda cube_key, resolve_cube_fn=None: [
        "Blue-Eyes White Dragon", "Dark Magician", "Red-Eyes Black Dragon", "Kuriboh", "Exodia the Forbidden One"
    ] * 10
    
    try:
        handler.start_game(session)
        assert "draft" in session
        assert session["draft"]["finished"] is False
        
        # Test get public state for Player1
        state_p1 = session_public_state(session, target_username="Player1")
        assert "draft_state" in state_p1
        ds1 = state_p1["draft_state"]
        
        assert ds1["round"] == 1
        assert ds1["step"] == 1
        assert ds1["finished"] is False
        assert ds1["has_picked_this_step"] is False
        assert len(ds1["collection"]) == 0
        assert ds1["current_pack"] is not None
        assert len(ds1["current_pack"]["cards"]) == 5
        
        # Player1 picks a card
        card_to_pick = ds1["current_pack"]["cards"][0]["name"]
        session["draft"]["picks_in_step"]["Player1"] = ds1["current_pack"]["cards"][0]
        session["draft"]["current_packs"]["Player1"]["cards"].remove(ds1["current_pack"]["cards"][0])
        session["draft"]["collections"]["Player1"].append(ds1["current_pack"]["cards"][0])
        
        # Test get public state for Player1 again
        state_p1_after = session_public_state(session, target_username="Player1")
        ds1_after = state_p1_after["draft_state"]
        assert ds1_after["has_picked_this_step"] is True
        assert len(ds1_after["collection"]) == 1
        assert ds1_after["current_pack"] is None  # no pack to show because already picked
        
    finally:
        # Restore original
        yugioh_handler.get_cube_card_pool = original_get_pool
        # Cleanup
        sessions.pop(session_id, None)
