# 🚀 AutoServis Finder — Ishga Tushirish Qo'llanmasi

## 📁 Loyiha strukturasi
```
autoservis_bot/
├── bot/
│   └── main.py          ← Telegram Bot
├── backend/
│   └── main.py          ← API Server
├── miniapp/
│   └── index.html       ← Foydalanuvchi ko'radigan ekran
└── requirements.txt     ← Python kutubxonalari
```

---

## 1️⃣ QADAM: Python kutubxonalarini o'rnatish

VS Code ni oching. `Terminal` → `New Terminal` bosing. Quyidagini yozing:
```
pip install -r requirements.txt
```

---

## 2️⃣ QADAM: Bot token olish

1. Telegramda **@BotFather** ga yozing
2. `/newbot` yozing
3. Bot nomini bering (masalan: `AutoServis Finder`)
4. Username bering (masalan: `autoservisfinder_bot`)
5. **Token** ni nusxalab oling (shunday ko'rinadi: `7123456789:AAF...`)

`bot/main.py` faylini oching, bu qatorni toping:
```python
BOT_TOKEN = "BU_YERGA_BOT_TOKENINGIZNI_YOZING"
```
Tokeningizni o'rnating.

---

## 3️⃣ QADAM: Mini App ni internetga chiqarish (Vercel)

1. **vercel.com** ga kiring → GitHub bilan ro'yxatdan o'ting
2. `miniapp` papkasini yuklang
3. Vercel sizga URL beradi (masalan: `https://autoservis.vercel.app`)

`bot/main.py` faylida:
```python
MINIAPP_URL = "https://autoservis.vercel.app"
```

---

## 4️⃣ QADAM: Backend serverni ishga tushirish

VS Code terminali:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

Brauzerda tekshirish: `http://localhost:8000`
Ishlab tursa `{"xabar": "AutoServis Finder API ishlayapti ✅"}` ko'rasiz.

---

## 5️⃣ QADAM: Botni ishga tushirish

Yangi terminal oching:
```bash
cd bot
python main.py
```

`✅ Bot ishga tushdi...` chiqsa — muvaffaqiyat!

---

## 6️⃣ QADAM: Sinab ko'rish

1. Telegramda o'zingizning botingizni toping
2. `/start` yozing
3. "AutoServis Finder ni ochish" tugmasini bosing
4. Mini App ochiladi! 🎉

---

## ❓ Muammolar bo'lsa

- **"pip not found"** → Python o'rnatilmagan, python.org dan o'rnating
- **Bot ishlamaydi** → Token noto'g'ri kiritilgan
- **Mini App ochilmaydi** → Vercel URL noto'g'ri

---

## 📞 Keyingi qadamlar (ixtiyoriy)

- PostgreSQL ulash (real ma'lumotlar bazasi)
- Google Maps API ulash (real xarita)
- Firebase bildirishnomalar ulash
- Railway ga deploy qilish (server doim ishlashi uchun)
