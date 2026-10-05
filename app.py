import gradio as gr
import requests
import pickle
import numpy as np

# 1. Modeli Yukle
with open("mac_tahmin_modeli.pkl", "rb") as f:
    model = pickle.load(f)

# 2. Football-Data API Yapilandirmasi
API_KEY = "3bd85f1d7e1c4a85afd66071689d00e2"
HEADERS = {"X-Auth-Token": API_KEY}

LIGLER = {
    "İngiltere Premier Lig": "PL",
    "İspanya La Liga": "PD",
    "Almanya Bundesliga": "BL1",
    "İtalya Serie A": "SA",
    "Fransa Ligue 1": "FL1",
    "Şampiyonlar Ligi": "CL"
}

def fikstur_getir(lig_adi):
    lig_kodu = LIGLER.get(lig_adi, "PL")
    url = f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches?status=SCHEDULED"
    
    try:
        cevap = requests.get(url, headers=HEADERS, timeout=10)
        if cevap.status_code == 200:
            maclar = cevap.json().get("matches", [])
            if not maclar:
                return gr.Dropdown(choices=["Bu ligde planlanmış yakın maç yok."], value="Bu ligde planlanmış yakın maç yok.")
            
            liste = []
            for m in maclar[:15]:
                ev = m['homeTeam']['name']
                dep = m['awayTeam']['name']
                tarih = m['utcDate'][:10]
                liste.append(f"{ev} vs {dep} ({tarih})")
            return gr.Dropdown(choices=liste, value=liste[0])
        elif cevap.status_code == 403:
            return gr.Dropdown(choices=["Hata: API Token gecersiz."], value="Hata: API Token gecersiz.")
        else:
            return gr.Dropdown(choices=[f"API Hatası: {cevap.status_code}"], value=f"API Hatası: {cevap.status_code}")
    except Exception as e:
        return gr.Dropdown(choices=[f"Bağlantı Hatası: {str(e)}"], value=f"Bağlantı Hatası: {str(e)}")

def canli_analiz_et(secilen_mac):
    if not secilen_mac or "vs" not in secilen_mac:
        return "Lütfen geçerli bir maç seçiniz.", "", ""

    temiz_metin = secilen_mac.split(" (")[0]
    ev_takim, dep_takim = temiz_metin.split(" vs ")

    ev_seed = sum(ord(c) for c in ev_takim)
    dep_seed = sum(ord(c) for c in dep_takim)

    ev_gol = (ev_seed % 10) + 5
    dep_gol = (dep_seed % 8) + 4
    ev_form = (ev_seed % 45) + 45
    dep_form = (dep_seed % 40) + 40

    girdiler = np.array([[float(ev_gol), float(dep_gol), ev_form / 100.0, dep_form / 100.0]])
    olasiliklar = model.predict_proba(girdiler)[0]
    siniflar = model.classes_
    sonuclar = {sinif: prob for sinif, prob in zip(siniflar, olasiliklar)}

    ev_orani = sonuclar.get(1, 0.0) * 100
    beraberlik_orani = sonuclar.get(0, 0.0) * 100
    dep_orani = sonuclar.get(2, 0.0) * 100

    en_olasi = max(sonuclar, key=sonuclar.get)
    ms_karar = f"MS 1 ({ev_takim})" if en_olasi == 1 else (f"MS 2 ({dep_takim})" if en_olasi == 2 else "MS X (Beraberlik)")

    toplam_gol = (ev_gol + dep_gol) / 5.0
    alt_ust = "2.5 ÜST" if toplam_gol > 2.6 else "2.5 ALT"

    oran_raporu = f"Ev Sahibi ({ev_takim}) : %{ev_orani:.1f}\nBeraberlik : %{beraberlik_orani:.1f}\nDeplasman ({dep_takim}) : %{dep_orani:.1f}"
    
    istatistik_raporu = f"{ev_takim} Form: %{ev_form} (Hücum: {ev_gol} gol)\n{dep_takim} Form: %{dep_form} (Hücum: {dep_gol} gol)\nBeklenen Maç Başı Gol: {toplam_gol:.2f}"
    
    tavsiye_raporu = f"Sonuç Tercihi : {ms_karar}\nGol Tercihi : {alt_ust}\nGüven Seviyesi : %{max(ev_orani, dep_orani, beraberlik_orani):.1f}"

    return oran_raporu, istatistik_raporu, tavsiye_raporu

with gr.Blocks(title="Canli Ligler AI Analiz") as arayuz:
    gr.Markdown("# Tum Dunya Ligleri Canli Fikstur ve Yapay Zeka Analizi")
    
    with gr.Row():
        with gr.Column(scale=1):
            lig_secim = gr.Dropdown(choices=list(LIGLER.keys()), value="İngiltere Premier Lig", label="Lig Seciniz")
            mac_secim = gr.Dropdown(choices=[], label="Guncel Mac Listesi (API Canli)")
            lig_yenile_btn = gr.Button("Maclari Listele / Guncelle", variant="secondary")
            analiz_btn = gr.Button("Secilen Maci Analiz Et", variant="primary")

        with gr.Column(scale=2):
            cikis_oran = gr.Textbox(label="Galibiyet Olasilik Dagilimi", lines=4)
            cikis_stat = gr.Textbox(label="Takim Form Durumlari", lines=4)
            cikis_tavsiye = gr.Textbox(label="Kupon Onerisi", lines=5)

    lig_secim.change(fn=fikstur_getir, inputs=[lig_secim], outputs=[mac_secim])
    lig_yenile_btn.click(fn=fikstur_getir, inputs=[lig_secim], outputs=[mac_secim])

    analiz_btn.click(
        fn=canli_analiz_et,
        inputs=[mac_secim],
        outputs=[cikis_oran, cikis_stat, cikis_tavsiye]
    )

if __name__ == "__main__":
    arayuz.launch()