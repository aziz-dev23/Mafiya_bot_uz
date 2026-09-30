# MAFIYA BOT — TO'LIQ TEXNIK TOPSHIRIQ (TZ)

> Telegram mafiya o'yini boti uchun barcha kerakli funksiyalar ro'yxati.
> **Yangilangan: 30.09.2026** — kodning hozirgi holatiga ko'ra (GitHub: `aziz-dev23/Mafiya_bot_uz`, commit `9cca453`).
> Batafsil qo'llanma: `Mafiya_bot_qollanma.pdf`.

**Belgilar:** ✅ bajarildi · 🔄 boshqacha qarorga ko'ra o'zgartirildi · ❌ hali qilinmagan

---

## 0. QISQACHA HOLAT

| Bo'lim | Holat |
|---|---|
| 1. Deploy | ✅ Bot serverda ishlaydi (polling) |
| 2. Rollar | ✅ 19 ta rol (TZ dagi 10 ta + 9 ta yangi), 4–40 o'yinchi |
| 3. Buyumlar | ✅ 9 ta buyum o'yinda ishlaydi, faqat natijani o'zgartirganda sarflanadi · ❌ 5 ta buyum qilinmagan (pastda) |
| 4. Valyuta va transfer | ✅ 3 valyuta, Telegram Stars (+ ✨ ×2, 🌱 to'plam, 🎁 sovg'a, 🔗 taklif, 🤝 ulush), almashtirish, o'tkazmalar · 🔄 kurslar o'zgargan |
| 5. PRO obuna | 🔄 👑 VIP (Stars obunasi, 100⭐/30 kun) sifatida qilindi · ❌ nickname, chiroyli profil |
| 6. Menyu | ✅ asosiy qismi + bonus, VIP, taklif, 🎁 sovg'a · ❌ klan, WebApp, auksion bo'limlari |
| 7. Profil | ✅ VIP qatori, oxirgi 20 o'yin, ramka, unvon · ❌ "Keyingi o'yindagi rol", klan |
| 8. Klan tizimi | ❌ qilinmagan |
| 9. Statistika va reyting | ✅ + 🏰 premium guruhlar uchun haftalik statistika · ❌ guruhlar reytingi (Top guruhlar) |
| 10. O'yin oxiri | ✅ |
| Qo'shimcha (TZ da yo'q edi) | ✅ guruh sozlamalari, 3 til, Telegram limitlari navbati, chat qulfi, AFK, so'nggi so'z, o'yin tarixi, kunlik bonus, 🎨 kosmetika, 🎟 mavsum chiptasi, 🏰 guruh premiumi, 🏆 turnir, 📒 egasi uchun kirim-chiqim hisoboti, 190 ta test |

---

## 1. DEPLOY ✅

- [x] BotFather orqali bot yaratish → API TOKEN olish
- [x] `.env` faylga `BOT_TOKEN` yozish, `.gitignore` ga qo'shish
- [x] Polling (webhook shart emas)
- [x] Server: `/opt/mafia_bot`, systemd xizmati `mafia-bot` (yangilash: baza zaxirasi → `git pull` → `systemctl restart mafia-bot`)
- [x] `pip install -r requirements.txt`
- [x] Bot doim ishlab turadi
- [x] `/start` bilan tekshirildi
- [x] **Qo'shimcha:** baza migratsiyalari avtomatik, har bir migratsiyadan oldin `mafia.db.backup-...` zaxirasi olinadi
- [x] **Adminlar:** `ADMIN_IDS=8608722981,6003509043` · bot egasi `OWNER_IDS=8608722981`

---

## 2. ROLLAR TIZIMI ✅

Rollar o'yinchilar soniga qarab avtomatik tarqatiladi. Mafiya ~25% (har doim bitta Don), kamida 20% oddiy tinch aholi. Qavs ichida — rol paydo bo'ladigan minimal o'yinchi soni.

| Rol | Tomon | Vazifasi | Holat |
|---|---|---|---|
| 🔪 Mafiya | Mafiya | Kechasi Don bilan birga bitta odamni o'ldiradi (ovoz berish, ovozlar jonli ko'rinadi) | ✅ |
| 🤵🏻 Don | Mafiya | Mafiya boshlig'i; ovozlar teng bo'lsa uning tanlovi hal qiladi; o'yinda 1 marta Komissarni aniqlaydi | ✅ |
| 🕵️ Komissar (4) | Tinch | Kechasi bir kishini tekshiradi (mafiya / mafiya emas) | 🔄 faqat tekshiradi, otmaydi |
| 🔪 Qotil (7) | Mustaqil | Har kecha alohida o'ldiradi; yolg'iz yoki 1 ga 1 qolsa yutadi | ✅ |
| 🥷 Yollanma qotil (8) | Mafiya | Alohida o'ldiradi; maxfiy buyurtmani bajarsa +2000💵 | 🔄 Mafiya jamoasiga o'tkazildi |
| 💉 Doktor (6; 22+ da ikkita) | Tinch | Kechasi bir kishini Mafiya va zahardan himoya qiladi | 🔄 Kezuvchidan alohida rol |
| 💊 Kezuvchi (6) | Tinch | O'yinda 2 marta zahar beradi → keyingi kechasi o'ladi | 🔄 Doktor emas, alohida rol |
| 🚶 Daydi (7) | Tinch | Kimningdir oldiga boradi; u o'ldirilsa, qotilning ismini biladi | ✅ |
| ⛏ Konchi (8) | Tinch | Har kecha qaziydi: Coin yoki buyum topadi | 🔄 "sirpanib o'lish" o'rniga qazilma |
| 👨‍💼 Advokat (9) | Mafiya | Komissar tekshiruvidan himoya qiladi | ✅ yangi |
| 🧞‍♂️ Afsungar (10) | Mustaqil | O'ldirilsa bitta mafiyani olib ketadi / haydalsa o'ch oladi | ✅ yangi |
| 🐺 Bo'ri (11) | Mustaqil | Mafiya hujum qilsa, Mafiyaga aylanadi | ✅ yangi |
| 👮 Serjant (20) | Tinch | Komissarni biladi, natijalarini ko'radi, u o'lsa o'rnini oladi | ✅ yangi |
| 📰 Jurnalist (25) | Tinch | Ikki kishi bir jamoadami — biladi | ✅ yangi |
| 🛡 Tansoqchi (27) | Tinch | Qo'riqlagan odamining o'rniga o'ladi | ✅ yangi |
| 🕶 Josus (28) | Mafiya | Har kecha bitta o'yinchining rolini biladi | ✅ yangi |
| 👨‍⚖️ Sudya (30) | Tinch | O'yinda 1 marta kunduzgi haydashni bekor qiladi | ✅ yangi |
| 💘 Kupidon (32) | Tinch | Ikki kishini oshiq qiladi (biri o'lsa, ikkinchisi ham) | ✅ yangi |
| 👤 Tinch aholi | Tinch | Ovoz berish orqali mafiyani topadi | ✅ |
| 🦸 Geroy | — | Rol emas, profil buyumi: tunda 1 marta otish (§3) | 🔄 buyumga aylantirildi, tong bosqichi olib tashlandi |

- [x] Har bir rol uchun kecha/kunduz harakati aniq yozilgan (rol xabarida tavsif + maslahat, `/rollar`)
- [x] Tungi hisob-kitob tartibi aniq belgilangan va hujjatlashtirilgan
- [x] Adminlar `/sozlamalar` da rollarni yoqib/o'chira oladi (Don, Mafiya, Komissar majburiy)

**G'alaba:** tinch aholi — Mafiya jamoasi ham, Qotil ham o'lganda; Mafiya — tiriklar soniga teng yoki ko'p bo'lganda; Qotil — yolg'iz yoki 1 ga 1 qolganda. G'olib jamoaning o'lgan a'zolari ham g'olib hisoblanadi.

---

## 3. INVENTAR — BUYUMLAR AMALDA ISHLASHI KERAK

**Umumiy qoida:** bitta o'yinda har bir buyum turidan ko'pi bilan 1 dona ishlaydi. Buyum **faqat natijani o'zgartirganda** sarflanadi (masalan, Doktor allaqachon qutqargan bo'lsa, 🛡 sarflanmaydi). Hujumchi nishoni omon qolsa, sababi aytilmaydi: "🎯 Nishon omon qoldi". Paketlar, mavsum va VIP faqat 💵 buyumlarni (🛡, 💊, 🎭) beradi; 💎 buyumlar va Geroy hech qanday mukofotda berilmaydi.

| Buyum | Narx | Vazifasi | Status |
|---|---|---|---|
| 🛡 Himoya | 100 💵 | Mafiya hujumidan bir marta saqlaydi (Miltiqqa qarshi ishlamaydi) | ✅ |
| 📁 Soxta hujjat | 190 💵 | Komissar tekshirsa "mafiya emas" chiqadi | ✅ |
| ⚖️ Ovozdan himoya | 1 💎 | Kunduzi osishdan bir marta qutqaradi | ✅ |
| 🔫 Miltiq | 1 💎 | Mafiya/Don — tunda qo'lda yoqiladi, 🛡 Himoyani teshadi | 🔄 Komissar uchun emas; faqat himoyani teshganda sarflanadi |
| 💊 Doridan himoya | 100 💵 | Kezuvchi dorisidan himoya | ✅ |
| 🎭 Maska | 100 💵 | Siz o'ldirgan odamning oldiga borgan Daydi sizni taniy olmaydi | ✅ |
| ⛑ Qotildan himoya | 2 💎 | Qotil va Yollanma qotildan himoya | 🔄 cheksiz emas: har himoyada sarflanadi (eski egalariga ×10 dona berildi) |
| 🔰 Geroydan himoya | 5 💎 | Geroy hujumidan omon qolish (10+ darajadan tashqari) | ✅ |
| 🔮 Sehrli Oyna | **20 💎** | Mafiya o'qi sizga ovoz bergan Don/Mafiyalardan biriga qaytadi; Geroy zarbasi Geroyning o'ziga qaytadi (qaytgan o'qqa himoya ishlamaydi) | ✅ 🔄 narxi 1000 💎 → 20 💎 |
| 🦸 Geroy | **249 💎** (+100 💎 har daraja) | Mafiya/Don/Komissar bo'lganda tunda 1 marta otish (Doktor himoya qilmaydi); 10-darajadan har qanday himoyani teshadi; ism yonida 🦸N | ✅ 🔄 profil buyumi, `/geroy` |
| 🪤 Sirpanishdan himoya | 300 💵 | Konchi sirpanishidan saqlash | ❌ kerak emas — Konchi endi sirpanmaydi |
| 🧪 Zahar (buyum) | 1000 💎 | Kunduzi yashirincha zaharlash | ❌ qilinmagan (zahar hozir faqat Kezuvchi rolida) |
| 🔄 Profil almashish | 5 💎 | Profilni almashtirish | ❌ qilinmagan |
| 🌿 Verbena giyohi | — | (§6 va §7 da tilga olingan, vazifasi yozilmagan) | ❌ vazifasini aniqlash kerak |
| 🔰 Temir qalqon | — | (§6 va §7 da tilga olingan, vazifasi yozilmagan) | ❌ vazifasini aniqlash kerak |

### Har bir buyum uchun kerak bo'ladigan logika:
1. [x] **Sotib olish** — `/dokon` dan 1/3/5/10 dona, balansdan atomik yechiladi
2. [x] **Yoqish/o'chirish (ON/OFF)** — `/sumka` yoki `/profile` da
3. [x] **O'yinda ishlash** — tegishli vaqtda avtomatik
4. [x] **Sarflash** — ishlatilgandan keyin inventardan kamayadi
5. [x] **Xabar berish** — "Himoyangiz sizni saqlab qoldi! Qoldi: N dona" kabi + o'yin tarixida ko'rinadi; `/buyumlar` — barcha buyumlar tavsifi
6. [x] **Qo'shimcha:** guruh sozlamasida buyumlar/Geroyni o'chirish mumkin (yoki "Buyumsiz" rejim)

---

## 4. VALYUTA TIZIMI

Uch xil valyuta:
- [x] 💵 **Dollar** — o'yin oxirida beriladi, buyumlar uchun
- [x] 💎 **Olmos** — premium valyuta
- [x] 🪙 **Coin** — Konchi qazib topadi, "Kim o'ladi?" taxmini uchun beriladi 🔄 ("Overlord Coin" nomi ishlatilmagan)

### Olmos sotib olish 🔄 (TZ dagi dollar → olmos jadvali o'rniga)
Telegram qoidasiga ko'ra raqamli tovar **Telegram Stars** orqali sotiladi (birinchi turadi); karta orqali to'lov qo'shimcha, `CARD_PAYMENTS_ENABLED` bilan o'chiriladi.

| Paket | ⭐ Stars | 💳 Karta |
|---|---|---|
| 1 💎 | 5 ⭐ | 990 so'm |
| 5 💎 | 25 ⭐ | 4 950 so'm |
| 10 💎 | 50 ⭐ | 9 900 so'm |
| 30 💎 | 149 ⭐ | 29 500 so'm |
| 50 💎 | 247 ⭐ | 49 000 so'm |
| 799 💎 | 3 591 ⭐ | 711 000 so'm (−10%) |
| 899 💎 | 3 818 ⭐ | 756 000 so'm (−15%) |
| 999 💎 | 3 990 ⭐ | 790 000 so'm (−20%) |

- [x] Stars to'lovi avtomatik, bir to'lov ikki marta hisoblanmaydi, `/refund` bilan qaytarish, `/paysupport` `/support` `/terms`
- [x] Pul qaytarilsa, shu to'lov bilan berilgan hamma narsa (×2 bonus, buyumlar, unvon, VIP, taklif mukofoti, ulush, guruh premiumi) ham qaytarib olinadi (`payment_grants` jurnali)

### ⭐ Stars xaridlari qoidalari ✅ (faqat Stars uchun, karta uchun emas)
| Imkoniyat | Qoida |
|---|---|
| ✨ Birinchi xarid | Birinchi Stars olmos paketida olmos ×2 (avval karta bilan olganlarga ham) |
| 🌱 Boshlang'ich to'plam — 50⭐ | 10💎 + 3× 🛡 + «🌱 Yangi o'yinchi» unvoni; 1 marta; faqat hech narsa sotib olmaganlarga ko'rinadi (karta ham hisobga olinadi) |
| 🎁 Sovg'a | `/shop` → 🎁 → ID yoki @username → paket; ×2 yo'q; to'lovchining "birinchi xaridi" hisoblanmaydi, to'plamni yashirmaydi, taklif mukofotini bermaydi; qabul qiluvchi holati o'zgarmaydi |
| 🔗 Do'st taklifi (`/taklif`) | `?start=ref_<ID>` havola; yangi do'st birinchi Stars xaridini qilsa (sovg'a emas) — taklif qilganga +5💎 |
| 🤝 Guruh egasi ulushi | Xaridning bazaviy olmosidan 10% — o'yinchi oxirgi o'ynagan guruh egasiga (guruh yaratuvchisi yoki u `/sozlamalar` da tayinlagan admin); kasr bilan yig'iladi (0.5💎), butun 💎 bo'lganda tushadi; egasi /start bosmagan bo'lsa, bosganda to'lanadi; sovg'alar ham hisoblanadi; egasining o'z xaridi hisoblanmaydi |
- [x] Karta: buyurtma raqami + chek → admin tasdiqlaydi

### Almashtirish 🔄
- [x] 💎 → 💵: 1 💎 = 250 💵 (`/almashtir`)
- [x] 🪙 → 💵: 1 🪙 = 10 💵
- [ ] 💎 → 🪙 (TZ dagi "Overlord") — qilinmagan
- [ ] 💵 → 💎 (dollarga olmos sotib olish, TZ dagi jadval) — qilinmagan

### Transfer (pul yuborish) ✅
1. [x] Foydalanuvchi "Pul yuborish" bosadi (`/send`, `/sendgem`)
2. [x] Bot qabul qiluvchining **ID yoki username**ini so'raydi
3. [x] Shart: qabul qiluvchi botga `/start` bosgan bo'lishi kerak
4. [x] Miqdorni so'raydi
5. [x] Tasdiqlash → o'tkazish (atomik, jurnalga yoziladi)
6. [x] Ikkala tomonga xabar
7. [x] **Qo'shimcha cheklov:** kamida 20 ta o'yin, kunlik limit 5000 💵 / 50 💎 (adminlarga cheklov yo'q)

> Olmos yuborish ham xuddi shu tarzda ishlaydi ✅

### Qo'shimcha (TZ da yo'q edi)
- [x] 🛍 Bozor (`/market`) — valyutalar savdosi, e'lonlarni faqat `SELLER_IDS` joylaydi
- [x] 🏆 Haftalik mukofot — har dushanba `/top7` dagi 1–3-o'ringa 10 / 5 / 3 💎, 1-o'ringa 1 haftaga «🏆 Hafta chempioni» unvoni
- [x] 🎁 Kunlik bonus (`/bonus`) — 7 kunlik zanjir: 20, 30, 40 … 80💵, 7-kuni +1💎; kun o'tkazilsa 1-kundan boshlanadi

---

## 5. PRO AKKAUNT → 👑 VIP ✅🔄

TZ dagi PRO o'rniga **👑 VIP** qilindi: Telegram Stars obunasi, **100⭐ / 30 kun**, Telegram har oy o'zi yangilaydi (`/vip`, menyuda 👑 VIP).

- [x] 👑 **VIP belgisi** — ism yonida (ro'yxat, o'lim e'loni, o'yin yakuni, `/top`)
- [x] 🎁 Kunlik bonusda 💵 ×2
- [x] 🛡 Har dushanba 1 ta bepul Himoya
- [x] 🕘 `/profile` da oxirgi 20 o'yin tarixi
- [x] Muddat avtomatik: obuna to'xtasa VIP o'chadi; pul qaytarilsa VIP ham bekor bo'ladi
- [x] 🚪 **O'yindan chiqish** — 🔄 hamma uchun ochiq: ro'yxatda "🚪 Chiqish" tugmasi
- [ ] 🏷 **Nickname** (`/nickname`) — qilinmagan
- [ ] ✨ **Chiroyli profil** — 🔄 o'rniga 🎨 kosmetika (unvon, o'lim uslubi, profil ramkasi) qilindi
- [ ] 💎/💵 ga PRO sotish (7/15/30 kun) — 🔄 Stars obunasi bilan almashtirildi

### 🎨 Kosmetika ✅ (TZ da yo'q edi)
O'yinga ta'sir qilmaydi, doimiy; har turdan bittasi faol. `/dokon` → 🎨 (sotib olish), `/sumka` → 🎨 (tanlash).

| Tur | Narsalar |
|---|---|
| 🏷 Unvon | 🌙 Tun qo'riqchisi 150🪙 · 🗣 Notiq 3000💵 · 🎩 Qari tulki, 🦉 Boyo'g'li 15💎 · 🧊 Sovuqqon, 🃏 Hiylakor, 🦅 Burgut ko'z 30💎 · 🌑 Soya, 🐉 Afsonaviy 60💎 · sotilmaydi: 🌱 Yangi o'yinchi, 🏆 Hafta chempioni, 🏰 guruh unvoni, mavsumiy |
| 💀 O'lim uslubi | 🌹 Atirgul, 🎬 Parda 25💎 · 👻 Arvoh, ⚡ Chaqmoq 40💎 |
| 🖼 Profil ramkasi | ✨ Yulduzli 20💎 · ❄️ Muzli 30💎 · 🔥 Olovli 50💎 |

### 🎟 Mavsum chiptasi ✅ (`/mavsum`)
- Har oy yangi mavsum (1-mavsum 🍂 Kuz — noyabr 2026), 30 daraja
- XP (kamida 6 kishilik o'yinlarda): g'alaba 3, mag'lubiyat 1, kunning birinchi o'yini +2
- 🆓 Bepul yo'lak: 100💵 / 10🪙 navbatma-navbat, 10/20/30-darajada 🛡
- 💎 Premium yo'lak (50💎): jami 60💎, 🛡/💊/🎭, 20🪙, mavsumiy unvon (12), o'lim uslubi (22), ramka (30)
- Tugashiga 3 kun qolganda eslatma

---

## 6. MENYU TUZILISHI (inline keyboard, 2 ustunli)

### Hozirgi bosh menyu (`/start`) ✅
```
➕ Guruhingizga qo'shish          (kerakli admin huquqlarini ham so'raydi)
👤 Mening profilim   🛒 Do'kon
🛍 Bozor             💎 Olmos sotib olish   (ichida: 🌱 to'plam, 🎁 sovg'a)
💸 Pul yuborish      💎 Olmos yuborish
💱 Almashtirish      🔗 Do'st taklif
🎁 Kunlik bonus      👑 VIP
❓ Yordam            🌐 Til / Язык
```
- [x] Har bir ichki menyuda `⬅️ Orqaga` / `⬅️ Bosh menyu` tugmasi bor
- [x] Buyumlarni ON/OFF qilish — `/sumka` va profil ichida
- [x] O'yindagi nishon/ovoz tugmalari 2 ustunda, faqat tiriklar bilan

### TZ dagi, lekin hali qilinmagan bo'limlar ❌
- [x] ⭐ Pro Obuna → 👑 VIP · 🎲 Pro guruhlar → 🏰 guruh premiumi (`/premium`)
- [ ] 🏆 Top guruhlar
- [x] 🎁 Gift → olmos sovg'a qilish (`/shop` → 🎁) · 🥷 Mening geroyim — `/geroy` ✅
- [ ] 🏰 Mening klanim
- [ ] 🌐 Mafia WebApp, 📢 Yangiliklar (kanal linki)
- [ ] Do'kon ichida: 🎯 Auksion, 🥇 Oltin, 🗃 Sandiqlar, 🃏 Faol rol

---

## 7. PROFIL SAHIFASI

Hozirgi ko'rinish (`/profile`) ✅:
```
👤 Ism
🆔 ID: 6003509043

💵 Dollar: 1901
💎 Olmos: 125
🪙 Coin: 0

🏅 Ball — kunlik | haftalik | oylik | jami
🦸 Geroy: 3-daraja

🎒 Buyumlar: (9 ta buyum, soni bilan)

🎮 O'yinlar: 59 | 🏆 G'alabalar: 10
📊 Rollar bo'yicha: Doktor: 12 o'yin, 58% g'alaba ...
[buyumlarni ON/OFF qilish tugmalari]
```
- [x] Balanslar, buyumlar, o'yinlar, g'alabalar
- [x] 🆕 Rollar bo'yicha o'yinlar va g'alaba foizi
- [x] 👑 VIP holati (qachongacha) va oxirgi 20 o'yin tarixi (VIP'larga)
- [x] 🖼 Profil ramkasi va 🏷 unvon (kosmetika)
- [ ] 🏰 Klan qatori — klan bilan birga
- [ ] 🃏 "Keyingi o'yindagi rol" — ❌ qilinmagan (rolni oldindan tanlash / sotib olish; qoidasini aniqlash kerak)

---

## 8. KLAN TIZIMI ❌

Hali qilinmagan:
- [ ] Klan yaratish (nom + teg, masalan `[XURS]`)
- [ ] A'zolarni qo'shish / chiqarish
- [ ] Rollar: 👑 Boshliq (Don) → Yordamchi → A'zo
- [ ] Klan reytingi
- [ ] Klan xazinasi (umumiy balans)

---

## 9. STATISTIKA VA REYTING

- [x] 🎲 Jami o'yinlar
- [x] 🏆 G'alabalar
- [x] G'alaba foizi — rollar bo'yicha (`/profile`)
- [x] Reyting: `/top` (umumiy), `/top1` (kun), `/top7` (hafta), `/top30` (oy), Toshkent vaqti bilan; TOP-10 da bo'lmasangiz o'z o'rningiz ko'rinadi
- [x] MVP: 10+ kishilik o'yinda eng foydali 3 g'olibga +50 ball
- [x] 👑 VIP foydalanuvchilar `/top` da belgili ko'rinadi
- [x] 📊 Premium guruhlarga har dushanba 10:00 da haftalik statistika (§11)
- [ ] 🏆 Top guruhlar (guruhlar liderboardi)

---

## 10. O'YIN OXIRI ✅

Eski muammo (`Sizga 💵 5, -3 🎯 berildi!`) hal qilindi:
- [x] G'alaba/mag'lubiyat uchun alohida mukofot: Mafiya g'alabasi +40 💵, tinch g'alabasi +30 💵, mag'lubiyat +15 💵 (g'alaba doim ko'p); ball +10 / +3
- [x] Rol bo'yicha bonus: Komissar mafiyani topsa +200 💵, Yollanma buyurtma +2000 💵, Qotil yakka g'alabasi +5000 💵, tirik qolgan g'olibga +10 💵, MVP top-3 ga +50 ball
- [x] Xabarda aniq yoziladi: kim yutdi, har bir o'yinchi qanday rol edi, kim halok bo'ldi, o'yin davomiyligi
- [x] Har bir o'yinchiga shaxsiy xabar: roli, natijasi, 💵 va ball
- [x] Statistika avtomatik yangilanadi (umumiy + rollar bo'yicha)
- [x] 🆕 O'yin tarixi: har bir tun/kun bo'yicha kim nima qilgani
- [x] 🆕 Premium guruhda turnir bo'lsa, yakun xabariga turnirning TOP-5 jadvali qo'shiladi

---

## 11. TZ DA YO'Q EDI, LEKIN QO'SHILDI ✅

- **Guruh sozlamalari** (`/sozlamalar`, adminlar): vaqtlar, o'yinchilar soni, rollar, buyumlar/Geroy, rol e'loni, so'nggi so'z, ochiq/anonim ovoz, chat qulfi rejimi, Klassik/Tezkor/Buyumsiz rejim, har kuni avtomatik o'yin, guruh tili
- **Tillar:** o'zbekcha (lotin), o'zbekcha (kirill, avtomatik), ruscha — `/til`; guruh xabarlari guruh tilida, shaxsiy xabarlar har kimning o'z tilida
- **40 kishilik o'yinlar:** mafiya chati, jonli mafiya ovozi, dinamik vaqt, Telegram limitlari navbati (429 da qayta yuborish), e'lonlarni birlashtirish
- **Chat qulfi:** tunda guruh `setChatPermissions` bilan yopiladi, bot qayta ishga tushsa ruxsatlar tiklanadi
- **O'yinchilarga yordam:** ro'yxatga deep-link orqali qo'shilish va chiqish, rol maslahatlari, `/rollar`, 10 s oldin eslatma, AFK chiqarish, so'nggi so'z, o'liklar chati, "Bu tun kim o'ladi?" taxmini, ovozni o'zgartirish
- **Kunlik bonus, 🎨 kosmetika, 🎟 mavsum chiptasi** (§4, §5)
- **🏰 Guruh premiumi** (`/premium`, 300⭐ / 30 kun, Stars obunasi, admin to'laydi; faqat faol bo'lganda ishlaydi):
  - 📊 har dushanba 10:00 da o'tgan hafta statistikasi: TOP-10 (ball), eng faol 3 kishi, jami o'yinlar, tinch/mafiya g'alaba foizi; o'yin bo'lmasa yuborilmaydi
  - 🏰 shu guruhda 50 o'yin o'ynaganlarga «🏰 <nom>» unvoni (nom `/sozlamalar` da, 14 belgigacha); premium tugasa ko'rinmaydi, qayta yoqilsa qaytadi
  - 🏆 `/turnir` (adminlar): 3/5/10 o'yin, sovrin 10/20/50/100💎 admin hisobidan; ≥6 kishilik o'yinlar; ochko: g'alaba 3, tirik +1, MVP top-3 +2, AFK — 0; taqsimot 50/30/20, qoldiq adminga; teng bo'lsa g'alabalar, keyin tasodifiy; faqat 1-o'yingacha bekor qilinadi; 48 soatda tugamasa joriy natija bo'yicha
- **📒 Kirim-chiqim hisoboti** (`/hisobot`, faqat `OWNER_IDS`; davr: bugun / 7 kun / 30 kun / hammasi):
  - 💰 Stars sotuvlari turi bo'yicha (paket, 🌱 to'plam, 🎁 sovg'a, 👑 VIP, 🏰 premium): soni, ⭐ tushum, berilgan 💎, qaytarilganlar
  - 💳 karta orqali: tasdiqlangan (so'm, 💎), rad etilgan, kutilayotgan
  - 🎁 o'yinchilar bir-biriga yuborgan 💵/💎
  - 🛠 har bir admin bergani (`/addcash`, `/addgem`, `/addcoin`), ko'rib chiqqan karta to'lovlari, qaytargan Stars to'lovlari
  - 🛍 bozorda sotilganlar, 🤖 bot mukofotlari (taklif, guruh egasi ulushi, turnir), 🕘 oxirgi 15 ta harakat
  - boshqa admin harakat qilsa, egaga darhol xabar keladi
  - adminlar jurnali, bozor xaridori va karta tasdiqlovchisi 01.10.2026 dan yoziladi; Stars, karta va o'tkazmalar — boshidan
- **Sifat:** 190 ta avtomatik test, jumladan 4–40 kishilik to'liq o'yin simulyatsiyalari

---

## KEYINGI NAVBATDAGI ISHLAR

1. Yangi imkoniyatlarni jonli botda sinab ko'rish (Stars to'lovlari, VIP va guruh premiumi obunalari, turnir)
2. **Klan tizimi** (§8) va profildagi klan qatori
3. **Guruhlar reytingi** — Top guruhlar (§9); PRO dagi nickname (§5)
4. **Qolgan buyumlar** — Zahar, Profil almashish; Verbena va Temir qalqon vazifasini aniqlash (§3)
5. **"Keyingi o'yindagi rol"** — qoidasini aniqlash (§7)
6. **Valyuta:** 💎 → 🪙 va 💵 → 💎 almashtirish kerakmi — qaror qilish (§4)
7. **Menyu:** giftlar, WebApp, yangiliklar kanali, do'kon bo'limlari (auksion, sandiqlar) (§6)
8. `/terms` matnini va ruscha tarjimani ko'rib chiqish

---

## MA'LUMOTLAR BAZASI

Hozirgi jadvallar (SQLite, `mafia.db`):

- `users` — user_id, full_name, username, dollars, diamonds, coins, wins, games, lang
- `inventory` — user_id, item_key, count, enabled
- `hero` — user_id, level
- `points_log` — reyting ballari (vaqt bilan)
- `role_stats` — user_id, role, games, wins
- `transfers` — sender_id, recipient_id, currency, amount, created_at
- `star_payments` — charge_id, user_id, diamonds, stars, status, payer_id, kind (diamonds/starter/gift/vip/group_premium)
- `payment_grants` — to'lov bilan berilgan qo'shimcha narsalar (refund uchun)
- `diamond_orders` — karta orqali buyurtmalar
- `market_listings` — bozor e'lonlari
- `group_settings` — har bir guruhning sozlamalari (JSON)
- `weekly_rewards` — berilgan haftalik mukofotlar
- `chat_locks` — tunda yopilgan guruhlarning asl ruxsatlari
- `migrations` — bajarilgan migratsiyalar
- `cosmetics_owned`, `cosmetics_active`, `season_progress` — kosmetika va mavsum
- `daily_bonus`, `vip`, `vip_weekly_items` — kunlik bonus va VIP
- `game_results`, `game_log` — har bir o'yin va o'yinchi natijasi (tarix, guruh hisoblagichlari)
- `owner_share`, `group_owner`, `referrals` — ulush va takliflar
- `group_premium`, `group_weekly_stats`, `group_chats`, `tournaments`, `tournament_scores` — guruh premiumi va turnir
- `admin_log` — adminlar harakatlari (kim, kimga, nima, qancha); `market_listings.buyer_id/closed_at`, `diamond_orders.reviewed_by/reviewed_at` — hisobot uchun

> O'yin holati (games / game_players) bazada emas, xotirada saqlanadi — bot qayta ishga tushsa, ketayotgan o'yinlar tugaydi (guruh ruxsatlari tiklanadi).

Kelajakda kerak bo'ladi (klan va nickname uchun):
- `users.nickname`, `users.clan_id`
- `clans` — id, name, tag, owner_id, balance
- `clan_members` — clan_id, user_id, role
