"""
AutoServis Finder — Backend API
Bu fayl ustaxonalar, bronlar va foydalanuvchilar uchun API endpointlarini ta'minlaydi.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import math

app = FastAPI(title="AutoServis Finder API", version="1.0")

# CORS — Mini App frontend bilan bog'lanish uchun
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# NAMUNAVIY MA'LUMOTLAR (keyinchalik DB bilan almashtirasiz)
# =============================================
ustaxonalar = [
    {
        "id": 1,
        "nomi": "Sherzod Auto Servis",
        "manzil": "Toshkent, Yunusobod, 5-mavze",
        "telefon": "+998901234567",
        "reyting": 4.8,
        "sharhlar_soni": 124,
        "lat": 41.3375,
        "lng": 69.3486,
        "xizmatlar": ["Moy almashtirish", "Tormoz tizimi", "Dvigatel ta'miri"],
        "narx_dan": 50000,
        "rasm": "https://via.placeholder.com/300x200?text=Sherzod+Auto",
        "ish_vaqti": "08:00 - 20:00",
        "ochiq": True
    },
    {
        "id": 2,
        "nomi": "Master Auto",
        "manzil": "Toshkent, Chilonzor, 9-kvartal",
        "telefon": "+998907654321",
        "reyting": 4.5,
        "sharhlar_soni": 89,
        "lat": 41.2995,
        "lng": 69.2401,
        "xizmatlar": ["Kuzov ta'miri", "Bo'yash", "Elektr tizimi"],
        "narx_dan": 80000,
        "rasm": "https://via.placeholder.com/300x200?text=Master+Auto",
        "ish_vaqti": "09:00 - 19:00",
        "ochiq": True
    },
    {
        "id": 3,
        "nomi": "Speed Service",
        "manzil": "Toshkent, Mirzo Ulug'bek, 3-mavze",
        "telefon": "+998991112233",
        "reyting": 4.2,
        "sharhlar_soni": 56,
        "lat": 41.3203,
        "lng": 69.3100,
        "xizmatlar": ["Shina almashtirish", "Balansировка", "Diagnostika"],
        "narx_dan": 30000,
        "rasm": "https://via.placeholder.com/300x200?text=Speed+Service",
        "ish_vaqti": "08:00 - 22:00",
        "ochiq": False
    },
]

bronlar = []
sharhlar = []


# =============================================
# YORDAMCHI FUNKSIYA — masofa hisoblash (km)
# =============================================
def masofa_hisobla(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


# =============================================
# MODELLAR
# =============================================
class BronModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    sana: str           # "2026-06-15"
    vaqt: str           # "10:00"
    xizmat: str
    izoh: Optional[str] = ""

class SharxModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    yulduz: int         # 1-5
    matn: str


# =============================================
# ENDPOINTLAR
# =============================================

@app.get("/")
def root():
    return {"xabar": "AutoServis Finder API ishlayapti ✅"}


@app.get("/ustaxonalar")
def ustaxonalar_royxati(lat: float = 41.2995, lng: float = 69.2401, radius: float = 10):
    """Yaqin ustaxonalarni qaytaradi (radius km)"""
    natija = []
    for u in ustaxonalar:
        masofa = masofa_hisobla(lat, lng, u["lat"], u["lng"])
        if masofa <= radius:
            natija.append({**u, "masofa_km": round(masofa, 1)})
    natija.sort(key=lambda x: x["masofa_km"])
    return natija


@app.get("/ustaxonalar/{id}")
def ustaxona_detail(id: int):
    """Bitta ustaxona haqida to'liq ma'lumot"""
    for u in ustaxonalar:
        if u["id"] == id:
            return u
    raise HTTPException(status_code=404, detail="Ustaxona topilmadi")


@app.post("/bron")
def bron_qilish(bron: BronModel):
    """Yangi bron qo'shish"""
    yangi_bron = {
        "id": len(bronlar) + 1,
        "holat": "kutilmoqda",
        **bron.dict()
    }
    bronlar.append(yangi_bron)
    return {"xabar": "Bron muvaffaqiyatli qabul qilindi ✅", "bron_id": yangi_bron["id"]}


@app.get("/bronlar/{foydalanuvchi_id}")
def foydalanuvchi_bronlari(foydalanuvchi_id: str):
    """Foydalanuvchining bronlari"""
    return [b for b in bronlar if b["foydalanuvchi_id"] == foydalanuvchi_id]


@app.post("/sharh")
def sharh_qoldirish(sharh: SharxModel):
    """Sharh va reyting qoldirish"""
    if not 1 <= sharh.yulduz <= 5:
        raise HTTPException(status_code=400, detail="Yulduz 1 dan 5 gacha bo'lishi kerak")
    yangi_sharh = {"id": len(sharhlar) + 1, **sharh.dict()}
    sharhlar.append(yangi_sharh)
    return {"xabar": "Sharh qabul qilindi ✅"}


@app.get("/sharhlar/{ustaxona_id}")
def ustaxona_sharhlari(ustaxona_id: int):
    """Ustaxona sharhlari"""
    return [s for s in sharhlar if s["ustaxona_id"] == ustaxona_id]
