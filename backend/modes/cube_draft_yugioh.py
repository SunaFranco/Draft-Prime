"""
Implementación del modo `cube_draft_yugioh`.
Contiene la lógica específica del draft de tipo 'cube' (preparar sobres,
iniciar draft, abrir packs, etc.).
"""

import json
import random
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Dict

from backend.database import get_all_cubes, get_cube_by_id

# Cache simple para cartas consultadas por nombre
CARD_CACHE: Dict[str, dict] = {}

YGOPRODECK_API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


def validate_config(config: dict) -> bool:
    required = ("cube_key", "pack_count", "cards_per_pack")
    return all(k in config for k in required)


def default_config() -> dict:
    return {"cube_key": None, "pack_count": 3, "cards_per_pack": 5}


def fetch_yugioh_card(name: str) -> dict:
    if name in CARD_CACHE:
        return CARD_CACHE[name]

    query = urllib.parse.urlencode({"name": name})
    url = f"{YGOPRODECK_API_URL}?{query}"
    try:
        ctx = ssl.create_default_context()
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        with urllib.request.urlopen(request, context=ctx, timeout=8) as response:
            payload = json.loads(response.read().decode())
            card_data = payload.get("data", [])[0]
            image_info = card_data.get("card_images", [{}])[0]
            card = {
                "id":        card_data.get("id", name),
                "name":      card_data.get("name", name),
                "type":      card_data.get("type", ""),
                "desc":      card_data.get("desc", ""),
                "image_url": image_info.get("image_url_small") or image_info.get("image_url") or "",
            }
    except Exception:
        card = {
            "id":        name,
            "name":      name,
            "type":      "Desconocido",
            "desc":      "No se pudo cargar la carta desde la API.",
            "image_url": "",
        }

    CARD_CACHE[name] = card
    return card


def build_card_from_name(card_name: str) -> dict:
    card = fetch_yugioh_card(card_name)
    return {**card, "name": card.get("name") or card_name}


def get_available_cubes() -> List[dict]:
    cubes = []
    for cube in get_all_cubes():
        cube_id = cube.get("id")
        if not cube_id:
            continue
        cubes.append({"key": cube_id, "title": cube.get("title", "Cube")})
    return cubes


def resolve_cube_for_key(cube_key: str) -> dict | None:
    return get_cube_by_id(cube_key)


def get_cube_card_pool(cube_key: str) -> List[dict]:
    db_cube = resolve_cube_for_key(cube_key)
    if db_cube:
        cards = db_cube.get("cards", []) or []
        return cards
    raise ValueError(f"Cube desconocido: {cube_key}")


def get_connected_player_order(session: dict) -> List[str]:
    return [p["username"] for p in session["players"] if p["connected"]]


def init_draft_round(session: dict, round_num: int):
    draft = session["draft"]
    order = draft["picker_order"]
    cube_key = draft["cube_key"]
    cards_per_pack = draft["cards_per_pack"]
    pool = get_cube_card_pool(cube_key)

    draft["current_round"] = round_num
    draft["current_step"] = 1
    draft["picks_in_step"] = {u: None for u in order}
    draft["current_packs"] = {}

    for idx, username in enumerate(order):
        selected_names = random.sample(pool, k=cards_per_pack)
        pack_cards = [build_card_from_name(card_name) for card_name in selected_names]
        draft["current_packs"][username] = {
            "pack_id": f"round_{round_num}_pack_{idx + 1}",
            "initial_owner": username,
            "cards": pack_cards,
        }


def start_draft_session(session: dict):
    config = session["mode_config"]
    order = get_connected_player_order(session)

    session["draft"] = {
        "cube_key":        config["cube_key"],
        "pack_count":      config["pack_count"],
        "cards_per_pack":  config["cards_per_pack"],
        "current_round":   1,
        "current_step":    1,
        "picker_order":    order,
        "current_packs":   {},
        "picks_in_step":   {u: None for u in order},
        "collections":     {u: [] for u in order},
        "finished":        False,
    }

    init_draft_round(session, 1)

