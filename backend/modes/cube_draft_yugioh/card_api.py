"""
backend/modes/cube_draft_yugioh/card_api.py - Integración con API de Yu-Gi-Oh (YGOPRODECK)
"""

import json
import ssl
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Dict

YGOPRODECK_API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
MAX_CARD_CACHE = 250
CARD_CACHE: OrderedDict[str, dict] = OrderedDict()


def fetch_yugioh_card(name: str) -> dict:
    """Consulta la API de YGOPRODECK para obtener detalles e imágenes de una carta de Yu-Gi-Oh."""
    if name in CARD_CACHE:
        CARD_CACHE.move_to_end(name)
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
                "id":         card_data.get("id", name),
                "name":       card_data.get("name", name),
                "type":       card_data.get("type", ""),
                "desc":       card_data.get("desc", ""),
                "race":       card_data.get("race", ""),
                "attribute":  card_data.get("attribute", ""),
                "level":      card_data.get("level"),
                "atk":        card_data.get("atk"),
                "def":        card_data.get("def"),
                "frameType":  card_data.get("frameType", ""),
                "archetype":  card_data.get("archetype", ""),
                "image_url":  image_info.get("image_url_small") or image_info.get("image_url_cropped") or image_info.get("image_url") or "",
            }
    except Exception:
        card = {
            "id":        name,
            "name":      name,
            "type":      "Desconocido",
            "desc":      "No se pudo cargar la carta desde la API.",
            "image_url": "",
        }

    if len(CARD_CACHE) >= MAX_CARD_CACHE:
        CARD_CACHE.popitem(last=False)
    CARD_CACHE[name] = card
    return card


def build_card_from_name(card_name: str) -> dict:
    """Construye la representación completa de la carta desde su nombre."""
    card = fetch_yugioh_card(card_name)
    return {**card, "name": card.get("name") or card_name}
