import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Ro'yxat xabaridagi o'yin nomi (hech bir tilga o'girilmaydi).
BRAND_NAME = os.getenv("BRAND_NAME", "Mafiya Gamer's")
MIN_PLAYERS = int(os.getenv("MIN_PLAYERS", "4"))
MAX_PLAYERS = int(os.getenv("MAX_PLAYERS", "40"))
NIGHT_DURATION = int(os.getenv("NIGHT_DURATION", "45"))
REVENGE_DURATION = int(os.getenv("REVENGE_DURATION", "20"))
DAY_DISCUSSION_DURATION = int(os.getenv("DAY_DISCUSSION_DURATION", "30"))
VOTE_DURATION = int(os.getenv("VOTE_DURATION", "30"))
CONFIRM_VOTE_DURATION = int(os.getenv("CONFIRM_VOTE_DURATION", "30"))
LOBBY_AUTOSTART_DELAY = int(os.getenv("LOBBY_AUTOSTART_DELAY", "15"))
# Dinamik vaqt: muhokama = DAY_DISCUSSION_DURATION + PER_PLAYER × tiriklar (ko'pi bilan MAX), ovoz ham shunday.
DAY_DISCUSSION_PER_PLAYER = int(os.getenv("DAY_DISCUSSION_PER_PLAYER", "2"))
DAY_DISCUSSION_MAX = int(os.getenv("DAY_DISCUSSION_MAX", "150"))
VOTE_PER_PLAYER = int(os.getenv("VOTE_PER_PLAYER", "1"))
VOTE_MAX = int(os.getenv("VOTE_MAX", "90"))
# O'lgan o'yinchi so'nggi so'zini yozishi uchun vaqt (soniya) va uzunlik chegarasi.
LAST_WORD_DURATION = int(os.getenv("LAST_WORD_DURATION", "30"))
LAST_WORD_MAX_LENGTH = int(os.getenv("LAST_WORD_MAX_LENGTH", "200"))
# Tun va ovoz berish tugashiga shuncha soniya qolganda hali tanlamaganlarga eslatma yuboriladi.
REMINDER_BEFORE_END = int(os.getenv("REMINDER_BEFORE_END", "10"))
# Ketma-ket shuncha marta ovoz bermagan / tunda harakat qilmagan o'yinchi o'yindan chiqariladi.
AFK_LIMIT = int(os.getenv("AFK_LIMIT", "2"))
# Shuncha o'yindan kam o'ynaganlarga qo'shimcha maslahatlar ko'rsatiladi.
NEWBIE_GAMES = int(os.getenv("NEWBIE_GAMES", "5"))
# Sudya haydashni bekor qilish uchun beriladigan vaqt (soniya).
JUDGE_DURATION = int(os.getenv("JUDGE_DURATION", "10"))
# Ro'yxat xabari ko'pi bilan shuncha soniyada bir marta tahrirlanadi.
LOBBY_EDIT_INTERVAL = float(os.getenv("LOBBY_EDIT_INTERVAL", "3"))
# Guruhga ketma-ket chiqadigan qisqa e'lonlar shu soniya ichida yig'ilib, bitta xabar bo'lib chiqadi.
ANNOUNCE_BATCH_DELAY = float(os.getenv("ANNOUNCE_BATCH_DELAY", "3"))

# Telegram limitlari (navbat): bitta chatga soniyasiga 1 ta, guruhga daqiqasiga 20 ta, jami soniyasiga 25 ta.
RATE_PER_CHAT_INTERVAL = float(os.getenv("RATE_PER_CHAT_INTERVAL", "1"))
RATE_GROUP_PER_MINUTE = int(os.getenv("RATE_GROUP_PER_MINUTE", "20"))
RATE_GLOBAL_PER_SECOND = int(os.getenv("RATE_GLOBAL_PER_SECOND", "25"))
RATE_RETRY_ATTEMPTS = int(os.getenv("RATE_RETRY_ATTEMPTS", "5"))

DB_PATH = os.getenv("DB_PATH", "mafia.db")
# Reyting davrlari (kun/hafta/oy) shu vaqt mintaqasi bo'yicha hisoblanadi (Toshkent = UTC+5)
TIMEZONE_OFFSET_HOURS = int(os.getenv("TIMEZONE_OFFSET_HOURS", "5"))
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(",", " ").split() if x.strip()}
# Bot egasi(lari): /hisobot (kirim-chiqim) faqat shularga ko'rinadi; boshqa adminlar balans bergan,
# to'lovni qaytargan yoki karta buyurtmasini ko'rib chiqqanda egaga darhol xabar boradi.
OWNER_IDS = {int(x) for x in os.getenv("OWNER_IDS", "").replace(",", " ").split() if x.strip()}
# Faqat shu Telegram user_id'lar bozorda (/sell) sotuvchi sifatida e'lon joylay oladi
SELLER_IDS = {int(x) for x in os.getenv("SELLER_IDS", "").replace(",", " ").split() if x.strip()}

# Olmos sotib olish uchun to'lov kartasi — o'zingizning haqiqiy kartangizni yozing
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "")
PAYMENT_CARD_HOLDER = os.getenv("PAYMENT_CARD_HOLDER", "")
# To'lov chekini (skrinshot) qabul qiladigan Telegram username (@ belgisisiz ham bo'ladi)
PAYMENT_CONTACT_USERNAME = os.getenv("PAYMENT_CONTACT_USERNAME", "theaziz_art23").strip().lstrip("@")
# Karta orqali (qo'lda tasdiqlanadigan) to'lovni yoqish/o'chirish. Telegram Stars har doim ishlaydi.
CARD_PAYMENTS_ENABLED = os.getenv("CARD_PAYMENTS_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")
# /support va /paysupport da ko'rsatiladigan yordam kontakti (@ belgisisiz).
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", PAYMENT_CONTACT_USERNAME).strip().lstrip("@")
