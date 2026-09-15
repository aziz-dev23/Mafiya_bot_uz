import asyncio
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    MAFIA = "mafia"
    DOCTOR = "doctor"
    DETECTIVE = "detective"
    CIVILIAN = "civilian"


class GameState(str, Enum):
    LOBBY = "lobby"
    NIGHT = "night"
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
    clan_tag: str | None = None


@dataclass
class Game:
    chat_id: int
    host_id: int
    players: dict[int, Player] = field(default_factory=dict)
    state: GameState = GameState.LOBBY
    day_number: int = 0
    lobby_message_id: int | None = None
    task: "asyncio.Task | None" = None

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

    # day phase state
    day_votes: dict[int, int | None] = field(default_factory=dict)
    vote_needed: int = 0
    vote_event: "asyncio.Event | None" = None
    vote_message_id: int | None = None
