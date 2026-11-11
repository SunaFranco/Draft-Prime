"""
backend/engine/pkmn_ai_engine/core/models.py
Modelos de estado inspirados en la arquitectura de Pokémon Showdown (sim/battle.ts, sim/pokemon.ts, sim/side.ts, sim/field.ts).
Optimizado con slots=True para bajo consumo de RAM.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from backend.engine.pkmn_ai_engine.core.text_es import (
    get_move_text_es,
    get_ability_text_es,
    get_item_text_es,
)


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
            atk=int(data.get("atk", data.get("attack", 100))),
            def_=int(data.get("def", data.get("def_", data.get("defense", 100)))),
            spa=int(data.get("spa", data.get("special-attack", 100))),
            spd=int(data.get("spd", data.get("special-defense", 100))),
            spe=int(data.get("spe", data.get("speed", 100))),
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

    def reset(self) -> None:
        self.atk = 0
        self.def_ = 0
        self.spa = 0
        self.spd = 0
        self.spe = 0
        self.accuracy = 0
        self.evasion = 0

    def apply_boosts(self, changes: Dict[str, int]) -> Dict[str, int]:
        """Aplica cambios de etapas (-6 a +6) y devuelve los cambios efectivos aplicados."""
        applied: Dict[str, int] = {}
        mapping = {
            "atk": "atk", "attack": "atk",
            "def": "def_", "def_": "def_", "defense": "def_",
            "spa": "spa", "special-attack": "spa",
            "spd": "spd", "special-defense": "spd",
            "spe": "spe", "speed": "spe",
            "accuracy": "accuracy", "acc": "accuracy",
            "evasion": "evasion", "eva": "evasion",
        }
        for raw_key, delta in (changes or {}).items():
            attr = mapping.get(raw_key.lower())
            if not attr or not delta:
                continue
            old_val = getattr(self, attr)
            new_val = max(-6, min(6, old_val + int(delta)))
            setattr(self, attr, new_val)
            applied[raw_key.lower()] = new_val - old_val
        return applied

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
class SideConditions:
    """Condiciones activas en un lado del campo (Stealth Rock, Spikes, Pantallas, Tailwind)."""
    stealth_rock: bool = False
    spikes: int = 0               # 0 a 3 capas
    toxic_spikes: int = 0         # 0 a 2 capas
    sticky_web: bool = False
    reflect_turns: int = 0        # 0 a 8 turnos
    light_screen_turns: int = 0   # 0 a 8 turnos
    aurora_veil_turns: int = 0    # 0 a 8 turnos
    tailwind_turns: int = 0       # 0 a 4 turnos

    def clear_hazards(self) -> List[str]:
        cleared = []
        if self.stealth_rock:
            self.stealth_rock = False
            cleared.append("Stealth Rock")
        if self.spikes > 0:
            self.spikes = 0
            cleared.append("Spikes")
        if self.toxic_spikes > 0:
            self.toxic_spikes = 0
            cleared.append("Toxic Spikes")
        if self.sticky_web:
            self.sticky_web = False
            cleared.append("Sticky Web")
        return cleared

    def clear_screens(self) -> List[str]:
        cleared = []
        if self.reflect_turns > 0:
            self.reflect_turns = 0
            cleared.append("Reflect")
        if self.light_screen_turns > 0:
            self.light_screen_turns = 0
            cleared.append("Light Screen")
        if self.aurora_veil_turns > 0:
            self.aurora_veil_turns = 0
            cleared.append("Aurora Veil")
        return cleared

    def to_dict(self) -> dict:
        return {
            "stealth_rock": self.stealth_rock,
            "spikes": self.spikes,
            "toxic_spikes": self.toxic_spikes,
            "sticky_web": self.sticky_web,
            "reflect_turns": self.reflect_turns,
            "light_screen_turns": self.light_screen_turns,
            "aurora_veil_turns": self.aurora_veil_turns,
            "tailwind_turns": self.tailwind_turns,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "SideConditions":
        if not data:
            return cls()
        return cls(
            stealth_rock=bool(data.get("stealth_rock", False)),
            spikes=max(0, min(3, int(data.get("spikes", 0)))),
            toxic_spikes=max(0, min(2, int(data.get("toxic_spikes", 0)))),
            sticky_web=bool(data.get("sticky_web", False)),
            reflect_turns=max(0, int(data.get("reflect_turns", 0))),
            light_screen_turns=max(0, int(data.get("light_screen_turns", 0))),
            aurora_veil_turns=max(0, int(data.get("aurora_veil_turns", 0))),
            tailwind_turns=max(0, int(data.get("tailwind_turns", 0))),
        )


@dataclass(slots=True)
class MoveState:
    """Modelo de movimiento inspirado en Showdown data/moves.ts."""
    id: str
    name: str
    type: str
    category: str                                     # "physical" | "special" | "status"
    base_power: int = 0
    accuracy: float = 1.0                             # 0.0 a 1.0 (o True / >1.0 para movimientos que nunca fallan)
    never_miss: bool = False                          # True para Aerial Ace, Swift, Aura Sphere, etc.
    priority: int = 0
    pp: int = 15
    max_pp: int = 15
    drain_percent: float = 0.0                        # Fracción del daño curado (ej. 0.5 para Giga Drain)
    recoil_percent: float = 0.0                       # Fracción del daño recibido por retroceso (ej. 0.33 Flare Blitz)
    heal_fraction: float = 0.0                        # Fracción del max_hp curado (ej. 0.5 Recover)
    crit_ratio: int = 1                               # 1 (normal 1/24), 2 (1/8 Stone Edge/Slash), 3 (1/2), 4 (100%)
    multi_hit: Optional[Tuple[int, int]] = None       # Ej: (2, 5) para Bullet Seed, (2, 2) para Double Kick
    boosts: Optional[Dict[str, int]] = None           # Boosts al objetivo (o al usuario si target=="self")
    self_boosts: Optional[Dict[str, int]] = None      # Boosts al propio usuario tras golpear (ej. Close Combat)
    target_status: Optional[str] = None               # "BRN", "PAR", "PSN", "TOX", "SLP", "FRZ"
    volatile_status: Optional[str] = None             # "confusion", "leech_seed", "taunt", "protect", "substitute", "partially_trapped"
    secondary: Optional[Dict[str, Any]] = None        # {"chance": 0.3, "status": "BRN", "flinch": True, "boosts": {...}, "self_boosts": {...}}
    weather: Optional[str] = None                     # "Sun", "Rain", "Sandstorm", "Snow"
    terrain: Optional[str] = None                     # "Electric", "Grassy", "Psychic", "Misty"
    pseudo_weather: Optional[str] = None              # "trick_room"
    side_condition: Optional[str] = None              # "stealth_rock", "spikes", "toxic_spikes", "sticky_web", "reflect", "light_screen", "aurora_veil", "tailwind"
    hazard_clear: Optional[str] = None                # "rapid_spin" o "defog"
    self_switch: bool = False                         # True para U-turn, Volt Switch, Flip Turn
    force_switch: bool = False                        # True para Roar, Whirlwind, Dragon Tail
    override_defensive_stat: Optional[str] = None     # "def" para Psyshock / Psystrike
    override_offensive_stat: Optional[str] = None     # "def" para Body Press
    must_recharge: bool = False                       # True para Hyper Beam, Giga Impact
    makes_contact: bool = False                       # True para movimientos de contacto
    name_es: str = ""                                 # Nombre oficial en español (Showdown data/text/es/moves.ts)
    desc_es: str = ""                                 # Descripción en español

    def to_dict(self) -> dict:
        es_info = get_move_text_es(self.name or self.id)
        d = {
            "id": self.id,
            "name": self.name,
            "name_es": self.name_es or es_info["es"],
            "desc_es": self.desc_es or es_info["desc"],
            "type": self.type,
            "category": self.category,
            "base_power": self.base_power,
            "accuracy": self.accuracy,
            "never_miss": self.never_miss,
            "priority": self.priority,
            "pp": self.pp,
            "max_pp": self.max_pp,
            "drain_percent": self.drain_percent,
            "recoil_percent": self.recoil_percent,
            "heal_fraction": self.heal_fraction,
            "crit_ratio": self.crit_ratio,
        }
        if self.multi_hit:
            d["multi_hit"] = list(self.multi_hit)
        if self.boosts:
            d["boosts"] = self.boosts
        if self.self_boosts:
            d["self_boosts"] = self.self_boosts
        if self.target_status:
            d["target_status"] = self.target_status
        if self.volatile_status:
            d["volatile_status"] = self.volatile_status
        if self.secondary:
            d["secondary"] = self.secondary
        if self.weather:
            d["weather"] = self.weather
        if self.terrain:
            d["terrain"] = self.terrain
        if self.pseudo_weather:
            d["pseudo_weather"] = self.pseudo_weather
        if self.side_condition:
            d["side_condition"] = self.side_condition
        if self.hazard_clear:
            d["hazard_clear"] = self.hazard_clear
        if self.self_switch:
            d["self_switch"] = self.self_switch
        if self.force_switch:
            d["force_switch"] = self.force_switch
        if self.override_defensive_stat:
            d["override_defensive_stat"] = self.override_defensive_stat
        if self.override_offensive_stat:
            d["override_offensive_stat"] = self.override_offensive_stat
        if self.must_recharge:
            d["must_recharge"] = self.must_recharge
        if self.makes_contact:
            d["makes_contact"] = self.makes_contact
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MoveState":
        mh = data.get("multi_hit")
        multi_hit_tuple = (int(mh[0]), int(mh[1])) if isinstance(mh, (list, tuple)) and len(mh) == 2 else None
        return cls(
            id=str(data.get("id", data.get("slug", data.get("name", "tackle")))).lower().replace(" ", "-"),
            name=str(data.get("name", "Tackle")),
            type=str(data.get("type", "Normal")).capitalize(),
            category=str(data.get("category", "physical")).lower(),
            base_power=int(data.get("base_power", data.get("power", 0) or 0)),
            accuracy=float(data.get("accuracy", 1.0) if data.get("accuracy") is not None else 1.0),
            never_miss=bool(data.get("never_miss", False)),
            priority=int(data.get("priority", 0) or 0),
            pp=int(data.get("pp", 15) or 15),
            max_pp=int(data.get("max_pp", data.get("pp", 15) or 15)),
            drain_percent=float(data.get("drain_percent", 0.0) or 0.0),
            recoil_percent=float(data.get("recoil_percent", 0.0) or 0.0),
            heal_fraction=float(data.get("heal_fraction", 0.0) or 0.0),
            crit_ratio=int(data.get("crit_ratio", 1) or 1),
            multi_hit=multi_hit_tuple,
            boosts=data.get("boosts"),
            self_boosts=data.get("self_boosts"),
            target_status=data.get("target_status"),
            volatile_status=data.get("volatile_status"),
            secondary=data.get("secondary"),
            weather=data.get("weather"),
            terrain=data.get("terrain"),
            pseudo_weather=data.get("pseudo_weather"),
            side_condition=data.get("side_condition"),
            hazard_clear=data.get("hazard_clear"),
            self_switch=bool(data.get("self_switch", False)),
            force_switch=bool(data.get("force_switch", False)),
            override_defensive_stat=data.get("override_defensive_stat"),
            override_offensive_stat=data.get("override_offensive_stat"),
            must_recharge=bool(data.get("must_recharge", False)),
            makes_contact=bool(data.get("makes_contact", False)),
            name_es=str(data.get("name_es") or ""),
            desc_es=str(data.get("desc_es") or ""),
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
    status: Optional[str] = None                  # "BRN", "PAR", "SLP", "PSN", "TOX", "FRZ", None
    status_counter: int = 0                       # Contador de turnos para TOX (veneno grave)
    sleep_turns: int = 0                          # Turnos restantes de sueño (SLP)
    volatiles: Dict[str, Any] = field(default_factory=dict)  # Estados volátiles (confusion, leech_seed, taunt, protect, substitute, etc.)
    substitute_hp: int = 0                        # HP actual del Sustituto (0 si no tiene)
    protect_counter: int = 0                      # Usos consecutivos de Protect
    active_turns: int = 0                         # Turnos que lleva activo en el campo (para First Impression / Fake Out)
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

    def is_grounded(self) -> bool:
        """Determina si el Pokémon toca el suelo (afectado por Spikes, Sticky Web y Terrenos)."""
        if "Flying" in self.types:
            return False
        if (self.ability or "").lower() == "levitate":
            return False
        if (self.item or "").lower() == "air balloon":
            return False
        return True

    def clear_volatile_state_on_switch(self) -> None:
        """En Showdown, al salir del campo se reinician boosts, volátiles, sustituto y contador de tóxico."""
        self.boosts.reset()
        self.volatiles.clear()
        self.substitute_hp = 0
        self.protect_counter = 0
        self.active_turns = 0
        if self.status == "TOX":
            self.status_counter = 1

    def to_dict(self) -> dict:
        ab_es = get_ability_text_es(self.ability)
        it_es = get_item_text_es(self.item)
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
            "status_counter": self.status_counter,
            "sleep_turns": self.sleep_turns,
            "volatiles": dict(self.volatiles),
            "substitute_hp": self.substitute_hp,
            "protect_counter": self.protect_counter,
            "active_turns": self.active_turns,
            "item": self.item,
            "item_es": it_es["es"],
            "item_desc": it_es["desc"],
            "ability": self.ability,
            "ability_es": ab_es["es"],
            "ability_desc": ab_es["desc"],
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
            status_counter=int(data.get("status_counter", 1 if data.get("status") == "TOX" else 0)),
            sleep_turns=int(data.get("sleep_turns", 0)),
            volatiles=dict(data.get("volatiles") or {}),
            substitute_hp=int(data.get("substitute_hp", 0)),
            protect_counter=int(data.get("protect_counter", 0)),
            active_turns=int(data.get("active_turns", 0)),
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
    terrain: Optional[str] = None          # "Electric", "Grassy", "Psychic", "Misty", None
    terrain_turns: int = 0
    trick_room_turns: int = 0              # >0 cuando Trick Room está activo
    player_active: Optional[PokemonState] = None
    player_bench: List[PokemonState] = field(default_factory=list)
    ai_active: Optional[PokemonState] = None
    ai_bench: List[PokemonState] = field(default_factory=list)
    player_side: SideConditions = field(default_factory=SideConditions)
    ai_side: SideConditions = field(default_factory=SideConditions)
    player_mega_used: bool = False
    ai_mega_used: bool = False

    def __init__(
        self,
        turn: int = 1,
        weather: Optional[str] = None,
        weather_turns: int = 0,
        terrain: Optional[str] = None,
        terrain_turns: int = 0,
        trick_room_turns: int = 0,
        player_active: Optional[PokemonState] = None,
        player_bench: Optional[List[PokemonState]] = None,
        ai_active: Optional[PokemonState] = None,
        ai_bench: Optional[List[PokemonState]] = None,
        player_side: Optional[SideConditions] = None,
        ai_side: Optional[SideConditions] = None,
        player_mega_used: bool = False,
        ai_mega_used: bool = False,
        opponent_active: Optional[PokemonState] = None,
        opponent_bench: Optional[List[PokemonState]] = None,
        opponent_mega_used: Optional[bool] = None,
    ):
        self.turn = turn
        self.weather = weather
        self.weather_turns = weather_turns
        self.terrain = terrain
        self.terrain_turns = terrain_turns
        self.trick_room_turns = trick_room_turns
        self.player_active = player_active or opponent_active
        self.player_bench = player_bench if player_bench is not None else (opponent_bench or [])
        self.ai_active = ai_active
        self.ai_bench = ai_bench if ai_bench is not None else []
        self.player_side = player_side if player_side is not None else SideConditions()
        self.ai_side = ai_side if ai_side is not None else SideConditions()
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
            "terrain": self.terrain,
            "terrain_turns": self.terrain_turns,
            "trick_room_turns": self.trick_room_turns,
            "player_active": self.player_active.to_dict() if self.player_active else None,
            "player_bench": [p.to_dict() for p in self.player_bench],
            "ai_active": self.ai_active.to_dict() if self.ai_active else None,
            "ai_bench": [p.to_dict() for p in self.ai_bench],
            "player_side": self.player_side.to_dict(),
            "ai_side": self.ai_side.to_dict(),
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
            terrain=data.get("terrain"),
            terrain_turns=int(data.get("terrain_turns", 0)),
            trick_room_turns=int(data.get("trick_room_turns", 0)),
            player_active=player_active,
            player_bench=player_bench,
            ai_active=ai_active,
            ai_bench=ai_bench,
            player_side=SideConditions.from_dict(data.get("player_side")),
            ai_side=SideConditions.from_dict(data.get("ai_side")),
            player_mega_used=bool(data.get("player_mega_used", data.get("opponent_mega_used", False))),
            ai_mega_used=bool(data.get("ai_mega_used", False)),
        )
