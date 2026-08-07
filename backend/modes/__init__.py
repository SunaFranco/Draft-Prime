from backend.modes import cube_draft
from backend.modes import pokemon_auction

async def handle_mode_action(session: dict, username: str, message: dict, manager, websocket):
    mode = session.get("mode")
    if mode == "cube_draft_yugioh":
        await cube_draft.handle_action(session, username, message, manager, websocket)
    elif mode == "subasta_pokemon":
        await pokemon_auction.handle_action(session, username, message, manager, websocket)
    else:
        await manager.send_personal(websocket, {
            "event": "error",
            "data": {"message": f"Modo de juego no soportado o desconocido: '{mode}'"}
        })
