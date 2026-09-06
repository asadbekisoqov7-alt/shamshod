import os
import logging
from datetime import datetime
from typing import Optional

import httpx
import math
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # "*" bilan birga allow_credentials=True ishlamaydi (brauzer rad etadi) va hech qayerda cookie ishlatilmaydi
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://garage-247777-bot.vercel.app")
RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
if RAILWAY_URL and not RAILWAY_URL.startswith("http"):
    RAILWAY_URL = "https://" + RAILWAY_URL

# Supabase maxfiy kalitlarini kodga yozib qo'ymaymiz — Railway Variables orqali beriladi.
SB_URL = os.getenv("SB_URL", "https://zpdididueiysnzmrxdco.supabase.co")
SB_KEY = os.getenv("SB_KEY", "")
if not SB_KEY:
    logger.warning("SB_KEY o'rnatilmagan — Supabase so'rovlari ishlamaydi. Railway Variables'ga SB_KEY qo'shing.")

SB_H = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def dist(lat1, lon1, lat2, lon2):
    R = 6371
    x = math.sin(math.radians(lat2 - lat1) / 2)
    y = math.sin(math.radians(lon2 - lon1) / 2)
    a = x * x + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * y * y
    return round(R * 2 * math.asin(math.sqrt(a)), 1)


async def sb_get(table, query=""):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, timeout=10)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.error(f"sb_get {table}: {e}")
    return []


async def sb_post(table, data):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{SB_URL}/rest/v1/{table}", headers=SB_H, json=data, timeout=10)
            if r.status_code in [200, 201]:
                return r.json()
    except Exception as e:
        logger.error(f"sb_post {table}: {e}")
    return None


async def sb_patch(table, query, data):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.patch(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, json=data, timeout=10)
            return r.status_code in [200, 204]
    except Exception as e:
        logger.error(f"sb_patch {table}: {e}")
    return False


async def sb_delete(table, query):
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, timeout=10)
    except Exception as e:
        logger.error(f"sb_delete {table}: {e}")


async def tg(method, payload):
    if not BOT_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                json=payload, timeout=10,
            )
            return r.json()
    except Exception as e:
        logger.error(f"tg {method}: {e}")


async def send(chat_id, text, markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    return await tg("sendMessage", p)


# ── MODELS ──────────────────────────────────────────────
class BronModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    xizmat: str
    avto: Optional[str] = ""
    sana: str
    vaqt: str
    narx: int = 0
    tolov_usul: str = "bepul"
    holat: str = "kutilmoqda"
    izoh: Optional[str] = ""


class FoyModel(BaseModel):
    tg_id: str
    ism: str
    username: Optional[str] = ""
    balans: int = 0
    rol: str = "haydovchi"


class UstModel(BaseModel):
    nomi: str
    manzil: str
    telefon: str
    lat: float = 41.2995
    lng: float = 69.2401
    narx_dan: int = 50000
    ish_vaqti: str = "08:00-20:00"
    ochiq: bool = True


class SharhModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    yulduz: int
    matn: str


# ── ENDPOINTS ───────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "bot": "@shamashod_kotbot", "time": str(datetime.now())}


@app.get("/sb/{table}")
async def sb_proxy_get(table: str, request: Request):
    """Supabase GET proxy"""
    query = str(request.url.query)
    q = "?" + query if query else ""
    return await sb_get(table, q)


@app.post("/sb/{table}")
async def sb_proxy_post(table: str, request: Request):
    """Supabase POST proxy"""
    body = await request.json()
    result = await sb_post(table, body)
    return result or {}


@app.get("/ustaxonalar")
async def list_ustaxonalar(lat: float = 41.2995, lng: float = 69.2401):
    """
    Ustaxonalar ro'yxati — har biriga bog'langan xizmatlar va foydalanuvchi
    joylashuvidan masofasi bilan, eng yaqinidan boshlab saralangan.
    """
    data = await sb_get("ustaxonalar", "?select=*,xizmatlar(nomi,narx)&order=id")
    if not data:
        return []
    result = []
    for u in data:
        xz = u.get("xizmatlar") or []
        result.append({
            **u,
            "xizmatlar_list": [x["nomi"] for x in xz],
            "narxlar": {x["nomi"]: x["narx"] for x in xz},
            "masofa_km": dist(lat, lng, u.get("lat", 41.2995), u.get("lng", 69.2401)),
        })
    result.sort(key=lambda x: x["masofa_km"])
    return result


@app.get("/ustaxonalar/{uid}")
async def get_ustaxona(uid: int):
    data = await sb_get("ustaxonalar", f"?id=eq.{uid}&select=*,xizmatlar(nomi,narx)")
    if data:
        u = data[0]
        xz = u.get("xizmatlar") or []
        u["xizmatlar_list"] = [x["nomi"] for x in xz]
        u["narxlar"] = {x["nomi"]: x["narx"] for x in xz}
        return u
    return {}


@app.post("/ustaxonalar")
async def add_ustaxona(u: UstModel):
    return await sb_post("ustaxonalar", u.dict())


@app.patch("/ustaxonalar/{uid}")
async def update_ustaxona(uid: int, req: Request):
    data = await req.json()
    await sb_patch("ustaxonalar", f"?id=eq.{uid}", data)
    return {"ok": True}


@app.delete("/ustaxonalar/{uid}")
async def delete_ustaxona(uid: int):
    await sb_delete("ustaxonalar", f"?id=eq.{uid}")
    return {"ok": True}


@app.post("/bron")
async def create_bron(b: BronModel):
    result = await sb_post("bronlar", b.dict())
    try:
        ust = await sb_get("ustaxonalar", f"?id=eq.{b.ustaxona_id}&select=nomi")
        nom = ust[0]["nomi"] if ust else "Ustaxona"
        msg = (
            f"🔔 <b>YANGI BRON!</b>\n\n"
            f"🏪 {nom}\n"
            f"🔧 {b.xizmat}\n"
            f"📅 {b.sana} · {b.vaqt}\n"
            f"🚗 {b.avto or '-'}\n"
            f"💰 {b.narx:,} so'm\n"
            f"👤 {b.foydalanuvchi_id}"
        )
        if ADMIN_ID:
            await send(ADMIN_ID, msg)
    except Exception as e:
        logger.error(f"bron xabar: {e}")
    return result or {"ok": True}


@app.get("/bronlar")
async def get_bronlar():
    return await sb_get("bronlar", "?select=*&order=created_at.desc&limit=50")


@app.get("/bronlar/{foy_id}")
async def get_user_bronlar(foy_id: str):
    return await sb_get("bronlar", f"?foydalanuvchi_id=eq.{foy_id}&order=created_at.desc")


@app.post("/foydalanuvchi")
async def save_foy(f: FoyModel):
    ex = await sb_get("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}&select=id,rol")
    if ex:
        await sb_patch("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}", {"ism": f.ism, "username": f.username})
        return {"ok": True, "rol": ex[0].get("rol", "haydovchi")}
    await sb_post("foydalanuvchilar", f.dict())
    return {"ok": True, "rol": "haydovchi"}


@app.get("/foydalanuvchi_tekshir/{tg_id}")
async def check_foy(tg_id: str):
    data = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=*")
    return data[0] if data else {}


@app.post("/sharh")
async def add_sharh(s: SharhModel):
    result = await sb_post("sharhlar", s.dict())
    sharhlar = await sb_get("sharhlar", f"?ustaxona_id=eq.{s.ustaxona_id}&select=yulduz")
    if sharhlar:
        avg = sum(x["yulduz"] for x in sharhlar) / len(sharhlar)
        await sb_patch("ustaxonalar", f"?id=eq.{s.ustaxona_id}", {
            "reyting": round(avg, 1),
            "sharhlar_soni": len(sharhlar),
        })
    return result or {"ok": True}


@app.get("/statistika")
async def statistika():
    ust = await sb_get("ustaxonalar", "?select=id")
    bron = await sb_get("bronlar", "?select=narx,holat")
    foy = await sb_get("foydalanuvchilar", "?select=id")
    daromad = sum(b.get("narx", 0) for b in bron)
    return {
        "ustaxonalar": len(ust),
        "bronlar": len(bron),
        "foydalanuvchilar": len(foy),
        "daromad": daromad,
    }


# ── TELEGRAM BOT WEBHOOK ────────────────────────────────
@app.post("/webhook")
async def webhook(req: Request):
    try:
        update = await req.json()
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return {"ok": True}

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user = msg.get("from", {})
        tg_id = f"tg_{user.get('id', '')}"
        name = (user.get("first_name") or "") + (" " + user.get("last_name", "") if user.get("last_name") else "")

        # Foydalanuvchini saqlash (agar birinchi marta yozayotgan bo'lsa)
        ex = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=rol,balans")
        is_new = not ex
        if is_new:
            await sb_post("foydalanuvchilar", {
                "tg_id": tg_id, "ism": name,
                "username": user.get("username", ""),
                "balans": 0, "rol": "haydovchi",
            })

        if text.startswith("/start"):
            # Eslatma: usta kirish bonusi (+20,000) va referral bonusi (+5,000) bu yerda
            # BERILMAYDI — chunki /start bosqichida foydalanuvchi hali rolini tanlamagan.
            # Ikkala bonus ham Mini App'dagi ro'yxatdan o'tish oqimida (regUser) to'g'ri
            # shartlar bilan (usta bo'lib ro'yxatdan o'tsagina) beriladi — shu yerda ham
            # berilsa, referrer bonusni ikki marta olib qo'yishi mumkin edi.
            kb = {
                "keyboard": [
                    [{"text": "🔧 Ustaxona topish", "web_app": {"url": MINIAPP_URL}}],
                    [{"text": "📋 Bronlarim"}, {"text": "👤 Profilim"}],
                    [{"text": "👥 Do'st taklif"}],
                ],
                "resize_keyboard": True,
            }
            await send(
                chat_id,
                f"👋 Xush kelibsiz, <b>{name}</b>!\n\n"
                f"🚗 <b>GARAGE 24/7</b>\n"
                f"O'zbekistondagi avtomobil ustaxona platformasi\n\n"
                f"📍 Yaqin ustaxonalarni toping\n"
                f"📅 Online bron qiling\n"
                f"⭐ Sharhlar qoldiring",
                kb,
            )

        elif text == "📋 Bronlarim":
            bronlar = await sb_get("bronlar", f"?foydalanuvchi_id=eq.{tg_id}&order=created_at.desc&limit=10")
            if bronlar:
                txt = "📋 <b>So'nggi bronlar:</b>\n\n"
                for b in bronlar:
                    txt += f"🔧 {b.get('xizmat')} · 📅 {b.get('sana')} {b.get('vaqt')} — {b.get('holat')}\n"
            else:
                txt = "📋 Hozircha bronlar yo'q.\n\n🔧 Ustaxona topish tugmasini bosing!"
            await send(chat_id, txt)

        elif text == "👤 Profilim":
            u = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=*")
            if u:
                u = u[0]
                await send(
                    chat_id,
                    f"👤 <b>Profil</b>\n\n"
                    f"📛 {u.get('ism', '-')}\n"
                    f"🔑 Rol: {u.get('rol', 'haydovchi')}\n"
                    f"💰 Balans: {u.get('balans', 0):,} so'm",
                )

        elif text == "👥 Do'st taklif":
            # Mini App'ning "Do'st taklif" ekrani bilan BIR XIL formatda (ref_ prefiksisiz),
            # aks holda regUser() referrer'ni topa olmay, bonus berilmay qoladi.
            link = f"https://t.me/shamashod_kotbot?start={tg_id}"
            await send(
                chat_id,
                f"👥 <b>Do'stlaringizni taklif qiling!</b>\n\n"
                f"Havola:\n<code>{link}</code>",
            )

        elif text == "/stats" and str(user.get("id")) == str(ADMIN_ID):
            s = await statistika()
            await send(
                chat_id,
                f"📊 <b>STATISTIKA</b>\n\n"
                f"🏪 Ustaxonalar: {s['ustaxonalar']}\n"
                f"📅 Bronlar: {s['bronlar']}\n"
                f"👥 Foydalanuvchilar: {s['foydalanuvchilar']}\n"
                f"💰 Daromad: {s['daromad']:,} so'm",
            )

        # ── CHEK YUBORISH (rasm) ──────────────────────────
        photo = msg.get("photo")
        if photo and not text:
            # Foydalanuvchi rasm yubordi — chek deb qabul qilamiz
            user_data = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=ism,rol,balans")
            user_rol = user_data[0].get("rol", "haydovchi") if user_data else "haydovchi"
            user_ism = user_data[0].get("ism", name) if user_data else name
            user_bal = user_data[0].get("balans", 0) if user_data else 0

            if user_rol == "usta":
                file_id = photo[-1]["file_id"]
                if ADMIN_ID:
                    await tg("sendPhoto", {
                        "chat_id": ADMIN_ID,
                        "photo": file_id,
                        "caption": (
                            f"🧾 <b>YANGI CHEK!</b>\n\n"
                            f"👤 Usta: <b>{user_ism}</b>\n"
                            f"🆔 ID: {tg_id}\n"
                            f"💰 Joriy balans: {user_bal:,} so'm\n\n"
                            f"✅ Tasdiqlash uchun quyidagi buyruqni yuboring:\n"
                            f"<code>/tolov {tg_id} SUMMA</code>\n\n"
                            f"Masalan: <code>/tolov {tg_id} 50000</code>"
                        ),
                        "parse_mode": "HTML",
                    })
                await send(
                    chat_id,
                    f"✅ Chekingiz adminga yuborildi!\n\n"
                    f"⏳ Admin tekshirib, balansingizni to'ldiradi.\n"
                    f"Odatda 5-15 daqiqa ichida.",
                )
            else:
                await send(chat_id, "ℹ️ Chek faqat ustalar uchun. Siz haydovchisiz.")

        # ── ADMIN: TO'LOV TASDIQLASH ──────────────────────
        elif text and text.startswith("/tolov") and str(user.get("id")) == str(ADMIN_ID):
            parts = text.split()
            if len(parts) == 3:
                target_tg_id = parts[1]
                try:
                    summa = int(parts[2])
                    u = await sb_get("foydalanuvchilar", f"?tg_id=eq.{target_tg_id}&select=balans,ism")
                    if u:
                        new_bal = (u[0].get("balans") or 0) + summa
                        await sb_patch("foydalanuvchilar", f"?tg_id=eq.{target_tg_id}", {"balans": new_bal})
                        await sb_post("balans_tarixi", {
                            "foydalanuvchi_id": target_tg_id,
                            "tur": "tolov",
                            "miqdor": summa,
                            "izoh": "Admin tasdiqlagan to'lov",
                        })
                        await send(
                            target_tg_id,
                            f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                            f"💰 Hisobingizga {summa:,} so'm qo'shildi.\n"
                            f"🏦 Yangi balans: {new_bal:,} so'm",
                        )
                        await send(chat_id, f"✅ {u[0].get('ism', 'Usta')} ga {summa:,} so'm qo'shildi.")
                    else:
                        await send(chat_id, f"❌ Foydalanuvchi topilmadi: {target_tg_id}")
                except ValueError:
                    await send(chat_id, "❌ Summa noto'g'ri. Masalan: /tolov tg_123456 50000")
            else:
                await send(chat_id, "❌ Format: /tolov tg_ID SUMMA\nMasalan: /tolov tg_123456 50000")

    except Exception as e:
        logger.error(f"Webhook xato: {e}")
    return {"ok": True}


# ── WEBHOOK BOSHQARUVI ────────────────────────────────
@app.get("/set_webhook")
async def set_webhook():
    backend_url = RAILWAY_URL or "https://shamshod-production.up.railway.app"
    webhook_url = f"{backend_url}/webhook"
    result = await tg("setWebhook", {"url": webhook_url, "drop_pending_updates": True})
    return {"ok": True, "result": result, "webhook_url": webhook_url}


@app.get("/del_webhook")
async def del_webhook():
    result = await tg("deleteWebhook", {"drop_pending_updates": True})
    return {"ok": True, "result": result}


@app.on_event("startup")
async def startup():
    if BOT_TOKEN:
        backend_url = RAILWAY_URL or "https://shamshod-production.up.railway.app"
        webhook_url = f"{backend_url}/webhook"
        result = await tg("setWebhook", {"url": webhook_url, "drop_pending_updates": True})
        logger.info(f"Webhook: {result}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
