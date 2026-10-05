import gradio as gr
import requests
import joblib

# --- API AYARLARI ---
API_KEY = "03e08d07f2d355040c37fb62cdb52d5a"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# --- TÜRKİYE LİGLERİ ---
LIGLER = {
    "Süper Lig": 203,
    "1. Lig": 204,
    "2. Lig": 205,
    "3. Lig": 206
}

# --- MODELİ YÜKLE ---
try:
    model = joblib.load("mac_tahmin_modeli.pkl")
except Exception:
    model = None

# --- ÖZEL MODERN CSS TASARIMI ---
CUSTOM_CSS = """
body, .gradio-container {
    background-color: #0b0f19 !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.match-header-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    margin: 15px 0;
}

.team-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}

.team-logo {
    width: 75px;
    height: 75px;
    object-fit: contain;
    filter: drop-shadow(0 4px 6px rgba(0,0,0,0.5));
    transition: transform 0.2s;
}

.team-logo:hover {
    transform: scale(1.08);
}

.team-title {
    font-size: 1.15rem;
    font-weight: 700;
    margin-top: 10px;
    color: #f8fafc;
}

.vs-badge {
    background: linear-gradient(135deg, #ef4444, #f97316);
    color: white;
    font-weight: 900;
    font-size: 1.2rem;
    padding: 8px 18px;
    border-radius: 9999px;
    box-shadow: 0 0 15px rgba(239, 68, 68, 0.5);
}

.stat-chip {
    background: rgba(51, 65, 85, 0.5);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.9rem;
    border: 1px solid #475569;
}

.pred-winner-card {
    background: linear-gradient(135deg, #059669 0%, #047857 100%);
    color: #ffffff;
    border-radius: 12px;
    padding: 16px;
    font-size: 1.2rem;
    font-weight: 800;
    text-align: center;
    box-shadow: 0 4px 15px rgba(5, 150, 105, 0.4);
    margin: 12px 0;
}

.kupon-card {
    background: #1e293b;
    border-left: 5px solid #10b981;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
"""

FIXTURE_STORE = {}

# --- 1. LİGİN MAÇLARINI VE LOGOLARINI ÇEK ---
def maclari_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    url = f"{BASE_URL}/fixtures"
    params = {"league": league_id, "next": 15}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = res.json().get("response", [])
        
        matches = []
        FIXTURE_STORE[lig_adi] = {}
        
        for m in data:
            f_id = str(m["fixture"]["id"])
            dt = m["fixture"]["date"].split("T")[0]
            time = m["fixture"]["date"].split("T")[1][:5]
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            
            label = f"{dt} {time} | {ev} vs {dep}"
            matches.append(label)
            
            FIXTURE_STORE[lig_adi][label] = {
                "home": ev,
                "away": dep,
                "home_logo": m["teams"]["home"]["logo"],
                "away_logo": m["teams"]["away"]["logo"],
                "date": f"{dt} - {time}"
            }
        
        if not matches:
            return gr.Dropdown(choices=["Bu ligde yakın maç bulunamadı"], value="Bu ligde yakın maç bulunamadı")
        return gr.Dropdown(choices=matches, value=matches[0])
    except Exception as e:
        return gr.Dropdown(choices=[f"Hata: {str(e)}"], value=f"Hata: {str(e)}")

# --- 2. DETAYLI AI MAÇ ANALİZİ (GÖRSEL KART) ---
def mac_analizi_yap(lig_adi, secilen_mac):
    if not secilen_mac or "vs" not in secilen_mac:
        return "<p style='color:#f87171;'>Lütfen geçerli bir maç seçiniz.</p>"
    
    mac_bilgi = FIXTURE_STORE.get(lig_adi, {}).get(secilen_mac)
    if not mac_bilgi:
        parts = secilen_mac.split(" | ")[1].split(" vs ")
        ev_takim = parts[0].strip()
        dep_takim = parts[1].strip()
        ev_logo = "https://media.api-sports.io/football/teams/dummy.png"
        dep_logo = "https://media.api-sports.io/football/teams/dummy.png"
        mac_tarih = "Yakında"
    else:
        ev_takim = mac_bilgi["home"]
        dep_takim = mac_bilgi["away"]
        ev_logo = mac_bilgi["home_logo"]
        dep_logo = mac_bilgi["away_logo"]
        mac_tarih = mac_bilgi["date"]
        
    league_id = LIGLER.get(lig_adi, 203)
    
    # Gerçek gol verilerini çek
    ev_ag, ev_yg, dep_ag, dep_yg = 1.6, 1.0, 1.3, 1.2
    try:
        url = f"{BASE_URL}/standings"
        res = requests.get(url, headers=HEADERS, params={"league": league_id, "season": 2024}, timeout=8)
        standings = res.json().get("response", [])[0]["league"]["standings"][0]
        
        for team in standings:
            t_name = team["team"]["name"]
            played = max(team["all"]["played"], 1)
            gf = team["all"]["goals"]["for"]
            ga = team["all"]["goals"]["against"]
            if ev_takim.lower() in t_name.lower():
                ev_ag = round(gf / played, 2)
                ev_yg = round(ga / played, 2)
            elif dep_takim.lower() in t_name.lower():
                dep_ag = round(gf / played, 2)
                dep_yg = round(ga / played, 2)
    except Exception:
        pass

    # Model Tahmini
    if model is not None:
        veri = [[ev_ag, ev_yg, dep_ag, dep_yg]]
        tahmin = model.predict(veri)[0]
        prob = model.predict_proba(veri)[0]
    else:
        tahmin, prob = 1, [0.30, 0.52, 0.18]
        
    sonuclar = {
        1: f"🟢 MS 1 - {ev_takim} Galibiyeti",
        0: "🟡 MS X - Beraberlik",
        2: f"🔴 MS 2 - {dep_takim} Galibiyeti"
    }
    
    toplam_gol = ev_ag + dep_ag
    alt_ust = "2.5 ÜST" if toplam_gol >= 2.5 else "2.5 ALT"
    kg = "VAR" if (ev_ag >= 1.0 and dep_ag >= 1.0) else "YOK"

    # HTML Çıktısı (Modern UI Dashboard)
    html_card = f"""
    <div class="match-header-card">
        <div style="text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 12px;">
            🕒 <b>Başlama:</b> {mac_tarih} | 🏆 <b>{lig_adi}</b>
        </div>
        
        <div style="display: flex; justify-content: space-around; align-items: center;">
            <div class="team-box">
                <img class="team-logo" src="{ev_logo}" alt="{ev_takim}">
                <div class="team-title">{ev_takim}</div>
                <div style="color: #38bdf8; font-size: 0.85rem; margin-top: 4px;">Ev Sahibi</div>
            </div>
            
            <div>
                <span class="vs-badge">VS</span>
            </div>
            
            <div class="team-box">
                <img class="team-logo" src="{dep_logo}" alt="{dep_takim}">
                <div class="team-title">{dep_takim}</div>
                <div style="color: #f43f5e; font-size: 0.85rem; margin-top: 4px;">Deplasman</div>
            </div>
        </div>
        
        <div class="pred-winner-card">
            🎯 AI Ana Öngörüsü: {sonuclar.get(tahmin)}
        </div>

        <div style="display: flex; gap: 10px; margin-top: 15px; justify-content: center; flex-wrap: wrap;">
            <div class="stat-chip"><b>MS 1:</b> %{prob[1]*100:.1f}</div>
            <div class="stat-chip"><b>MS X:</b> %{prob[0]*10
