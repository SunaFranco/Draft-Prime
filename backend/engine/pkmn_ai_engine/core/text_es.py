"""
backend/engine/pkmn_ai_engine/core/text_es.py
Sistema de localización en Español basado en el sistema TL de Pokémon Showdown
(smogon/pokemon-showdown/data/text/es/moves.ts, abilities.ts, items.ts).
Mantiene los IDs canónicos en inglés para el simulador y expone nombres y descripciones en español.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

_DATA_PATH = Path(__file__).parent / "data" / "showdown_text_es.json"
_CATALOG: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None


def to_showdown_id(text: Any) -> str:
    """Convierte cualquier identificador al formato ID de Showdown (solo minúsculas alfanuméricas)."""
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _get_catalog() -> Dict[str, Dict[str, Dict[str, str]]]:
    global _CATALOG
    if _CATALOG is None:
        try:
            _CATALOG = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            _CATALOG = {"moves": {}, "abilities": {}, "items": {}}
    return _CATALOG


def get_move_text_es(name_or_id: str) -> Dict[str, str]:
    """Devuelve {'id', 'en', 'es', 'desc'} para un movimiento."""
    raw = str(name_or_id or "").strip()
    clean = raw[3:].strip() if raw.startswith("MT ") else raw
    sid = to_showdown_id(clean)
    entry = _get_catalog().get("moves", {}).get(sid) or {}
    return {
        "id": sid,
        "en": entry.get("en") or clean,
        "es": entry.get("es") or clean,
        "desc": entry.get("desc") or "",
    }


def get_ability_text_es(name_or_id: Optional[str]) -> Dict[str, str]:
    """Devuelve {'id', 'en', 'es', 'desc'} para una habilidad."""
    raw = str(name_or_id or "").strip()
    if not raw:
        return {"id": "", "en": "", "es": "", "desc": ""}
    sid = to_showdown_id(raw)
    entry = _get_catalog().get("abilities", {}).get(sid) or {}
    return {
        "id": sid,
        "en": entry.get("en") or raw,
        "es": entry.get("es") or raw,
        "desc": entry.get("desc") or "",
    }


def get_item_text_es(name_or_id: Optional[str]) -> Dict[str, str]:
    """Devuelve {'id', 'en', 'es', 'desc'} para un objeto equipado."""
    raw = str(name_or_id or "").strip()
    if not raw:
        return {"id": "", "en": "", "es": "", "desc": ""}
    sid = to_showdown_id(raw)
    entry = _get_catalog().get("items", {}).get(sid) or {}
    return {
        "id": sid,
        "en": entry.get("en") or raw,
        "es": entry.get("es") or raw,
        "desc": entry.get("desc") or "",
    }
