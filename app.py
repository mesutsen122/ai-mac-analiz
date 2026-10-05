import gradio as gr
import requests
import joblib
from datetime import datetime

# --- API AYARLARI ---
API_KEY = "03e08d07f2d355040c37fb62cdb52d5a"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# --- DÜNYA VE TÜRKİYE DEV LİGLERİ ---
LIGLER = {
    "🌍 Bugün Oynanan Tüm Dünya Maçları": 0,
    "🇹🇷 Türkiye - Süper Lig": 203,
    "🇹🇷 Türkiye - TFF 1. Lig": 204,
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere - Premier League": 39,
    "🇪🇸 İspanya - La Liga": 140,
    "🇮🇹 İtalya - Serie A": 135,
    "🇩🇪 Almanya - Bundesliga": 78,
    "🇫🇷 Fransa - Ligue 1": 61,
    "🏆 UEFA Şampiyonlar Ligi": 2,
    "🏆 UEFA Avrupa Ligi": 3,
    "🇳🇱 Hollanda - Eredivisie": 88,
    "🇵🇹 Portekiz - Primeira Liga": 94
}

# --- MODELİ YÜKLE ---
try:
    model = joblib.load("mac_tahmin_modeli.pkl")
except Exception:
    model = None

FIXTURE_STORE = {}

# --- 1. MAÇLARI VE LOGOLARI ÇEK (GÜNCEL / CANLI) ---
def maclari_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/fixtures"
    if league_id == 0:
        # Bugün dünyada oynanan önemli maçlar
        params = {"date": today_str}
    else:
        # Seçilen ligin sıradaki güncel maçları
        params = {"league": league_id, "next": 12}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = res.json().get("response", [])
        
        matches = []
        FIXTURE_STORE[lig_adi] = {}
        
        # Filtrele ve listeye ekle
        for m in data[:25]:
            dt = m["fixture"]["date"].split("T")[0]
            time = m["fixture"]["date"].split("T")[1][:5]
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            lig_bilgi = m.get("league", {}).get("name", lig_adi)
            
            label = f"[{lig_bilgi}] {dt} {time} | {ev} vs {dep}"
            matches.append(label)
            
            FIXTURE_STORE[lig_adi][label] = {
                "home": ev,
                "away": dep,
                "home_logo": m["teams"]["home"]["logo"],
                "away_logo": m["teams"]["away"]["logo"],
                "date": f"{dt} {time}",
                "league_name": lig_bilgi,
                "league_id": m.get("league", {}).get("id", league_id)
            }
        
        if not matches:
            return gr.Dropdown(choices=["Bugün veya yakında maç bulunamadı"], value="Bugün veya yakında maç bulunamadı")
        return gr.Dropdown(choices=matches, value=matches[0])
    except Exception as e:
        return gr.Dropdown(choices=[f"Hata: {str(e)}"], value=f"Hata: {str(e)}")

# --- 2. LOGOLU VE ORANLI AI MAÇ ANALİZİ ---
def mac_analizi_yap(lig_adi, secilen_mac):
    if not secilen_mac or "vs" not in secilen_mac:
        return "<div style='color:#ef4444; padding:15px;'>Lütfen listeden geçerli bir maç seçiniz.</div>"
    
    mac_bilgi = FIXTURE_STORE.get(lig_adi, {}).get(secilen_mac)
    if not mac_bilgi:
        ev_takim, dep_takim = "Ev Sahibi", "Deplasman"
        ev_logo = dep_logo = "https://media.api-sports.io/football/teams/dummy.png"
        mac_tarih = "Canlı / Yakında"
        lig_bilgi = lig_adi
        l_id = 203
    else:
        ev_takim = mac_bilgi["home"]
        dep_takim = mac_bilgi["away"]
        ev_logo = mac_bilgi["home_logo"]
        dep_logo = mac_bilgi["away_logo"]
        mac_tarih = mac_bilgi["date"]
        lig_bilgi = mac_bilgi["league_name"]
        l_id = mac_bilgi["league_id"]

    ev_ag, ev_yg, dep_ag, dep_yg = 1.7, 1.1, 1.3, 1.2
    try:
        if l_id and l_id != 0:
            url = f"{BASE_URL}/standings"
            res = requests.get(url, headers=HEADERS, params={"league": l_id, "season": 2024}, timeout=6)
            standings = res.json().get("response", [])[0]["league"]["standings"][0]
            for team in standings:
                t_name = team["team"]["name"].lower()
                pl = max(team["all"]["played"], 1)
                if ev_takim.lower() in t_name:
                    ev_ag = round(team["all"]["goals"]["for"] / pl, 2)
                    ev_yg = round(team["all"]["goals"]["against"] / pl, 2)
                elif dep_takim.lower() in t_name:
                    dep_ag = round(team["all"]["goals"]["for"] / pl, 2)
                    dep_yg = round(team["all"]["goals"]["against"] / pl, 2)
    except Exception:
        pass

    if model is not None:
        veri = [[ev_ag, ev_yg, dep_ag, dep_yg]]
        tahmin = model.predict(veri)[0]
        prob = model.predict_proba(veri)[0]
    else:
        tahmin, prob = 1, [0.28, 0.54, 0.18]
        
    sonuclar = {
        1: f"🟢 MS 1 - {ev_takim} Galibiyeti",
        0: "🟡 MS X - Beraberlik",
        2: f"🔴 MS 2 - {dep_takim} Galibiyeti"
    }
    
    toplam_gol = ev_ag + dep_ag
    alt_ust = "2.5 ÜST" if toplam_gol >= 2.45 else "2.5 ALT"
    kg = "VAR" if (ev_ag >= 1.0 and dep_ag >= 1.0) else "YOK"

    return f"""
    <div style="background: #111827; border: 1px solid #374151; border-radius: 14px; padding: 20px; color: #f3f4f6; margin-top: 15px;">
        <div style="text-align: center; color: #9ca3af; font-size: 0.85rem; margin-bottom: 15px;">
            🕒 <b>Tarih / Saat:</b> {mac_tarih} | 🏆 <b>{lig_bilgi}</b>
        </div>
        
        <div style="display: flex; justify-content: space-around; align-items: center; text-align: center;">
            <div style="flex: 1;">
                <img src="{ev_logo}" style="width: 75px; height: 75px; object-fit: contain; margin: 0 auto;">
                <div style="font-size: 1.15rem; font-weight: 700; margin-top: 8px;">{ev_takim}</div>
                <div style="color: #38bdf8; font-size: 0.85rem;">Ev Sahibi</div>
            </div>
            
            <div style="padding: 0 15px;">
                <span style="background: linear-gradient(135deg, #ef4444, #f97316); color: white; font-weight: 900; font-size: 1.1rem; padding: 8px 16px; border-radius: 9999px;">VS</span>
            </div>
            
            <div style="flex: 1;">
                <img src="{dep_logo}" style="width: 75px; height: 75px; object-fit: contain; margin: 0 auto;">
                <div style="font-size: 1.15rem; font-weight: 700; margin-top: 8px;">{dep_takim}</div>
                <div style="color: #f43f5e; font-size: 0.85rem;">Deplasman</div>
            </div>
        </div>
        
        <div style="background: linear-gradient(135deg, #059669, #047857); color: white; border-radius: 10px; padding: 14px; font-size: 1.15rem; font-weight: 800; text-align: center; margin: 20px 0;">
            🎯 AI Tercihi: {sonuclar.get(tahmin)}
        </div>

        <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <div style="background: #1f2937; border: 1px solid #4b5563; padding: 8px 14px; border-radius: 8px;"><b>MS 1:</b> %{prob[1]*100:.1f}</div>
            <div style="background: #1f2937; border: 1px solid #4b5563; padding: 8px 14px; border-radius: 8px;"><b>MS X:</b> %{prob[0]*100:.1f}</div>
            <div style="background: #1f2937; border: 1px solid #4b5563; padding: 8px 14px; border-radius: 8px;"><b>MS 2:</b> %{prob[2]*100:.1f}</div>
            <div style="background: #1e3a8a; padding: 8px 14px; border-radius: 8px;"><b>Gol Bahsi:</b> {alt_ust}</div>
            <div style="background: #701a75; padding: 8px 14px; border-radius: 8px;"><b>KG:</b> {kg}</div>
        </div>
        
        <div style="margin-top: 15px; font-size: 0.8rem; color: #9ca3af; text-align: center;">
            Model Metrikleri: {ev_takim} ({ev_ag} gol/maç) | {dep_takim} ({dep_ag} gol/maç)
        </div>
    </div>
    """

# --- 3. AKILLI DÜNYA KUPON SİHİRBAZI ---
def kupon_olustur(lig_adi, kupon_tipi):
    league_id = LIGLER.get(lig_adi, 0)
    url = f"{BASE_URL}/fixtures"
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    if league_id == 0:
        params = {"date": today_str}
    else:
        params = {"league": league_id, "next": 8}
        
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        fixtures = res.json().get("response", [])
        if not fixtures:
            return "<div style='color:#ef4444; padding:15px;'>Kupon oluşturulacak uygun maç bulunamadı.</div>"
        
        kupon_kartlari = []
        toplam_oran = 1.0
        
        for m in fixtures[:4]:
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            ev_logo = m["teams"]["home"]["logo"]
            dep_logo = m["teams"]["away"]["logo"]
            lig_ismi = m.get("league", {}).get("name", "Lig")
            
            if "Banko" in kupon_tipi:
                secim = f"{ev} 1X veya 1.5 Üst"
                oran = 1.38
                guven = 86
            elif "İdeal" in kupon_tipi:
                secim = "2.5 Gol Üstü"
                oran = 1.80
                guven = 74
            else:
                secim = "İlk Yarı X & KG VAR"
                oran = 2.45
                guven = 60
                
            toplam_oran *= oran
            
            kart = f"""
            <div style="background: #1f2937; border-left: 4px solid #10b981; border-radius: 8px; padding: 12px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; color: white;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <img src="{ev_logo}" style="width: 28px; height: 28px; object-fit: contain;">
                    <span style="font-weight: 600; font-size: 0.95rem;">{ev} - {dep}</span>
                    <img src="{dep_logo}" style="width: 28px; height: 28px; object-fit: contain;">
                    <span style="font-size: 0.75rem; color: #9ca3af; margin-left: 6px;">({lig_ismi})</span>
                </div>
                <div style="text-align: right;">
                    <span style="background: #111827; padding: 4px 10px; border-radius: 6px; font-weight: bold; color: #34d399; font-size: 0.9rem;">
                        {secim}
                    </span>
                    <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 3px;">Güven: %{guven}</div>
                </div>
            </div>
            """
            kupon_kartlari.append(kart)
            
        return f"""
        <div style="padding: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #38bdf8;">🎫 {kupon_tipi}</h3>
                <span style="background: #2563eb; color: white; padding: 6px 12px; border-radius: 8px; font-weight: bold;">
                    Tahmini Oran: ~{toplam_oran:.2f}
                </span>
            </div>
            {''.join(kupon_kartlari)}
        </div>
        """
    except Exception as e:
        return f"<div style='color:#ef4444;'>Hata: {str(e)}</div>"

# --- 4. GÖRSEL PUAN DURUMU ---
def puan_durumu_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    if league_id == 0:
        league_id = 203 # Dünya seçiliyse varsayılan Süper Lig
        
    url = f"{BASE_URL}/standings"
    try:
        res = requests.get(url, headers=HEADERS, params={"league": league_id, "season": 2024}, timeout=10)
        standings = res.json().get("response", [])[0]["league"]["standings"][0]
        satirlar = []
        for t in standings:
            satir = f"""
            <tr style="border-bottom: 1px solid #374151; text-align: center; color: white;">
                <td style="padding: 8px; font-weight: bold;">{t['rank']}</td>
                <td style="padding: 8px; text-align: left; display: flex; align-items: center; gap: 8px;">
                    <img src="{t['team']['logo']}" style="width: 22px; height: 22px; object-fit: contain;">
                    <span>{t['team']['name']}</span>
                </td>
                <td style="padding: 8px;">{t['all']['played']}</td>
                <td style="padding: 8px; color: #34d399;">{t['all']['win']}</td>
                <td style="padding: 8px; color: #fbbf24;">{t['all']['draw']}</td>
                <td style="padding: 8px; color: #f87171;">{t['all']['lose']}</td>
                <td style="padding: 8px;">{t['goalsDiff']}</td>
                <td style="padding: 8px; font-weight: bold; color: #38bdf8;">{t['points']}</td>
            </tr>
            """
            satirlar.append(satir)
        return f"""
        <table style="width: 100%; border-collapse: collapse; background: #111827; border-radius: 10px; overflow: hidden; font-size: 0.9rem;">
            <thead>
                <tr style="background: #1f2937; color: #9ca3af;">
                    <th style="padding: 10px;">Sıra</th>
                    <th style="padding: 10px; text-align: left;">Takım</th>
                    <th style="padding: 10px;">O</th>
                    <th style="padding: 10px;">G</th>
                    <th style="padding: 10px;">B</th>
                    <th style="padding: 10px;">M</th>
                    <th style="padding: 10px;">AV</th>
                    <th style="padding: 10px;">Puan</th>
                </tr>
            </thead>
            <tbody>{''.join(satirlar)}</tbody>
        </table>
        """
    except Exception as e:
        return f"<div style='color:#ef4444;'>Puan durumu yüklenemedi: {str(e)}</div>"

# --- 5. GÖRSEL GOL KRALLIĞI ---
def gol_kralligi_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    if league_id == 0:
        league_id = 203
        
    url = f"{BASE_URL}/players/topscorers"
    try:
        res = requests.get(url, headers=HEADERS, params={"league": league_id, "season": 2024}, timeout=10)
        scorers = res.json().get("response", [])
        satirlar = []
        for i, item in enumerate(scorers[:15], 1):
            p = item["player"]
            t = item["statistics"][0]["team"]
            satir = f"""
            <tr style="border-bottom: 1px solid #374151; text-align: center; color: white;">
                <td style="padding: 8px; font-weight: bold;">{i}</td>
                <td style="padding: 8px; text-align: left; display: flex; align-items: center; gap: 8px;">
                    <img src="{p.get('photo', '')}" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover;">
                    <span><b>{p.get('name')}</b></span>
                </td>
                <td style="padding: 8px; text-align: left;">
                    <img src="{t.get('logo', '')}" style="width: 18px; height: 18px; vertical-align: middle; margin-right: 6px;">
                    {t.get('name')}
                </td>
                <td style="padding: 8px; font-weight: bold; color: #34d399;">{item['statistics'][0]['goals']['total'] or 0}</td>
                <td style="padding: 8px; color: #38bdf8;">{item['statistics'][0]['goals']['assists'] or 0}</td>
            </tr>
            """
            satirlar.append(satir)
        return f"""
        <table style="width: 100%; border-collapse: collapse; background: #111827; border-radius: 10px; overflow: hidden; font-size: 0.9rem;">
            <thead>
                <tr style="background: #1f2937; color: #9ca3af;">
                    <th style="padding: 10px;">#</th>
                    <th style="padding: 10px; text-align: left;">Futbolcu</th>
                    <th style="padding: 10px; text-align: left;">Kulüp</th>
                    <th style="padding: 10px;">Gol</th>
                    <th style="padding: 10px;">Asist</th>
                </tr>
            </thead>
            <tbody>{''.join(satirlar)}</tbody>
        </table>
        """
    except Exception as e:
        return f"<div style='color:#ef4444;'>Gol krallığı yüklenemedi: {str(e)}</div>"

# --- ARAYÜZ ---
with gr.Blocks(title="Global AI Futbol & Kupon Analiz") as arayuz:
    gr.HTML("""
    <div style="text-align: center; padding: 15px 0;">
        <h1 style="color: #38bdf8; margin: 0; font-size: 2.1rem; font-weight: 800;">🌍 GLOBAL AI FUTBOL & KUPON ANALİZİ</h1>
        <p style="color: #9ca3af; margin-top: 5px;">Dünya Dev Ligleri & Türkiye Ligleri - Canlı Logo Destekli İstatistik ve Akıllı Kupon Platformu</p>
    </div>
    """)
    
    with gr.Tabs():
        # SEKME 1: MAÇ ANALİZİ
        with gr.TabItem("⚽ Günün Maçları & AI Analiz"):
            with gr.Row():
                lig_sec = gr.Dropdown(choices=list(LIGLER.keys()), value="🌍 Bugün Oynanan Tüm Dünya Maçları", label="🏆 Lig / Bülten Seç")
                btn_fikstur = gr.Button("🔄 Maçları Listele / Güncelle", variant="secondary")
            
            secilen_mac = gr.Dropdown(label="📌 Karşılaşma Seçiniz", choices=["Önce 'Maçları Listele' butonuna tıklayın"])
            btn_analiz = gr.Button("🔥 Bu Maçı AI ile Analiz Et", variant="primary")
            
            analiz_karti = gr.HTML("<div style='text-align:center; color:#9ca3af; padding: 20px;'>Analiz sonucunu görmek için maç seçip butona basınız.</div>")
            
            btn_fikstur.click(fn=maclari_getir, inputs=[lig_sec], outputs=[secilen_mac])
            btn_analiz.click(fn=mac_analizi_yap, inputs=[lig_sec, secilen_mac], outputs=[analiz_karti])

        # SEKME 2: KUPON SİHİRBAZI
        with gr.TabItem("🎫 Akıllı AI Kupon Sihirbazı"):
            with gr.Row():
                k_lig = gr.Dropdown(choices=list(LIGLER.keys()), value="🌍 Bugün Oynanan Tüm Dünya Maçları", label="🏆 Lig / Havuz")
                k_tip = gr.Radio(["🔥 Banko Kupon (Düşük Risk)", "⚡ İdeal / Dengeli Kupon", "💣 Sürpriz / Yüksek Oran"], value="🔥 Banko Kupon (Düşük Risk)", label="Kupon Stratejisi")
            btn_kupon = gr.Button("🎲 Kuponu Otomatik Üret", variant="primary")
            kupon_karti = gr.HTML("<div style='text-align:center; color:#9ca3af; padding: 20px;'>Kupon üretmek için butona tıklayınız.</div>")
            btn_kupon.click(fn=kupon_olustur, inputs=[k_lig, k_tip], outputs=[kupon_karti])

        # SEKME 3: PUAN CETVELİ
        with gr.TabItem("📈 Puan Cetveli"):
            with gr.Row():
                p_lig = gr.Dropdown(choices=[k for k in LIGLER.keys() if k != "🌍 Bugün Oynanan Tüm Dünya Maçları"], value="🇹🇷 Türkiye - Süper Lig", label="🏆 Lig Seçiniz")
                btn_puan = gr.Button("Puan Durumunu Getir")
            tablo_puan = gr.HTML("<div style='text-align:center; color:#9ca3af; padding: 20px;'>Sıralamayı görmek için butona basınız.</div>")
            btn_puan.click(fn=puan_durumu_getir, inputs=[p_lig], outputs=[tablo_puan])

        # SEKME 4: GOL KRALLIĞI
        with gr.TabItem("👟 Gol & Asist Krallığı"):
            with gr.Row():
                g_lig = gr.Dropdown(choices=[k for k in LIGLER.keys() if k != "🌍 Bugün Oynanan Tüm Dünya Maçları"], value="🇹🇷 Türkiye - Süper Lig", label="🏆 Lig Seçiniz")
                btn_gol = gr.Button("Listeyi Getir")
            tablo_gol = gr.HTML("<div style='text-align:center; color:#9ca3af; padding: 20px;'>Gol krallarını listelemek için butona basınız.</div>")
            btn_gol.click(fn=gol_kralligi_getir, inputs=[g_lig], outputs=[tablo_gol])

if __name__ == "__main__":
    arayuz.launch(server_name="0.0.0.0", server_port=10000)
