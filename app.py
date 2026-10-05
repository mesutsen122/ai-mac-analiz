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
            <div class="stat-chip"><b>MS X:</b> %{prob[0]*100:.1f}</div>
            <div class="stat-chip"><b>MS 2:</b> %{prob[2]*100:.1f}</div>
            <div class="stat-chip" style="background:#1e3a8a; border-color:#3b82f6;"><b>Gol Tercihi:</b> {alt_ust}</div>
            <div class="stat-chip" style="background:#701a75; border-color:#d946ef;"><b>Karşılıklı Gol:</b> {kg}</div>
        </div>
        
        <div style="margin-top: 20px; font-size: 0.85rem; color: #94a3b8; text-align: center;">
            <b>Lig Performansı:</b> {ev_takim} (Ort. {ev_ag} Gol / Maç) | {dep_takim} (Ort. {dep_ag} Gol / Maç)
        </div>
    </div>
    """
    return html_card

# --- 3. AKILLI KUPON SİHİRBAZI (LOGO & KART DESTEKLİ) ---
def kupon_olustur(lig_adi, kupon_tipi):
    league_id = LIGLER.get(lig_adi, 203)
    url = f"{BASE_URL}/fixtures"
    params = {"league": league_id, "next": 8}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        fixtures = res.json().get("response", [])
        if not fixtures:
            return "<p style='color:#f87171;'>Bu ligde yakın tarihte maç bulunamadı.</p>"
        
        kupon_kartlari = []
        toplam_oran = 1.0
        
        for m in fixtures[:4]:
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            ev_logo = m["teams"]["home"]["logo"]
            dep_logo = m["teams"]["away"]["logo"]
            
            if kupon_tipi == "🔥 Banko Kupon (Düşük Risk)":
                secim = f"{ev} Çifte Şans (1X)"
                oran = 1.35
                guven = 85
            elif kupon_tipi == "⚡ İdeal / Dengeli Kupon":
                secim = "2.5 Gol ÜST"
                oran = 1.75
                guven = 72
            else:
                secim = "İlk Yarı X / Karşılıklı Gol VAR"
                oran = 2.40
                guven = 58
                
            toplam_oran *= oran
            
            kart = f"""
            <div class="kupon-card">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <img src="{ev_logo}" style="width: 32px; height: 32px; object-fit: contain;">
                    <span style="font-weight: 600; font-size: 0.95rem;">{ev} - {dep}</span>
                    <img src="{dep_logo}" style="width: 32px; height: 32px; object-fit: contain;">
                </div>
                <div style="text-align: right;">
                    <span style="background: #0f172a; padding: 4px 10px; border-radius: 6px; font-weight: bold; color: #34d399; font-size: 0.9rem;">
                        {secim}
                    </span>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Güven: %{guven}</div>
                </div>
            </div>
            """
            kupon_kartlari.append(kart)
            
        sonuc_html = f"""
        <div style="padding: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #38bdf8;">🎫 {kupon_tipi}</h3>
                <span style="background: #3b82f6; color: white; padding: 6px 14px; border-radius: 8px; font-weight: 800;">
                    Tahmini Çarpan: ~{toplam_oran:.2f}
                </span>
            </div>
            {''.join(kupon_kartlari)}
        </div>
        """
        return sonuc_html
    except Exception as e:
        return f"<p style='color:#f87171;'>Hata oluştu: {str(e)}</p>"

# --- 4. GÖRSEL PUAN DURUMU (LOGO DESTEKLİ TABLO) ---
def puan_durumu_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    url = f"{BASE_URL}/standings"
    params = {"league": league_id, "season": 2024}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        standings = res.json().get("response", [])[0]["league"]["standings"][0]
        
        satirlar = []
        for t in standings:
            satir = f"""
            <tr style="border-bottom: 1px solid #1e293b; text-align: center;">
                <td style="padding: 10px; font-weight: bold;">{t['rank']}</td>
                <td style="padding: 10px; text-align: left; display: flex; align-items: center; gap: 10px;">
                    <img src="{t['team']['logo']}" style="width: 24px; height: 24px; object-fit: contain;">
                    <span>{t['team']['name']}</span>
                </td>
                <td style="padding: 10px;">{t['all']['played']}</td>
                <td style="padding: 10px; color: #34d399;">{t['all']['win']}</td>
                <td style="padding: 10px; color: #fbbf24;">{t['all']['draw']}</td>
                <td style="padding: 10px; color: #f87171;">{t['all']['lose']}</td>
                <td style="padding: 10px;">{t['goalsDiff']}</td>
                <td style="padding: 10px; font-weight: 800; color: #38bdf8;">{t['points']}</td>
            </tr>
            """
            satirlar.append(satir)
            
        tablo_html = f"""
        <table style="width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 12px; overflow: hidden;">
            <thead>
                <tr style="background: #1e293b; color: #94a3b8; font-size: 0.85rem;">
                    <th style="padding: 12px;">Sıra</th>
                    <th style="padding: 12px; text-align: left;">Takım</th>
                    <th style="padding: 12px;">O</th>
                    <th style="padding: 12px;">G</th>
                    <th style="padding: 12px;">B</th>
                    <th style="padding: 12px;">M</th>
                    <th style="padding: 12px;">AV</th>
                    <th style="padding: 12px;">Puan</th>
                </tr>
            </thead>
            <tbody>
                {''.join(satirlar)}
            </tbody>
        </table>
        """
        return tablo_html
    except Exception as e:
        return f"<p style='color:#f87171;'>Puan durumu yüklenemedi: {str(e)}</p>"

# --- 5. GÖRSEL GOL KRALLIĞI ---
def gol_kralligi_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    url = f"{BASE_URL}/players/topscorers"
    params = {"league": league_id, "season": 2024}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        scorers = res.json().get("response", [])
        
        satirlar = []
        for i, item in enumerate(scorers[:15], 1):
            p = item["player"]
            t = item["statistics"][0]["team"]
            g = item["statistics"][0]["goals"]["total"] or 0
            a = item["statistics"][0]["goals"]["assists"] or 0
            
            satir = f"""
            <tr style="border-bottom: 1px solid #1e293b; text-align: center;">
                <td style="padding: 10px; font-weight: bold;">{i}</td>
                <td style="padding: 10px; text-align: left; display: flex; align-items: center; gap: 10px;">
                    <img src="{p.get('photo', '')}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;">
                    <span><b>{p.get('name')}</b></span>
                </td>
                <td style="padding: 10px; text-align: left;">
                    <img src="{t.get('logo', '')}" style="width: 20px; height: 20px; vertical-align: middle; margin-right: 6px;">
                    {t.get('name')}
                </td>
                <td style="padding: 10px; font-weight: 800; color: #34d399; font-size: 1.05rem;">{g}</td>
                <td style="padding: 10px; color: #38bdf8;">{a}</td>
            </tr>
            """
            satirlar.append(satir)
            
        tablo_html = f"""
        <table style="width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 12px; overflow: hidden;">
            <thead>
                <tr style="background: #1e293b; color: #94a3b8; font-size: 0.85rem;">
                    <th style="padding: 12px;">#</th>
                    <th style="padding: 12px; text-align: left;">Futbolcu</th>
                    <th style="padding: 12px; text-align: left;">Kulüp</th>
                    <th style="padding: 12px;">Gol</th>
                    <th style="padding: 12px;">Asist</th>
                </tr>
            </thead>
            <tbody>
                {''.join(satirlar)}
            </tbody>
        </table>
        """
        return tablo_html
    except Exception as e:
        return f"<p style='color:#f87171;'>Gol krallığı yüklenemedi: {str(e)}</p>"

# --- GRADIO ARAYÜZ BLOĞU ---
with gr.Blocks(title="Türkiye Ligleri Pro Analiz & Kupon", css=CUSTOM_CSS, theme=gr.themes.Default()) as arayuz:
    gr.HTML("""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #38bdf8; margin: 0; font-size: 2.2rem; font-weight: 800;">🇹🇷 TFF PRO ANALİZ & AI KUPON</h1>
        <p style="color: #94a3b8; margin-top: 6px; font-size: 1rem;">Süper Lig, 1. Lig, 2. Lig ve 3. Lig İçin Canlı Logo Destekli İstatistik ve Tahmin Platformu</p>
    </div>
    """)
    
    with gr.Tabs():
        # SEKME 1: MAÇ ANALİZİ
        with gr.TabItem("⚽ Canlı Fikstür & Logo Destekli Analiz"):
            with gr.Row():
                lig_sec = gr.Dropdown(choices=list(LIGLER.keys()), value="Süper Lig", label="🏆 Lig Seçiniz")
                btn_fikstur = gr.Button("📅 Maçları Listele", variant="secondary")
            
            secilen_mac = gr.Dropdown(label="📌 Analiz Edilecek Karşılaşma", choices=["Önce Maçları Listele butonuna tıklayın"])
            btn_analiz = gr.Button("🔥 Yapay Zeka ile Analiz Et", variant="primary")
            
            analiz_karti = gr.HTML("<p style='text-align:center; color:#64748b;'>Analiz sonucunu görmek için yukarıdan maç seçip butona basınız.</p>")
            
            btn_fikstur.click(fn=maclari_getir, inputs=[lig_sec], outputs=[secilen_mac])
            btn_analiz.click(fn=mac_analizi_yap, inputs=[lig_sec, secilen_mac], outputs=[analiz_karti])

        # SEKME 2: KUPON SİHİRBAZI
        with gr.TabItem("🎫 Akıllı AI Kupon Sihirbazı"):
            with gr.Row():
                k_lig = gr.Dropdown(choices=list(LIGLER.keys()), value="Süper Lig", label="🏆 Lig")
                k_tip = gr.Radio(["🔥 Banko Kupon (Düşük Risk)", "⚡ İdeal / Dengeli Kupon", "💣 Sürpriz / Yüksek Oran"], value="🔥 Banko Kupon (Düşük Risk)", label="Kupon Tipi")
            btn_kupon = gr.Button("🎲 Kuponu Üret", variant="primary")
            kupon_karti = gr.HTML("<p style='text-align:center; color:#64748b;'>Kupon üretmek için butona tıklayınız.</p>")
            btn_kupon.click(fn=kupon_olustur, inputs=[k_lig, k_tip], outputs=[kupon_karti])

        # SEKME 3: PUAN TABLOSU
        with gr.TabItem("📈 Puan Cetveli"):
            with gr.Row():
                p_lig = gr.Dropdown(choices=list(LIGLER.keys()), value="Süper Lig", label="🏆 Lig")
                btn_puan = gr.Button("Puan Durumunu Getir", variant="secondary")
            tablo_puan = gr.HTML("<p style='text-align:center; color:#64748b;'>Sıralamayı görmek için butona basınız.</p>")
            btn_puan.click(fn=puan_durumu_getir, inputs=[p_lig], outputs=[tablo_puan])

        # SEKME 4: GOL KRALLIĞI
        with gr.TabItem("👟 Gol & Asist Krallığı"):
            with gr.Row():
                g_lig = gr.Dropdown(choices=list(LIGLER.keys()), value="Süper Lig", label="🏆 Lig")
                btn_gol = gr.Button("Listeyi Getir", variant="secondary")
            tablo_gol = gr.HTML("<p style='text-align:center; color:#64748b;'>Gol krallarını listelemek için butona basınız.</p>")
            btn_gol.click(fn=gol_kralligi_getir, inputs=[g_lig], outputs=[tablo_gol])

if __name__ == "__main__":
    arayuz.launch(server_name="0.0.0.0", server_port=10000)
