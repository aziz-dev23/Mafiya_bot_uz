import asyncio
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    MAFIA = "mafia"
    DON = "don"
    KILLER = "killer"
    HITMAN = "hitman"
    DOCTOR = "doctor"
    DETECTIVE = "detective"
    POISONER = "poisoner"
    WANDERER = "wanderer"
    MINER = "miner"
    LAWYER = "lawyer"
    SORCERER = "sorcerer"
    WOLF = "wolf"
    CIVILIAN = "civilian"


class GameState(str, Enum):
    LOBBY = "lobby"
    NIGHT = "night"
    DAWN = "dawn"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTING = "day_voting"
    FINISHED = "finished"


@dataclass
class Player:
    user_id: int
    full_name: str
    username: str | None = None
    role: Role | None = None
    alive: bool = True
    items: dict[str, int] = field(default_factory=dict)
    contract_target: int | None = None


@dataclass
class Game:
    chat_id: int
    host_id: int
    players: dict[int, Player] = field(default_factory=dict)
    state: GameState = GameState.LOBBY
    day_number: int = 0
    lobby_message_id: int | None = None
    task: "asyncio.Task | None" = None
    autostart_scheduled: bool = False
    starting: bool = False

    # night phase state
    mafia_votes: dict[int, int] = field(default_factory=dict)
    doctor_target: int | None = None
    doctor_acted: bool = False
    detective_target: int | None = None
    detective_acted: bool = False
    night_mafia_needed: int = 0
    night_doctor_needed: bool = False
    night_detective_needed: bool = False
    night_event: "asyncio.Event | None" = None
    mafia_rifle_users: set[int] = field(default_factory=set)
    detective_correct: bool = False

    # Bosqich 2: yangi mustaqil/maxsus rollar
    don_check_used: bool = False
    night_killer_needed: bool = False
    killer_acted: bool = False
    killer_target: int | None = None
    night_hitman_needed: bool = False
    hitman_acted: bool = False
    hitman_target: int | None = None
    night_poisoner_needed: bool = False
    poisoner_acted: bool = False
    night_wanderer_needed: bool = False
    wanderer_acted: bool = False
    wanderer_target: int | None = None
    pending_poison: dict[int, int] = field(default_factory=dict)

    # Bosqich 4: Advokat / Afsungar / Bo'ri
    night_advokat_needed: bool = False
    advokat_acted: bool = False
    advokat_target: int | None = None
    revenge_event: "asyncio.Event | None" = None
    revenge_target: int | None = None

    # dawn phase state (Geroy buyumi)
    dawn_event: "asyncio.Event | None" = None
    dawn_needed: int = 0
    dawn_acted: set[int] = field(default_factory=set)
    dawn_shots: dict[int, int] = field(default_factory=dict)

    # day phase state
    day_votes: dict[int, int | None] = field(default_factory=dict)
    vote_needed: int = 0
    vote_event: "asyncio.Event | None" = None
