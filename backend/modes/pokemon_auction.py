"""
pokemon_auction.py - Reglas para el modo de juego "Subasta Pokémon"

Implementa aquí tu propia lógica para la subasta:
- Inicialización del estado de la subasta.
- Manejo de pujas de los jugadores (bids).
- Control de turnos y adjudicación de cartas.
"""

async def handle_action(session: dict, username: str, message: dict, manager, websocket):
    action = message.get("action")
    session_id = session["id"]

    # TODO: Implementar lógica de subasta de Pokémon.
    # Por ejemplo, responder con un error temporal o evento indicando que está en construcción:
    await manager.send_personal(websocket, {
        "event": "error",
        "data": {"message": "El modo Subasta Pokémon está en desarrollo. ¡Escribe tu lógica aquí!"}
    })
