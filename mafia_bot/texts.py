from game.models import Role

ROLE_NAMES = {
    Role.MAFIA: "🔪 Mafiya",
    Role.DON: "🤵🏻 Don",
    Role.KILLER: "🔪 Qotil",
    Role.HITMAN: "🥷 Yollanma qotil",
    Role.DOCTOR: "💊 Doktor",
    Role.DETECTIVE: "🕵️ Komissar",
    Role.POISONER: "💊 Kezuvchi",
    Role.WANDERER: "🚶 Daydi",
    Role.MINER: "⛏ Konchi",
    Role.LAWYER: "👨‍💼 Advokat",
    Role.SORCERER: "🧞‍♂️ Afsungar",
    Role.WOLF: "🐺 Bo'ri",
    Role.CIVILIAN: "👤 Tinch aholi",
}

ROLE_DESCRIPTIONS = {
    Role.MAFIA: (
        "Siz — <b>Mafiya</b> a'zosisiz. Har kecha sheriklaringiz bilan birga "
        "shahar aholisidan birini yo'q qilasiz.\nMaqsad: tinch aholi sonini "
        "mafiyaga teng yoki undan kam qilib qo'yish.\n\n"
        "🤵🏻 Donga bo'ysunasiz. Agar Don halok bo'lsa, sizlardan biri "
        "tasodifiy tarzda yangi Don bo'ladi."
    ),
    Role.DON: (
        "Siz — Mafiyaning <b>Doni</b>siz. Sheriklaringiz bilan birga har kecha "
        "birovni yo'q qilasiz. Bundan tashqari, o'yin davomida <b>bir marta</b> "
        "kimningdir Komissar ekanini aniqlashga urinishingiz mumkin."
    ),
    Role.KILLER: (
        "Siz — mustaqil <b>Qotil</b>siz. Hech kim bilan hamkorlik qilmaysiz. "
        "Har kecha o'zingiz xohlagan birovni yo'q qilasiz.\nAgar oxirigacha "
        "<b>yolg'iz qolib ketsangiz</b> — yakka o'zingiz g'alaba qilasiz!"
    ),
    Role.HITMAN: (
        "Siz — <b>Yollanma qotil</b>siz. Sizga maxfiy bitta 'buyurtma' "
        "(nishon) berilgan — profilingizni tekshiring. Har kecha istagan "
        "birovni o'ldirishingiz mumkin. Aynan buyurtma nishonini o'ldirsangiz "
        "— katta pul bonusi olasiz."
    ),
    Role.DOCTOR: (
        "Siz — <b>Doktor</b>siz. Har kecha bitta odamni (o'zingizni ham) "
        "mafiyaning hujumidan himoya qilishingiz mumkin."
    ),
    Role.DETECTIVE: (
        "Siz — <b>Komissar</b>siz. Har kecha bitta odamni tekshirib, uning "
        "mafiya ekan-emasligini bilib olasiz."
    ),
    Role.POISONER: (
        "Siz — <b>Kezuvchi</b>siz. Har kecha birovga yashirincha 'dori' "
        "berasiz. Agar u himoyalanmagan bo'lsa — keyingi tunning boshida "
        "halok bo'ladi."
    ),
    Role.WANDERER: (
        "Siz — <b>Daydi</b>siz. Har kecha kimningdir oldiga borasiz. Agar "
        "o'sha kishi aynan shu kecha o'ldirilsa — ertasi kuni bundan xabar "
        "topasiz."
    ),
    Role.MINER: (
        "Siz — <b>Konchi</b>siz. Maxsus qobiliyatingiz yo'q — tinch aholi "
        "kabi kunduzi muhokama va ovoz berish orqali mafiyani aniqlashga "
        "harakat qiling."
    ),
    Role.LAWYER: (
        "Siz — <b>Advokat</b>siz, Mafiya tomonidasiz. Har kecha bitta odamni "
        "(odatda mafiya sherigingizni) tanlaysiz — agar Komissar aynan shu "
        "kecha o'sha kishini tekshirsa, natija soxta 'mafiya emas' chiqadi."
    ),
    Role.SORCERER: (
        "Siz — <b>Afsungar</b>siz, mustaqilsiz. Agar mafiya tunda sizni "
        "o'ldirsa, o'zingiz bilan birga bitta mafiya a'zosini ham olib "
        "ketasiz. Agar kunduzi ovoz bilan haydalsangiz, o'limingizdan oldin "
        "birovdan o'ch olish huquqiga ega bo'lasiz."
    ),
    Role.WOLF: (
        "Siz — <b>Bo'ri</b>siz, hozircha hech kimga tegishli emassiz. Agar "
        "mafiya tunda sizni o'ldirmoqchi bo'lsa, halok bo'lmaysiz — o'rniga "
        "yashirincha Mafiya jamoasiga aylanasiz. Qotil sizni o'ldirsa, "
        "oddiy halok bo'lasiz."
    ),
    Role.CIVILIAN: (
        "Siz — <b>Tinch aholi</b>siz. Maxsus qobiliyatingiz yo'q. Kunduzi "
        "muhokama va ovoz berish orqali mafiyani aniqlashga harakat qiling."
    ),
}


HELP_TEXT = (
    "<b>Mafiya o'yini boti — buyruqlar</b>\n\n"
    "<b>O'yin:</b>\n"
    "/mafia — guruhda yangi o'yin uchun ro'yxat ochish\n"
    "/stop — joriy o'yinni to'xtatish (faqat boshlovchi)\n\n"
    "<b>Profil va iqtisodiyot:</b>\n"
    "/profile — balansingiz, statistikangiz va ballaringiz (Dollar 💵, Olmos 💎, Coin 🪙)\n"
    "/shop — olmos sotib olish (karta orqali, admin tasdig'idan so'ng)\n"
    "/almashtir <miqdor> — olmosni Dollarga almashtirish\n"
    "/market — bozordagi faol e'lonlarni ko'rish va sotib olish\n"
    "/dokon — buyumlar do'koni (Himoya, Soxta hujjat, Ovozdan himoya, Miltiq, Sehrli oyna)\n"
    "/sumka — buyumlaringiz, o'yin oldidan yoqish/o'chirish\n"
    "/send — boshqa foydalanuvchiga Dollar yuborish\n"
    "/sendgem — boshqa foydalanuvchiga Olmos yuborish\n\n"
    "/help — shu yordam xabari\n\n"
    "O'yin qoidalari: tunda mafiya bittasini yo'q qiladi, doktor birini "
    "himoya qiladi, komissar birini tekshiradi. Kunduzi hamma birgalikda "
    "muhokama qilib, ovoz berish orqali kimnidir shahardan haydaydi. "
    "Mafiya soni tinch aholiga teng yoki ko'p bo'lsa — mafiya g'alaba "
    "qiladi; barcha mafiya tutilsa — tinch aholi g'alaba qiladi.\n\n"
    "G'olib bo'lgan o'yinchilar Dollar 💵 va ball yutib olishadi — ballaringiz "
    "kunlik/haftalik/oylik reytingga qo'shiladi."
)
