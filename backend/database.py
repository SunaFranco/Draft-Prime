"""
database.py - Conexión a Supabase (PostgreSQL)

Maneja la inicialización del cliente de Supabase usando variables de entorno.
Si no hay credenciales configuradas (desarrollo local sin .env), opera en modo
fallback usando datos en memoria para no romper el flujo de trabajo.
"""

import os
import random
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_PUBLIC_KEY: str = (
    os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    or os.getenv("SUPABASE_ANON_KEY", "")
    or os.getenv("SUPABASE_KEY", "")
)
SUPABASE_SERVICE_KEY: str = (
    os.getenv("SUPABASE_SECRET_KEY", "")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
)
# Database writes must use a server-only key once RLS is enabled. Keep the
# legacy key as a development fallback until deployment config is updated.
SUPABASE_KEY: str = SUPABASE_SERVICE_KEY or SUPABASE_PUBLIC_KEY

supabase_client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase_client: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[OK] Conexion con Supabase inicializada correctamente.")
    except Exception as e:
        print(f"[WARNING] Error al conectar con Supabase: {e}. Se usara el almacenamiento local en memoria.")
else:
    print("[INFO] No se detectaron SUPABASE_URL y SUPABASE_KEY. Operando en modo fallback (Memoria Local).")


def get_all_cubes() -> List[dict]:
    """Obtiene todos los cubes desde Supabase."""
    if not supabase_client:
        return []

    try:
        res = supabase_client.table("cubes").select("*, cube_cards(card_name, qty)").execute()
        if res.data:
            processed = []
            for item in res.data:
                cards = []
                for card in item.get("cube_cards", []):
                    cards.extend([card["card_name"]] * card.get("qty", 1))
                processed.append({
                    "id": str(item["id"]),
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "author": item.get("author", "Anon"),
                    "is_public": item.get("is_public", True),
                    "cards": cards
                })
            return processed
    except Exception as e:
        print(f"[WARNING] Error consultando Supabase: {e}")

    return []


def get_cube_by_id(cube_id: str) -> Optional[dict]:
    """Obtiene un cube por su ID desde Supabase."""
    if not supabase_client:
        return None

    try:
        res = supabase_client.table("cubes").select("*, cube_cards(card_name, qty)").eq("id", cube_id).execute()
        if res.data and len(res.data) > 0:
            item = res.data[0]
            cards = []
            for card in item.get("cube_cards", []):
                cards.extend([card["card_name"]] * card.get("qty", 1))
            return {
                "id": str(item["id"]),
                "title": item["title"],
                "description": item.get("description", ""),
                "author": item.get("author", "Anon"),
                "is_public": item.get("is_public", True),
                "cards": cards
            }
    except Exception as e:
        print(f"[WARNING] Error al obtener Cube {cube_id} de Supabase: {e}")

    return None


def create_new_cube(title: str, description: str, cards: List[str], author: str = "Anon") -> dict:
    """Crea un nuevo cube en Supabase."""
    if not supabase_client:
        raise RuntimeError("No hay cliente de Supabase inicializado.")

    try:
        cube_res = supabase_client.table("cubes").insert({
            "title": title,
            "description": description,
            "author": author
        }).execute()

        if cube_res.data and len(cube_res.data) > 0:
            created_cube = cube_res.data[0]
            new_id = created_cube["id"]

            card_counts: Dict[str, int] = {}
            for card in cards:
                card_counts[card] = card_counts.get(card, 0) + 1

            cards_to_insert = [
                {"cube_id": new_id, "card_name": card_name, "qty": qty}
                for card_name, qty in card_counts.items()
            ]

            if cards_to_insert:
                supabase_client.table("cube_cards").insert(cards_to_insert).execute()

            return {
                "id": str(new_id),
                "title": title,
                "description": description,
                "author": author,
                "cards": cards
            }
    except Exception as e:
        raise RuntimeError(f"Error guardando Cube en Supabase: {e}") from e

    raise RuntimeError("No se pudo crear el cube en Supabase.")


from collections import OrderedDict

MAX_MEMORY_SESSIONS = 50
MEMORY_GAME_SESSIONS: OrderedDict[str, dict] = OrderedDict()


def save_full_session(session: dict) -> None:
    """Guarda la estructura completa de una sesión en Supabase y caché local."""
    session_id = session.get("id")
    if not session_id:
        return

    mode = session.get("mode") or "lobby"

    # Preparar copia sin referencias de sockets
    clean_players = [
        {
            "username": p["username"],
            "display_name": p.get("display_name", p["username"]),
            "avatar_key": p.get("avatar_key", "avatar_01"),
            "user_id": p.get("user_id"),
            "is_admin": p.get("is_admin", False),
            "ready": p.get("ready", False),
            "connected": False,  # Al persistir, el socket se reconectará después
        }
        for p in session.get("players", [])
    ]

    session_payload = {
        "id": session_id,
        "host": session.get("host"),
        "created_by": session.get("created_by"),
        "status": session.get("status", "active"),
        "finish_type": session.get("finish_type"),
        "finished_at": session.get("finished_at"),
        "players": clean_players,
        "max_players": session.get("max_players", 4),
        "started": session.get("started", False),
        "created_at": session.get("created_at"),
        "created_ts": session.get("created_ts"),
        "last_activity": session.get("last_activity"),
        "mode": mode,
        "mode_config": session.get("mode_config"),
    }

    if "subasta" in session:
        session_payload["subasta"] = session["subasta"]
    if "draft" in session:
        session_payload["draft"] = session["draft"]

    if session_id in MEMORY_GAME_SESSIONS:
        MEMORY_GAME_SESSIONS.move_to_end(session_id)
    elif len(MEMORY_GAME_SESSIONS) >= MAX_MEMORY_SESSIONS:
        MEMORY_GAME_SESSIONS.popitem(last=False)

    MEMORY_GAME_SESSIONS[session_id] = session_payload

    if supabase_client:
        try:
            supabase_client.table("game_sessions").upsert({
                "session_id": session_id,
                "mode": mode,
                "state_data": session_payload,
                "created_by": session.get("created_by"),
                "status": session.get("status", "active"),
                "finish_type": session.get("finish_type"),
                "finished_at": session.get("finished_at"),
            }).execute()
        except Exception as e:
            print(f"[WARNING] Error guardando sesión {session_id} en Supabase: {e}")


def get_full_session(session_id: str) -> Optional[dict]:
    """Recupera la sesión completa desde Supabase o memoria local."""
    raw_data = None
    if session_id in MEMORY_GAME_SESSIONS:
        MEMORY_GAME_SESSIONS.move_to_end(session_id)
        raw_data = MEMORY_GAME_SESSIONS[session_id]

    if not raw_data and supabase_client:
        try:
            res = supabase_client.table("game_sessions").select("mode, state_data").eq("session_id", session_id).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                raw_data = row.get("state_data")
                mode = row.get("mode")
                if raw_data:
                    # Soporte retrocompatible si solo se guardó subasta_state
                    if "players" not in raw_data and isinstance(raw_data, dict) and "player_order" in raw_data:
                        order = raw_data.get("player_order", [])
                        raw_data = {
                            "id": session_id,
                            "host": order[0] if order else "Host",
                            "players": [{"username": u, "ready": True, "connected": False} for u in order],
                            "max_players": 4,
                            "started": True,
                            "mode": mode or "subasta_pokemon",
                            "subasta": raw_data,
                        }
                    if len(MEMORY_GAME_SESSIONS) >= MAX_MEMORY_SESSIONS:
                        MEMORY_GAME_SESSIONS.popitem(last=False)
                    MEMORY_GAME_SESSIONS[session_id] = raw_data
        except Exception as e:
            print(f"[WARNING] Error recuperando sesión {session_id} desde Supabase: {e}")

    if raw_data and isinstance(raw_data, dict):
        return dict(raw_data)

    return None


def save_game_session(session_id: str, mode: str, state_data: dict) -> None:
    """Guarda o actualiza el estado de una partida en Supabase o en memoria local."""
    try:
        from backend.services.session_manager import sessions
        session = sessions.get(session_id)
        if session:
            if mode == "subasta_pokemon":
                session["subasta"] = state_data
            elif mode == "cube_draft_yugioh":
                session["draft"] = state_data
            else:
                session[mode] = state_data
            save_full_session(session)
            return
    except Exception:
        pass

    if session_id in MEMORY_GAME_SESSIONS:
        MEMORY_GAME_SESSIONS.move_to_end(session_id)
    elif len(MEMORY_GAME_SESSIONS) >= MAX_MEMORY_SESSIONS:
        MEMORY_GAME_SESSIONS.popitem(last=False)

    MEMORY_GAME_SESSIONS[session_id] = state_data

    if supabase_client:
        try:
            supabase_client.table("game_sessions").upsert({
                "session_id": session_id,
                "mode": mode,
                "state_data": state_data
            }).execute()
        except Exception as e:
            print(f"[WARNING] Error guardando estado de partida {session_id} en Supabase: {e}")


def get_game_session(session_id: str) -> Optional[dict]:
    """Obtiene el estado guardado de una partida desde Supabase o memoria local."""
    if session_id in MEMORY_GAME_SESSIONS:
        MEMORY_GAME_SESSIONS.move_to_end(session_id)
        return MEMORY_GAME_SESSIONS[session_id]

    if supabase_client:
        try:
            res = supabase_client.table("game_sessions").select("state_data").eq("session_id", session_id).execute()
            if res.data and len(res.data) > 0:
                data = res.data[0].get("state_data")
                if data:
                    if len(MEMORY_GAME_SESSIONS) >= MAX_MEMORY_SESSIONS:
                        MEMORY_GAME_SESSIONS.popitem(last=False)
                    MEMORY_GAME_SESSIONS[session_id] = data
                    return data
        except Exception as e:
            print(f"[WARNING] Error cargando partida {session_id} desde Supabase: {e}")

    return None


def delete_game_session(session_id: str) -> None:
    """Elimina una sesión de la memoria local."""
    MEMORY_GAME_SESSIONS.pop(session_id, None)


def get_legendary_pokemon_from_db() -> List[str]:
    """Obtiene los nombres de Pokémon legendarios desde la tabla dedicada de Supabase."""
    if not supabase_client:
        return []

    try:
        res = supabase_client.table("legendarios").select("nombre").execute()
        names = [row["nombre"] for row in res.data or [] if row.get("nombre")]
        if names:
            print(f"[OK] [SUPABASE] Se obtuvieron {len(names)} Pokémon desde la tabla 'legendarios'.")
        return names
    except Exception as e:
        print(f"[WARNING] Error consultando la tabla 'legendarios' en Supabase: {e}")
        return []


def get_pokemon_pools_from_db(year: Optional[int] = None, auction_type: Optional[str] = None) -> List[str]:
    """Obtiene la lista de nombres de Pokémon desde la base de datos filtrada por año y tipo de subasta."""
    if not supabase_client:
        print("[INFO] [SUPABASE] Sin cliente de Supabase (sin SUPABASE_URL / KEY). Usando pool local.")
        return []

    clean_type = auction_type.strip().lower() if auction_type else None

    if clean_type == "legendary":
        names = get_legendary_pokemon_from_db()
        if names:
            return names

    # 1. Si se buscan megas, intentar primero si existe tabla dedicada 'mega_pokemon'
    if clean_type == "mega":
        try:
            res_mega = supabase_client.table("mega_pokemon").select("name").execute()
            if res_mega.data and len(res_mega.data) > 0:
                names = [row["name"] for row in res_mega.data if row.get("name")]
                if names:
                    print(f"[OK] [SUPABASE] Se obtuvieron {len(names)} Megas desde la tabla 'mega_pokemon'.")
                    return names
        except Exception:
            pass  # Si la tabla mega_pokemon no existe, continúa buscando en pokemon_pools

    try:
        query = supabase_client.table("pokemon_pools").select("id, year, auction_type, pokemon_pool_cards(pokemon_name, qty)")
        if year is not None:
            query = query.eq("year", year)
        if clean_type:
            query = query.ilike("auction_type", clean_type)

        res = query.execute()
        if res.data:
            names = []
            for pool_item in res.data:
                for card in pool_item.get("pokemon_pool_cards", []):
                    if card.get("pokemon_name"):
                        names.extend([card["pokemon_name"]] * card.get("qty", 1))
            if names:
                print(f"[OK] [SUPABASE] Se obtuvieron {len(names)} Pokémon de la DB (Año={year}, Tipo='{clean_type}').")
                return names

        # Si no encontró resultados exactos con filtro por año, buscar en pokemon_pools respetando el auction_type
        if clean_type:
            res_fallback = supabase_client.table("pokemon_pools").select("id, auction_type, pokemon_pool_cards(pokemon_name, qty)").ilike("auction_type", clean_type).execute()
            if res_fallback.data:
                names = []
                for pool_item in res_fallback.data:
                    for card in pool_item.get("pokemon_pool_cards", []):
                        if card.get("pokemon_name"):
                            names.extend([card["pokemon_name"]] * card.get("qty", 1))
                if names:
                    print(f"[OK] [SUPABASE FALLBACK] Obtenidos {len(names)} Pokémon de tipo '{clean_type}' en la DB.")
                    return names

    except Exception as e:
        print(f"[WARNING] Error consultando pokemon_pools en Supabase: {e}")

    return []


def remove_pokemon_from_db(
    pokemon_name: str, year: Optional[int] = None, auction_type: Optional[str] = None
) -> bool:
    """Elimina una carta Pokémon inválida del pool de subasta correspondiente."""
    if not supabase_client:
        return False

    clean_type = auction_type.strip().lower() if auction_type else None
    if clean_type == "legendary":
        try:
            response = (
                supabase_client.table("legendarios")
                .delete(returning="representation")
                .eq("nombre", pokemon_name)
                .execute()
            )
            if response.data:
                return True
        except Exception as error:
            print(f"[WARNING] No se pudo eliminar '{pokemon_name}' de 'legendarios': {error}")

    if clean_type == "mega":
        try:
            response = (
                supabase_client.table("mega_pokemon")
                .delete(returning="representation")
                .eq("name", pokemon_name)
                .execute()
            )
            if response.data:
                return True
        except Exception:
            # Puede que la pool de Megas esté almacenada en pokemon_pools.
            pass

    try:
        query = (
            supabase_client.table("pokemon_pools")
            .select("id, year, auction_type, pokemon_pool_cards(id, pokemon_name)")
        )
        if year is not None:
            query = query.eq("year", year)
        if clean_type:
            query = query.ilike("auction_type", clean_type)

        pools = query.execute().data or []
        if not pools and year is not None:
            fallback_query = (
                supabase_client.table("pokemon_pools")
                .select("id, year, auction_type, pokemon_pool_cards(id, pokemon_name)")
            )
            if clean_type:
                fallback_query = fallback_query.ilike("auction_type", clean_type)
            pools = fallback_query.execute().data or []

        deleted = False
        for pool in pools:
            for card in pool.get("pokemon_pool_cards") or []:
                card_name = card.get("pokemon_name")
                if not card_name or card_name.casefold() != pokemon_name.casefold():
                    continue
                response = (
                    supabase_client.table("pokemon_pool_cards")
                    .delete(returning="representation")
                    .eq("id", card["id"])
                    .execute()
                )
                deleted = deleted or bool(response.data)
        return deleted
    except Exception as error:
        print(f"[WARNING] No se pudo eliminar '{pokemon_name}' de 'pokemon_pools': {error}")
        return False


def get_random_pokemon_from_db(year: Optional[int] = None, auction_type: Optional[str] = None) -> Optional[str]:
    """Obtiene un único Pokémon aleatorio sin cargar completa la pool en memoria."""
    if not supabase_client:
        return None

    clean_type = auction_type.strip().lower() if auction_type else None

    if clean_type == "legendary":
        names = get_legendary_pokemon_from_db()
        if names:
            return random.choice(names)

    if clean_type == "mega":
        try:
            count_res = supabase_client.table("mega_pokemon").select("name", count="exact", head=True).execute()
            if count_res.count:
                index = random.randrange(count_res.count)
                res = supabase_client.table("mega_pokemon").select("name").range(index, index).execute()
                if res.data:
                    return res.data[0].get("name")
        except Exception:
            pass  # Si la tabla mega_pokemon no existe, continúa buscando en pokemon_pools

    def choose_from_pools(pool_year: Optional[int]) -> Optional[str]:
        query = supabase_client.table("pokemon_pools").select("id, pokemon_pool_cards(count)")
        if pool_year is not None:
            query = query.eq("year", pool_year)
        if clean_type:
            query = query.ilike("auction_type", clean_type)

        pool_res = query.execute()
        pool_sizes = []
        for pool in pool_res.data or []:
            counts = pool.get("pokemon_pool_cards") or []
            card_count = counts[0].get("count", 0) if counts else 0
            if card_count:
                pool_sizes.append((pool["id"], card_count))

        total_cards = sum(size for _, size in pool_sizes)
        if not total_cards:
            return None

        selected_index = random.randrange(total_cards)
        for pool_id, card_count in pool_sizes:
            if selected_index < card_count:
                card_res = (
                    supabase_client.table("pokemon_pools")
                    .select("pokemon_pool_cards(pokemon_name)")
                    .eq("id", pool_id)
                    .range(0, 0)
                    .range(selected_index, selected_index, foreign_table="pokemon_pool_cards")
                    .execute()
                )
                if card_res.data:
                    cards = card_res.data[0].get("pokemon_pool_cards") or []
                    if cards:
                        return cards[0].get("pokemon_name")
                return None
            selected_index -= card_count
        return None

    try:
        chosen = choose_from_pools(year)
        if chosen:
            return chosen
        if clean_type and year is not None:
            return choose_from_pools(None)
    except Exception as e:
        print(f"[WARNING] Error eligiendo Pokémon aleatorio desde Supabase: {e}")

    return None
