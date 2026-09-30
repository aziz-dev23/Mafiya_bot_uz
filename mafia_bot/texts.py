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
    "/send — boshqa foydalanuvchiga Dollar yuborish\n"
    "/sendgem — boshqa foydalanuvchiga Olmos yuborish\n"
    "/geroy — Geroyni sotib olish / darajasini oshirish\n"
    "/rollar — barcha rollar tavsifi\n"
    "/sozlamalar — guruh sozlamalari (faqat guruh adminlari)\n\n"
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
    "mirror": "Mafiya o'qini qaytaradi — o'rningizga tasodifiy Mafiya a'zosi halok bo'ladi. "
    "Geroy zarbasini ham qaytaradi (10+ darajali Geroydan tashqari).",
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
DAWN_ANNOUNCEMENT = "🌄 <b>Tong otmoqda...</b>\n⏳ Kun boshlanishiga {seconds} soniya qoldi."
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
EXCHANGE_NOT_ENOUGH_COINS = "Coin'ingiz yetarli emas."
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
HISTORY_DAWN = "\n🌄 <b>Tong {n}</b>"
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
    "dawn": "🌄 Tong",
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
