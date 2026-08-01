"""
database.py - Conexión a Supabase (PostgreSQL)

Maneja la inicialización del cliente de Supabase usando variables de entorno.
Si no hay credenciales configuradas (desarrollo local sin .env), opera en modo
fallback usando datos en memoria para no romper el flujo de trabajo.
"""

import os
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

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
