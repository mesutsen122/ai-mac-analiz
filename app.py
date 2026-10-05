import gradio as gr
import requests
import joblib
import random
import sqlite3
from datetime import datetime

# --- API AYARLARI ---
API_KEY = "03e08d07f2d355040c37fb62cdb52d5a"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# --- VERITABANI BASLATMA (Seffaf Kasa & Kupon Takibi) ---
DB_NAME = "kupon_kasa.db"
def db_baslat():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kuponlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT,
                maclar TEXT,
                kupon_tipi TEXT,
                toplam_oran REAL,
                durum TEXT,
                kazanc REAL
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM kuponlar")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                           ("2026-10-01", "Galatasaray vs Alanyaspor (MS 1) / Arsenal vs Chelsea (1X)", "Banko", 1.85, "Kazandi", 85.0))
            cursor.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                           ("2026-10-03", "Real Madrid vs Villarreal (2.5 UST) / Bayern vs Leipzig (KG)", "Ideal", 2.30, "Kazandi", 130.0))
            cursor.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                           ("2026-10-04", "Inter vs Milan (IY X) / Fenerbahce vs Kasimpasa (MS 1)", "Surpriz", 3.10, "Kaybetti", -100.0))
        conn.commit()

db_baslat()

# --- DEV TAKIMLAR VE KULUP BILGILERI ---
DEV_TAKIMLAR = [
    "galatasaray", "fenerbahce", "besiktas", "trabzonspor",
    "real madrid", "barcelona", "manchester city", "arsenal",
    "liverpool", "bayern munich", "inter", "milan", "paris saint germain"
]

KULUP_BILGILERI = {
    "Galatasaray": {
        "sehir": "Istanbul, Turkiye",
        "stadyum": "RAMS Park (Kapasite: 52.280)",
        "kurulus": "1905",
        "basarilar": "UEFA Kupasi (2000), UEFA Super Kupa (2000), 24 Super Lig Sampiyonlugu, 18 Turkiye Kupasi.",
        "ozet": "Ali Sami Yen ve arkadaslari tarafindan kurulan Galatasaray, Turk futbol tarihinin Avrupa'da kupa kaldiran tek temsilcisidir."
    },
    "Fenerbahce": {
        "sehir": "Istanbul, Turkiye",
        "stadyum": "Ulker Stadyumu Sukru Saracoglu Spor Kompleksi (Kapasite: 50.530)",
        "kurulus": "1907",
        "basarilar": "19 Super Lig Sampiyonlugu, 7 Turkiye Kupasi, 9 Super Kupa, UEFA Sampiyonlar Ligi Ceyrek Finali (2008).",
        "ozet": "Kadikoy temsilcisi sari-lacivertliler, Turkiye'nin en koklu ve en yuksek taraftar kitlesine sahip spor kuluplerindendir."
    },
    "Besiktas": {
        "sehir": "Istanbul, Turkiye",
        "stadyum": "Tupras Stadyumu (Inonu) (Kapasite: 42.590)",
        "kurulus": "1903",
        "basarilar": "16 Super Lig Sampiyonlugu, 11 Turkiye Kupasi, 10 Super Kupa, UEFA Avrupa Ligi Ceyrek Finalleri.",
        "ozet": "Turkiye'nin tescil edilen ilk spor kulubu unvanina sahip olan Siyah-Beyazlilar, Bogaz kenarindaki tarihi stadyumu ile unludur."
    },
    "Trabzonspor": {
        "sehir": "Trabzon, Turkiye",
        "stadyum": "Papara Park (Kapasite: 40.782)",
        "kurulus": "1967",
        "basarilar": "7 Super Lig Sampiyonlugu, 9 Turkiye Kupasi, 10 Super Kupa.",
        "ozet": "Anadolu'dan cikarak Istanbul hakimiyetini kiran ilk sampiyon Karadeniz Firtinasi, Turk futbolunun 4 buyuk efsanesinden biridir."
    },
    "Real Madrid": {
        "sehir": "Madrid, Ispanya",
        "stadyum": "Santiago Bernabeu (Kapasite: 84.744)",
        "kurulus": "1902",
        "basarilar": "15 UEFA Sampiyonlar Ligi Sampiyonlugu, 36 La Liga Sampiyonlugu, 5 FIFA Kulupler Dunya Kupasi.",
        "ozet": "FIFA tarafindan 20. yuzyilin en iyi kulubu secilen Los Blancos, dunya futbolunun zirvesindeki en basarili kuluptur."
    },
    "Barcelona": {
        "sehir": "Barselona, Ispanya",
        "stadyum": "Spotify Camp Nou (Kapasite: 105.000)",
        "kurulus": "1899",
        "basarilar": "5 UEFA Sampiyonlar Ligi, 27 La Liga, 31 Copa del Rey, 3 FIFA Kulupler Dunya Kupasi.",
        "ozet": "Mes que un club (Bir kulupten daha fazlasi) sloganiyla taninan Katalan devi, La Masia akademisiyle dunya futbol ekoludur."
    },
    "Arsenal": {
        "sehir": "Londra, Ingiltere",
        "stadyum": "Emirates Stadium (Kapasite: 60.704)",
        "kurulus": "1886",
        "basarilar": "13 Premier League Sampiyonlugu (2003-04 Yenilgisiz Invincibles), 14 FA Cup.",
        "ozet": "Kuzey Londra temsilcisi Topcular, Ingiltere Premier Lig tarihinin tek namaglup sampiyonluk unvanina sahiptir."
    }
}

LIGLER = {
    "Dunya - Tum Ligler": 0,
    "Turkiye - Super Lig": 203,
    "Turkiye - TFF 1. Lig": 204,
    "Ingiltere - Premier League": 39,
    "Ispanya - La Liga": 140,
    "Italya - Serie A": 135,
    "Almanya - Bundesliga": 78,
    "Fransa - Ligue 1": 61,
    "Sampiyonlar Ligi": 2
}

try:
    model = joblib.load("mac_tahmin_modeli.pkl")
except Exception:
    model = None

FIXTURE_STORE = {}

def guncel_sezon_bul():
    simdi = datetime.utcnow()
    return simdi.year - 1 if simdi.month < 8 else simdi.year

# ==========================================
# 1. CANLI SKORLAR (SAHADAN TARZI)
# ==========================================
def canli_skorlari_getir():
    url = f"{BASE_URL}/fixtures"
    try:
        res = requests.get(url, headers=HEADERS, params={"live": "all"}, timeout=10)
        fixtures = res.json().get("response", [])
        
        if not fixtures:
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            res_today = requests.get(url, headers=HEADERS, params={"date": today_str}, timeout=10)
            fixtures = res_today.json().get("response", [])
            baslik_notu = "Canli mac bulunamadi. Gunun bulteni gosteriliyor:"
        else:
