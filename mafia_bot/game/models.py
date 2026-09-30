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
    SERGEANT = "sergeant"
    JOURNALIST = "journalist"
    BODYGUARD = "bodyguard"
    SPY = "spy"
    JUDGE = "judge"
    CUPID = "cupid"
    CIVILIAN = "civilian"


MAFIA_TEAM_ROLES = (Role.MAFIA, Role.DON, Role.LAWYER, Role.HITMAN, Role.SPY)
# Mafiya o'ldirish ovozida qatnashadiganlar.
MAFIA_KILL_ROLES = (Role.MAFIA, Role.DON)


class GameState(str, Enum):
    LOBBY = "lobby"
    NIGHT = "night"
    DAWN = "dawn"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTING = "day_voting"
    DAY_CONFIRM = "day_confirm"
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
    shield_used: bool = False
    hero_level: int = 0
    # O'yin boshidagi rol (statistika uchun; Bo'ri/Serjant keyin rolini o'zgartirishi mumkin).
    initial_role: Role | None = None
    # AFK hisoblagichlari: ketma-ket ovoz bermaganlar / tunda harakat qilmaganlar soni.
    missed_votes: int = 0
    missed_nights: int = 0
    afk: bool = False
    # Shaxsiy xabarlar tili (i18n.LANGS).
    lang: str = "uz"
    # O'yinda tugatgan o'yinlari soni (yangi o'yinchilarga maslahat berish uchun).
    games_played: int = 0


def _default_settings():
    from .settings import GroupSettings

    return GroupSettings()


@dataclass
class Game:
    chat_id: int
    host_id: int
    players: dict[int, Player] = field(default_factory=dict)
    state: GameState = GameState.LOBBY
    day_number: int = 0
    lobby_message_id: int | None = None
    task: "asyncio.Task | None" = None
    starting: bool = False
    started_at: float = 0.0
    settings: "GroupSettings" = field(default_factory=_default_settings)  # noqa: F821
    # O'yin tarixi (o'yin oxirida guruhga chiqadi).
    history: list[str] = field(default_factory=list)
    # So'nggi so'z: o'lgan o'yinchi -> qachongacha (time.monotonic) yozishi mumkin.
    last_word_deadline: dict[int, float] = field(default_factory=dict)

    # Tun holati. night_expected — shu tun harakat qilishi kutilayotganlar, night_acted — harakat qilganlar;
    # hamma harakat qilsa, tun vaqt tugashini kutmasdan yakunlanadi.
    night_event: "asyncio.Event | None" = None
    night_expected: set[int] = field(default_factory=set)
    night_acted: set[int] = field(default_factory=set)
    mafia_votes: dict[int, int] = field(default_factory=dict)
    mafia_rifle_users: set[int] = field(default_factory=set)
    # Mafiya jamoasining har bir a'zosiga yuborilgan, ovozlar bilan tahrirlanib boriladigan xabar.
    mafia_status_msgs: dict[int, int] = field(default_factory=dict)
    doctor_targets: dict[int, int] = field(default_factory=dict)
    detective_target: int | None = None
    detective_correct: bool = False
    don_check_used: bool = False
    killer_target: int | None = None
    hitman_target: int | None = None
    wanderer_target: int | None = None
    advokat_target: int | None = None
    bodyguard_targets: dict[int, int] = field(default_factory=dict)
    journalist_first: dict[int, int] = field(default_factory=dict)
    cupid_pick: list[int] = field(default_factory=list)
    # "Bu tun kim o'ladi?" taxminlari: taxmin qilgan -> nishon.
    guesses: dict[int, int] = field(default_factory=dict)
    pending_poison: dict[int, int] = field(default_factory=dict)
    # Shu tunda halok bo'lganlar: qurbon user_id -> uni o'ldirgan o'yinchi user_id (noma'lum bo'lsa None).
    night_kills: dict[int, int | None] = field(default_factory=dict)
    # Tun natijalari — hammasi bitta xabar bo'lib guruhga chiqadi.
    night_results: list[str] = field(default_factory=list)

    # Butun o'yin davomidagi cheklovlar
    poison_uses: int = 0
    doctor_self_used: set[int] = field(default_factory=set)
    doctor_last_target: dict[int, int] = field(default_factory=dict)
    hero_shot_used: set[int] = field(default_factory=set)
    judge_used: bool = False
    lovers: tuple[int, int] | None = None
    # MVP ochkolari (10+ kishilik o'yinda top-3 g'olibga qo'shimcha ball berish uchun).
    mvp: dict[int, int] = field(default_factory=dict)

    # Afsungar o'chi / Sudya qarori
    revenge_event: "asyncio.Event | None" = None
    revenge_target: int | None = None
    judge_event: "asyncio.Event | None" = None

    # Guruhga yig'ib yuboriladigan qisqa e'lonlar
    announce_buffer: list[str] = field(default_factory=list)
    announce_task: "asyncio.Task | None" = None
    # Guruh ruxsatlari yopilganmi (setChatPermissions orqali)
    chat_locked: bool = False
    # Ro'yxat xabarini tahrirlashni cheklash uchun
    lobby_last_edit: float = 0.0
    lobby_edit_task: "asyncio.Task | None" = None

    # dawn phase state (Geroy buyumi)
    dawn_event: "asyncio.Event | None" = None
    dawn_needed: int = 0
    dawn_acted: set[int] = field(default_factory=set)
    dawn_shots: dict[int, int] = field(default_factory=dict)

    # day phase state
    day_votes: dict[int, int | None] = field(default_factory=dict)
    vote_needed: int = 0
    vote_event: "asyncio.Event | None" = None

    # guruhdagi 👍/👎 tasdiqlash ovozi (eng ko'p ovoz olgan nomzod uchun)
    confirm_candidate: int | None = None
    confirm_votes: dict[int, bool] = field(default_factory=dict)
    confirm_needed: int = 0
    confirm_event: "asyncio.Event | None" = None

    # har bir o'yinchiga yuborilgan oxirgi shaxsiy so'rov xabari (yangisi yuborilishidan
    # oldin shu xabar o'chiriladi — shaxsiy chatda eski tugmalar to'planib qolmasligi uchun)
    last_action_msg: dict[int, int] = field(default_factory=dict)
