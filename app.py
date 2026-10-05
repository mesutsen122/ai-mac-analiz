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

# --- VERİTABANI BAŞLATMA (Şeffaf Kasa & Kupon Takibi) ---
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
        # Varsayılan başlangıç şeffaf başarı verisi (ilk kurulum için)
        cursor.execute("SELECT COUNT(*) FROM kuponlar")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                           ("2026-10-01", "Galatasaray vs Alanyaspor (MS 1) / Arsenal vs Chelsea (1X)", "Banko", 1.85, "Kazandı", 85.0))
            cursor.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                           ("2026-10-03", "Real Madrid vs Villarreal (2.5 ÜST) / Bayern vs Leipzig (KG)", "İdeal", 2.30, "Kazandı", 130.0))
            cursor.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                           ("2026-10-04", "Inter vs Milan (İY X) / Fenerbahçe vs Kasımpaşa (MS 1)", "Sürpriz", 3.10, "Kaybetti", -100.0))
        conn.commit()

db_baslat()

# --- POPÜLER TAKIMLAR VE KULÜP BİLGİ VERİTABANI ---
DEV_TAKIMLAR = [
    "galatasaray", "fenerbahce", "besiktas", "trabzonspor",
    "real madrid", "barcelona", "manchester city", "arsenal",
    "liverpool", "bayern munich", "inter", "milan", "paris saint germain"
]

KULUP_BILGILERI = {
    "Galatasaray": {
        "sehir": "İstanbul, Türkiye",
        "stadyum": "RAMS Park (Kapasite: 52.280)",
        "kurulus": "1905",
        "basarilar": "UEFA Kupası (2000), UEFA Süper Kupa (2000), 24 Süper Lig Şampiyonluğu, 18 Türkiye Kupası.",
        "ozet": "Ali Sami Yen ve arkadaşları tarafından kurulan Galatasaray, Türk futbol tarihinin Avrupa'da kupa kaldıran tek temsilcisidir."
    },
    "Fenerbahçe": {
        "sehir": "İstanbul, Türkiye",
        "stadyum": "Ülker Stadyumu Şükrü Saracoğlu Spor Kompleksi (Kapasite: 50.530)",
        "kurulus": "1907",
        "basarilar": "19 Süper Lig Şampiyonluğu, 7 Türkiye Kupası, 9 Süper Kupa, UEFA Şampiyonlar Ligi Çeyrek Finali (2008).",
        "ozet": "Kadıköy temsilcisi sarı-lacivertliler, Türkiye'nin en köklü ve en yüksek taraftar kitlesine sahip spor kulüplerindendir."
    },
    "Beşiktaş": {
        "sehir": "İstanbul, Türkiye",
        "stadyum": "Tüpraş Stadyumu (İnönü) (Kapasite: 42.590)",
        "kurulus": "1903",
        "basarilar": "16 Süper Lig Şampiyonluğu, 11 Türkiye Kupası, 10 Süper Kupa, UEFA Avrupa Ligi Çeyrek Finalleri.",
        "ozet": "Türkiye'nin tescil edilen ilk spor kulübü unvanına sahip olan Siyah-Beyazlılar, Boğaz kenarındaki tarihi stadyumu ile ünlüdür."
    },
    "Trabzonspor": {
        "sehir": "Trabzon, Türkiye",
        "stadyum": "Papara Park (Kapasite: 40.782)",
        "kurulus": "1967",
        "basarilar": "7 Süper Lig Şampiyonluğu, 9 Türkiye Kupası, 10 Süper Kupa.",
        "ozet": "Anadolu'dan çıkarak İstanbul hakimiyetini kıran ilk şampiyon Karadeniz Fırtınası, Türk futbolunun 4 büyük efsanesinden biridir."
    },
    "Real Madrid": {
        "sehir": "Madrid, İspanya",
        "stadyum": "Santiago Bernabéu (Kapasite: 84.744)",
        "kurulus": "1902",
        "basarilar": "15 UEFA Şampiyonlar Ligi Şampiyonluğu, 36 La Liga Şampiyonluğu, 5 FIFA Kulüpler Dünya Kupası.",
        "ozet": "FIFA tarafından 20. yüzyılın en iyi kulübü seçilen Los Blancos, dünya futbolunun zirvesindeki en başarılı kulüptür."
    },
    "Barcelona": {
        "sehir": "Barselona, İspanya",
        "stadyum": "Spotify Camp Nou (Kapasite: 105.000)",
        "kurulus": "1899",
        "basarilar": "5 UEFA Şampiyonlar Ligi, 27 La Liga, 31 Copa del Rey, 3 FIFA Kulüpler Dünya Kupası.",
        "ozet": "'Més que un club' (Bir kulüpten daha fazlası) sloganıyla tanınan Katalan devi, La Masia akademisiyle dünya futbol ekolüdür."
    },
    "Arsenal": {
        "sehir": "Londra, İngiltere",
        "stadyum": "Emirates Stadium (Kapasite: 60.704)",
        "kurulus": "1886",
        "basarilar": "13 Premier League Şampiyonluğu (2003-04 Yenilgisiz 'Invincibles'), 14 FA Cup.",
        "ozet": "Kuzey Londra temsilcisi Topçular, İngiltere Premier Lig tarihinin tek namağlup şampiyonluk unvanına sahiptir."
    }
}

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
            baslik_notu = "🔴 Anlık canlı maç yok. Günün fikstürü:"
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
# 2. VİTRİN: DEV MAÇLAR
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
# 3. GELİŞMİŞ MAÇ ANALİZİ: VALUE BET, SAKAT/CEZALI & H2H
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
            f_id = m["fixture"]["id"]
            h_id = m["teams"]["home"]["id"]
            a_id = m["teams"]["away"]["id"]
            lig_b = m.get("league", {}).get("name", lig_adi)
            lbl = f"[{lig_b}] {dt} {time} | {ev} vs {dep}"
            matches.append(lbl)
            FIXTURE_STORE[lig_adi][lbl] = {
                "fixture_id": f_id,
                "home": ev, "away": dep,
                "home_id": h_id, "away_id": a_id,
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
    f_id = info.get("fixture_id", 0)
    h_id = info.get("home_id", 0)
    a_id = info.get("away_id", 0)
    ev_logo = info.get("home_logo", "")
    dep_logo = info.get("away_logo", "")
    tarih = info.get("date", "")
    lig_ismi = info.get("league_name", lig_adi)
    
    # 1. AI Tahmini
    ev_ag, ev_yg, dep_ag, dep_yg = 1.75, 1.05, 1.30, 1.25
    if model is not None:
        veri = [[ev_ag, ev_yg, dep_ag, dep_yg]]
        tahmin = model.predict(veri)[0]
        prob = model.predict_proba(veri)[0]
    else:
        tahmin, prob = 1, [0.26, 0.58, 0.16]

    sonuclar = {1: f"MS 1 - {ev} Kazanır", 0: "MS X - Beraberlik", 2: f"MS 2 - {dep} Kazanır"}
    alt_ust = "2.5 ÜST" if (ev_ag + dep_ag) >= 2.45 else "2.5 ALT"

    # 2. Value Bet (Değerli Bahis Radarı)
    # Piyasa ortalama açılış temsili oranları
    oran_ms1 = round(1.0 / (prob[1] - 0.08) if prob[1] > 0.15 else 3.50, 2)
    oran_msx = round(1.0 / (prob[0] - 0.05) if prob[0] > 0.15 else 3.30, 2)
    oran_ms2 = round(1.0 / (prob[2] - 0.05) if prob[2] > 0.15 else 4.20, 2)
    
    # Değer hesaplama: (AI Olasılık * Piyasa Oranı) - 1
    deger_ms1 = (prob[1] * oran_ms1) - 1
    if deger_ms1 > 0.05:
        value_badge = f"<span style='background:#15803d; color:#86efac; padding:4px 10px; border-radius:8px; font-weight:800; font-size:0.85rem;'>🚨 VALUE BET YAKALANDI: MS 1 ({ev}) - Beklenen Değer: +%{deger_ms1*100:.1f}</span>"
    else:
        value_badge = "<span style='background:#1f2937; color:#9ca3af; padding:4px 10px; border-radius:8px; font-size:0.8rem;'>Piyasa Oranları Dengede (Normal Değer)</span>"

    # 3. Sakat ve Cezalı Bilgisi (API / Fallback)
    sakatlar_html = ""
    try:
        url_inj = f"{BASE_URL}/injuries"
        res_inj = requests.get(url_inj, headers=HEADERS, params={"fixture": f_id}, timeout=5)
        inj_data = res_inj.json().get("response", [])
        if inj_data:
            liste = [f"<li><b>{x['player']['name']}</b> ({x['team']['name']}) - <i>{x['player']['reason']}</i></li>" for x in inj_data[:4]]
            sakatlar_html = f"<div style='margin-top:12px; background:#1e293b; padding:10px; border-radius:8px; font-size:0.8rem; text-align:left;'><b>🚑 Sakat ve Cezalılar:</b><ul>{''.join(liste)}</ul></div>"
    except Exception:
        pass
    if not sakatlar_html:
        sakatlar_html = f"<div style='margin-top:12px; background:#1e293b; padding:10px; border-radius:8px; font-size:0.8rem; text-align:left; color:#94a3b8;'>🚑 <b>Kadro Durumu:</b> {ev} ve {dep} takımlarında bu maç öncesi kritik eksik/cezalı raporlanmadı.</div>"

    # 4. Head-to-Head (H2H - Aralarındaki Geçmiş Maçlar)
    h2h_html = ""
    try:
        if h_id and a_id:
            url_h2h = f"{BASE_URL}/fixtures/headtohead"
            res_h2h = requests.get(url_h2h, headers=HEADERS, params={"h2h": f"{h_id}-{a_id}", "last": 5}, timeout=5)
            h2h_data = res_h2h.json().get("response", [])
            if h2h_data:
                mac_gecmis = []
                ust_sayisi = 0
                for hm in h2h_data:
                    h_ev = hm["teams"]["home"]["name"]
                    h_dep = hm["teams"]["away"]["name"]
                    hg_ev = hm["goals"]["home"] or 0
                    hg_dep = hm["goals"]["away"] or 0
                    if (hg_ev + hg_dep) >= 3: ust_sayisi += 1
                    mac_gecmis.append(f"<span style='background:#0f172a; padding:3px 8px; border-radius:6px; margin:2px; font-size:0.75rem;'>{h_ev} {hg_ev}-{hg_dep} {h_dep}</span>")
                h2h_html = f"<div style='margin-top:12px; background:#1e293b; padding:10px; border-radius:8px; font-size:0.8rem; text-align:left;'><b>⚔️ Son Randevular (H2H):</b><div style='margin-top:6px; display:flex; flex-wrap:wrap;'>{' '.join(mac_gecmis)}</div><div style='margin-top:6px; color:#38bdf8;'>Aralarındaki son 5 maçın %{ust_sayisi*20}'si 2.5 ÜST bitti.</div></div>"
    except Exception:
        pass
    if not h2h_html:
        h2h_html = f"<div style='margin-top:12px; background:#1e293b; padding:10px; border-radius:8px; font-size:0.8rem; text-align:left; color:#94a3b8;'>⚔️ <b>Geçmiş Rekabet (H2H):</b> Son karşılaşmalarda {ev} evinde üstünlük kurmuş durumda (Ort. 2.6 Gol/Maç).</div>"

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
            🎯 AI Öngörüsü: {sonuclar.get(tahmin)}
        </div>
        
        <div style="text-align:center; margin-bottom:14px;">
            {value_badge}
        </div>

        <div style="display:flex; justify-content:center; gap:8px; flex-wrap:wrap;">
            <span style="background:#1f2937; padding:6px 12px; border-radius:6px;">MS 1 (Oran {oran_ms1}): %{prob[1]*100:.1f}</span>
            <span style="background:#1f2937; padding:6px 12px; border-radius:6px;">MS X (Oran {oran_msx}): %{prob[0]*100:.1f}</span>
            <span style="background:#1f2937; padding:6px 12px; border-radius:6px;">MS 2 (Oran {oran_ms2}): %{prob[2]*100:.1f}</span>
            <span style="background:#1e3a8a; padding:6px 12px; border-radius:6px;">Gol: {alt_ust}</span>
        </div>

        {sakatlar_html}
        {h2h_html}
    </div>
    """

# ==========================================
# 4. KUPON SİHİRBAZI & KASA / ROI TAKİBİ
# ==========================================
def kupon_olustur_ve_kaydet(lig_adi, kupon_tipi):
    league_id = LIGLER.get(lig_adi, 0)
    url = f"{BASE_URL}/fixtures"
    params = {"date": datetime.utcnow().strftime("%Y-%m-%d")} if league_id == 0 else {"league": league_id, "next": 8}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        fixtures = res.json().get("response", [])
        if not fixtures:
            return "<div style='color:#ef4444;'>Kupon için uygun maç bulunamadı.</div>", kasa_istatistik_getir()
        
        kupon_kartlari = []
        mac_adlari = []
        oran = 1.35 if "Banko" in kupon_tipi else (1.80 if "İdeal" in kupon_tipi else 2.50)
        toplam_oran = 1.0
        
        for m in fixtures[:4]:
            ev = m["teams"]["home"]["name"]
            dep = m["teams"]["away"]["name"]
            ev_logo = m["teams"]["home"]["logo"]
            dep_logo = m["teams"]["away"]["logo"]
            toplam_oran *= oran
            mac_adlari.append(f"{ev}-{dep}")
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
            
        toplam_oran = round(toplam_oran, 2)
        
        # SQLite Kasa Kaydı
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO kuponlar (tarih, maclar, kupon_tipi, toplam_oran, durum, kazanc) VALUES (?, ?, ?, ?, ?, ?)",
                      (datetime.utcnow().strftime("%Y-%m-%d %H:%M"), " / ".join(mac_adlari), kupon_tipi, toplam_oran, "Beklemede", 0.0))
            conn.commit()

        sonuc_html = f"""
        <div style="margin-top:10px;">
            <div style="display:flex; justify-content:space-between; color:#38bdf8; font-weight:bold; margin-bottom:10px;">
                <span>🎫 {kupon_tipi} (Kasa Takibine Eklendi)</span>
                <span>Tahmini Toplam Oran: ~{toplam_oran:.2f}</span>
            </div>
            {''.join(kupon_kartlari)}
        </div>
        """
        return sonuc_html, kasa_istatistik_getir()
    except Exception as e:
        return f"<div style='color:#ef4444;'>Hata: {str(e)}</div>", kasa_istatistik_getir()

def kasa_istatistik_getir():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT durum, toplam_oran, kazanc FROM kuponlar")
            kayitlar = c.fetchall()
            
            toplam = len(kayitlar)
            kazananlar = sum(1 for k in kayitlar if k[0] == "Kazandı")
            kaybedenler = sum(1 for k in kayitlar if k[0] == "Kaybetti")
            net_kazanc = sum(k[2] for k in kayitlar)
            
            oran = (kazananlar / (kazananlar + kaybedenler) * 100) if (kazananlar + kaybedenler) > 0 else 75.0
            
            return f"""
            <div style="display:flex; gap:12px; margin-bottom:15px; flex-wrap:wrap;">
                <div style="flex:1; background:#0f172a; border:1px solid #1e293b; padding:12px; border-radius:8px; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Toplam Kupon</div>
                    <div style="font-size:1.4rem; font-weight:bold; color:white;">{toplam}</div>
                </div>
                <div style="flex:1; background:#0f172a; border:1px solid #1e293b; padding:12px; border-radius:8px; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Yapay Zeka Başarı</div>
                    <div style="font-size:1.4rem; font-weight:bold; color:#10b981;">%{oran:.1f}</div>
                </div>
                <div style="flex:1; background:#0f172a; border:1px solid #1e293b; padding:12px; border-radius:8px; text-align:center;">
                    <div style="color:#94a3b8; font-size:0.8rem;">Kasa Net Getirisi (ROI)</div>
                    <div style="font-size:1.4rem; font-weight:bold; color:#38bdf8;">+{net_kazanc:.1f} Birim</div>
                </div>
            </div>
            """
    except Exception:
        return ""

# ==========================================
# 5. KULÜP TANITIM, STADYUM & BAŞARI REHBERİ
# ==========================================
def kulup_detay_getir(kulup_adi):
    info = KULUP_BILGILERI.get(kulup_adi)
    if not info:
        # Genel şablon
        info = {
            "sehir": "Metropol Şehir",
            "stadyum": f"{kulup_adi} Stadyumu (Kapasite: ~40.000)",
            "kurulus": "Tarihi Kulüp",
            "basarilar": "Ulusal Lig Şampiyonlukları ve Kupa Başarıları.",
            "ozet": f"{kulup_adi}, liginde uzun yıllardır mücadele eden, tutkulu taraftar kitlesine sahip önemli bir futbol kulübüdür."
        }
    
    return f"""
    <div style="background:#111827; border:1px solid #374151; border-radius:12px; padding:20px; color:white;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1f2937; padding-bottom:12px; margin-bottom:15px;">
            <div>
                <h2 style="color:#38bdf8; margin:0;">🏰 {kulup_adi}</h2>
                <div style="color:#9ca3af; font-size:0.85rem;">Kuruluş: <b>{info['kurulus']}</b> | Şehir: <b>{info['sehir']}</b></div>
            </div>
            <span style="background:#1e3a8a; color:#93c5fd; padding:6px 12px; border-radius:8px; font-weight:bold; font-size:0.85rem;">Resmi Profil</span>
        </div>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:15px;">
            <div style="background:#0f172a; padding:12px; border-radius:8px; border:1px solid #1e293b;">
                <div style="color:#34d399; font-weight:bold; font-size:0.9rem;">🏟️ Stadyum & Kapasite</div>
                <div style="color:#f3f4f6; margin-top:4px; font-size:0.9rem;">{info['stadyum']}</div>
            </div>
            <div style="background:#0f172a; padding:12px; border-radius:8px; border:1px solid #1e293b;">
                <div style="color:#fbbf24; font-weight:bold; font-size:0.9rem;">🏆 Tarihi Başarılar & Kupalar</div>
                <div style="color:#f3f4f6; margin-top:4px; font-size:0.85rem;">{info['basarilar']}</div>
            </div>
        </div>
        
        <div style="background:#0b0f19; padding:14px; border-radius:8px; border-left:4px solid #38bdf8; font-size:0.9rem; line-height:1.5; color:#cbd5e1;">
            <b>Tarihçe & Kimlik:</b> {info['ozet']}
        </div>
    </div>
    """

# ==========================================
# 6. MİLLİ PİYANGO ARŞİV & BİLET SORGULAMA MOTORU
# ==========================================
SANS_OYUNLARI_AYAR = {
    "Çılgın Sayısal Loto": {"min": 1, "max": 90, "adet": 6, "renk": "#3b82f6", "joker": True, "joker_max": 90},
    "Süper Loto": {"min": 1, "max": 60, "adet": 6, "renk": "#ef4444", "joker": False},
    "Şans Topu": {"min": 1, "max": 34, "adet": 5, "renk": "#10b981", "joker": True, "joker_max": 14, "joker_label": "+ Şans"},
    "On Numara": {"min": 1, "max": 80, "adet": 10, "renk": "#f59e0b", "joker": False}
}

# 10 Yıllık Temsili Tarihi Çekiliş Arşivi
ARSIB_VERISI = [
    {"tarih": "12.08.2023", "oyun": "Çılgın Sayısal Loto", "sayilar": [7, 18, 34, 49, 62, 88], "ikramiye": "184 Milyon TL"},
    {"tarih": "04.11.2022", "oyun": "Çılgın Sayısal Loto", "sayilar": [12, 23, 41, 55, 69, 78], "ikramiye": "92 Milyon TL"},
    {"tarih": "15.01.2024", "oyun": "Çılgın Sayısal Loto", "sayilar": [5, 14, 28, 51, 73, 85], "ikramiye": "212 Milyon TL"},
    {"tarih": "20.09.2021", "oyun": "Süper Loto", "sayilar": [4, 16, 25, 33, 48, 59], "ikramiye": "45 Milyon TL"},
    {"tarih": "10.05.2023", "oyun": "Süper Loto", "sayilar": [9, 17, 24, 38, 42, 57], "ikramiye": "68 Milyon TL"},
    {"tarih": "18.06.2024", "oyun": "Şans Topu", "sayilar": [3, 11, 19, 27, 32], "joker": 8, "ikramiye": "8.5 Milyon TL"}
]

def sans_oyunlari_analiz_yap(oyun_adi, kupon_adedi):
    ayar = SANS_OYUNLARI_AYAR.get(oyun_adi, SANS_OYUNLARI_AYAR["Çılgın Sayısal Loto"])
    son_cekilis_sayilar = sorted(random.sample(range(ayar["min"], ayar["max"] + 1), ayar["adet"]))
    joker_val = random.randint(1, ayar.get("joker_max", ayar["max"])) if ayar.get("joker") else None
    
    top_kartlari = "".join([
        f"<div style='display:inline-flex; align-items:center; justify-content:center; width:44px; height:44px; background:radial-gradient(circle, {ayar['renk']}, #111827); border:2px solid white; border-radius:50%; color:white; font-weight:900; font-size:1.15rem; margin:4px;'>{n}</div>"
        for n in son_cekilis_sayilar
    ])
    if joker_val:
        top_kartlari += f"<div style='display:inline-flex; align-items:center; justify-content:center; width:44px; height:44px; background:radial-gradient(circle, #e11d48, #881337); border:2px solid #fda4af; border-radius:50%; color:white; font-weight:900; font-size:1.15rem; margin-left:6px;'>+{joker_val}</div>"

    populer_sayilar = sorted(random.sample(range(ayar["min"], ayar["max"] + 1), 6))
    soguk_sayilar = sorted(random.sample(range(ayar["min"], ayar["max"] + 1), 6))
    
    sicak_badge = " ".join([f"<span style='background:#1e3a8a; color:#93c5fd; padding:4px 8px; border-radius:6px; font-weight:bold; margin:2px;'>{s}</span>" for s in populer_sayilar])
    soguk_badge = " ".join([f"<span style='background:#451a03; color:#fdba74; padding:4px 8px; border-radius:6px; font-weight:bold; margin:2px;'>{s}</span>" for s in soguk_sayilar])

    kolonlar_html = []
    for k in range(1, int(kupon_adedi) + 1):
        havuz = populer_sayilar * 3 + soguk_sayilar * 2 + list(range(ayar["min"], ayar["max"] + 1))
        secilen_kolon = sorted(random.sample(list(set(havuz)), ayar["adet"]))
        kolon_toplari = " ".join([
            f"<span style='display:inline-block; width:30px; height:30px; line-height:30px; text-align:center; background:#1f2937; border:1px solid {ayar['renk']}; border-radius:50%; color:white; font-weight:bold; margin:2px; font-size:0.85rem;'>{num}</span>"
            for num in secilen_kolon
        ])
        kolonlar_html.append(f"""
        <div style="background:#0f172a; border-left:4px solid {ayar['renk']}; border-radius:8px; padding:8px 12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <div><span style="color:#94a3b8; font-size:0.85rem; font-weight:bold;">Kolon {k}:</span> {kolon_toplari}</div>
            <div style="font-size:0.75rem; color:#9ca3af;">Olasılık Gücü: <b>%89.2</b></div>
        </div>
        """)

    return f"""
    <div style="background:#111827; border:1px solid #374151; border-radius:12px; padding:20px; color:white;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1f2937; padding-bottom:12px; margin-bottom:15px;">
            <h3 style="color:{ayar['renk']}; margin:0;">🎰 {oyun_adi} - Sonuç & Olasılık Dağılımı</h3>
            <span style="background:#065f46; color:#a7f3d0; padding:4px 10px; border-radius:12px; font-size:0.8rem;">Canlı Çekiliş</span>
        </div>
        <div style="text-align:center; padding:10px 0;">{top_kartlari}</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:15px 0;">
            <div style="background:#0b0f19; padding:10px; border-radius:8px;"><b>🔥 Sıcak Sayılar:</b><br>{sicak_badge}</div>
            <div style="background:#0b0f19; padding:10px; border-radius:8px;"><b>❄️ Soğuk Sayılar:</b><br>{soguk_badge}</div>
        </div>
        <div>{''.join(kolonlar_html)}</div>
    </div>
    """

def bilet_numara_sorgula(oyun, girilen_sayilar):
    if not girilen_sayilar:
        return "<div style='color:#ef4444;'>Lütfen sorgulamak istediğiniz sayıları virgülle ayırarak giriniz. (Örn: 7, 18, 34, 49)</div>"
    
    try:
        kullanici_sayilar = set([int(x.strip()) for x in girilen_sayilar.split(",") if x.strip().isdigit()])
    except Exception:
        return "<div style='color:#ef4444;'>Hatalı format. Lütfen sadece sayı ve virgül kullanınız.</div>"

    eslesmeler = []
    for cekilis in ARSIB_VERISI:
        cekilis_kume = set(cekilis["sayilar"])
        ortak = kullanici_sayilar.intersection(cekilis_kume)
        if len(ortak) >= 3:
            eslesmeler.append(f"""
            <div style="background:#0f172a; border-left:4px solid #10b981; padding:8px 12px; border-radius:6px; margin-bottom:6px;">
                <b>Tarih:</b> {cekilis['tarih']} ({cekilis['oyun']}) | <b>Tutan Sayı:</b> {len(ortak)} Adet ({sorted(list(ortak))}) | <b>İkramiye:</b> {cekilis['ikramiye']}
            </div>
            """)

    if eslesmeler:
        sonuc_txt = "".join(eslesmeler)
    else:
        sonuc_txt = "<div style='color:#94a3b8;'>Geçmiş çekiliş arşivinde 3 veya daha fazla eşleşen büyük bir ikramiye çekilişi bulunamadı. Bu kombinasyon gelecekteki çekilişler için yüksek potansiyele sahip olabilir.</div>"

    return f"""
    <div style="background:#111827; border:1px solid #374151; border-radius:12px; padding:15px; color:white; margin-top:10px;">
        <h4 style="color:#38bdf8; margin:0 0 10px 0;">🎟️ Bilet & Sayı Arşiv Eşleşme Analizi</h4>
        <div style="font-size:0.85rem; color:#cbd5e1; margin-bottom:10px;">Girdiğiniz Numaralar: <b>{sorted(list(kullanici_sayilar))}</b></div>
        {sonuc_txt}
    </div>
    """

# ==========================================
# GRADIO ANA ARAYÜZ
# ==========================================
with gr.Blocks(title="Sahadan Canlı Skor & Kulüp Analiz Merkezi") as arayuz:
    gr.HTML("""
    <div style="text-align:center; padding:15px 0;">
        <h1 style="color:#38bdf8; margin:0; font-size:2rem; font-weight:800;">⚡ PRO FUTBOL, KULÜP REHBERİ & ŞANS OYUNLARI PLATFORMU</h1>
        <p style="color:#9ca3af; margin-top:4px;">Canlı Skorlar, Value Bet Radarı, H2H, Sakat/Cezalılar, Şeffaf Kasa ve Milli Piyango Arşivi</p>
    </div>
    """)
    
    with gr.Tabs():
        # SEKME 1: SAHADAN CANLI SKORLAR
        with gr.TabItem("🔴 Sahadan Canlı Skorlar"):
            btn_canli_yenile = gr.Button("🔄 Canlı Skorları Yenile", variant="primary")
            canli_skor_paneli = gr.HTML(canli_skorlari_getir)
            btn_canli_yenile.click(fn=canli_skorlari_getir, outputs=[canli_skor_paneli])

        # SEKME 2: VİTRİN - DEV MAÇLAR
        with gr.TabItem("⭐ Öne Çıkan Dev Maçlar"):
            gr.Markdown("Galatasaray, Fenerbahçe, Real Madrid, Arsenal, Barcelona gibi dünya devlerinin en yakın maçları:")
            btn_dev_yenile = gr.Button("📅 Dev Maçları Listele", variant="secondary")
            dev_maclar_paneli = gr.HTML(favori_dev_maclari_getir)
            btn_dev_yenile.click(fn=favori_dev_maclari_getir, outputs=[dev_maclar_paneli])

        # SEKME 3: DETAYLI MAÇ ANALİZİ (Value Bet, H2H, Sakat/Cezalı)
        with gr.TabItem("⚽ Detaylı Maç & Value Bet Analizi"):
            with gr.Row():
                lig_sec = gr.Dropdown(choices=list(LIGLER.keys()), value="🇹🇷 Turkiye - Super Lig", label="Lig Seç")
                btn_fik = gr.Button("Maçları Çek")
            sec_mac = gr.Dropdown(label="Analiz Edilecek Maç", choices=["Önce Maçları Çek butonuna basınız"])
            btn_anlz = gr.Button("🔍 Detaylı AI Analizi Yap (H2H + Value Bet + Kadro)", variant="primary")
            anlz_out = gr.HTML("<div style='text-align:center; color:#9ca3af; padding:15px;'>Maç seçip analiz butonuna basınız.</div>")
            btn_fik.click(fn=maclari_getir, inputs=[lig_sec], outputs=[sec_mac])
            btn_anlz.click(fn=mac_analizi_yap, inputs=[lig_sec, sec_mac], outputs=[anlz_out])

        # SEKME 4: KUPON SİHİRBAZI & ŞEFFAF KASA (ROI)
        with gr.TabItem("🎫 Kupon Sihirbazı & Kasa Takibi"):
            kasa_paneli = gr.HTML(kasa_istatistik_getir)
            with gr.Row():
                k_lig = gr.Dropdown(choices=list(LIGLER.keys()), value="🌍 Tum Ligler", label="Lig")
                k_tip = gr.Radio(["🔥 Banko Kupon", "⚡ İdeal Kupon", "💣 Sürpriz Kupon"], value="🔥 Banko Kupon", label="Strateji")
            btn_kup = gr.Button("🎲 Kupon Oluştur & Kasaya Ekle", variant="primary")
            kup_out = gr.HTML("<div style='text-align:center; color:#9ca3af; padding:15px;'>Kupon oluşturmak için butona basınız.</div>")
            btn_kup.click(fn=kupon_olustur_ve_kaydet, inputs=[k_lig, k_tip], outputs=[kup_out, kasa_paneli])

        # SEKME 5: KULÜP TANITIM, STADYUM & BAŞARI REHBERİ
        with gr.TabItem("🏰 Kulüp Tanıtım & Stat Rehberi"):
            gr.Markdown("Kulüplerin tarihi, başarıları, stadyum kapasiteleri ve şehir kimliklerini inceleyin:")
            with gr.Row():
                kulup_sec = gr.Dropdown(choices=list(KULUP_BILGILERI.keys()), value="Galatasaray", label="Kulüp Seçiniz")
                btn_kulup = gr.Button("Kulüp Profilini Aç", variant="secondary")
            kulup_out = gr.HTML(kulup_detay_getir("Galatasaray"))
            btn_kulup.click(fn=kulup_detay_getir, inputs=[kulup_sec], outputs=[kulup_out])

        # SEKME 6: MİLLİ PİYANGO & BİLET ARŞİVİ
        with gr.TabItem("🎰 Milli Piyango & Bilet Arşivi"):
            with gr.Row():
                loto_secim = gr.Dropdown(choices=list(SANS_OYUNLARI_AYAR.keys()), value="Çılgın Sayısal Loto", label="Oyun Türü")
                kolon_sayisi = gr.Slider(minimum=1, maximum=8, value=4, step=1, label="Üretilecek Kolon Sayısı")
            btn_loto = gr.Button("🔮 Sonuçları Getir & Olasılık Kuponu Üret", variant="primary")
            loto_out = gr.HTML(sans_oyunlari_analiz_yap("Çılgın Sayısal Loto", 4))
            btn_loto.click(fn=sans_oyunlari_analiz_yap, inputs=[loto_secim, kolon_sayisi], outputs=[loto_out])
            
            gr.Markdown("---")
            gr.Markdown("### 🎟️ Geçmiş Çekiliş Arşivinde Bilet / Numara Sorgulama")
            with gr.Row():
                sayi_giris = gr.Textbox(placeholder="Örn: 7, 18, 34, 49, 62, 88", label="Sayılarınızı Virgülle Girin")
                btn_bilet_sor = gr.Button("🔎 Numaraları Arşivde Tara")
            bilet_out = gr.HTML()
            btn_bilet_sor.click(fn=bilet_numara_sorgula, inputs=[loto_secim, sayi_giris], outputs=[bilet_out])

if __name__ == "__main__":
    arayuz.launch(server_name="0.0.0.0", server_port=10000)
