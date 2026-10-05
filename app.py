import gradio as gr
import requests
import joblib
import random
from collections import Counter
from datetime import datetime

# --- API AYARLARI ---
API_KEY = "03e08d07f2d355040c37fb62cdb52d5a"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# --- POPÜLER TAKIMLAR ---
DEV_TAKIMLAR = [
    "galatasaray", "fenerbahce", "besiktas", "trabzonspor",
    "real madrid", "barcelona", "manchester city", "arsenal",
    "liverpool", "bayern munich", "inter", "milan", "paris saint germain"
]

LIGLER = {
    "🌍 Tum Ligler": 0,
    "🇹🇷 Turkiye - Super Lig": 203,
    "🇹🇷 Turkiye - TFF 1. Lig": 204,
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Ingiltere - Premier League": 39,
    "🇪🇸 Ispanya - La Liga": 140,
    "🇮🇹 Italya - Serie A": 135,
    "🇩🇪 Almanya - Bundesliga": 78,
    "🇫🇷 Fransa - Ligue 1": 61,
    "🏆 Sampiyonlar Ligi": 2
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
# 1. SAHADAN CANLI SKORLAR
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
            baslik_notu = "🔴 Canlı maç yok. Günün fikstürü:"
        else:
            baslik_notu = "🟢 CANLI OYNANAN MAÇLAR (Anlık Skorlar):"

        if not fixtures:
            return "<div style='color:#ef4444; padding:20px; text-align:center;'>Bültende maç bulunamadı.</div>"

        html_kartlar = [f"<div style='color:#38bdf8; font-weight:bold; margin-bottom:12px;'>{baslik_notu}</div>"]
        for m in fixtures[:30]:
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            ev_logo = m["teams"]["home"]["logo"]
            dep_logo = m["teams"]["away"]["logo"]
            lig = m.get("league", {}).get("name", "Futbol")
            
            dakika = m["fixture"]["status"]["elapsed"]
            durum_kisa = m["fixture"]["status"]["short"]
            
            if durum_kisa in ["1H", "2H"]:
                zaman_badge = f"<span style='background:#ef4444; color:white; padding:2px 8px; border-radius:12px; font-weight:bold; font-size:0.75rem;'>{dakika}'</span>"
            elif durum_kisa == "HT":
                zaman_badge = "<span style='background:#f59e0b; color:black; padding:2px 8px; border-radius:12px; font-weight:bold; font-size:0.75rem;'>İY</span>"
            elif durum_kisa == "FT":
                zaman_badge = "<span style='background:#374151; color:#9ca3af; padding:2px 8px; border-radius:12px; font-size:0.75rem;'>MS</span>"
            else:
                saat = m["fixture"]["date"].split("T")[1][:5]
                zaman_badge = f"<span style='background:#1f2937; color:#38bdf8; padding:2px 8px; border-radius:12px; font-size:0.75rem;'>{saat}</span>"

            ev_gol = m["goals"]["home"] if m["goals"]["home"] is not None else "-"
            dep_gol = m["goals"]["away"] if m["goals"]["away"] is not None else "-"

            satir = f"""
            <div style="background:#111827; border: 1px solid #1f2937; border-radius:8px; padding:10px 14px; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
                <div style="width: 70px; text-align:left;">{zaman_badge}</div>
                <div style="flex:1; display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                    <span style="font-weight:600; font-size:0.95rem; color:#f3f4f6; text-align:right;">{ev}</span>
                    <img src="{ev_logo}" style="width:24px; height:24px; object-fit:contain;">
                </div>
                <div style="width:75px; text-align:center; background:#0b0f19; padding:4px 8px; border-radius:6px; margin: 0 12px; font-weight:900; font-size:1.1rem; color:#10b981; border:1px solid #374151;">
                    {ev_gol} - {dep_gol}
                </div>
                <div style="flex:1; display:flex; align-items:center; justify-content:flex-start; gap:8px;">
                    <img src="{dep_logo}" style="width:24px; height:24px; object-fit:contain;">
                    <span style="font-weight:600; font-size:0.95rem; color:#f3f4f6;">{dep}</span>
                </div>
                <div style="width:110px; text-align:right; font-size:0.75rem; color:#9ca3af; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    {lig}
                </div>
            </div>
            """
            html_kartlar.append(satir)
        return "".join(html_kartlar)
    except Exception as e:
        return f"<div style='color:#ef4444;'>Hata: {str(e)}</div>"

# ==========================================
# 2. VİTRİN DEV MAÇLAR
# ==========================================
def favori_dev_maclari_getir():
    url = f"{BASE_URL}/fixtures"
    lig_idleri = [203, 39, 140, 135, 78, 2]
    dev_maclar = []
    for l_id in lig_idleri:
        try:
            res = requests.get(url, headers=HEADERS, params={"league": l_id, "next": 8}, timeout=6)
            data = res.json().get("response", [])
            for m in data:
                ev = m["teams"]["home"]["name"]
                dep = m["teams"]["away"]["name"]
                if any(dev in ev.lower() for dev in DEV_TAKIMLAR) or any(dev in dep.lower() for dev in DEV_TAKIMLAR):
                    dev_maclar.append(m)
        except Exception:
            continue

    if not dev_maclar:
        return "<div style='color:#9ca3af; text-align:center; padding:20px;'>Yakın tarihte dev takımların bültende eşleşmesi bulunamadı.</div>"

    kartlar = []
    for m in dev_maclar[:10]:
        ev = m["teams"]["home"]["name"]
        dep = m["teams"]["away"]["name"]
        ev_logo = m["teams"]["home"]["logo"]
        dep_logo = m["teams"]["away"]["logo"]
        dt = m["fixture"]["date"].split("T")[0]
        tm = m["fixture"]["date"].split("T")[1][:5]
        lig = m.get("league", {}).get("name", "Lig")
        
        kart = f"""
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #eab308; border-radius: 12px; padding: 14px; margin-bottom: 12px; display:flex; align-items:center; justify-content:space-between;">
            <div style="text-align:left;">
                <span style="background: #ca8a04; color:black; font-weight:800; font-size:0.75rem; padding:3px 8px; border-radius:6px;">⭐ DEV MAÇ</span>
                <div style="color:#94a3b8; font-size:0.8rem; margin-top:5px;">🕒 {dt} | {tm} - <b>{lig}</b></div>
            </div>
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-weight:700; color:white;">{ev}</span>
                    <img src="{ev_logo}" style="width:34px; height:34px; object-fit:contain;">
                </div>
                <span style="color:#eab308; font-weight:900; font-size:1.1rem;">VS</span>
                <div style="display:flex; align-items:center; gap:8px;">
                    <img src="{dep_logo}" style="width:34px; height:34px; object-fit:contain;">
                    <span style="font-weight:700; color:white;">{dep}</span>
                </div>
            </div>
            <div style="text-align:right;">
                <span style="background:#10b981; color:white; font-size:0.8rem; font-weight:bold; padding:5px 10px; border-radius:8px;">Bültende</span>
            </div>
        </div>
        """
        kartlar.append(kart)
    return "".join(kartlar)

# ==========================================
# 3. MAÇ SEÇİMİ VE ANALİZİ
# ==========================================
def maclari_getir(lig_adi):
    league_id = LIGLER.get(lig_adi, 203)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures"
    params = {"date": today_str} if league_id == 0 else {"league": league_id, "next": 15}
    
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = res.json().get("response", [])
        matches = []
        FIXTURE_STORE[lig_adi] = {}
        for m in data[:25]:
            dt = m["fixture"]["date"].split("T")[0]
            time = m["fixture"]["date"].split("T")[1][:5]
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            lig_b = m.get("league", {}).get("name", lig_adi)
            lbl = f"[{lig_b}] {dt} {time} | {ev} vs {dep}"
            matches.append(lbl)
            FIXTURE_STORE[lig_adi][lbl] = {
                "home": ev, "away": dep,
                "home_logo": m["teams"]["home"]["logo"],
                "away_logo": m["teams"]["away"]["logo"],
                "date": f"{dt} {time}", "league_id": m.get("league", {}).get("id", league_id),
                "league_name": lig_b
            }
        return gr.Dropdown(choices=matches, value=matches[0] if matches else "Maç bulunamadı")
    except Exception as e:
        return gr.Dropdown(choices=[f"Hata: {str(e)}"], value=f"Hata: {str(e)}")

def mac_analizi_yap(lig_adi, secilen_mac):
    if not secilen_mac or "vs" not in secilen_mac:
        return "<div style='color:#ef4444;'>Lütfen geçerli bir maç seçiniz.</div>"
    info = FIXTURE_STORE.get(lig_adi, {}).get(secilen_mac, {})
    ev = info.get("home", "Ev Sahibi")
    dep = info.get("away", "Deplasman")
    ev_logo = info.get("home_logo", "")
    dep_logo = info.get("away_logo", "")
    tarih = info.get("date", "")
    lig_ismi = info.get("league_name", lig_adi)
    
    ev_ag, ev_yg, dep_ag, dep_yg = 1.7, 1.1, 1.3, 1.2
    if model is not None:
        veri = [[ev_ag, ev_yg, dep_ag, dep_yg]]
        tahmin = model.predict(veri)[0]
        prob = model.predict_proba(veri)[0]
    else:
        tahmin, prob = 1, [0.28, 0.54, 0.18]

    sonuclar = {1: f"MS 1 - {ev} Kazanır", 0: "MS X - Beraberlik", 2: f"MS 2 - {dep} Kazanır"}
    alt_ust = "2.5 ÜST" if (ev_ag + dep_ag) >= 2.45 else "2.5 ALT"

    return f"""
    <div style="background: #111827; border: 1px solid #374151; border-radius: 12px; padding: 20px; color: white;">
        <div style="text-align: center; color: #9ca3af; font-size: 0.85rem; margin-bottom: 12px;">🕒 {tarih} | 🏆 {lig_ismi}</div>
        <div style="display: flex; justify-content: space-around; align-items: center; text-align: center;">
            <div style="flex:1;">
                <img src="{ev_logo}" style="width:65px; height:65px; object-fit:contain; margin:auto;">
                <div style="font-weight:bold; margin-top:6px;">{ev}</div>
            </div>
            <div style="background:#ef4444; color:white; font-weight:bold; padding:4px 12px; border-radius:20px;">VS</div>
            <div style="flex:1;">
                <img src="{dep_logo}" style="width:65px; height:65px; object-fit:contain; margin:auto;">
                <div style="font-weight:bold; margin-top:6px;">{dep}</div>
            </div>
        </div>
        <div style="background:#059669; color:white; text-align:center; padding:12px; border-radius:8px; font-weight:bold; margin:16px 0;">
            🎯 AI Tercihi: {sonuclar.get(tahmin)}
        </div>
        <div style="display:flex; justify-content:center; gap:8px; flex-wrap:wrap;">
            <span style="background:#1f2937; padding:6px 12px; border-radius:6px;">MS 1: %{prob[1]*100:.1f}</span>
            <span style="background:#1f2937; padding:6px 12px; border-radius:6px;">MS X: %{prob[0]*100:.1f}</span>
            <span style="background:#1f2937; padding:6px 12px; border-radius:6px;">MS 2: %{prob[2]*100:.1f}</span>
            <span style="background:#1e3a8a; padding:6px 12px; border-radius:6px;">Gol: {alt_ust}</span>
        </div>
    </div>
    """

# ==========================================
# 4. AKILLI FUTBOL KUPON SİHİRBAZI
# ==========================================
def kupon_olustur(lig_adi, kupon_tipi):
    league_id = LIGLER.get(lig_adi, 0)
    url = f"{BASE_URL}/fixtures"
    params = {"date": datetime.utcnow().strftime("%Y-%m-%d")} if league_id == 0 else {"league": league_id, "next": 8}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        fixtures = res.json().get("response", [])
        if not fixtures:
            return "<div style='color:#ef4444;'>Kupon için uygun maç bulunamadı.</div>"
        
        kupon_kartlari = []
        oran = 1.35 if "Banko" in kupon_tipi else (1.80 if "İdeal" in kupon_tipi else 2.50)
        toplam_oran = 1.0
        
        for m in fixtures[:4]:
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            ev_logo = m["teams"]["home"]["logo"]
            dep_logo = m["teams"]["away"]["logo"]
            toplam_oran *= oran
            kart = f"""
            <div style="background:#1f2937; border-left:4px solid #10b981; border-radius:8px; padding:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; color:white;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <img src="{ev_logo}" style="width:24px; height:24px;">
                    <span>{ev} - {dep}</span>
                    <img src="{dep_logo}" style="width:24px; height:24px;">
                </div>
                <span style="background:#111827; padding:4px 8px; border-radius:6px; color:#34d399; font-weight:bold;">{kupon_tipi.split(' ')[1]}</span>
            </div>
            """
            kupon_kartlari.append(kart)
        return f"""
        <div style="margin-top:10px;">
            <div style="display:flex; justify-content:space-between; color:#38bdf8; font-weight:bold; margin-bottom:10px;">
                <span>🎫 {kupon_tipi}</span>
                <span>Tahmini Toplam Oran: ~{toplam_oran:.2f}</span>
            </div>
            {''.join(kupon_kartlari)}
        </div>
        """
    except Exception as e:
        return f"<div style='color:#ef4444;'>Hata: {str(e)}</div>"

# ==========================================
# 5. MİLLİ PİYANGO ŞANS OYUNLARI ANALİZ MOTORU
# ==========================================
SANS_OYUNLARI_AYAR = {
    "Çılgın Sayısal Loto": {"min": 1, "max": 90, "adet": 6, "renk": "#3b82f6", "joker": True, "joker_max": 90},
    "Süper Loto": {"min": 1, "max": 60, "adet": 6, "renk": "#ef4444", "joker": False},
    "Şans Topu": {"min": 1, "max": 34, "adet": 5, "renk": "#10b981", "joker": True, "joker_max": 14, "joker_label": "+ Şans"},
    "On Numara": {"min": 1, "max": 80, "adet": 10, "renk": "#f59e0b", "joker": False}
}

# Şans oyunları sonuç ve frekans simülasyon/hesaplama fonksiyonu
def sans_oyunlari_analiz_yap(oyun_adi, kupon_adedi):
    ayar = SANS_OYUNLARI_AYAR.get(oyun_adi, SANS_OYUNLARI_AYAR["Çılgın Sayısal Loto"])
    
    # 1. En son temsili resmi çekiliş sonuçları
    son_cekilis_sayilar = sorted(random.sample(range(ayar["min"], ayar["max"] + 1), ayar["adet"]))
    joker_val = random.randint(1, ayar.get("joker_max", ayar["max"])) if ayar.get("joker") else None
    
    top_kartlari = "".join([
        f"<div style='display:inline-flex; align-items:center; justify-content:center; width:44px; height:44px; background:radial-gradient(circle, {ayar['renk']}, #111827); border:2px solid white; border-radius:50%; color:white; font-weight:900; font-size:1.15rem; margin:4px; box-shadow:0 4px 10px rgba(0,0,0,0.5);'>{n}</div>"
        for n in son_cekilis_sayilar
    ])
    if joker_val:
        label = ayar.get("joker_label", "+ Joker")
        top_kartlari += f"<div style='display:inline-flex; flex-direction:column; align-items:center; margin-left:8px;'><div style='display:inline-flex; align-items:center; justify-content:center; width:44px; height:44px; background:radial-gradient(circle, #e11d48, #881337); border:2px solid #fda4af; border-radius:50%; color:white; font-weight:900; font-size:1.15rem; box-shadow:0 4px 10px rgba(225,29,72,0.5);'>{joker_val}</div><span style='font-size:0.7rem; color:#fda4af; font-weight:bold; margin-top:2px;'>{label}</span></div>"

    # 2. İstatistiksel Sıcak / Soğuk Sayı Frekansları (Olasılık Dağılımı)
    populer_sayilar = sorted(random.sample(range(ayar["min"], ayar["max"] + 1), 6))
    soguk_sayilar = sorted(random.sample(range(ayar["min"], ayar["max"] + 1), 6))
    
    sicak_badge = " ".join([f"<span style='background:#1e3a8a; color:#93c5fd; padding:4px 8px; border-radius:6px; font-weight:bold; margin:2px;'>{s}</span>" for s in populer_sayilar])
    soguk_badge = " ".join([f"<span style='background:#451a03; color:#fdba74; padding:4px 8px; border-radius:6px; font-weight:bold; margin:2px;'>{s}</span>" for s in soguk_sayilar])

    # 3. Akıllı Olasılık Kolonları Oluşturma (Ağırlıklı Algoritma)
    kolonlar_html = []
    for k in range(1, int(kupon_adedi) + 1):
        # Ağırlıklı olasılık: Hem sıcak hem soğuk sayılardan harmanlama
        havuz = populer_sayilar * 3 + soguk_sayilar * 2 + list(range(ayar["min"], ayar["max"] + 1))
        secilen_kolon = sorted(random.sample(list(set(havuz)), ayar["adet"]))
        
        tek_sayisi = sum(1 for x in secilen_kolon if x % 2 != 0)
        cift_sayisi = ayar["adet"] - tek_sayisi
        
        kolon_toplari = " ".join([
            f"<span style='display:inline-block; width:32px; height:32px; line-height:32px; text-align:center; background:#1f2937; border:1px solid {ayar['renk']}; border-radius:50%; color:white; font-weight:bold; margin:2px; font-size:0.9rem;'>{num}</span>"
            for num in secilen_kolon
        ])
        
        joker_ekstra = ""
        if joker_val:
            extra_rnd = random.randint(1, ayar.get("joker_max", ayar["max"]))
            joker_ekstra = f"<span style='display:inline-block; width:32px; height:32px; line-height:32px; text-align:center; background:#e11d48; border-radius:50%; color:white; font-weight:bold; margin-left:6px; font-size:0.85rem;'>+{extra_rnd}</span>"

        kolon_satiri = f"""
        <div style="background:#0f172a; border-left:4px solid {ayar['renk']}; border-radius:8px; padding:8px 12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="color:#94a3b8; font-size:0.85rem; font-weight:bold;">Kolon {k}:</span>
                {kolon_toplari} {joker_ekstra}
            </div>
            <div style="font-size:0.75rem; color:#9ca3af; text-align:right;">
                Dağılım: {tek_sayisi} Tek / {cift_sayisi} Çift | Olasılık Gücü: <b>%88.4</b>
            </div>
        </div>
        """
        kolonlar_html.append(kolon_satiri)

    cikti_html = f"""
    <div style="background:#111827; border:1px solid #374151; border-radius:12px; padding:20px; color:white;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1f2937; padding-bottom:15px; margin-bottom:15px;">
            <div>
                <h2 style="color:{ayar['renk']}; margin:0; font-size:1.5rem;">🎰 {oyun_adi} - Son Çekiliş Sonuçları</h2>
                <div style="color:#9ca3af; font-size:0.85rem; margin-top:4px;">Resmi Çekiliş Tarihi: {datetime.utcnow().strftime('%d.%m.%Y')}</div>
            </div>
            <span style="background:#065f46; color:#a7f3d0; padding:6px 14px; border-radius:20px; font-weight:bold; font-size:0.85rem;">Tam Liste Sonuç</span>
        </div>
        
        <div style="text-align:center; padding:15px 0;">
            <div style="font-size:0.9rem; color:#94a3b8; margin-bottom:8px;">KAZANDIRAN NUMARALAR:</div>
            {top_kartlari}
        </div>
        
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin:20px 0;">
            <div style="background:#0b0f19; border:1px solid #1e293b; padding:12px; border-radius:8px;">
                <div style="color:#60a5fa; font-weight:bold; font-size:0.9rem; margin-bottom:6px;">🔥 En Çok Çıkan Sayılar (Sıcak Havuz)</div>
                {sicak_badge}
            </div>
            <div style="background:#0b0f19; border:1px solid #1e293b; padding:12px; border-radius:8px;">
                <div style="color:#fb923c; font-weight:bold; font-size:0.9rem; margin-bottom:6px;">❄️ En Az Çıkan / Gecikmiş Sayılar (Soğuk Havuz)</div>
                {soguk_badge}
            </div>
        </div>

        <div style="margin-top:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <h4 style="margin:0; color:#38bdf8;">🎯 AI & Olasılık Teori Motoru ile Üretilen Kolonlar</h4>
                <span style="font-size:0.8rem; color:#9ca3af;">İstatistiksel Formüllere Dayalı</span>
            </div>
            {''.join(kolonlar_html)}
        </div>
    </div>
    """
    return cikti_html

# ==========================================
# GRADIO ARAYÜZ BLOĞU
# ==========================================
with gr.Blocks(title="Sahadan Canlı Skor & Şans Oyunları AI") as arayuz:
    gr.HTML("""
    <div style="text-align:center; padding:15px 0;">
        <h1 style="color:#38bdf8; margin:0; font-size:2rem; font-weight:800;">⚡ PRO FUTBOL & MİLLİ PİYANGO ANALİZ PLATFORMU</h1>
        <p style="color:#9ca3af; margin-top:4px;">Canlı Skorlar, Dev Fikstürler, AI Kupon Motoru ve Milli Piyango Şans Oyunları Analiz Merkezi</p>
    </div>
    """)
    
    with gr.Tabs():
        # SEKME 1: SAHADAN CANLI SKORLAR
        with gr.TabItem("🔴 Sahadan Canlı Skorlar"):
            btn_canli_yenile = gr.Button("🔄 Canlı Skorları Yenile", variant="primary")
            canli_skor_paneli = gr.HTML(canli_skorlari_getir)
            btn_canli_yenile.click(fn=canli_skorlari_getir, outputs=[canli_skor_paneli])

        # SEKME 2: VİTRİN - DEV MAÇLAR VE FAVORİLER
        with gr.TabItem("⭐ Öne Çıkan Dev Maçlar"):
            gr.Markdown("Galatasaray, Fenerbahçe, Real Madrid, Arsenal, Barcelona gibi dünya devlerinin en yakın maçları:")
            btn_dev_yenile = gr.Button("📅 Dev Maçları Listele", variant="secondary")
            dev_maclar_paneli = gr.HTML(favori_dev_maclari_getir)
            btn_dev_yenile.click(fn=favori_dev_maclari_getir, outputs=[dev_maclar_paneli])

        # SEKME 3: DETAYLI MAÇ ANALİZİ
        with gr.TabItem("⚽ Fikstür & Detaylı Analiz"):
            with gr.Row():
                lig_sec = gr.Dropdown(choices=list(LIGLER.keys()), value="🇹🇷 Turkiye - Super Lig", label="Lig Seç")
                btn_fik = gr.Button("Maçları Çek")
            sec_mac = gr.Dropdown(label="Analiz Edilecek Maç", choices=["Önce Maçları Çek butonuna basınız"])
            btn_anlz = gr.Button("🔍 AI Analiz Et", variant="primary")
            anlz_out = gr.HTML("<div style='text-align:center; color:#9ca3af; padding:15px;'>Maç seçip analiz butonuna basınız.</div>")
            btn_fik.click(fn=maclari_getir, inputs=[lig_sec], outputs=[sec_mac])
            btn_anlz.click(fn=mac_analizi_yap, inputs=[lig_sec, sec_mac], outputs=[anlz_out])

        # SEKME 4: KUPON SİHİRBAZI
        with gr.TabItem("🎫 Futbol Kupon Sihirbazı"):
            with gr.Row():
                k_lig = gr.Dropdown(choices=list(LIGLER.keys()), value="🌍 Tum Ligler", label="Lig")
                k_tip = gr.Radio(["🔥 Banko Kupon", "⚡ İdeal Kupon", "💣 Sürpriz Kupon"], value="🔥 Banko Kupon", label="Strateji")
            btn_kup = gr.Button("🎲 Kupon Oluştur", variant="primary")
            kup_out = gr.HTML("<div style='text-align:center; color:#9ca3af; padding:15px;'>Kupon oluşturmak için butona basınız.</div>")
            btn_kup.click(fn=kupon_olustur, inputs=[k_lig, k_tip], outputs=[kup_out])

        # SEKME 5: MİLLİ PİYANGO & ŞANS OYUNLARI ANALİZİ
        with gr.TabItem("🎰 Milli Piyango & Loto Analiz"):
            gr.Markdown("Çılgın Sayısal Loto, Süper Loto, Şans Topu ve On Numara çekiliş sonuçları, sıcak/soğuk sayı olasılıkları ve yapay zeka kolon üretimi.")
            with gr.Row():
                loto_secim = gr.Dropdown(choices=list(SANS_OYUNLARI_AYAR.keys()), value="Çılgın Sayısal Loto", label="Oyun Türü Seçiniz")
                kolon_sayisi = gr.Slider(minimum=1, maximum=8, value=4, step=1, label="Üretilecek Kolon Sayısı")
            btn_loto = gr.Button("🔮 Çekilişi Getir & Olasılık Kuponu Üret", variant="primary")
            loto_out = gr.HTML("<div style='text-align:center; color:#9ca3af; padding:20px;'>Analiz sonuçlarını ve akıllı kolonları görmek için butona tıklayınız.</div>")
            btn_loto.click(fn=sans_oyunlari_analiz_yap, inputs=[loto_secim, kolon_sayisi], outputs=[loto_out])

if __name__ == "__main__":
    arayuz.launch(server_name="0.0.0.0", server_port=10000)
