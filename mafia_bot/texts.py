from game.models import Role

ROLE_NAMES = {
    Role.MAFIA: "🔪 Mafiya",
    Role.DON: "🤵🏻 Don",
    Role.KILLER: "🔪 Qotil",
    Role.HITMAN: "🥷 Yollanma qotil",
    Role.DOCTOR: "💉 Doktor",
    Role.DETECTIVE: "🕵️ Komissar",
    Role.POISONER: "💊 Kezuvchi",
    Role.WANDERER: "🚶 Daydi",
    Role.MINER: "⛏ Konchi",
    Role.LAWYER: "👨‍💼 Advokat",
    Role.SORCERER: "🧞‍♂️ Afsungar",
    Role.WOLF: "🐺 Bo'ri",
    Role.SERGEANT: "👮 Serjant",
    Role.JOURNALIST: "📰 Jurnalist",
    Role.BODYGUARD: "🛡 Tansoqchi",
    Role.SPY: "🕶 Josus",
    Role.JUDGE: "👨‍⚖️ Sudya",
    Role.CUPID: "💘 Kupidon",
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
        "Siz — <b>Yollanma qotil</b>siz, Mafiya jamoasining a'zosisiz. "
        "Sheriklaringizni bilasiz, ular ham sizni biladi. Har kecha Mafiya "
        "ovozidan alohida o'zingiz bitta odamni o'ldirasiz. Sizga maxfiy "
        "'buyurtma' (nishon) berilgan — aynan uni o'ldirsangiz katta pul "
        "bonusi olasiz."
    ),
    Role.DOCTOR: (
        "Siz — <b>Doktor</b>siz. Har kecha bitta odamni mafiya hujumidan va "
        "Kezuvchi dorisidan himoya qilasiz. O'zingizni o'yinda faqat bir marta "
        "himoya qila olasiz, bir odamni esa ketma-ket ikki kecha himoya qilib bo'lmaydi."
    ),
    Role.DETECTIVE: (
        "Siz — <b>Komissar</b>siz. Har kecha bitta odamni tekshirib, uning "
        "mafiya ekan-emasligini bilib olasiz."
    ),
    Role.POISONER: (
        "Siz — <b>Kezuvchi</b>siz. O'yinda ko'pi bilan 2 marta birovga "
        "yashirincha 'dori' berasiz. U keyingi kecha halok bo'ladi — agar "
        "o'sha kecha Doktor uni himoya qilmasa."
    ),
    Role.WANDERER: (
        "Siz — <b>Daydi</b>siz. Har kecha kimningdir oldiga borasiz. Agar "
        "o'sha kishi aynan shu kecha o'ldirilsa — ertalab uni kim "
        "o'ldirganini bilib olasiz (agar qotilda 🎭 Maska bo'lmasa)."
    ),
    Role.MINER: (
        "Siz — <b>Konchi</b>siz. Har kecha avtomatik ravishda qazilma "
        "qilasiz: 🪙 Coin yoki foydali buyum topishingiz mumkin — topilgan "
        "narsa darhol hisobingizga tushadi. Kunduzi tinch aholi kabi "
        "mafiyani aniqlashga harakat qiling."
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
    Role.SERGEANT: (
        "Siz — <b>Serjant</b>siz, Tinch aholi tomonidasiz. Komissar kimligini bilasiz va "
        "uning har bir tekshiruv natijasini ko'rib borasiz. Komissar halok bo'lsa — "
        "uning o'rniga siz Komissar bo'lasiz."
    ),
    Role.JOURNALIST: (
        "Siz — <b>Jurnalist</b>siz, Tinch aholi tomonidasiz. Har kecha ikki kishini tanlab, "
        "ular bir jamoadami yoki yo'qligini bilib olasiz. Advokat va Soxta hujjat sizni aldamaydi."
    ),
    Role.BODYGUARD: (
        "Siz — <b>Tansoqchi</b>siz, Tinch aholi tomonidasiz. Har kecha bir kishini qo'riqlaysiz. "
        "Unga Mafiya, Qotil yoki Yollanma qotil hujum qilsa — uning o'rniga siz halok bo'lasiz."
    ),
    Role.SPY: (
        "Siz — <b>Josus</b>siz, Mafiya jamoasining a'zosisiz. Har kecha bitta o'yinchining "
        "rolini bilib olasiz. Sheriklaringizni bilasiz va mafiya chatida qatnashasiz, lekin "
        "o'ldirish ovozida qatnashmaysiz."
    ),
    Role.JUDGE: (
        "Siz — <b>Sudya</b>siz, Tinch aholi tomonidasiz. O'yinda bir marta kunduzgi haydash "
        "natijasini bekor qila olasiz — haydash tasdiqlangach, shaxsiy chatingizga tugma keladi."
    ),
    Role.CUPID: (
        "Siz — <b>Kupidon</b>siz, Tinch aholi tomonidasiz. Birinchi kecha ikki kishini oshiq "
        "qilasiz — ular bir-birini bilib oladi. Oshiqlardan biri halok bo'lsa, ikkinchisi ham "
        "halok bo'ladi. Tanlamasangiz, juftlik tasodifiy tanlanadi."
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
    "/stop — joriy o'yinni to'xtatish (faqat guruh adminlari)\n\n"
    "<b>Profil va iqtisodiyot:</b>\n"
    "/profile — balansingiz, statistikangiz va ballaringiz (Dollar 💵, Olmos 💎, Coin 🪙)\n"
    "/shop — olmos sotib olish (Telegram Stars ⭐)\n"
    "/almashtir — olmos 💎 yoki coin 🪙 ni Dollarga almashtirish\n"
    "/market — bozordagi faol e'lonlarni ko'rish va sotib olish\n"
    "/dokon — buyumlar do'koni (Himoya, Soxta hujjat, Ovozdan himoya, Miltiq, Sehrli oyna)\n"
    "/sumka — buyumlaringiz, o'yin oldidan yoqish/o'chirish\n"
    "/buyumlar — barcha buyumlar nima qilishi\n"
    "/mavsum — mavsum chiptasi: daraja, XP va mukofotlar\n"
    "/bonus — kunlik bonus, /vip — VIP obuna\n"
    "/taklif — do'st taklif qilish havolasi\n"
    "/premium — guruh premiumi, /turnir — turnir (guruhda)\n"
    "/send — boshqa foydalanuvchiga Dollar yuborish\n"
    "/sendgem — boshqa foydalanuvchiga Olmos yuborish\n"
    "/geroy — Geroyni sotib olish / darajasini oshirish\n"
    "/qoidalar — o'yin qoidalari va qisqa qo'llanma\n"
    "/rollar — barcha rollar tavsifi\n"
    "/sozlamalar — guruh sozlamalari (faqat guruh adminlari)\n"
    "/til — tilni tanlash\n\n"
    "<b>Reyting:</b>\n"
    "/top — umumiy reyting\n"
    "/top1 — kunlik, /top7 — haftalik, /top30 — oylik reyting\n\n"
    "/help — shu yordam xabari\n"
    "/support — yordam, /paysupport — to'lovlar bo'yicha yordam, /terms — foydalanish shartlari\n\n"
    "O'yin qoidalari: tunda mafiya bittasini yo'q qiladi, doktor birini "
    "himoya qiladi, komissar birini tekshiradi. Kunduzi hamma birgalikda "
    "muhokama qilib, ovoz berish orqali kimnidir shahardan haydaydi. "
    "Mafiya soni tinch aholiga teng yoki ko'p bo'lsa — mafiya g'alaba "
    "qiladi; barcha mafiya va Qotil yo'q qilinsa — tinch aholi g'alaba qiladi.\n\n"
    "G'olib jamoa a'zolari (halok bo'lganlari ham) Dollar 💵 va ball yutib olishadi — ballaringiz "
    "kunlik/haftalik/oylik reytingga qo'shiladi (/top1, /top7, /top30).\n\n"
    "ℹ️ Bot guruhda admin bo'lishi kerak: xabarlarni o'chirish, foydalanuvchilarni cheklash va "
    "xabarlarni qadash huquqlari bilan.\n\n"
    "⚠️ O'yin davomida guruhda faqat kunduzi yozish mumkin — tunda guruh yopiladi, halok bo'lganlarning xabarlari o'chiriladi."
)


# Buyumlar tavsifi — /dokon da buyumni tanlaganda ko'rsatiladi.
ITEM_DESCRIPTIONS = {
    "shield": "Mafiya hujumidan bir marta saqlaydi (bir o'yinda 1 marta). Mafiya 🔫 Miltiq ishlatsa, ishlamaydi.",
    "fake_doc": "Komissar sizni tekshirsa — natija \"mafiya emas\" chiqadi.",
    "vote_shield": "Kunduzi ovoz bilan haydalish tasdiqlansa ham omon qolasiz.",
    "rifle": "Mafiya/Don uchun: tunda yoqilsa, nishonning 🛡 Himoyasini teshib o'tadi.",
    "mirror": "Hujumni qaytaradi: Mafiya hujumida sizga ovoz bergan Don/Mafiyalardan biri, "
    "Geroy zarbasida (10+ darajadan tashqari) otgan Geroyning o'zi halok bo'ladi.",
    "killer_shield": "Qotil yoki Yollanma qotil hujumidan bir marta himoya qiladi.",
    "poison_shield": "Kezuvchi bergan dorini zararsizlantiradi.",
    "mask": "Siz kimnidir o'ldirganingizda, qurbonning oldiga borgan Daydi qotil kimligini bila olmaydi.",
    "hero_immunity": "Geroy zarbasidan bir marta saqlaydi (10+ darajali Geroydan tashqari).",
}

# Tun / tong
MAFIA_KILL_PROMPT = "🔪 Kimni yo'q qilmoqchisiz?\nSheriklaringiz: {teammates}"
HITMAN_KILL_PROMPT = "🥷 Kimni yo'q qilmoqchisiz?\nSheriklaringiz: {teammates}"
NO_TEAMMATES = "yo'q"
NOT_FOR_TEAMMATE = "O'z sherigingizni tanlay olmaysiz."
WANDERER_SAW_KILLER = "🚶 Siz tashrif buyurgan {victim} shu kecha halok bo'ldi. Uni <b>{killer}</b> o'ldirdi!"
MINER_FOUND_COINS = "⛏ Tungi qazilmadan {amount}🪙 Coin topdingiz! Hisobingizga qo'shildi."
MINER_FOUND_ITEM = "⛏ Tungi qazilmadan {emoji} {name} topdingiz! Sumkangizga qo'shildi."
MINER_FOUND_NOTHING = "⛏ Bu kecha qazilmadan hech narsa chiqmadi."

# O'yin natijasi (shaxsiy xabar)
PAYOUT_WON = "🏆 Siz g'alaba qozondingiz!"
PAYOUT_LOST = "💀 Siz mag'lub bo'ldingiz."
PAYOUT_KILLER_SOLO = "🔪 Siz yakka o'zingiz g'alaba qozondingiz!"
PAYOUT_NOTE_ALIVE = "🟢 tirik qolganingiz uchun +{amount}💵"
PAYOUT_NOTE_DETECTIVE = "🕵️ komissar bonusi +{amount}💵"
PAYOUT_NOTE_MVP = "⭐ MVP bonusi"

# /almashtir
EXCHANGE_TEXT = (
    "💱 <b>ALMASHTIRISH</b>\n"
    "Kurs: 1💎 = {diamond_rate}💵, 1🪙 = {coin_rate}💵\n\n"
    "Kerakli miqdorni tanlang:"
)
EXCHANGE_DONE = "💱 <b>ALMASHTIRISH</b>\n\n✅ {amount}{emoji} → {dollars}💵 hisobingizga qo'shildi."
EXCHANGE_DONE_SHORT = "✅ {amount}{emoji} → {dollars}💵 almashtirildi."
EXCHANGE_BAD_AMOUNT = "Noto'g'ri miqdor."
EXCHANGE_NOT_ENOUGH_DIAMONDS = "Olmosingiz yetarli emas."
EXCHANGE_NOT_ENOUGH_COINS = "Coinlaringiz yetarli emas."
MENU_EXCHANGE_BUTTON = "💱 Almashtirish (💎/🪙 → 💵)"
KILLER_WIN_RESULT = "🔪 <b>Qotil yakka o'zi g'alaba qozondi!</b> Shaharda unga qarshi turadigan hech kim qolmadi."

DOCTOR_TARGET_FORBIDDEN = "Bu odamni hozir himoya qila olmaysiz (o'zingizni faqat bir marta, bir odamni ketma-ket ikki kecha emas)."
POISONER_NO_USES_LEFT = "Siz dori berish imkoniyatlaringizni ishlatib bo'ldingiz."
HERO_SHOT_ALREADY_USED = "Geroy zarbasini bu o'yinda allaqachon ishlatgansiz."
ITEM_STORE_RULE = "ℹ️ Har bir buyum turidan bir o'yinda ko'pi bilan 1 dona ishlaydi."

# Haftalik mukofot
WEEKLY_REWARD_MESSAGE = (
    "🏆 <b>Haftalik reyting mukofoti!</b>\n\n"
    "O'tgan hafta /top7 reytingida <b>{place}-o'rin</b>ni egalladingiz ({points} ball).\n"
    "💎 +{diamonds} olmos hisobingizga qo'shildi!"
)

# Pul/olmos yuborish cheklovlari
TRANSFER_MIN_GAMES_REQUIRED = (
    "💸 Pul/olmos yuborish uchun kamida {required} ta o'yin o'ynagan bo'lishingiz kerak "
    "(sizda: {played})."
)
TRANSFER_DAILY_LIMIT_EXCEEDED = (
    "Kunlik limit: {limit}{emoji}. Bugun yuborilgan: {sent}{emoji}, yana {left}{emoji} yuborishingiz mumkin."
)

# Tungi so'rovlar va natijalar (3-bosqich)
DOCTOR_PROMPT = "💉 Kimni himoya qilmoqchisiz?"
SPY_PROMPT = "🕶 Kimning rolini bilmoqchisiz?"
SPY_RESULT = "🕶 Josuslik natijasi: {name} — {role}."
JOURNALIST_PROMPT_FIRST = "📰 Birinchi odamni tanlang:"
JOURNALIST_PROMPT_SECOND = "📰 Birinchi: {first}. Endi ikkinchi odamni tanlang:"
JOURNALIST_SAME = "📰 {first} va {second} — <b>bir jamoada</b>."
JOURNALIST_DIFFERENT = "📰 {first} va {second} — <b>turli jamoalarda</b>."
BODYGUARD_PROMPT = "🛡 Kimni qo'riqlamoqchisiz?"
BODYGUARD_CHOSEN = "🛡 Siz qo'riqlayapsiz: {name}"
BODYGUARD_DIED = "🛡 <b>{guard}</b> {target}ni himoya qilib, uning o'rniga halok bo'ldi."
CUPID_PROMPT_FIRST = "💘 Birinchi oshiqni tanlang:"
CUPID_PROMPT_SECOND = "💘 Birinchi oshiq: {first}. Endi ikkinchisini tanlang:"
CUPID_CHOSEN = "💘 Oshiqlar: {first} va {second}."
CUPID_RANDOM = "💘 Siz tanlamadingiz — oshiqlar tasodifiy tanlandi: {first} va {second}."
LOVER_NOTICE = "💘 Kupidon sizni <b>{partner}</b> bilan oshiq qildi! Biringiz halok bo'lsangiz, ikkinchingiz ham halok bo'ladi."
LOVER_DIED = "💔 <b>{name}</b> sevgilisining o'limiga chiday olmay halok bo'ldi.{role}"
SERGEANT_KNOWS = "👮 Komissar: <b>{name}</b>"
SERGEANT_SEES_CHECK = "👮 Komissar tekshirdi: {name} — {result}"
SERGEANT_PROMOTED = "👮 Komissar halok bo'ldi! Endi siz — <b>Komissar</b>siz. Har kecha bitta odamni tekshirasiz."
JUDGE_PROMPT = "👨‍⚖️ Shahar <b>{name}</b>ni haydashga qaror qildi. Bekor qilasizmi? ({seconds} soniya)"
JUDGE_BUTTON = "⚖️ Haydashni bekor qilish"
JUDGE_DONE = "👨‍⚖️ Qaror qabul qilindi."
JUDGE_TOO_LATE = "Bu imkoniyat endi mavjud emas."
JUDGE_CANCELLED = "👨‍⚖️ <b>Sudya</b> aralashdi: {name}ni haydash bekor qilindi!"
GUESS_PROMPT = "🔮 Bu tun kim halok bo'ladi deb o'ylaysiz? To'g'ri topsangiz — +{coins}🪙"
GUESS_CHOSEN = "🔮 Taxminingiz: {name}"
GUESS_WON = "🔮 Taxminingiz to'g'ri chiqdi! +{coins}🪙 Coin hisobingizga qo'shildi."
MAFIA_CHAT_LINE = "🔪 {name}: {text}"
MAFIA_VOTES_HEADER = "🗳 <b>Mafiya ovozlari:</b>"
MAFIA_VOTE_LINE = "{voter} → {target}"
MAFIA_VOTE_PENDING = "…"
MAFIA_CHAT_HINT = "💬 Tunda shu yerga yozgan xabaringiz sheriklaringizga yetkaziladi."
NIGHT_QUIET = "🌤 Tun tinch o'tdi. Bu safar hech kim halok bo'lmadi."
CHAT_LOCK_NO_RIGHTS = (
    "⚠️ Adminlar diqqatiga: botda <b>foydalanuvchilarni cheklash</b> huquqi yo'q, shuning uchun "
    "tunda guruh yopilmaydi — xabarlar birma-bir o'chiriladi. Botga shu huquqni bering."
)
ADD_TO_GROUP_RIGHTS = (
    "ℹ️ Botni guruhga <b>admin</b> qilib qo'shing va quyidagi huquqlarni bering: "
    "xabarlarni o'chirish, foydalanuvchilarni cheklash, xabarlarni qadash."
)

# ---------- 4-bosqich ----------

# Rol xabaridagi qisqa "nima qilish kerak" maslahati.
ROLE_TIPS = {
    Role.MAFIA: "Tunda Don bilan bitta nishonga ovoz bering, kunduzi o'zingizni tinch aholidek tuting.",
    Role.DON: "Mafiya ovozi teng bo'lsa, sizning tanlovingiz hal qiladi. Komissarni topishga urinib ko'ring.",
    Role.KILLER: "Har kecha bittadan yo'q qiling va kunduzi shubha uyg'otmang — oxirida yolg'iz qolishingiz kerak.",
    Role.HITMAN: "Buyurtma nishonini o'ldirishga harakat qiling — bu katta bonus beradi.",
    Role.DOCTOR: "Kunduzi kim xavf ostida ekanini kuzating va o'shani himoya qiling.",
    Role.DETECTIVE: "Har kecha shubhali odamni tekshiring. Natijani kunduzi ehtiyotkorlik bilan ayting.",
    Role.POISONER: "Dorini ikki marta berishingiz mumkin — eng shubhali odamlarga saqlang.",
    Role.WANDERER: "Xavf ostidagi odamning oldiga boring — u o'ldirilsa, qotilni bilib olasiz.",
    Role.MINER: "Qazilma o'zi bo'ladi. Kunduzi muhokamada faol bo'ling.",
    Role.LAWYER: "Komissar tekshirishi mumkin bo'lgan sherigingizni himoya qiling.",
    Role.SORCERER: "Mafiya sizni o'ldirsa, bittasini olib ketasiz — o'zingizni ko'rsatishdan qo'rqmang.",
    Role.WOLF: "Mafiya sizga hujum qilsa, ularga qo'shilasiz. Hozircha tinch aholi kabi o'ynang.",
    Role.SERGEANT: "Komissarning natijalarini kuzating va u o'lsa, uning ishini davom ettiring.",
    Role.JOURNALIST: "Bir odamga ishonsangiz, uni shubhali odam bilan solishtiring.",
    Role.BODYGUARD: "Muhim o'yinchini (Komissar, Doktor) qo'riqlang — siz uning o'rniga o'lasiz.",
    Role.SPY: "Komissar va Doktorni topib, sheriklaringizga mafiya chatida ayting.",
    Role.JUDGE: "Imkoniyatingiz bitta — begunoh odam haydalayotgan paytga saqlang.",
    Role.CUPID: "Oshiqlarni o'ylab tanlang: biri o'lsa, ikkinchisi ham o'ladi.",
    Role.CIVILIAN: "Kim kimga ovoz berayotganini kuzating — mafiya ko'pincha bir-birini himoya qiladi.",
}
ROLE_TIP_PREFIX = "💡 <b>Maslahat:</b> "
NEWBIE_TIPS = (
    "🆕 <b>Yangi o'yinchilarga:</b>\n"
    "• Tunda botdan kelgan tugmalar orqali harakat qiling — vaqt cheklangan.\n"
    "• Kunduzi guruhda muhokama qiling, keyin shaxsiy chatda ovoz bering.\n"
    "• Ketma-ket 2 marta ovoz bermasangiz yoki tunda harakat qilmasangiz, o'yindan chiqarilasiz.\n"
    "• Barcha rollar tavsifi: /rollar"
)
ROLES_LIST_HEADER = "🎭 <b>Barcha rollar</b>\n"
ROLES_TEAM_MAFIA = "🔪 <b>Mafiya jamoasi</b>"
ROLES_TEAM_TOWN = "🏘 <b>Tinch aholi jamoasi</b>"
ROLES_TEAM_SOLO = "🎲 <b>Mustaqil rollar</b>"

# Eslatmalar
REMINDER_NIGHT = "⏰ Tun tugashiga {seconds} soniya qoldi — tanlovingizni qiling!"
REMINDER_VOTE = "⏰ Ovoz berish tugashiga {seconds} soniya qoldi — ovozingizni bering!"

# AFK
AFK_KICKED = "💤 <b>{name}</b> faol bo'lmagani uchun o'yindan chiqarildi.{role}"
AFK_KICKED_PRIVATE = "💤 Siz faol bo'lmaganingiz uchun o'yindan chiqarildingiz va bu o'yin uchun mukofot olmaysiz."
PAYOUT_AFK = "💤 Siz o'yindan chiqarilgansiz — mukofot berilmadi."

# Rol e'loni (sozlamada o'chirilishi mumkin)
ROLE_REVEAL = "\nU — {role} edi."

# So'nggi so'z va o'liklar chati
LAST_WORD_PROMPT = (
    "☠️ Siz halok bo'ldingiz. {seconds} soniya ichida shu yerga bitta xabar ({limit} belgigacha) "
    "yozsangiz, u guruhga so'nggi so'zingiz sifatida chiqadi."
)
LAST_WORD_GROUP = "💬 <b>{name}</b>ning so'nggi so'zi:\n<i>{text}</i>"
LAST_WORD_TOO_LONG = "Xabar juda uzun ({length} belgi). Ko'pi bilan {limit} belgi yozing."
LAST_WORD_SENT = "✅ So'nggi so'zingiz guruhga yuborildi."
DEAD_CHAT_LINE = "☠️ {name}: {text}"
DEAD_CHAT_HINT = "👻 Endi shu yerga yozgan xabarlaringizni faqat halok bo'lgan boshqa o'yinchilar ko'radi."

# Ovozni o'zgartirish
VOTE_CHOSEN = "🗳 Siz tanladingiz: {name}\n(Vaqt tugaguncha tanlovingizni o'zgartirishingiz mumkin.)"
VOTE_ANNOUNCE = "🔵 {voter} — {target}ga ovoz berdi."
VOTE_ANNOUNCE_CHANGED = "🔄 {voter} — ovozini {target}ga o'zgartirdi."
VOTE_ANNOUNCE_SKIP = "🔵 {voter} — ovoz bermaslikni tanladi."
VOTE_ANNOUNCE_ANON = "🔵 Kimdir ovoz berdi."
MAFIA_VOTE_CHOSEN = "🔪 Siz tanladingiz: {name}\nVaqt tugaguncha o'zgartirishingiz mumkin."

# O'yin tarixi
HISTORY_HEADER = "📜 <b>O'yin tarixi</b>"
HISTORY_NIGHT = "\n🌙 <b>Tun {n}</b>"
HISTORY_DAY = "\n☀️ <b>Kun {n}</b>"
H_MAFIA_VOTE = "🔪 {voter} → {target}"
H_DOCTOR = "💉 {actor} {target}ni himoya qildi"
H_DETECTIVE = "🕵️ {actor} {target}ni tekshirdi: {result}"
H_DON_CHECK = "🎩 {actor} {target}ni tekshirdi: {result}"
H_KILLER = "🔪 Qotil {actor} → {target}"
H_HITMAN = "🥷 Yollanma {actor} → {target}"
H_POISON = "💊 {actor} {target}ga dori berdi"
H_WANDERER = "🚶 {actor} {target}ning oldiga bordi"
H_LAWYER = "👨‍💼 {actor} {target}ni himoya qildi"
H_BODYGUARD = "🛡 {actor} {target}ni qo'riqladi"
H_SPY = "🕶 {actor} {target}ning rolini bildi"
H_JOURNALIST = "📰 {actor}: {first} va {second} — {result}"
H_LOVERS = "💘 Oshiqlar: {first} va {second}"
H_HERO = "🦸 {actor} {target}ni otdi"
H_ITEM = "{emoji} {owner}: «{item}» ishladi"
H_DEATH = "⚰️ {name} halok bo'ldi ({role})"
H_VOTE = "🗳 {voter} → {target}"
H_VOTE_SKIP = "🗳 {voter} → ovoz bermadi"
H_CONFIRM = "⚖️ {name} uchun tasdiq: 👍 {likes} | 👎 {dislikes}"
H_JUDGE = "👨‍⚖️ Sudya haydashni bekor qildi"
H_AFK = "💤 {name} AFK sababli chiqarildi"

# Qo'shilish / chiqish
LOBBY_LEAVE_BUTTON = "🚪 Chiqish"
LOBBY_LEFT = "Ro'yxatdan chiqdingiz."
LOBBY_NOT_IN = "Siz ro'yxatda emassiz."
JOIN_VIA_START_OK = "✅ Siz o'yin ro'yxatiga qo'shildingiz! O'yin boshlanganda rolingiz shu yerga keladi."
JOIN_VIA_START_CLOSED = "Bu o'yin ro'yxati yopilgan yoki o'yin allaqachon boshlangan."
JOIN_VIA_START_FULL = "Ro'yxat to'lgan."
JOIN_VIA_START_OTHER_GAME = "Siz boshqa o'yinda ishtirok etyapsiz."

# /profile va /top
PROFILE_ROLE_STATS_HEADER = "📊 <b>Rollar bo'yicha:</b>"
PROFILE_ROLE_STATS_LINE = "{role}: {games} o'yin, {pct}% g'alaba"
TOP_YOUR_PLACE = "…\n{place}. Siz — {total} ball"

# /sozlamalar
SETTINGS_ADMIN_ONLY = "Sozlamalarni faqat guruh adminlari o'zgartira oladi."
SETTINGS_GROUP_ONLY = "Bu buyruq faqat guruhda ishlaydi."
SETTINGS_TITLE = "⚙️ <b>Guruh sozlamalari</b>\nO'zgarishlar keyingi o'yindan boshlab ishlaydi."
SETTINGS_TIMES_TITLE = "⏱ <b>Vaqtlar</b> (soniya). Muhokama va ovoz — asosiy vaqt, tiriklar soniga qarab uzayadi."
SETTINGS_PLAYERS_TITLE = "👥 <b>O'yinchilar soni</b>"
SETTINGS_ROLES_TITLE = "🎭 <b>Rollar</b>\nDon, Mafiya va Komissar majburiy."
SETTINGS_AUTO_TITLE = "⏰ <b>Avtomatik o'yin</b>\nHar kuni belgilangan vaqtda (Toshkent) ro'yxat o'zi ochiladi."
SETTINGS_BACK = "⬅️ Orqaga"
SETTINGS_CLOSE = "✖️ Yopish"
SETTINGS_CLOSED = "⚙️ Sozlamalar saqlandi."
SETTINGS_ON = "✅"
SETTINGS_OFF = "❌"
SETTINGS_BTN_TIMES = "⏱ Vaqtlar"
SETTINGS_BTN_PLAYERS = "👥 O'yinchilar soni"
SETTINGS_BTN_ROLES = "🎭 Rollar"
SETTINGS_BTN_AUTO = "⏰ Avto o'yin: {state}"
SETTINGS_BTN_ITEMS = "🎒 Buyumlar: {state}"
SETTINGS_BTN_HERO = "🦸 Geroy: {state}"
SETTINGS_BTN_REVEAL = "🪪 O'lganda rol e'loni: {state}"
SETTINGS_BTN_LAST_WORD = "💬 So'nggi so'z: {state}"
SETTINGS_BTN_VOTES = "🗳 Ovozlar: {state}"
SETTINGS_BTN_LOCK = "🔒 Chat qulfi: {state}"
SETTINGS_BTN_MODE = "🎮 Rejim: {state}"
SETTINGS_VOTES_OPEN = "ochiq"
SETTINGS_VOTES_ANON = "anonim"
SETTINGS_LOCK_ALL = "hamma uchun"
SETTINGS_LOCK_PLAYERS = "faqat o'yinchilar"
SETTINGS_MODE_NAMES = {"classic": "Klassik", "fast": "Tezkor (×0.5 vaqt)", "noitems": "Buyumsiz"}
SETTINGS_TIME_NAMES = {
    "night": "🌌 Tun",
    "discussion": "☀️ Muhokama",
    "vote": "🗳 Ovoz berish",
    "confirm": "⚖️ Tasdiq",
}
SETTINGS_MIN_PLAYERS = "Kamida: {value}"
SETTINGS_MAX_PLAYERS = "Ko'pi bilan: {value}"
SETTINGS_AUTO_TIME = "Vaqt: {value}"
SETTINGS_AUTO_OFF = "o'chiq"
SETTINGS_AUTO_TOGGLE_ON = "✅ Yoqish"
SETTINGS_AUTO_TOGGLE_OFF = "❌ O'chirish"
SETTINGS_ROLE_LOCKED = "🔒 majburiy"
AUTO_GAME_OPENED = "⏰ Avtomatik o'yin vaqti keldi!"
SETTINGS_HOUR_MINUS = "−1 soat"
SETTINGS_HOUR_PLUS = "+1 soat"
SETTINGS_MINUTES_MINUS = "−{step} daq"
SETTINGS_MINUTES_PLUS = "+{step} daq"

# ---------- 5-bosqich: Telegram Stars ----------
SHOP_TITLE = "💎 <b>OLMOS DO'KONI</b>"
SHOP_STARS_SECTION = "⭐ <b>Telegram Stars</b> — darhol va avtomatik:"
SHOP_CARD_SECTION = "💳 <b>Karta orqali</b> — administrator tasdiqlagach (pastki tugmalar)."
SHOP_FOOTER = "Savollar: /paysupport · Shartlar: /terms"
SHOP_STARS_BUTTON = "{diamonds}💎 — {stars}⭐"
SHOP_CARD_DISABLED = "Karta orqali to'lov hozir o'chirilgan. Telegram Stars orqali sotib oling: /shop"
INVOICE_TITLE = "{diamonds} Olmos"
INVOICE_DESCRIPTION = "Mafiya o'yini uchun {diamonds}💎 olmos. To'lovdan so'ng hisobingizga darhol qo'shiladi."
INVOICE_LABEL = "{diamonds}💎"
PRECHECKOUT_ERROR = "To'lov ma'lumotlari noto'g'ri. /shop orqali qaytadan urinib ko'ring."
STARS_PAYMENT_OK = "✅ To'lov qabul qilindi! {diamonds}💎 hisobingizga qo'shildi.\nTo'lov ID: <code>{charge_id}</code>"
STARS_PAYMENT_ADMIN = "⭐ Stars to'lovi: {name} (id=<code>{user_id}</code>) — {diamonds}💎 / {stars}⭐\nID: <code>{charge_id}</code>"
STARS_PAYMENT_BAD = "⚠️ Noma'lum Stars to'lovi (payload: <code>{payload}</code>), ID: <code>{charge_id}</code> — qo'lda tekshiring."

PAYSUPPORT_TEXT = (
    "🧾 <b>To'lovlar bo'yicha yordam</b>\n\n"
    "To'lov bilan muammo bo'lsa (olmos tushmadi, xato to'lov va h.k.) @{support} ga yozing va "
    "quyidagi to'lov ID sini yuboring. Murojaatlar 72 soat ichida ko'rib chiqiladi.\n\n"
    "Pul qaytarish shartlari: /terms"
)
PAYSUPPORT_NO_PAYMENTS = "Sizda hali Telegram Stars to'lovlari yo'q."
PAYSUPPORT_PAYMENTS_HEADER = "<b>Oxirgi to'lovlaringiz:</b>"
PAYSUPPORT_PAYMENT_LINE = "{date} — {diamonds}💎 / {stars}⭐ — {status}\n<code>{charge_id}</code>"
PAYMENT_STATUS_NAMES = {"paid": "✅ to'langan", "refunding": "⏳ qaytarilmoqda", "refunded": "↩️ qaytarilgan"}
SUPPORT_TEXT = (
    "🆘 <b>Yordam</b>\n\n"
    "O'yin qoidalari: /help va /rollar\n"
    "To'lovlar bo'yicha: /paysupport\n"
    "Boshqa savollar: @{support}"
)
TERMS_TEXT = (
    "📜 <b>Foydalanish shartlari</b>\n\n"
    "1. Olmos (💎) — faqat shu bot ichida ishlatiladigan raqamli valyuta. Uni haqiqiy pulga "
    "qaytarib almashtirib bo'lmaydi.\n"
    "2. Olmos Telegram Stars orqali to'lov tasdiqlanishi bilan darhol hisobingizga qo'shiladi.\n"
    "3. Pul qaytarish: agar olmos hisobingizga tushmagan bo'lsa yoki texnik xato bo'lsa, to'lovdan "
    "keyin 14 kun ichida /paysupport orqali murojaat qiling. Olingan olmos hali sarflanmagan bo'lsa, "
    "Stars to'liq qaytariladi va olmos hisobdan yechiladi.\n"
    "4. Sarflangan olmos (buyum, Geroy, almashtirish, o'tkazma) uchun pul qaytarilmaydi.\n"
    "5. Qoidalarni buzgan (firibgarlik, xatolardan foydalanish) akkauntlar cheklanishi mumkin.\n"
    "6. Savollar: /support"
)

# Admin: pulni qaytarish
REFUND_USAGE = "Foydalanish: /refund &lt;to'lov ID&gt; [force]"
REFUND_NOT_FOUND = "Bunday to'lov topilmadi."
REFUND_WRONG_STATUS = "Bu to'lov qaytarib bo'lmaydigan holatda: {status}."
REFUND_NOT_ENOUGH = (
    "Foydalanuvchida {diamonds}💎 yo'q (olmos sarflangan). Baribir qaytarish uchun: "
    "<code>/refund {charge_id} force</code> — bor olmosi yechiladi."
)
REFUND_API_ERROR = "❌ Telegram pulni qaytarmadi: {error}. Olmos joyiga qaytarildi."
REFUND_DONE = "✅ {stars}⭐ qaytarildi, {taken}💎 yechildi (to'lov <code>{charge_id}</code>)."
REFUND_USER_NOTICE = "↩️ {stars}⭐ to'lovingiz qaytarildi, hisobingizdan {taken}💎 yechildi."
REFUND_EXTERNAL_ADMIN = (
    "↩️ Telegram orqali qaytarilgan to'lov: id=<code>{user_id}</code>, {stars}⭐, "
    "{taken}/{diamonds}💎 yechildi. ID: <code>{charge_id}</code>"
)

# ---------- Engine (o'yin jarayoni) ----------
GOTO_BOT_BUTTON = "🤖 Botga o'tish"
DEATH_LINE = "{prefix} <b>{name}</b> halok bo'ldi.{role}"
NEW_DON = "🤵🏻 Don halok bo'ldi! Mafiya jamoasi ichida endi siz — yangi Donsiz."
NIGHT_BANNER = (
    "🌌 <b>Tun — {n}</b>\n"
    "Ko'chaga faqat jasur va qo'rqmas odamlar chiqishdi. Ertalab tirik qolganlarni sanaymiz..."
)
ALIVE_LIST = "👥 <b>Tirik o'yinchilar:</b>\n{players}"
NIGHT_TIME_LEFT = "⏳ Tonggacha {seconds} soniya qoldi."
DETECTIVE_PROMPT = "🕵️ Kimni tekshirmoqchisiz?"
KILLER_PROMPT = "🔪 Kimni yo'q qilmoqchisiz? (mustaqil)"
POISONER_PROMPT = "💊 Kimga dori bermoqchisiz?"
WANDERER_PROMPT = "🚶 Kimning oldiga bormoqchisiz?"
LAWYER_PROMPT = "👨‍💼 Kimni tekshiruvdan (Komissardan) himoya qilmoqchisiz?"
DON_CHECK_PROMPT = (
    "🎩 Xohlasangiz, kimningdir Komissar ekanini aniqlashga urinib ko'rishingiz mumkin "
    "(butun o'yin davomida faqat bir marta):"
)
PREFIX_POISON = "💊 Tun natijasi: kezuvchining dorisidan"
WOLF_TURNED = (
    "🐺 Mafiya sizni tunda yo'q qilishga urindi... lekin siz aslida ulardan ekansiz! "
    "Siz endi Mafiya jamoasining a'zosisiz.\nSherik mafiyalar: {teammates}"
)
PREFIX_MAFIA = "☠️ Tun natijasi:"
SORCERER_DRAGGED = "🧞‍♂️ Afsungar o'limidan oldin <b>{name}</b>ni ham o'zi bilan olib ketdi!{role}"
PREFIX_KILLER = "🔪 Tun natijasi: noma'lum qotil tomonidan"
PREFIX_HITMAN = "🥷 Tun natijasi: yollanma qotil tomonidan"
HITMAN_CONTRACT_DONE = "🎯 Buyurtmangizni bajardingiz! +{amount}💵 bonus oldingiz."
SORCERER_LAST_WORDS = "🧞‍♂️ Lekin Afsungar so'nggi so'zini aytishga ulguradi..."
SORCERER_REVENGE_PROMPT = "🧞‍♂️ O'limingizdan oldin kimdan o'ch olmoqchisiz?"
PREFIX_REVENGE = "🧞‍♂️ Afsungarning o'chi:"
CONFIRM_PROMPT = (
    "⚖️ Eng ko'p ovozni <b>{name}</b> oldi.\n"
    "Uni rostdan ham osamizmi? 👍 — ha, 👎 — yo'q.\n"
    "⏳ {seconds} soniya vaqt bor."
)
CONFIRM_REJECTED = "🙅 Ovozlar: 👍 {likes} | 👎 {dislikes}\n<b>{name}</b> omon qoldi — bugun hech kim osilmadi."
DAY_BANNER = "🌅 <b>Xayrli tong!</b>\n☀️ Kun: {n}\nShamollar tundagi mish-mishlarni butun shaharga yetkazmoqda.."
DISCUSSION_TIME_LEFT = "⏳ Muhokama tugashiga {seconds} soniya qoldi."
VOTING_STARTED = (
    "🗳 <b>Ovoz berish boshlandi!</b>\nHar bir o'yinchi ovozini shaxsiy xabarda beradi.\n"
    "⏳ {seconds} soniya vaqt bor."
)
VOTE_PROMPT = "🗳 Kimni shahardan haydab chiqarmoqchisiz?"
VOTE_SKIP_BUTTON = "🚫 Ovoz bermaslik"
VOTE_SKIP_NAME = "Ovoz bermaslik"
VOTE_SHIELD_SAVED = "⚖️ {name} eng ko'p ovoz oldi, lekin Ovozdan himoya buyumi tufayli omon qoldi!"
ELIMINATED = "⚖️ Shahar ovoz berdi: <b>{name}</b> haydab chiqarildi.{role}"
NOBODY_ELIMINATED = "⚖️ Ovozlar teng bo'ldi yoki hech kim ovoz bermadi — bugun hech kim haydalmadi."
TOWN_WIN_RESULT = "🎉 <b>Tinch aholi g'alaba qozondi!</b> Barcha mafiyalar tutildi."
MAFIA_WIN_RESULT = "🔪 <b>Mafiya g'alaba qozondi!</b> Shahar ularning qo'liga o'tdi."
GAME_OVER = "🏁 <b>O'yin tugadi!</b>"
WINNERS_HEADER = "<b>G'oliblar:</b>"
OTHERS_HEADER = "<b>Qolgan o'yinchilar:</b>"
DEAD_MARK = " (⚰️ halok)"
GAME_DURATION = "⏱ O'yin: {minutes} daqiqa davom etdi"
RANKING_HINT = "🏅 Reyting uchun: /top (jami), /top1 (kunlik), /top7 (haftalik), /top30 (oylik)"
GAME_ERROR = "⚠️ O'yinda kutilmagan xatolik yuz berdi, o'yin to'xtatildi."
RIFLE_ON = "🔫 Miltiq: yoqiq ✅"
RIFLE_OFF = "🔫 Miltiq: o'chiq"
PAYOUT_ROLE_LINE = "🎭 Rolingiz: {role} ({status})"
PAYOUT_ALIVE = "🟢 tirik"
PAYOUT_DEAD = "⚰️ halok"
PAYOUT_TOTALS = "💰 +{dollars}💵  🏅 +{points} ball{note}"

# Buyum nomlari (economy.ITEMS kalitlari bo'yicha)
ITEM_NAMES = {
    "shield": "Himoya",
    "fake_doc": "Soxta hujjat",
    "vote_shield": "Ovozdan himoya",
    "rifle": "Miltiq",
    "mirror": "Sehrli oyna",
    "killer_shield": "Qotildan himoya",
    "poison_shield": "Doridan himoya",
    "mask": "Maska",
    "hero_immunity": "Geroydan himoya",
}

# ---------- Ro'yxat (lobby) ----------
LOBBY_TEXT = (
    "🎭 <b>{brand}</b>\n\n"
    "<b>Ro'yxatdan o'tish boshlandi</b>\n\n"
    "Ro'yxatdan o'tganlar:\n{names}\n\n"
    "Jami {count}ta odam. (kamida {min_players} kerak)\n\n"
    "▶️ Boshlash tugmasini faqat o'yin egasi yoki guruh adminlari bosa oladi."
)
LOBBY_JOIN_BUTTON = "🤵‍♂️🤵‍♀️ Qo'shilish"
LOBBY_START_BUTTON = "▶️ Boshlash"
ROLE_YOURS = "🎭 Sizning rolingiz: <b>{role}</b>"
TEAMMATES_LINE = "Sherik mafiyalar: {names}"
HITMAN_CONTRACT_LINE = "🎯 Sizning maxfiy buyurtma nishoningiz: <b>{name}</b>"
JOIN_PROBE = "✅ Siz Mafiya o'yiniga qo'shildingiz! O'yin boshlanganda rolingiz shu yerga yuboriladi."
GAME_ALREADY_RUNNING = "Bu guruhda allaqachon o'yin ketyapti yoki ro'yxat ochiq."
IN_OTHER_GAME = "Siz allaqachon boshqa o'yinda ishtirok etyapsiz."
START_BOT_FIRST = "Avval botga shaxsiy xabar yozib, /start bosing, so'ng qayta urinib ko'ring: https://t.me/{bot}"
GROUP_ONLY_COMMAND = "Bu buyruq faqat guruhda ishlaydi. Botni guruhga qo'shing va shu yerda ishga tushiring."
GAME_ALREADY_STARTED = "Bu guruhda o'yin allaqachon boshlangan. U tugagach /start bosib yangisini oching."
ALREADY_REGISTERED = "Siz allaqachon ro'yxatdasiz. O'yin tez orada boshlanadi!"
LOBBY_OPEN_JOIN = "🎮 Bu guruhda o'yin ro'yxati ochiq! Qo'shilish uchun tugmani bosing:"
NO_ACTIVE_GAME = "Bu guruhda faol o'yin yo'q."
STOP_ADMIN_ONLY = "Faqat guruh adminlari o'yinni to'xtata oladi."
GAME_STOPPED = "🛑 O'yin to'xtatildi."
LOBBY_CLOSED = "Ro'yxat yopiq."
ALREADY_JOINED = "Siz allaqachon qo'shilgansiz."
LOBBY_FULL = "Ro'yxat to'lgan."
IN_OTHER_GAME_SHORT = "Siz boshqa o'yinda ishtirok etyapsiz."
JOINED = "Qo'shildingiz! ✅"
GAME_ALREADY_STARTING = "O'yin allaqachon boshlanmoqda."
START_OWNER_ONLY = "Faqat o'yin egasi yoki guruh adminlari boshlashi mumkin."
MIN_PLAYERS_NEEDED = "Kamida {count} o'yinchi kerak."
GAME_STARTING = "O'yin boshlanmoqda... ▶️"
BACK_TO_GROUP = "⬅️ Guruhga qaytish"
GAME_STARTED = "🎮 O'yin boshlandi! Rollar shaxsiy xabarlarga yuborildi."

# ---------- Bozor ----------
MARKET_SELL_USAGE = (
    "Foydalanish: /sell &lt;miqdor&gt; &lt;valyuta&gt; &lt;narx&gt; &lt;narx_valyutasi&gt;\n"
    "Masalan: /sell 100 coin 5000 dollar"
)
MARKET_NOT_NUMBER = "Miqdor va narx butun son bo'lishi kerak."
MARKET_BAD_CURRENCY = "Valyuta noto'g'ri. Mavjud: dollar, diamond (olmos), coin"
MARKET_SAME_CURRENCY = "Ikki xil valyuta tanlang."
MARKET_NOT_POSITIVE = "Miqdor musbat bo'lishi kerak."
NOT_ENOUGH_BALANCE = "Balansingizda yetarli {emoji} yo'q."
MARKET_LISTED = "✅ E'lon joylandi (#{id}): {sell} → {price}\nBekor qilish uchun: /cancel {id}"
MARKET_CANCEL_USAGE = "Foydalanish: /cancel &lt;e'lon raqami&gt;"
MARKET_NOT_YOURS = "Bu e'lon sizga tegishli emas."
MARKET_ALREADY_CLOSED = "Bu e'lon allaqachon yopilgan."
MARKET_CANCELLED = "❌ E'lon #{id} bekor qilindi, {amount} qaytarildi."
MARKET_NO_LISTINGS_MINE = "Sizda faol e'lonlar yo'q."
MARKET_MY_LISTINGS = "<b>Sizning faol e'lonlaringiz:</b>"
MARKET_EMPTY = "Bozorda hozircha hech narsa yo'q."
MARKET_TITLE = "🛒 <b>BOZOR</b>"
MARKET_BUY_BUTTON = "🛒 #{id} sotib olish"
MARKET_GONE = "Bu e'lon endi mavjud emas."
MARKET_OWN = "O'z e'loningizni sotib ololmaysiz."
MARKET_SOLD_TO_OTHER = "Bu e'lonni boshqa birov sotib oldi."
MARKET_BOUGHT = "Xarid muvaffaqiyatli! ✅"
MARKET_SOLD_MARK = "✅ #{id} sotildi."
MARKET_SOLD_NOTICE = "💰 E'loningiz #{id} sotildi: {sell} → {price} hisobingizga qo'shildi."

# ---------- Buyumlar do'koni va sumka ----------
STORE_TEXT = (
    "🎒 <b>BUYUMLAR DO'KONI</b>\n"
    "O'yin ichida foydali bo'ladigan buyumlarni sotib oling. Sotib olingan buyum avtomatik "
    "yoqilgan (✅) holatda bo'ladi — /sumka orqali o'chirib qo'yishingiz mumkin.\n\n"
    "{rule}\n\nKerakli buyumni tanlang:"
)
ITEM_NOT_FOUND = "Bu buyum topilmadi."
ITEM_PRICE_LINE = "{emoji} <b>{name}</b> — {price} (1 dona)"
ITEM_HOW_MANY = "Nechta sotib olmoqchisiz?"
QUANTITY_BUTTON = "{qty} ta"
BACK_BUTTON = "⬅️ Orqaga"
ITEM_BOUGHT_ALERT = "✅ {qty} ta {emoji} {name} sotib olindi!"
ITEM_BOUGHT = "✅ Xarid qilindi: {qty} ta {emoji} {name} (-{price})"
INVENTORY_EMPTY = "🎒 Sizda hali hech qanday buyum yo'q.\n\n/dokon orqali sotib olishingiz mumkin."
INVENTORY_TITLE = "🎒 <b>MENING BUYUMLARIM</b>"
ITEM_STATE_ON = "✅"
ITEM_STATE_OFF = "❌"
INVENTORY_LINE = "{state} {emoji} {name}: {count} ta"
ITEM_TURN_OFF = "O'chirish"
ITEM_TURN_ON = "Yoqish"
ITEM_NOT_OWNED = "Bu buyum sizda yo'q."
ITEM_ENABLED = "Yoqildi ✅"
ITEM_DISABLED = "O'chirildi"

# ---------- Profil va admin ----------
PROFILE_TEXT = (
    "👤 <b>{name}</b>\n"
    "🆔 ID: <code>{user_id}</code>\n\n"
    "💵 Dollar: {dollars}\n"
    "💎 Olmos: {diamonds}\n"
    "🪙 Coin: {coins}\n\n"
    "🏅 Ball — kunlik: {daily} | haftalik: {weekly} | oylik: {monthly} | jami: {total}\n\n"
    "🦸 Geroy: {hero}\n\n"
    "🎒 <b>Buyumlar:</b>"
)
PROFILE_HERO_LEVEL = "{level}-daraja"
PROFILE_HERO_NONE = "yo'q (/geroy)"
PROFILE_ITEM_LINE = "{emoji} {name}: {count} ta"
PROFILE_GAMES = "🎮 O'yinlar: {games} | 🏆 G'alabalar: {wins}"
PROFILE_TOGGLE_HINT = "⚙️ Buyumlarni yoqish/o'chirish uchun pastdagi tugmalarni bosing:"
PROFILE_ITEM_ON = "✅"
PROFILE_ITEM_OFF = "❌"
MAIN_MENU_BUTTON = "🏠 Bosh menyu"
ADMIN_REPLY_USAGE = "Foydalanish: xabarga reply qiling va miqdorni yozing, masalan /addcash 1000"
ADMIN_USAGE = "Foydalanish: /addcash &lt;user_id&gt; &lt;miqdor&gt; yoki xabarga reply qilib /addcash &lt;miqdor&gt;"
ADMIN_BALANCE_ADDED = "✅ {amount}{emoji} balansga qo'shildi (user_id={user_id})."

# ---------- Geroy ----------
HERO_INTRO = (
    "🦸 <b>GEROY</b>\n\n"
    "Geroy — bir marta sotib olinadigan va profilingizda umrbod qoladigan maxsus buyum.\n"
    "Darajasini cheksiz oshirish mumkin.\n\n"
    "🎭 Mafiya, Don yoki Komissar bo'lib qolgan o'yinlarda tunda nishonni otish huquqi beradi "
    "(bir o'yinda 1 marta).\n"
    "🔓 {bypass}-darajadan boshlab zarbangiz HAR QANDAY himoyani chetlab o'tadi.\n\n"
    "Narxi: {price}💎"
)
HERO_BUY_BUTTON = "🦸 Sotib olish — {price}💎"
HERO_BYPASS_ACTIVE = "🔓 Zarbangiz har qanday himoyani chetlab o'tadi!"
HERO_BYPASS_LOCKED = "🔒 {level}-darajaga yetganda zarbangiz har qanday himoyani chetlab o'tadi."
HERO_STATUS = "🦸 <b>GEROY</b>\n\nJoriy darajangiz: <b>{level}</b>\n{bypass}\n\nDarajani oshirish narxi: {price}💎"
HERO_LEVELUP_BUTTON = "⬆️ Darajani oshirish — {price}💎"
HERO_ALREADY_OWNED = "Sizda allaqachon Geroy bor."
NOT_ENOUGH_DIAMONDS = "Balansingizda yetarli 💎 yo'q."
HERO_BOUGHT = "✅ Geroy sotib olindi!"
HERO_BUY_FIRST = "Avval Geroyni sotib oling."
HERO_LEVELED_UP = "✅ Geroy {level}-darajaga o'tdi!"

# ---------- Karta orqali olmos xaridi ----------
SHOP_CARD_BUTTON = "{diamonds}💎 — {price} so'm"
PACKAGE_NOT_FOUND = "Bu paket topilmadi."
CARD_ORDER_TEXT = (
    "💎 <b>{diamonds} Olmos xaridi</b>\n\n"
    "To'lov summasi: <b>{price} so'm</b>\n\n"
    "Karta raqami: <code>{card}</code>\n"
    "Karta egasi: {holder}\n\n"
    "⚠️ <b>DIQQAT!</b> To'lovni amalga oshirayotganda <b>IZOH</b> qismiga "
    "faqat ushbu buyurtma raqamini yozing:\n\n<code>#{order_id}</code>\n\n"
    "To'lov qilgach kuting — administrator tekshirib, olmoslarni hisobingizga qo'shadi."
)
CARD_ORDER_RECEIPT = (
    "\n\n🧾 To'lovdan so'ng <b>chekni (skrinshot)</b> buyurtma raqami "
    "<code>#{order_id}</code> bilan birga @{contact} ga yuboring."
)
CARD_RECEIPT_BUTTON = "🧾 Chekni yuborish"
CARD_APPROVE_BUTTON = "✅ Tasdiqlash"
CARD_REJECT_BUTTON = "❌ Rad etish"
CARD_ADMIN_ORDER = (
    "🧾 <b>Yangi buyurtma #{order_id}</b>\n"
    "Foydalanuvchi: {name} (id=<code>{user_id}</code>)\n"
    "Paket: {diamonds}💎 — {price} so'm\n\n"
    "To'lov tushganini tekshirib, tugmalardan birini bosing."
)
NOT_FOR_YOU = "Bu tugma siz uchun emas."
ORDER_NOT_FOUND = "Buyurtma topilmadi."
ORDER_ALREADY_REVIEWED = "Bu buyurtma allaqachon ko'rib chiqilgan."
ORDER_APPROVED_ALERT = "Tasdiqlandi ✅"
ORDER_APPROVED_MARK = "✅ Tasdiqlandi va olmos berildi."
ORDER_APPROVED_USER = "✅ To'lovingiz tasdiqlandi! {diamonds}💎 hisobingizga qo'shildi."
ORDER_REJECTED_ALERT = "Rad etildi ❌"
ORDER_REJECTED_MARK = "❌ Rad etildi."
ORDER_REJECTED_USER = "❌ Buyurtma #{order_id} rad etildi. Savol bo'lsa administratorga murojaat qiling."

# ---------- Bosh menyu ----------
MAIN_MENU_TEXT = (
    "🎩 <b>Qorong'u shaharga xush kelibsiz!</b>\n\n"
    "<i>Bu yerda oddiy qoidalar ishlamaydi. Do'stlik, xiyonat va intriga — "
    "barchasi bir-biriga qorishib ketgan.</i>\n\n"
    "🛡 <b>Tinch aholi</b> bo'lib shaharni qutqarasizmi yoki 🔪 <b>Mafiya</b> bo'lib "
    "hammani yo'q qilasizmi?\n\n"
    "Guruhga qo'shing va <code>/mafia</code> yozing yoki pastdagi tugmalardan foydalaning 👇"
)
MENU_ADD_TO_GROUP = "➕ Guruhingizga qo'shish"
MENU_PROFILE = "👤 Mening profilim"
MENU_STORE = "🛒 Do'kon"
MENU_MARKET = "🛍 Bozor"
MENU_SHOP = "💎 Olmos sotib olish"
MENU_SEND_DOLLAR = "💸 Pul yuborish"
MENU_SEND_DIAMOND = "💎 Olmos yuborish"
MENU_HELP = "❓ Yordam"
MENU_LANGUAGE = "🌐 Til / Язык"
MENU_BACK = "⬅️ Bosh menyu"

# ---------- Til tanlash ----------
LANG_PROMPT = "🌐 Tilni tanlang / Тилни танланг / Выберите язык:"
LANG_GROUP_PROMPT = "🌐 Guruh tilini tanlang (guruhdagi o'yin xabarlari shu tilda chiqadi):"
LANG_SET = "✅ Til o'zgartirildi: {name}."
LANG_GROUP_SET = "✅ Guruh tili o'zgartirildi: {name}. Yangi o'yindan boshlab ishlaydi."
LANG_ADMIN_ONLY = "Guruh tilini faqat guruh adminlari o'zgartira oladi."

# ---------- Pul / olmos yuborish ----------
CURRENCY_LABELS = {"dollar": "Dollar 💵", "diamond": "Olmos 💎"}
TRANSFER_START = (
    "{currency} yubormoqchisiz.\n\n"
    "Kimga yuborasiz? Qabul qiluvchining foydalanuvchi ID raqami yoki @username'ini yuboring.\n"
    "(Qabul qiluvchi avval botga /start bosgan bo'lishi kerak.)"
)
TRANSFER_PRIVATE_ONLY = "💸 Pul/olmos yuborish faqat bot bilan shaxsiy chatda ishlaydi."
TRANSFER_USER_NOT_FOUND = (
    "Bunday foydalanuvchi topilmadi — u botga hali /start bosmagan bo'lishi mumkin.\n"
    "Qaytadan ID yoki @username yuboring."
)
TRANSFER_SELF = "O'zingizga yubora olmaysiz. Boshqa foydalanuvchi ID/username yuboring."
TRANSFER_ASK_AMOUNT = "Qabul qiluvchi: <b>{name}</b>\nEndi miqdorni kiriting (butun son):"
TRANSFER_BAD_AMOUNT = "Miqdor musbat butun son bo'lishi kerak. Qaytadan kiriting:"
TRANSFER_CONFIRM_BUTTON = "✅ Tasdiqlash"
TRANSFER_CANCEL_BUTTON = "❌ Bekor qilish"
TRANSFER_CONFIRM = "<b>{name}</b>ga {amount}{emoji} yubormoqchisiz. Tasdiqlaysizmi?"
TRANSFER_CANCELLED_ALERT = "Bekor qilindi."
TRANSFER_CANCELLED = "❌ Pul/olmos o'tkazish bekor qilindi."
TRANSFER_NOT_ENOUGH = "Balansingiz yetarli emas."
TRANSFER_SENT_ALERT = "Yuborildi ✅"
TRANSFER_SENT = "✅ {name}ga {amount}{emoji} yuborildi."
TRANSFER_RECEIVED = "💌 Sizga <b>{name}</b> tomonidan {amount}{emoji} yuborildi!"

# ---------- Reyting ----------
TOP_ALL_TITLE = "🏆 <b>Umumiy TOP (barcha o'yinlar)</b>"
TOP_DAY_TITLE = "🕐 <b>Kunlik TOP</b> (bugun 00:00 — 23:59)"
TOP_WEEK_TITLE = "📅 <b>Haftalik TOP</b> (dushanba — yakshanba)"
TOP_MONTH_TITLE = "🗓 <b>Oylik TOP</b> (oyning 1-sanasidan)"
TOP_EMPTY = "Hozircha ma'lumot yo'q."
TOP_LINE = "{place}. {name} — {total} ball"

# ---------- Kunduzgi ovoz ----------
NOT_VOTING_TIME = "Hozir ovoz berish vaqti emas."
NOT_IN_GAME_OR_DEAD = "Siz o'yinda emassiz yoki halok bo'lgansiz."
PLAYER_NOT_AVAILABLE = "Bu o'yinchi mavjud emas."
VOTE_ALREADY = "Ovozingiz allaqachon qabul qilingan."
VOTE_ACCEPTED = "Ovozingiz qabul qilindi ✅"
CONFIRM_SELF = "O'zingiz uchun ovoz bera olmaysiz."
CONFIRM_YES = "👍 Ha"
CONFIRM_NO = "👎 Yo'q"

# ---------- Tungi tugmalar ----------
NOT_NIGHT = "Hozir tun emas."
ALREADY_CHECKED = "Siz bu kecha allaqachon tekshirgansiz."
ALREADY_POISONED = "Siz bu kecha allaqachon dori bergansiz."
ALREADY_USED_ABILITY = "Siz bu imkoniyatdan allaqachon foydalangansiz."
ALREADY_LEARNED = "Siz bu kecha allaqachon bilib olgansiz."
ALREADY_CHOSEN = "Siz allaqachon tanlagansiz."
ABILITY_GONE = "Bu imkoniyat endi mavjud emas."
YOU_CHOSE_ALERT = "Siz {name}ni tanladingiz."
YOU_PROTECT_ALERT = "Siz {name}ni himoya qilyapsiz."
YOU_PROTECTED = "💉 Siz himoya qildingiz: {name}"
YOU_POISONED_ALERT = "Siz {name}ga dori berdingiz."
YOU_POISONED = "💊 Siz dori berdingiz: {name}"
YOU_VISITED_ALERT = "Siz {name}ning oldiga bordingiz."
YOU_VISITED = "🚶 Siz tashrif buyurdingiz: {name}"
KILLER_CHOSEN = "🔪 Siz tanladingiz: {name}"
HITMAN_CHOSEN = "🥷 Siz tanladingiz: {name}"
LAWYER_CHOSEN = "👨‍💼 Siz himoya qildingiz: {name}"
HERO_CHOSEN_ALERT = "Siz {name}ni otishga qaror qildingiz."
HERO_CHOSEN = "🥷 Siz otishga qaror qildingiz: {name}"
REVENGE_CHOSEN_ALERT = "O'ch: {name}"
REVENGE_CHOSEN = "🧞‍♂️ O'ch tanlandi: {name}"
RIFLE_TOGGLED_OFF = "Miltiq o'chirildi."
RIFLE_TOGGLED_ON = "Miltiq yoqildi — himoyani bekor qiladi!"
DETECTIVE_RESULT_MAFIA = "u — Mafiya a'zosi! 🔪"
DETECTIVE_RESULT_CLEAN = "u — mafiya emas. ✅"
DETECTIVE_RESULT = "🕵️ Tekshiruv natijasi: {name} — {result}"
DON_RESULT_DETECTIVE = "u — Komissar! 🕵️"
DON_RESULT_NOT = "u — komissar emas."
DON_RESULT = "🎩 Aniqlash natijasi: {name} — {result}"
H_SAME_TEAM = "bir jamoa"
H_DIFF_TEAM = "turli jamoa"
ANN_MAFIA_CHOSE = "🔪 Mafiya o'ljasini tanladi."
ANN_DOCTOR = "💉 Doktor tungi navbatchilikka ketdi."
ANN_DETECTIVE = "🕵️ Komissar tekshiruvini boshladi."
ANN_KILLER = "🔪 Qotil nishonini tanladi."
ANN_HITMAN = "🥷 Yollanma qotil nishonini tanladi."
ANN_POISONER = "💊 Kezuvchi kimgadir dori berdi."
ANN_WANDERER = "🚶 Daydi kimningdir oldiga bordi."
ANN_DON = "🎩 Don o'z tekshiruvini o'tkazdi."
ANN_LAWYER = "👨‍💼 Advokat o'z himoyasini tayinladi."
ANN_BODYGUARD = "🛡 Tansoqchi navbatchilikka chiqdi."
ANN_JOURNALIST = "📰 Jurnalist tekshiruv o'tkazdi."

# ---------- Qo'llanma (/qoidalar) ----------
RULES_TEXT = (
    "📖 <b>MAFIYA — QISQA QO'LLANMA</b>\n\n"
    "<b>O'yinni boshlash:</b>\n"
    "1. Botga shaxsiy chatda bir marta /start bosing — rolingiz shu yerga keladi.\n"
    "2. Guruhda /mafia yozing — ro'yxat ochiladi, \"Qo'shilish\" tugmasini bosing.\n"
    "3. Yetarli odam yig'ilgach, o'yin egasi yoki admin \"Boshlash\"ni bosadi.\n\n"
    "<b>O'yin tartibi:</b>\n"
    "🌙 Tun — guruh yopiladi. Rolingiz bo'yicha tanlov tugmalari shaxsiy chatga keladi.\n"
    "☀️ Kun — kim halok bo'lgani e'lon qilinadi, muhokama va ovoz berish. Ko'p ovoz olgan haydaladi.\n"
    "🏆 Mafiya soni tinch aholiga teng yoki ko'p bo'lsa — mafiya, barcha mafiya va Qotil yo'q qilinsa — "
    "tinch aholi g'alaba qiladi.\n\n"
    "<b>Guruh qoidalari:</b>\n"
    "• Rolingizni yoki shaxsiy chatdagi xabarlarni skrinshot qilib ko'rsatmang.\n"
    "• Halok bo'lganingizdan keyin o'yin haqida yozmang.\n"
    "• Tunda tanlov qilmagan va ovoz bermagan o'yinchi o'yindan chiqariladi.\n"
    "• Haqorat va reklama taqiqlanadi.\n\n"
    "<b>Buyumlar:</b>\n"
    "/dokon — sotib olish, /sumka — yoqish/o'chirish, /buyumlar — har bir buyum nima qiladi.\n"
    "Yoqilgan (✅) buyum o'yinda o'zi ishlaydi va faqat sizni qutqarganda sarflanadi.\n\n"
    "/rollar — barcha rollar, /bonus — kunlik bonus, /help — barcha buyruqlar."
)
RULES_BTN_FULL = "📚 To'liq qo'llanma"
RULES_BTN_ROLES = "🎭 Rollar"
RULES_BTN_ITEMS = "🎒 Buyumlar"
RULES_SENT_PM = "📩 Shaxsiy chatga yuborildi."
RULES_PM_FAILED = "Avval botga shaxsiy chatda /start bosing, so'ng qayta urinib ko'ring."
LOBBY_RULES_BUTTON = "📖 Qoidalar"
MENU_RULES = "📖 Qoidalar va qo'llanma"

# ---------- Bot buyruqlari menyusi ----------
BOT_COMMANDS = {
    "mafia": "Yangi Mafiya o'yini boshlash (guruhda)",
    "stop": "Joriy o'yinni to'xtatish",
    "shop": "Olmos sotib olish",
    "almashtir": "Olmos va Coinni Dollarga almashtirish",
    "market": "Bozor — valyutalar savdosi",
    "dokon": "Buyumlar do'koni (Himoya, Miltiq va h.k.)",
    "sumka": "Mening buyumlarim (yoqish/o'chirish)",
    "buyumlar": "Barcha buyumlar tavsifi",
    "mavsum": "Mavsum chiptasi: daraja va mukofotlar",
    "bonus": "Kunlik bonus",
    "vip": "VIP obuna",
    "taklif": "Do'stlarni taklif qilish",
    "premium": "Guruh premiumi (guruhda)",
    "turnir": "Turnir (premium guruhda, adminlar)",
    "send": "Boshqa foydalanuvchiga Dollar yuborish",
    "sendgem": "Boshqa foydalanuvchiga Olmos yuborish",
    "profile": "Profilingiz (balans, statistika)",
    "geroy": "Geroyni sotib olish / darajasini oshirish",
    "top": "Umumiy reyting (barcha o'yinlar)",
    "top1": "Kunlik reyting",
    "top7": "Haftalik reyting",
    "top30": "Oylik reyting",
    "qoidalar": "Qoidalar va qisqa qo'llanma",
    "rollar": "Barcha rollar tavsifi",
    "sozlamalar": "Guruh sozlamalari (adminlar uchun)",
    "til": "Tilni tanlash / Выбор языка",
    "help": "Yordam",
    "support": "Yordam va aloqa",
    "paysupport": "To'lovlar bo'yicha yordam",
    "terms": "Foydalanish shartlari",
}

# ---------- 6-bosqich: buyumlar ----------
# Buyum haqiqatan ishlaganda egasiga boradigan xabar ({left} — qolgan dona).
ITEM_USED = {
    "shield": "🛡 Himoyangiz sizni Mafiya hujumidan qutqardi. Qoldi: {left} dona.",
    "fake_doc": "📁 Soxta hujjatingiz Komissarni aldadi — natija \"mafiya emas\" chiqdi. Qoldi: {left} dona.",
    "vote_shield": "⚖️ Ovozdan himoyangiz sizni haydalishdan qutqardi. Qoldi: {left} dona.",
    "rifle": "🔫 Miltiqingiz nishonning himoyasini teshib o'tdi. Qoldi: {left} dona.",
    "mirror": "🔮 Sehrli oynangiz hujumni qaytardi, siz omon qoldingiz. Qoldi: {left} dona.",
    "killer_shield": "⛑ Qotildan himoyangiz sizni qutqardi. Qoldi: {left} dona.",
    "poison_shield": "💊 Doridan himoyangiz sizga berilgan zaharni zararsizlantirdi. Qoldi: {left} dona.",
    "mask": "🎭 Maskangiz sizni Daydidan yashirdi. Qoldi: {left} dona.",
    "hero_immunity": "🔰 Geroydan himoyangiz sizni zarbadan qutqardi. Qoldi: {left} dona.",
}
TARGET_SURVIVED = "🎯 Nishon omon qoldi."
WANDERER_SAW_NOTHING = "🚶 Siz tashrif buyurgan {victim} shu kecha halok bo'ldi, lekin siz hech narsa ko'rmadingiz."
HERO_NIGHT_PROMPT = "🦸 Geroy zarbasi (ixtiyoriy, o'yinda 1 marta). Kimni otmoqchisiz?"
HERO_SHOT_KEPT = "🦸 Nishoningiz shu tunda boshqa sababdan halok bo'ldi — Geroy zarbangiz saqlanib qoldi."
ROLE_ITEMS_HEADER = "🎒 <b>Shu o'yinda yoqilgan buyumlaringiz:</b>"
ROLE_ITEMS_NONE = "🎒 Shu o'yinda yoqilgan buyumlaringiz yo'q."
ROLE_ITEMS_LINE = "{emoji} {name}"
ROLE_ITEMS_RIFLE = "🔫 Miltiq: {count} dona — tunda nishon tanlash xabaridagi tugma orqali"
NO_ITEMS_NOTICE = "🚫 Bu o'yin <b>buyumsiz</b>: buyumlar va Geroy ishlamaydi, hech narsa sarflanmaydi."
INVENTORY_RIFLE_LINE = "🔫 Miltiq: {count} ta — tunda qo'lda ishlatiladi (yoqish shart emas)"
HERO_BADGE = " 🦸{level}"
ITEM_INFO_BUTTON = "ℹ️"
ITEMS_LIST_HEADER = "🎒 <b>Barcha buyumlar</b>\nSotib olish: /dokon · Yoqish/o'chirish: /sumka"
ITEM_BOUGHT_CARD = "✅ Xarid: {qty} ta {emoji} {name}. Buyum haqida:"
SHOP_WHY_DIAMONDS = "💎 Olmos nimaga kerak: buyumlar (/dokon), 🦸 Geroy, 💵 ga almashtirish va do'stlarga sovg'a (/sendgem)."
ITEM_CARD = (
    "{emoji} <b>{name}</b> — {price}\n\n"
    "<b>Nima qiladi:</b> {what}\n"
    "<b>Kimga foydali:</b> {who}\n"
    "<b>Qanday ishlatiladi:</b> {how}\n"
    "<b>Sarflanadimi:</b> {spent}"
)
ITEM_INFO = {
    "shield": {
        "what": "Tunda Mafiya hujumini to'xtatadi, siz omon qolasiz. Hujumchi 🔫 Miltiq ishlatsa, ishlamaydi. "
        "Qotil, Yollanma qotil, Kezuvchi zahari va Geroyga qarshi ishlamaydi.",
        "who": "Hamma o'yinchiga, ayniqsa tinch aholi va Komissar, Doktor kabi muhim rollarga.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat sizni qutqarganda 1 dona. Doktor qutqargan bo'lsa, sarflanmaydi.",
    },
    "fake_doc": {
        "what": "Komissar sizni tekshirsa, natija \"mafiya emas\" chiqadi (Serjant ham shuni ko'radi). "
        "Jurnalist va Josusni aldamaydi.",
        "who": "Mafiya jamoasiga: Don, Mafiya, Advokat, Yollanma qotil, Josus.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat Mafiya jamoasida bo'lsangiz va shu kecha sizni Advokat himoya qilmagan bo'lsa, 1 dona.",
    },
    "vote_shield": {
        "what": "Kunduzgi ovoz sizni haydashni tasdiqlasa ham omon qolasiz, rolingiz ochilmaydi. "
        "Guruhga shu haqda e'lon qilinadi.",
        "who": "Kunduzi haydalish xavfi bor har kimga, ayniqsa Mafiya jamoasiga.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat qutqarganda 1 dona. Sudya hukmni bekor qilsa, sarflanmaydi.",
    },
    "rifle": {
        "what": "Mafiya nishonining 🛡 Himoyasini teshib o'tadi. Doktor, Tansoqchi va 🔮 Sehrli oynaga ta'sir qilmaydi.",
        "who": "Don va Mafiyaga.",
        "how": "Tunda nishon tanlash xabaridagi \"🔫 Miltiq\" tugmasini yoqing. /sumka da yoqish shart emas.",
        "spent": "Faqat Himoyani haqiqatan teshganda 1 dona (o'yinda 1 marta).",
    },
    "mirror": {
        "what": "Hujumni qaytaradi, siz omon qolasiz. Mafiya hujumida o'rningizga shu nishonga ovoz bergan Don "
        "yoki Mafiyalardan biri o'ladi. 10-darajadan past Geroy otsa, otgan kishining o'zi o'ladi.",
        "who": "Hamma o'yinchiga, ayniqsa Mafiya ov qiladigan tinch rollarga.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat hujumni qaytarganda 1 dona.",
    },
    "killer_shield": {
        "what": "Qotil yoki Yollanma qotil hujumini to'xtatadi, siz omon qolasiz (Yollanma buyurtmasi bajarilmaydi).",
        "who": "Hamma o'yinchiga.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat qutqarganda 1 dona.",
    },
    "poison_shield": {
        "what": "Kezuvchi zaharini zararsizlantiradi. Kezuvchi buni bilmaydi.",
        "who": "Hamma o'yinchiga.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Zahar ta'sir qiladigan kechada 1 dona. O'sha kecha Doktor davolagan bo'lsa, sarflanmaydi.",
    },
    "mask": {
        "what": "Siz o'ldirgan odamning oldiga Daydi borsa, u qotilni ko'rmaydi.",
        "who": "Tunda o'ldiradigan rollarga: Don, Mafiya, Yollanma qotil, Qotil, Kezuvchi.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat Daydi haqiqatan kelganda 1 dona.",
    },
    "hero_immunity": {
        "what": "10-darajadan past Geroy zarbasini to'xtatadi. 🔮 Sehrli oyna ham bo'lsa, avval oyna ishlaydi.",
        "who": "Hamma o'yinchiga.",
        "how": "/sumka da yoqib qo'ying (✅) — o'yinda o'zi ishlaydi.",
        "spent": "Faqat qutqarganda 1 dona. 10+ darajali Geroyga qarshi ishlamaydi va sarflanmaydi.",
    },
}
HERO_CARD = (
    "🦸 <b>Geroy</b> — {price}💎 bir marta, har bir daraja {level_price}💎\n\n"
    "<b>Nima qiladi:</b> tanlangan odam o'ladi. Doktor himoya qilmaydi, 🔮 va 🔰 to'xtatadi. "
    "{bypass}-darajadan boshlab hech qanday himoya ishlamaydi. Boshqa darajalar faqat belgi (🦸N).\n"
    "<b>Kimga foydali:</b> o'yinda Mafiya, Don yoki Komissar rolini olganingizda.\n"
    "<b>Qanday ishlatiladi:</b> tunda shaxsiy chatga \"🦸 Geroy zarbasi\" tugmalari keladi, o'yinda 1 marta.\n"
    "<b>Sarflanadimi:</b> yo'q, umrbod qoladi (/geroy)."
)

# ---------- 7-bosqich: 🎨 Kosmetika ----------
# Unvon matni (emojisiz qismi) 16 belgidan oshmasin.
COSMETIC_NAMES = {
    "night_guard": "🌙 Tun qo'riqchisi",
    "orator": "🗣 Notiq",
    "old_fox": "🎩 Qari tulki",
    "owl": "🦉 Boyo'g'li",
    "cold_blooded": "🧊 Sovuqqon",
    "trickster": "🃏 Hiylakor",
    "eagle_eye": "🦅 Burgut ko'z",
    "shadow": "🌑 Soya",
    "legendary": "🐉 Afsonaviy",
    "newcomer": "🌱 Yangi o'yinchi",
    "weekly_champion": "🏆 Hafta chempioni",
    "rose": "🌹 Atirgul",
    "curtain": "🎬 Parda",
    "ghost": "👻 Arvoh",
    "lightning": "⚡ Chaqmoq",
    "stars_frame": "✨ Yulduzli ramka",
    "ice_frame": "❄️ Muzli ramka",
    "fire_frame": "🔥 Olovli ramka",
    "s1_title": "🍂 Kuz afsonasi",
    "s1_death": "🍂 Kuzgi xazon",
    "s1_frame": "🍂 Kuzgi ramka",
}
# O'lim uslublari: kim o'ldirgani va qanday o'lgani aytilmaydi. Rol qismi (DEATH_STYLE_ROLE)
# guruhda rol e'loni yoqilgan bo'lsa qo'shiladi.
DEATH_STYLES = {
    "rose": "🌹 {name} atirgullar orasida mangu uyquga ketdi.",
    "curtain": "🎬 Parda yopildi: {name} sahnani tark etdi.",
    "ghost": "👻 {name} arvohga aylandi, endi shaharni soyadan kuzatadi.",
    "lightning": "⚡ Bir zumda! {name} halok bo'ldi.",
    "s1_death": "🍂 {name} kuzgi xazon bilan birga to'kildi.",
}
DEATH_STYLE_ROLE = " U {role} edi."
FRAME_LINES = {
    "stars_frame": "✨━━━━━━━━━━━━✨",
    "ice_frame": "❄️━━━━━━━━━━━━❄️",
    "fire_frame": "🔥━━━━━━━━━━━━🔥",
    "s1_frame": "🍂━━━━━━━━━━━━🍂",
}
COSMETIC_KIND_NAMES = {"title": "🏷 Unvonlar", "death": "💀 O'lim uslublari", "frame": "🖼 Profil ramkalari"}
COSMETICS_BUTTON = "🎨 Kosmetika"
COSMETICS_STORE_TITLE = (
    "🎨 <b>KOSMETIKA</b>\n"
    "Doimiy bezaklar — o'yinga ta'sir qilmaydi. Har turdan bittasi faol bo'ladi, /sumka da almashtiriladi."
)
COSMETIC_PRICE_LINE = "{name} — {price}"
COSMETIC_OWNED_LINE = "✅ {name}"
COSMETIC_DEATH_PREVIEW = "<i>{preview}</i>"
COSMETIC_BOUGHT = "✅ «{name}» sotib olindi va faollashtirildi. Almashtirish: /sumka → 🎨 Kosmetika."
COSMETIC_ALREADY_OWNED = "Bu sizda allaqachon bor."
COSMETIC_NOT_FOR_SALE = "Bu narsa do'konda sotilmaydi."
COSMETICS_MY_TITLE = "🎨 <b>MENING KOSMETIKAM</b>\nFaol narsani tanlash uchun bosing."
COSMETICS_MY_EMPTY = "🎨 Sizda hali kosmetika yo'q. /dokon → 🎨 Kosmetika."
COSMETIC_TAKE_OFF = "❌ {kind}: yechish"
COSMETIC_ACTIVATED = "✅ Faollashtirildi"
COSMETIC_REMOVED = "Yechildi"
COSMETIC_PREVIEW_NAME = "Ism"
PUBLIC_PROFILE = (
    "👤 <b>{name}</b>\n"
    "🎮 O'yinlar: {games} | 🏆 G'alabalar: {wins}\n"
    "🏅 Umumiy reytingdagi o'rni: {place}"
)
PUBLIC_PROFILE_NO_RANK = "—"
PUBLIC_PROFILE_UNKNOWN = "Bu foydalanuvchi hali botda o'ynamagan."
VOTE_RESULT_HEADER = "⚖️ Shahar ovoz berdi:"
WEEKLY_CHAMPION_NOTICE = (
    "🏆 Siz o'tgan haftaning chempionisiz! «🏆 Hafta chempioni» unvoni bir hafta davomida ismingiz oldida turadi."
)

# ---------- 7-bosqich: 🎟 Mavsum chiptasi ----------
SEASON_NAMES = {1: "🍂 Kuz"}
SEASON_DEFAULT_NAME = "{n}-mavsum"
SEASON_NOT_STARTED = "🎟 1-mavsum ({name}) {date} kuni boshlanadi."
SEASON_TEXT = (
    "🎟 <b>{name}</b> — {n}-mavsum\n"
    "Tugashiga {days} kun qoldi.\n\n"
    "⭐ Daraja: <b>{level}</b>/{max_level} · XP: {xp}\n"
    "{next_line}\n\n"
    "🆓 <b>Bepul yo'lak</b> — keyingi mukofot: {next_free}\n"
    "💎 <b>Premium yo'lak</b> {premium_state} — keyingi mukofot: {next_premium}\n\n"
    "XP: g'alaba {xp_win}, mag'lubiyat {xp_lose}, kunning birinchi o'yini +{xp_bonus} "
    "(kamida {min_players} kishilik o'yinlarda)."
)
SEASON_NEXT_LEVEL = "Keyingi darajagacha: {xp} XP"
SEASON_MAX_REACHED = "🏁 Maksimal darajaga yetdingiz!"
SEASON_PREMIUM_ON = "✅"
SEASON_PREMIUM_OFF = "🔒"
SEASON_NO_MORE_REWARDS = "—"
SEASON_REWARD_AT = "{level}-daraja: {rewards}"
SEASON_PREMIUM_BUTTON = "💎 Premium yo'lak — {price}💎"
SEASON_PREMIUM_BOUGHT = "✅ Premium yo'lak ochildi! Yetgan darajalaringiz mukofoti ham berildi."
SEASON_ALREADY_PREMIUM = "Sizda bu mavsum premium yo'lagi allaqachon bor."
SEASON_NOT_ACTIVE = "Hozir faol mavsum yo'q."
SEASON_REMINDER = "⏳ {name} mavsumi tugashiga {days} kun qoldi! Darajangiz: {level}. /mavsum"
SEASON_XP_LINE = "🎟 +{xp} XP · {level}-daraja"
SEASON_REWARDS_GOT = "🎁 Mavsum mukofotlari: {rewards}"
REWARD_DOLLAR = "{amount}💵"
REWARD_COIN = "{amount}🪙"
REWARD_DIAMOND = "{amount}💎"
REWARD_ITEM = "{count} ta {emoji} {name}"

# ---------- 7-bosqich: 🎁 Kunlik bonus ----------
BONUS_CLAIMED = (
    "🎁 <b>Kunlik bonus — {day}-kun:</b> +{dollars}💵{extra}{vip}\n"
    "Ertaga {next_day}-kun: {next_dollars}. Kun o'tkazib yuborilsa, hisob 1-kundan boshlanadi."
)
BONUS_EXTRA_DIAMONDS = " va +{diamonds}💎"
BONUS_VIP_NOTE = " (👑 VIP: 💵 ×2)"
BONUS_ALREADY = "🎁 Bugungi bonusni oldingiz ({day}-kun). Ertaga yana keling!"
MENU_BONUS = "🎁 Kunlik bonus"

# ---------- 7-bosqich: 👑 VIP ----------
VIP_PERKS = (
    "• ismingiz yonida 👑 (ro'yxat, o'lim e'loni, o'yin yakuni, /top)\n"
    "• kunlik bonusda 💵 ×2 (/bonus)\n"
    "• har dushanba 1 ta bepul 🛡 Himoya\n"
    "• /profile da oxirgi 20 o'yin tarixi"
)
VIP_TEXT_ACTIVE = (
    "👑 <b>VIP faol</b> — {date} gacha.\n\n{perks}\n\n"
    "Telegram obunani har 30 kunda o'zi yangilaydi. Bekor qilish: Telegram sozlamalari → Yulduzlar (Stars) → obunalar."
)
VIP_TEXT_INACTIVE = "👑 <b>VIP obuna</b> — {price}⭐ / 30 kun (Telegram o'zi yangilaydi).\n\n{perks}"
VIP_BUY_BUTTON = "👑 VIP — {price}⭐ / 30 kun"
VIP_INVOICE_TITLE = "👑 VIP obuna"
VIP_INVOICE_DESCRIPTION = "30 kunlik VIP: 👑 belgisi, kunlik bonus ×2, har dushanba 🛡 Himoya, o'yinlar tarixi."
VIP_LINK_ERROR = "VIP havolasini yaratib bo'lmadi, keyinroq urinib ko'ring."
VIP_ACTIVATED = "👑 VIP faollashtirildi! Amal qilish muddati: {date}."
VIP_RENEWED = "👑 VIP obunangiz yangilandi — {date} gacha."
VIP_PAYMENT_ADMIN = "👑 VIP to'lovi: {name} (id=<code>{user_id}</code>) — {stars}⭐\nID: <code>{charge_id}</code>"
VIP_WEEKLY_GIFT = "👑 VIP sovg'asi: {count} ta {emoji} {name} sumkangizga qo'shildi."
VIP_BADGE = " 👑"
MENU_VIP = "👑 VIP"
PROFILE_VIP_LINE = "👑 VIP: {date} gacha"
PROFILE_HISTORY_HEADER = "🕘 <b>Oxirgi o'yinlar:</b>"
PROFILE_HISTORY_LINE = "{date} — {role} — {result}"
PROFILE_HISTORY_WIN = "✅ g'alaba"
PROFILE_HISTORY_LOSS = "❌ mag'lubiyat"
PROFILE_HISTORY_AFK = "💤 AFK"
PROFILE_HISTORY_EMPTY = "🕘 Hali o'yinlar tarixi yo'q."

# ---------- 7-bosqich: ✨ birinchi xarid, 🌱 to'plam, 💝 sovg'a ----------
FIRST_PURCHASE_BONUS = "✨ Birinchi xarid bonusi: olmos ×{multiplier}!"
SHOP_FIRST_PURCHASE_NOTE = "✨ Birinchi Stars xaridingizda olmos ×{multiplier} beriladi!"
SHOP_STARTER_INFO = "🌱 <b>Boshlang'ich to'plam</b> (1 marta): {diamonds}💎, {items} va «{title}» unvoni."
SHOP_STARTER_BUTTON = "🌱 Boshlang'ich to'plam — {price}⭐"
STARTER_INVOICE_TITLE = "🌱 Boshlang'ich to'plam"
STARTER_INVOICE_DESCRIPTION = "{diamonds}💎, {items} va «{title}» unvoni. Har akkauntga 1 marta."
STARTER_PACK_BOUGHT = "🌱 Boshlang'ich to'plam berildi! To'lov ID: <code>{charge_id}</code>"
STARTER_NOT_AVAILABLE = "Boshlang'ich to'plam faqat hali hech narsa sotib olmaganlar uchun."
SHOP_GIFT_BUTTON = "🎁 Sovg'a qilish"
GIFT_ASK_RECIPIENT = (
    "🎁 Kimga sovg'a qilasiz? Qabul qiluvchining ID raqami yoki @username'ini yuboring.\n"
    "(U botga /start bosgan bo'lishi kerak.)"
)
GIFT_RECIPIENT_NOT_FOUND = "Bunday foydalanuvchi topilmadi — u botga hali /start bosmagan bo'lishi mumkin."
MENU_INVITE = "🔗 Do'st taklif"
GIFT_PRIVATE_ONLY = "🎁 Sovg'ani bot bilan shaxsiy chatda qiling: /shop"
GIFT_SELF = "O'zingizga sovg'a qila olmaysiz — o'zingiz uchun /shop dan sotib oling."
GIFT_CHOOSE_PACKAGE = "🎁 <b>{name}</b> uchun olmos paketini tanlang:"
GIFT_INVOICE_TITLE = "🎁 {diamonds}💎 sovg'a"
GIFT_INVOICE_DESCRIPTION = "{name} uchun {diamonds}💎 sovg'a. To'lovdan so'ng unga darhol yetkaziladi."
GIFT_SENT = "✅ {name} ga {diamonds}💎 sovg'a qilindi! To'lov ID: <code>{charge_id}</code>"
GIFT_RECEIVED = "🎁 <b>{name}</b> sizga {diamonds}💎 sovg'a qildi!"

# ---------- 🔗 Do'st taklifi va 🤝 guruh egasi ulushi ----------
REFERRAL_TEXT = (
    "🔗 <b>Do'stlaringizni taklif qiling</b>\n\n"
    "Havolangiz: {link}\n\n"
    "Do'stingiz shu havola orqali botga kirib, birinchi Stars xaridini qilsa, sizga +{diamonds}💎 beriladi.\n"
    "Taklif qilinganlar: {count} · ulardan xarid qilganlar: {rewarded}"
)
REFERRAL_REWARD = "🔗 Siz taklif qilgan do'st birinchi xaridini qildi — +{diamonds}💎!"
OWNER_SHARE_PAID = "🤝 Guruhingizdagi o'yinchilar xaridlaridan ulush: +{diamonds}💎 hisobingizga tushdi."

# ---------- 🏰 Guruh premiumi ----------
GROUP_PREMIUM_PERKS = (
    "• har dushanba 10:00 da guruhning haftalik statistikasi\n"
    "• shu guruhda {games}+ o'yin o'ynaganlarga «🏰 {name}» unvoni\n"
    "• /turnir — admin o'z olmosidan sovrin qo'yadigan turnirlar"
)
GROUP_PREMIUM_ACTIVE = "🏰 <b>Guruh premiumi faol</b> — {date} gacha.\n\n{perks}"
GROUP_PREMIUM_INACTIVE = (
    "🏰 <b>Guruh premiumi</b> — {price}⭐ / 30 kun (Telegram har oy o'zi yangilaydi, guruh admini to'laydi).\n\n{perks}"
)
GROUP_PREMIUM_LINK_SENT = "🏰 To'lov havolasi shaxsiy chatingizga yuborildi."
GROUP_PREMIUM_BUTTON = "🏰 Guruh premiumi — {price}⭐ / 30 kun"
GROUP_PREMIUM_INVOICE_TITLE = "🏰 Guruh premiumi"
GROUP_PREMIUM_INVOICE_DESCRIPTION = "«{chat}» guruhi uchun 30 kunlik premium: haftalik statistika, guruh unvoni, turnirlar."
GROUP_PREMIUM_ACTIVATED = "🏰 Guruh premiumi faollashtirildi — {date} gacha."
GROUP_PREMIUM_GROUP_NOTICE = "🏰 Bu guruhda premium yoqildi ({date} gacha)! Haftalik statistika, guruh unvoni va /turnir ochildi."
GROUP_PREMIUM_REQUIRED = "Bu imkoniyat faqat guruh premiumi faol bo'lganda ishlaydi: /premium"
ADMIN_ONLY = "Buni faqat guruh adminlari qila oladi."
GROUP_ONLY = "Bu buyruq faqat guruhda ishlaydi."
START_BOT_PRIVATE = "Avval botga shaxsiy chatda /start bosing: https://t.me/{bot}"
GROUP_STATS_TEXT = (
    "📊 <b>O'tgan hafta statistikasi</b> ({since} — {until})\n\n"
    "🎮 Jami o'yinlar: {games}\n"
    "🏘 Tinch aholi g'alabalari: {town}% · 🔪 Mafiya g'alabalari: {mafia}%\n\n"
    "🏆 <b>TOP-{top_n} (ball bo'yicha):</b>\n{top}\n\n"
    "🔥 <b>Eng faol o'yinchilar:</b>\n{active}"
)
GROUP_STATS_TOP_LINE = "{place}. {name} — {points} ball"
GROUP_STATS_ACTIVE_LINE = "{place}. {name} — {games} o'yin"
GROUP_TITLE_GRANTED = "🏰 Siz «{chat}» guruhida {games} ta o'yin o'ynadingiz — «{title}» unvoni berildi! /sumka → 🎨 Kosmetika"

# ---------- 🏆 Turnir ----------
TOURNAMENT_CHOOSE_GAMES = "🏆 <b>Yangi turnir</b>\nNechta o'yin bo'lsin? (kamida {min_players} kishilik o'yinlar hisoblanadi)"
TOURNAMENT_GAMES_BUTTON = "{n} ta o'yin"
TOURNAMENT_CHOOSE_PRIZE = "🏆 {games} ta o'yin. Sovrin qancha bo'lsin? (sizning hisobingizdan yechiladi)"
TOURNAMENT_PRIZE_BUTTON = "{prize}💎"
TOURNAMENT_NOT_ENOUGH = "Olmosingiz yetarli emas (kerak: {prize}💎)."
TOURNAMENT_ALREADY = "Bu guruhda allaqachon faol turnir bor."
TOURNAMENT_STARTED = (
    "🏆 <b>Turnir e'lon qilindi!</b>\n"
    "Keyingi {games} ta o'yin (kamida {min_players} kishilik) turnir o'yini hisoblanadi. Sovrin: {prize}💎 "
    "(1-o'rin {p1}%, 2-o'rin {p2}%, 3-o'rin {p3}%).\n"
    "Ochko: g'alaba {win}, oxirigacha tirik qolish +{alive}, o'yindagi eng yaxshi {mvp_top} MVP +{mvp}.\n"
    "Kirish bepul. Turnir {hours} soat ichida tugamasa, joriy natijalar bo'yicha yakunlanadi."
)
TOURNAMENT_STATUS = "🏆 <b>Faol turnir</b>: {played}/{games} o'yin, sovrin {prize}💎\n\n{table}"
TOURNAMENT_CANCEL_BUTTON = "❌ Turnirni bekor qilish"
TOURNAMENT_CANCELLED = "🏆 Turnir bekor qilindi, {prize}💎 adminga qaytarildi."
TOURNAMENT_CANNOT_CANCEL = "Turnirni faqat birinchi o'yini boshlanguncha bekor qilish mumkin."
TOURNAMENT_TABLE_HEADER = "🏆 <b>Turnir jadvali</b> ({played}/{games}):"
TOURNAMENT_TABLE_LINE = "{place}. {name} — {points} ochko ({wins} g'alaba)"
TOURNAMENT_TABLE_EMPTY = "hali natija yo'q"
TOURNAMENT_FINISHED = "🏆 <b>Turnir yakunlandi!</b>\n{winners}"
TOURNAMENT_WINNER_LINE = "{place}-o'rin: {name} — +{prize}💎"
TOURNAMENT_NO_WINNERS = "Qatnashchilar bo'lmadi — sovrin adminga qaytarildi."
TOURNAMENT_PRIZE_PRIVATE = "🏆 Turnirda {place}-o'rin! +{prize}💎 hisobingizga tushdi."

# ---------- /sozlamalar: guruh nomi va ulush oluvchi ----------
SETTINGS_BTN_GROUP_NAME = "🏰 Guruh unvoni nomi: {name}"
SETTINGS_ASK_GROUP_NAME = "🏰 Guruh unvoni uchun qisqa nomni yozing ({max} belgigacha). Bu xabarga javob (reply) qiling."
SETTINGS_GROUP_NAME_SAVED = "✅ Guruh unvoni: «🏰 {name}»."
SETTINGS_GROUP_NAME_DEFAULT = "guruh nomi"
SETTINGS_BTN_SHARE = "🤝 Ulush oluvchi: {name}"
SETTINGS_SHARE_TITLE = "🤝 <b>Guruh egasi ulushi</b>\nO'yinchilar Stars xaridining {percent}% i shu kishiga yig'iladi. Faqat guruh yaratuvchisi o'zgartira oladi."
SETTINGS_SHARE_CREATOR_ONLY = "Ulush oluvchini faqat guruh yaratuvchisi o'zgartira oladi."
SETTINGS_SHARE_SET = "✅ Ulush oluvchi: {name}"
SETTINGS_SHARE_CREATOR = "guruh yaratuvchisi"

# ---------- 📒 /hisobot — kirim-chiqim (faqat bot egasi) ----------
REPORT_TITLE = "📒 <b>Kirim-chiqim hisoboti</b> — {period}"
REPORT_PERIODS = {"today": "Bugun", "week": "7 kun", "month": "30 kun", "all": "Hammasi"}
REPORT_KIND_NAMES = {
    "diamonds": "💎 Olmos paketlari",
    "starter": "🌱 Boshlang'ich to'plam",
    "gift": "🎁 Sovg'a (Stars)",
    "vip": "👑 VIP",
    "group_premium": "🏰 Guruh premiumi",
}
REPORT_NONE = "— yo'q"
REPORT_STARS_HEADER = "💰 <b>Sotuvlar — Telegram Stars</b>"
REPORT_STARS_LINE = "{name}: {n} ta · {stars}⭐ · {diamonds}💎 berildi"
REPORT_REFUNDED_LINE = "↩️ Qaytarilgan: {n} ta · {stars}⭐ · {diamonds}💎"
REPORT_STARS_TOTAL = "Jami tushum: <b>{stars}⭐</b>"
REPORT_CARD_HEADER = "💳 <b>Sotuvlar — karta orqali</b>"
REPORT_CARD_APPROVED = "✅ Tasdiqlangan: {n} ta · {som} so'm · {diamonds}💎"
REPORT_CARD_OTHER = "❌ Rad etilgan: {rejected} · ⏳ Kutilmoqda: {pending}"
REPORT_TRANSFERS_HEADER = "🎁 <b>O'yinchilar bir-biriga yuborgani</b> (/send, /sendgem)"
REPORT_TRANSFER_LINE = "{n} ta o'tkazma · {amount}"
REPORT_ADMINS_HEADER = "🛠 <b>Adminlar bergani</b>"
REPORT_ADMIN_LINE = "{name} (<code>{admin_id}</code>): {parts}"
ADMIN_ACTION_SHORT = {
    "addcash": "+{amount} ({n} marta)",
    "addgem": "+{amount} ({n} marta)",
    "addcoin": "+{amount} ({n} marta)",
    "card_approve": "karta ✅ {amount} ({n} ta)",
    "card_reject": "karta ❌ {n} ta",
    "refund": "↩️ qaytarish {amount} ({n} ta)",
}
ADMIN_ACTION_NAMES = {
    "addcash": "+{amount}{emoji} berdi",
    "addgem": "+{amount}{emoji} berdi",
    "addcoin": "+{amount}{emoji} berdi",
    "card_approve": "karta to'lovini tasdiqladi: {amount}{emoji} {note}",
    "card_reject": "karta to'lovini rad etdi: {amount}{emoji} {note}",
    "refund": "Stars to'lovini qaytardi: {amount}{emoji} {note}",
}
REPORT_MARKET_HEADER = "🛍 <b>Bozor savdolari</b>"
REPORT_MARKET_LINE = "{n} ta: {sold} sotildi ← {paid} to'landi"
REPORT_REWARDS_HEADER = "🤖 <b>Bot bergan mukofotlar</b>"
REPORT_REFERRAL_LINE = "🔗 Taklif mukofoti: {n} ta · {diamonds}💎"
REPORT_SHARE_LINE = "🤝 Guruh egalari ulushi: {diamonds}💎"
REPORT_TOURNAMENT_LINE = "🏆 Tugagan turnirlar: {n} ta · {diamonds}💎 sovrin (admin hisobidan) · faol: {active}"
REPORT_RECENT_HEADER = "🕘 <b>Oxirgi harakatlar</b>"
REPORT_REFUND_MARK = " ↩️ qaytarilgan"
REPORT_RECENT = {
    "stars": "{t} · ⭐ {a}{target}: {name} — {diamonds}💎, {stars}⭐{mark}",
    "card": "{t} · 💳 {b}: {diamonds}💎, {som} so'm {mark} ({a})",
    "transfer": "{t} · 🎁 {a} → {b}: {amount}",
    "admin": "{t} · 🛠 {a} → {b}: {action}",
    "market": "{t} · 🛍 {a} → {b}: {sold} ({paid})",
}
REPORT_FOOTER = (
    "ℹ️ Adminlar bergani va bozorda kim sotib olgani shu yangilanishdan boshlab yoziladi; "
    "Stars, karta va o'tkazmalar — boshidan."
)
OWNER_ADMIN_ACTION = "🛠 Admin <b>{admin}</b> (<code>{admin_id}</code>) → <b>{target}</b> (<code>{target_id}</code>): {action}"

# ---------- 🏘 Bot ishlayotgan guruhlar (faqat bot egasi) ----------
PROFILE_GROUPS_BUTTON = "🏘 Bot ishlayotgan guruhlar"
GROUPS_HEADER = "🏘 <b>Bot ishlayotgan guruhlar</b>\nFaol: {active} ta · Bot chiqarilgan: {left} ta"
GROUPS_LINE = "{n}. {status} {title}\n     🎲 {games} ta o'yin · oxirgisi: {last}"
GROUPS_NEVER = "hali o'ynalmagan"
GROUPS_EMPTY = "🏘 Bot hali birorta guruhda ishlamagan."
GROUPS_LEGEND = "✅ bot guruhda · 🎮 hozir o'yin ketyapti · ❌ bot guruhdan chiqarilgan"
GROUPS_MORE = "… va yana {count} ta guruh."
