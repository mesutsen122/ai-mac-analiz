import gradio as gr
import requests
import pandas as pd
import joblib

# --- API AYARLARI ---
API_KEY = "03e08d07f2d355040c37fb62cdb52d5a"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# --- TÜRKIYE LİGLERİ LİSTESİ ---
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

# --- 1. PUAN DURUMU ÇEKME FONKSİYONU ---
def puan_durumu_getir(lig_adi, sezon=2024):
    league_id = LIGLER.get(lig_adi, 203)
    url = f"{BASE_URL}/standings"
    params = {"league": league_id, "season": sezon}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = res.json()
        
        standings = data.get("response", [])[0]["league"]["standings"][0]
        
        tablo = []
        for team in standings:
            tablo.append({
                "Sıra": team["rank"],
                "Takım": team["team"]["name"],
                "O": team["all"]["played"],
                "G": team["all"]["win"],
                "B": team["all"]["draw"],
                "M": team["all"]["lose"],
                "AG": team["all"]["goals"]["for"],
                "YG": team["all"]["goals"]["against"],
                "AV": team["goalsDiff"],
                "Puan": team["points"]
            })
        return pd.DataFrame(tablo)
    except Exception as e:
        return pd.DataFrame([{"Hata": f"Puan durumu alınamadı: {str(e)}"}])

# --- 2. GOL KRALLIĞI ÇEKME FONKSİYONU ---
def gol_kralligi_getir(lig_adi, sezon=2024):
    league_id = LIGLER.get(lig_adi, 203)
    url = f"{BASE_URL}/players/topscorers"
    params = {"league": league_id, "season": sezon}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = res.json()
        
        scorers = data.get("response", [])
        tablo = []
        for i, item in enumerate(scorers[:15], 1):
            player = item["player"]
            stats = item["statistics"][0]
            tablo.append({
                "Sıra": i,
                "Oyuncu": player.get("name", "Bilinmiyor"),
                "Takım": stats["team"]["name"],
                "Gol": stats["goals"]["total"] or 0,
                "Asist": stats["goals"]["assists"] or 0,
                "Oynanan Maç": stats["games"]["appearences"] or 0
            })
        return pd.DataFrame(tablo)
    except Exception as e:
        return pd.DataFrame([{"Hata": f"Gol krallığı alınamadı: {str(e)}"}])

# --- 3. MAÇ TAHMİN FONKSİYONU ---
def mac_tahmin_et(ev_sahibi, deplasman, ev_attigi, ev_yedigi, dep_attigi, dep_yedigi):
    if model is None:
        return "⚠ Model dosyası bulunamadı."
    
    veri = [[ev_attigi, ev_yedigi, dep_attigi, dep_yedigi]]
    tahmin = model.predict(veri)[0]
    olasiliklar = model.predict_proba(veri)[0]
    
    sonuclar = {1: f"🟢 {ev_sahibi} Galibiyeti", 0: "🟡 Beraberlik", 2: f"🔴 {deplasman} Galibiyeti"}
    
    rapor = f"""
    ### 📊 Maç Analiz Raporu: {ev_sahibi} vs {deplasman}
    * **Tahmin Edilen Sonuç:** **{sonuclar.get(tahmin, 'Belirsiz')}**
    
    **İhtimal Dağılımı:**
    * {ev_sahibi} Kazanır: %{olasiliklar[1]*100:.1f}
    * Beraberlik: %{olasiliklar[0]*100:.1f}
    * {deplasman} Kazanır: %{olasiliklar[2]*100:.1f}
    """
    return rapor

# --- GRADIO ARAYÜZÜ (TABS) ---
with gr.Blocks(title="Türkiye Ligleri Futbol Analiz Platformu", theme=gr.themes.Soft()) as arayuz:
    gr.Markdown("# 🇹🇷 Türkiye Profesyonel Ligleri & AI Analiz Platformu")
    gr.Markdown("Süper Lig, 1. Lig, 2. Lig ve 3. Lig canlı puan cetveli, gol krallığı ve yapay zeka maç tahmin motoru.")
    
    with gr.Tabs():
        # SEKME 1: Puan Durumu
        with gr.TabItem("📈 Puan Durumu"):
            lig_secim_puan = gr.Dropdown(choices=list(LIGLER.keys()), value="Süper Lig", label="Lig Seçiniz")
            btn_puan = gr.Button("Puan Durumunu Getir", variant="primary")
            tablo_puan = gr.Dataframe(label="Güncel Puan Cetveli")
            btn_puan.click(fn=puan_durumu_getir, inputs=[lig_secim_puan], outputs=[tablo_puan])
        
        # SEKME 2: Gol Krallığı
        with gr.TabItem("⚽ Gol Krallığı"):
            lig_secim_gol = gr.Dropdown(choices=list(LIGLER.keys()), value="Süper Lig", label="Lig Seçiniz")
            btn_gol = gr.Button("Gol Krallığını Getir", variant="primary")
            tablo_gol = gr.Dataframe(label="En Çok Gol Atan Oyuncular")
            btn_gol.click(fn=gol_kralligi_getir, inputs=[lig_secim_gol], outputs=[tablo_gol])
            
        # SEKME 3: AI Maç Tahmini
        with gr.TabItem("🤖 AI Maç Tahmin Motoru"):
            with gr.Row():
                ev_takim = gr.Textbox(label="Ev Sahibi Takım", placeholder="Örn: Galatasaray")
                dep_takim = gr.Textbox(label="Deplasman Takım", placeholder="Örn: Fenerbahçe")
            with gr.Row():
                ev_ag = gr.Slider(0, 5, value=2.1, step=0.1, label="Ev Sahibi Maç Başı Gol Ort.")
                ev_yg = gr.Slider(0, 5, value=0.8, step=0.1, label="Ev Sahibi Maç Başı Yediği Gol")
                dep_ag = gr.Slider(0, 5, value=1.8, step=0.1, label="Deplasman Maç Başı Gol Ort.")
                dep_yg = gr.Slider(0, 5, value=1.1, step=0.1, label="Deplasman Maç Başı Yediği Gol")
            btn_tahmin = gr.Button("Yapay Zeka ile Analiz Et", variant="primary")
            sonuc_tahmin = gr.Markdown()
            btn_tahmin.click(
                fn=mac_tahmin_et, 
                inputs=[ev_takim, dep_takim, ev_ag, ev_yg, dep_ag, dep_yg], 
                outputs=[sonuc_tahmin]
            )

if __name__ == "__main__":
    arayuz.launch(server_name="0.0.0.0", server_port=10000)
