"""
backend/engine/pkmn_ai_engine/core/models.py
Modelos inmutables y ultra-ligeros con slots=True para maximizar el rendimiento y ahorrar RAM.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple


@dataclass(slots=True)
class StatBlock:
    hp: int = 100
    atk: int = 100
    def_: int = 100
    spa: int = 100
    spd: int = 100
    spe: int = 100

    def to_dict(self) -> dict:
        return {
            "hp": self.hp,
            "atk": self.atk,
            "def": self.def_,
            "spa": self.spa,
            "spd": self.spd,
            "spe": self.spe,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "StatBlock":
        if not data:
            return cls()
        return cls(
            hp=int(data.get("hp", 100)),
            atk=int(data.get("atk", 100)),
            def_=int(data.get("def", data.get("def_", 100))),
            spa=int(data.get("spa", 100)),
            spd=int(data.get("spd", 100)),
            spe=int(data.get("spe", 100)),
        )


@dataclass(slots=True)
class StatBoosts:
    atk: int = 0
    def_: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0
    accuracy: int = 0
    evasion: int = 0

    def to_dict(self) -> dict:
        return {
            "atk": self.atk,
            "def": self.def_,
            "spa": self.spa,
            "spd": self.spd,
            "spe": self.spe,
            "accuracy": self.accuracy,
            "evasion": self.evasion,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "StatBoosts":
        if not data:
            return cls()
        return cls(
            atk=int(data.get("atk", 0)),
            def_=int(data.get("def", data.get("def_", 0))),
            spa=int(data.get("spa", 0)),
            spd=int(data.get("spd", 0)),
            spe=int(data.get("spe", 0)),
            accuracy=int(data.get("accuracy", 0)),
            evasion=int(data.get("evasion", 0)),
        )


@dataclass(slots=True)
class MoveState:
    id: str
    name: str
    type: str
    category: str              # "physical" | "special" | "status"
    base_power: int = 0
    accuracy: float = 1.0       # 0.0 a 1.0
    priority: int = 0
    pp: int = 15
    max_pp: int = 15
    drain_percent: float = 0.0
    recoil_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "base_power": self.base_power,
            "accuracy": self.accuracy,
            "priority": self.priority,
            "pp": self.pp,
            "max_pp": self.max_pp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MoveState":
        return cls(
            id=str(data.get("id", data.get("name", "tackle"))).lower().replace(" ", "-"),
            name=str(data.get("name", "Tackle")),
            type=str(data.get("type", "Normal")),
            category=str(data.get("category", "physical")).lower(),
            base_power=int(data.get("base_power", data.get("power", 0) or 0)),
            accuracy=float(data.get("accuracy", 1.0) or 1.0),
            priority=int(data.get("priority", 0)),
            pp=int(data.get("pp", 15)),
            max_pp=int(data.get("max_pp", 15)),
        )


@dataclass(slots=True)
class PokemonState:
    id: str
    species: str
    types: Tuple[str, ...]
    level: int = 50
    current_hp: int = 100
    max_hp: int = 100
    stats: StatBlock = field(default_factory=StatBlock)
    boosts: StatBoosts = field(default_factory=StatBoosts)
    status: Optional[str] = None  # "BRN", "PAR", "SLP", "PSN", "FRZ", None
    item: Optional[str] = None
    ability: Optional[str] = None
    moves: List[MoveState] = field(default_factory=list)
    is_fainted: bool = False
    is_mega: bool = False
    can_mega: bool = False
    mega_stone: Optional[str] = None
    image_url: Optional[str] = None

    @property
    def hp_percent(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_hp / self.max_hp))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "species": self.species,
            "types": list(self.types),
            "level": self.level,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "hp_percent": round(self.hp_percent, 3),
            "stats": self.stats.to_dict(),
            "boosts": self.boosts.to_dict(),
            "status": self.status,
            "item": self.item,
            "ability": self.ability,
            "moves": [m.to_dict() for m in self.moves],
            "is_fainted": self.is_fainted or self.current_hp <= 0,
            "is_mega": self.is_mega,
            "can_mega": self.can_mega,
            "mega_stone": self.mega_stone,
            "image_url": self.image_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PokemonState":
        raw_types = data.get("types", [])
        if isinstance(raw_types, list):
            types_tuple = tuple(raw_types)
        elif isinstance(raw_types, str):
            types_tuple = (raw_types,)
        else:
            types_tuple = ("Normal",)

        raw_moves = [MoveState.from_dict(m) if isinstance(m, dict) else m for m in data.get("moves", [])]

        cur_hp = int(data.get("current_hp", data.get("max_hp", 100)))
        max_hp = int(data.get("max_hp", 100))

        return cls(
            id=str(data.get("id", data.get("species", data.get("name", "pikachu")))),
            species=str(data.get("species", data.get("name", "Pikachu"))),
            types=types_tuple,
            level=int(data.get("level", 50)),
            current_hp=cur_hp,
            max_hp=max_hp,
            stats=StatBlock.from_dict(data.get("stats")),
            boosts=StatBoosts.from_dict(data.get("boosts")),
            status=data.get("status"),
            item=data.get("item") or data.get("held_item"),
            ability=data.get("ability"),
            moves=raw_moves,
            is_fainted=data.get("is_fainted", cur_hp <= 0),
            is_mega=bool(data.get("is_mega", False)),
            can_mega=bool(data.get("can_mega", False)),
            mega_stone=data.get("mega_stone"),
            image_url=data.get("image_url"),
        )


@dataclass(slots=True)
class Action:
    type: str            # "MOVE" o "SWITCH"
    choice: str          # ID del movimiento o ID del Pokémon a cambiar
    mega: bool = False   # ¿Activa Megaevolución en este turno?

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "choice": self.choice,
            "mega": self.mega,
        }


@dataclass(slots=True)
class DecisionResult:
    action: Action
    score: float
    debug_rationale: str = ""
    scores_evaluated: Dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class BattleSnapshot:
    turn: int = 1
    weather: Optional[str] = None          # "Sun", "Rain", "Sandstorm", "Snow", None
    weather_turns: int = 0
    player_active: Optional[PokemonState] = None
    player_bench: List[PokemonState] = field(default_factory=list)
    ai_active: Optional[PokemonState] = None
    ai_bench: List[PokemonState] = field(default_factory=list)
    player_mega_used: bool = False
    ai_mega_used: bool = False

    def __init__(
        self,
        turn: int = 1,
        weather: Optional[str] = None,
        weather_turns: int = 0,
        player_active: Optional[PokemonState] = None,
        player_bench: Optional[List[PokemonState]] = None,
        ai_active: Optional[PokemonState] = None,
        ai_bench: Optional[List[PokemonState]] = None,
        player_mega_used: bool = False,
        ai_mega_used: bool = False,
        opponent_active: Optional[PokemonState] = None,
        opponent_bench: Optional[List[PokemonState]] = None,
        opponent_mega_used: Optional[bool] = None,
    ):
        self.turn = turn
        self.weather = weather
        self.weather_turns = weather_turns
        self.player_active = player_active or opponent_active
        self.player_bench = player_bench if player_bench is not None else (opponent_bench or [])
        self.ai_active = ai_active
        self.ai_bench = ai_bench if ai_bench is not None else []
        self.player_mega_used = player_mega_used if opponent_mega_used is None else opponent_mega_used
        self.ai_mega_used = ai_mega_used

    @property
    def opponent_active(self) -> Optional[PokemonState]:
        return self.player_active

    @opponent_active.setter
    def opponent_active(self, val: Optional[PokemonState]) -> None:
        self.player_active = val

    @property
    def opponent_bench(self) -> List[PokemonState]:
        return self.player_bench

    @opponent_bench.setter
    def opponent_bench(self, val: List[PokemonState]) -> None:
        self.player_bench = val

    @property
    def opponent_mega_used(self) -> bool:
        return self.player_mega_used

    @opponent_mega_used.setter
    def opponent_mega_used(self, val: bool) -> None:
        self.player_mega_used = val

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "weather": self.weather,
            "weather_turns": self.weather_turns,
            "player_active": self.player_active.to_dict() if self.player_active else None,
            "player_bench": [p.to_dict() for p in self.player_bench],
            "ai_active": self.ai_active.to_dict() if self.ai_active else None,
            "ai_bench": [p.to_dict() for p in self.ai_bench],
            "player_mega_used": self.player_mega_used,
            "ai_mega_used": self.ai_mega_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BattleSnapshot":
        p_act = data.get("player_active") or data.get("opponent_active")
        p_bench = data.get("player_bench") or data.get("opponent_bench") or []
        ai_act = data.get("ai_active")
        ai_bench = data.get("ai_bench") or []

        player_active = PokemonState.from_dict(p_act) if p_act else None
        ai_active = PokemonState.from_dict(ai_act) if ai_act else None
        player_bench = [PokemonState.from_dict(p) for p in p_bench]
        ai_bench = [PokemonState.from_dict(p) for p in ai_bench]

        return cls(
            turn=int(data.get("turn", 1)),
            weather=data.get("weather"),
            weather_turns=int(data.get("weather_turns", 0)),
            player_active=player_active,
            player_bench=player_bench,
            ai_active=ai_active,
            ai_bench=ai_bench,
            player_mega_used=bool(data.get("player_mega_used", data.get("opponent_mega_used", False))),
            ai_mega_used=bool(data.get("ai_mega_used", False)),
        )
