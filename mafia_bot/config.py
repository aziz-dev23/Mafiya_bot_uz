import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MIN_PLAYERS = int(os.getenv("MIN_PLAYERS", "4"))
MAX_PLAYERS = int(os.getenv("MAX_PLAYERS", "15"))
NIGHT_DURATION = int(os.getenv("NIGHT_DURATION", "45"))
DAWN_DURATION = int(os.getenv("DAWN_DURATION", "20"))
DAY_DISCUSSION_DURATION = int(os.getenv("DAY_DISCUSSION_DURATION", "60"))
VOTE_DURATION = int(os.getenv("VOTE_DURATION", "30"))

DB_PATH = os.getenv("DB_PATH", "mafia.db")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(",", " ").split() if x.strip()}
# Faqat shu Telegram user_id'lar bozorda (/sell) sotuvchi sifatida e'lon joylay oladi
SELLER_IDS = {int(x) for x in os.getenv("SELLER_IDS", "").replace(",", " ").split() if x.strip()}

# Olmos sotib olish uchun to'lov kartasi — o'zingizning haqiqiy kartangizni yozing
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "")
PAYMENT_CARD_HOLDER = os.getenv("PAYMENT_CARD_HOLDER", "")
