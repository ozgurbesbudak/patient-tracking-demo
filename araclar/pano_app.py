#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pano_app.py — Streamlit interaktif hasta [gizli] (SALT-OKUNUR görüntüleyici).

CSV/rapor dosya[gizli] OKUR ve filtrelenebilir, sik bir panoda gosterir. Hicbir
dosyaya YAZMAZ; duz dosyalar otorite kaynak olarak kalir (CLAUDE.md Bolum 4).
Betimleyicidir; klinik yorum/hukum ICERMEZ (CLAUDE.md Bolum 0). Renkler
dekoratiftir, normal/anormal hukmu tasimaz.

Calistir:  python -m streamlit run araclar/pano_app.py
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from egilim import analiz, ozet_metin  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# ----------------------------------------------------------------------------
# Sabitler: aktif tedavi protokolu (durum_ozeti.py ile ayni kaynak)
# ----------------------------------------------------------------------------
PROTOKOL_AD = "CLAD + LDAC + VEN (28 günde bir)"
KUR1_D1 = datetime(2026, 6, 15)
PROTOKOL_ILAC = [
    ("Cladribine", "kemoterapi",       datetime(2026, 6, 15), datetime(2026, 6, 19), "10 mg IV · günde 1 · D1–5"),
    ("Cytarabine (LDAC)", "kemoterapi", datetime(2026, 6, 15), datetime(2026, 6, 25), "2×20 mg cilt altı · D1–10"),
    ("Venetoclax", "akıllı ilaç",       datetime(2026, 6, 16), datetime(2026, 7, 4),  "400 mg ağızdan · D1–21 · kademeli 100→200→400 · 04.07 durduruldu"),
]

ETIKET = {
    "wbc": "WBC (Lökosit)", "rbc": "RBC (Eritrosit)", "hemoglobin": "Hemoglobin",
    "hematokrit": "Hematokrit", "trombosit": "Trombosit", "notrofil": "Nötrofil",
    "notrofil_yuzde": "Nötrofil %", "lenfosit": "Lenfosit", "lenfosit_yuzde": "Lenfosit %",
    "monosit_yuzde": "Monosit %", "eozinofil_yuzde": "Eozinofil %", "bazofil_yuzde": "Bazofil %",
    "crp": "CRP", "ldh": "LDH", "kreatinin": "Kreatinin", "ure_bun": "Üre (BUN)",
    "urik_asit": "Ürik Asit", "sodyum": "Sodyum", "potasyum": "Potasyum",
    "kalsiyum": "Kalsiyum", "magnezyum": "Magnezyum", "fosfor": "Fosfor",
    "albumin": "Albümin", "total_protein": "Total Protein", "total_bilirubin": "Total Bilirubin",
    "ast": "AST", "alt": "ALT", "ggt": "GGT", "alp": "ALP", "rdw": "RDW", "mcv": "MCV",
    "pct": "Prokalsitonin (PCT)", "ferritin": "Ferritin", "fibrinojen": "Fibrinojen",
    "d_dimer": "D-Dimer", "egfr": "eGFR", "ure_bun": "Üre (BUN)",
}
# Dekoratif renk paleti (parametre -> cizgi rengi)
RENK = {
    "hemoglobin": "#ef4444", "trombosit": "#3b82f6", "wbc": "#22c55e",
    "notrofil": "#a855f7", "crp": "#ec4899", "potasyum": "#f59e0b",
    "kalsiyum": "#14b8a6", "magnezyum": "#8b5cf6", "ldh": "#06b6d4",
    "pct": "#f97316", "ferritin": "#e11d48", "fibrinojen": "#0ea5e9",
    "d_dimer": "#a3e635", "albumin": "#f472b6",
}
VARSAYILAN_RENK = "#7c3aed"

# Kısa, sade tanımlar (genel-eğitici; grafik başlıklarında gösterilir). Klinik
# yorum değil — yalnızca "bu değer nedir" betimlemesi (CLAUDE.md Bölüm 0).
ACIKLAMA = {
    "wbc": "akyuvar; enfeksiyonla savaşır",
    "notrofil": "akyuvar tipi; bakteri savunması",
    "notrofil_yuzde": "nötrofilin yüzde payı",
    "lenfosit": "akyuvar tipi; bağışıklık",
    "trombosit": "kanamayı durduran hücre",
    "hemoglobin": "oksijen taşıyan kan proteini",
    "hematokrit": "kanın hücre oranı",
    "crp": "genel iltihap/enfeksiyon göstergesi",
    "pct": "prokalsitonin; bakteriyel enfeksiyona özgül",
    "ferritin": "demir deposu + iltihap göstergesi",
    "fibrinojen": "pıhtılaşma proteini; iltihapta artar",
    "d_dimer": "pıhtı yıkım ürünü; pıhtı/iltihap göstergesi",
    "albumin": "kan proteini; beslenme/iltihapla ilişkili",
    "ldh": "hücre yıkımı/doku hasarı göstergesi",
    "potasyum": "elektrolit; kas-sinir/kalp ritmi",
    "sodyum": "elektrolit; sıvı dengesi",
    "kalsiyum": "mineral; kas-sinir/kemik",
    "magnezyum": "mineral; kas-sinir",
    "fosfor": "mineral; kemik/enerji",
    "egfr": "böbrek süzme hızı tahmini (yüksek=iyi)",
    "kreatinin": "kas atığı; böbrek göstergesi",
    "ure_bun": "protein atığı; böbrek/sıvı göstergesi",
    "urik_asit": "hücre yıkımı/böbrek atığı",
}

# Rapor terim sözlüğü (radyoloji/patoloji/epikriz) — sade, genel-eğitici tanımlar.
# Raporda GEÇEN terimler otomatik listelenir. Klinik yorum değil (Bölüm 0).
TERIM_SOZLUK = {
    "plevral efüzyon": "akciğer zarları arasında sıvı birikmesi (halk arasında ‘ciğerde su’)",
    "efüzyon": "bir boşlukta sıvı birikmesi",
    "konsolidasyon": "akciğer dokusunun hava yerine iltihap/sıvıyla dolması (pnömonide tipik)",
    "buzlu cam": "akciğerde hafif puslu görünüm; kısmi dolum/iltihap işareti",
    "mozaik atenüasyon": "akciğerde alacalı yoğunluk farkı (bazı alanlar açık/koyu)",
    "atenüasyon": "BT’de dokunun ışını tutma/yoğunluk derecesi",
    "atelektazi": "akciğerin bir bölümünün sönmesi / havasız kalması",
    "hava bronkogramı": "dolmuş akciğer içinde açık kalan hava yollarının görünmesi",
    "interlobüler septal": "akciğer bölmeciklerini ayıran ince duvarlar",
    "peribronkovasküler": "bronş ve damarların çevresi",
    "intersitisyum": "akciğerin destek (ara) dokusu",
    "kto": "kalp-toraks oranı: kalbin göğüs genişliğine oranı (artışı kalp büyümesi/sıvı olab[gizli])",
    "mediasten": "iki akciğer arasındaki bölge (kalp, büyük damarlar, lenf bezleri)",
    "lenf nod": "lenf bezi (bağışıklık sisteminin süzgeç istasyonu)",
    "lenfadenopati": "büyümüş lenf bezi",
    "nodül": "küçük, yuvarlak doku odağı",
    "lezyon": "dokuda anormal/değişmiş alan",
    "konsolide": "hava yerine dolmuş (katılaşmış) akciğer alanı",
    "hrct": "yüksek çözünürlüklü akciğer tomografisi",
    "santral kateter": "büyük bir damara yerleştirilen ince boru (ilaç/sıvı vermek için)",
    "ödem": "doku içinde sıvı birikmesi (şişlik)",
    "apikal": "akciğerin üst uç kısmı",
    "bazal": "akciğerin alt/taban kısmı",
    "retiküler": "ağsı (örgü benzeri) görünüm",
    "fibrozis": "dokunun sertleşmesi / nedbeleşmesi",
    "hipermetabolik": "PET’te şeker tutulumu artmış = aktif doku",
    "metabolik aktivite": "dokunun PET’teki şeker kullanımı (aktiflik ölçüsü)",
    "infiltrasyon": "hücrelerin bir dokuya yayılıp sızması",
    "biyopsi": "inceleme için küçük doku örneği alınması",
    "aspirasyon": "iğneyle sıvı/hücre örneği çekilmesi",
    "immünofenotip": "hücrelerin yüzey işaretleriyle tiplendirilmesi (akış sitometri)",
    "translokasyon": "iki kromozom parçasının yer değiştirmesi",
    "mutasyon": "bir gendeki kalıcı değişiklik",
    "karyotip": "hücrenin kromozom haritası",
    "sitogenetik": "kromozom düzeyinde genetik inceleme",
}

def etiket(slug):
    return ETIKET.get(slug, slug.replace("_", " ").title())

def renk(slug):
    return RENK.get(slug, VARSAYILAN_RENK)

def baslik(slug, birim=None):
    """Grafik başlığı: 'Ad — kısa tanım (birim)'."""
    ad = etiket(slug)
    ac = ACIKLAMA.get(slug)
    b = f" ({birim})" if birim else ""
    return f"{ad} — {ac}{b}" if ac else f"{ad}{b}"

def rapor_terimleri(metin):
    """Metinde GEÇEN sözlük terimlerini (uzun terim öncelikli) döndürür."""
    m = metin.lower()
    eslesen = [(k, v) for k, v in TERIM_SOZLUK.items() if k in m]
    anahtarlar = [k for k, _ in eslesen]
    return [(k, v) for k, v in eslesen
            if not any(k != k2 and k in k2 for k2 in anahtarlar)]

# Terim eşleştirme: kelime başı sınırı (\b) + uzun terim öncelikli. Sonek serbest
# (Türkçe: efüzyonu, mediastende…). "doktor" içindeki "kto" gibi yanlış eşleşmez.
_TERIM_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(TERIM_SOZLUK, key=len, reverse=True)) + r")",
    re.IGNORECASE)

def terimleri_tooltiple(metin):
    """Rapor metnindeki terimleri, üstüne gelince açıklama gösteren <span>'lerle sarar.
    `...` kod bloklarına (dosya [gizli]) dokunmaz."""
    def wrap(m):
        t = m.group(0)
        tanim = TERIM_SOZLUK.get(t.lower())
        if not tanim:
            return t
        tanim = tanim.replace('"', "'")
        return (f'<span title="{tanim}" style="border-bottom:1px dotted #7dd3fc;'
                f'cursor:help;text-underline-offset:2px">{t}</span>')
    parcalar = re.split(r"(`[^`]*`)", metin)
    for i, p in enumerate(parcalar):
        if not p.startswith("`"):
            parcalar[i] = _TERIM_RE.sub(wrap, p)
    return "".join(parcalar)

# Hazir grafik panelleri (Kan Değerleri sekmesi) — gruplu, duzenli gorunum
PANELLER = {
    "🔬 AML kilit panel": ["wbc", "notrofil", "trombosit", "hemoglobin"],
    "🦠 Enfeksiyon (CRP/PCT)": ["crp", "pct", "notrofil"],
    "🔥 İnflamasyon": ["ferritin", "fibrinojen", "d_dimer", "albumin"],
    "⚡ Elektrolit": ["potasyum", "sodyum", "kalsiyum", "magnezyum", "fosfor"],
    "🩺 Böbrek fonksiyonu": ["egfr", "kreatinin", "ure_bun", "urik_asit"],
}


# ----------------------------------------------------------------------------
# CSS — sik gorunum
# ----------------------------------------------------------------------------
CSS = """
<style>
:root { --accent:#7c3aed; --accent2:#06b6d4; --card:#181b26; --line:#262a38; }
.stApp { background: radial-gradient(1200px 600px at 20% -10%, #1c1030 0%, #0f1117 45%) fixed; }
.block-container { padding-top: 1.2rem; max-width: 1300px; }

.hero {
  border-radius: 22px; padding: 22px 26px; margin-bottom: 14px;
  background: linear-gradient(120deg, #7c3aed 0%, #4f46e5 45%, #06b6d4 110%);
  box-shadow: 0 12px 40px rgba(124,58,237,.35); position: relative; overflow: hidden;
}
.hero:after {
  content:""; position:absolute; right:-40px; top:-40px; width:220px; height:220px;
  background: radial-gradient(circle, rgba(255,255,255,.18), transparent 60%);
}
.hero h1 { color:#fff; font-size: 1.9rem; margin:0; font-weight: 800; letter-spacing:.3px; }
.hero .sub { color: rgba(255,255,255,.92); font-size: 1rem; margin-top: 2px; font-weight:500; }
.hero .chips { margin-top: 12px; display:flex; gap:8px; flex-wrap:wrap; }
.hero .chip {
  background: rgba(255,255,255,.16); color:#fff; padding: 5px 12px; border-radius: 999px;
  font-size:.82rem; backdrop-filter: blur(6px); border:1px solid rgba(255,255,255,.22);
}
.alert {
  border-radius: 14px; padding: 12px 16px; margin: 10px 0 4px 0;
  background: linear-gradient(90deg, rgba(239,68,68,.16), rgba(239,68,68,.05));
  border: 1px solid rgba(239,68,68,.45); color:#fecaca; font-size:.9rem;
}
.alert b { color:#fff; }

/* KPI X[gizli] */
.kpi { padding: 2px 2px 0 2px; }
.kpi .lab { font-size:.72rem; text-transform:uppercase; letter-spacing:.6px; color:#8b90a3; font-weight:600; }
.kpi .val { font-size:1.7rem; font-weight:800; color:#f1f3f8; line-height:1.1; margin-top:2px; }
.kpi .val .u { font-size:.8rem; color:#8b90a3; font-weight:600; margin-left:4px; }
.kpi .chip { display:inline-block; margin-top:6px; padding:2px 9px; border-radius:999px;
  font-size:.76rem; font-weight:700; background:#232838; color:#c7ccda; border:1px solid var(--line); }
.kpi .up:before { content:"▲ "; } .kpi .down:before { content:"▼ "; } .kpi .flat:before { content:"▬ "; }
.kpi .dt { font-size:.72rem; color:#6b7186; margin-top:4px; }
.kpi .tanim { font-size:.68rem; color:#7c8299; margin-top:1px; line-height:1.2; font-weight:500; }
.kpi .refrange { font-size:.72rem; color:#6b7186; margin-top:3px; }
.kpi .refbadge { display:inline-block; margin-top:6px; padding:2px 9px; border-radius:999px;
  font-size:.74rem; font-weight:800; letter-spacing:.3px; }
.kpi .refbadge.low  { background: rgba(245,158,11,.16); color:#fbbf24; border:1px solid rgba(245,158,11,.5); }
.kpi .refbadge.high { background: rgba(56,189,248,.14); color:#7dd3fc; border:1px solid rgba(56,189,248,.4); }
/* referans altı: sakin, betimleyici "dikkat" nabzı (klinik alarm degil) */
@keyframes nabiz {
  0%   { box-shadow: 0 0 0 0 rgba(245,158,11,.45); }
  70%  { box-shadow: 0 0 0 12px rgba(245,158,11,0); }
  100% { box-shadow: 0 0 0 0 rgba(245,158,11,0); }
}
.kpi.dikkat {
  border-radius: 14px; padding: 8px 10px; margin:-2px;
  border: 1px solid rgba(245,158,11,.5);
  background: linear-gradient(180deg, rgba(245,158,11,.08), rgba(245,158,11,.02));
  animation: nabiz 1.9s ease-out infinite;
}
.kpi.dikkat .val { color:#fbbf24; }
/* referans üstü: kırmızı betimleyici "dikkat" nabzı (klinik alarm degil) */
@keyframes nabiz_kirmizi {
  0%   { box-shadow: 0 0 0 0 rgba(239,68,68,.5); }
  70%  { box-shadow: 0 0 0 12px rgba(239,68,68,0); }
  100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
}
.kpi.dikkat-ust {
  border-radius: 14px; padding: 8px 10px; margin:-2px;
  border: 1px solid rgba(239,68,68,.55);
  background: linear-gradient(180deg, rgba(239,68,68,.10), rgba(239,68,68,.02));
  animation: nabiz_kirmizi 1.9s ease-out infinite;
}
.kpi.dikkat-ust .val { color:#f87171; }
.kpi .refbadge.high { background: rgba(239,68,68,.16); color:#f87171; border:1px solid rgba(239,68,68,.5); }

/* bordered container -> X */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(180deg, #191d29, #14171f);
  border: 1px solid var(--line) !important; border-radius: 18px !important;
  box-shadow: 0 6px 22px rgba(0,0,0,.35); padding: 6px 10px !important;
}

/* Sekmeler -> pill */
div[data-baseweb="tab-list"] { gap: 6px; border-bottom: none; flex-wrap: wrap; }
button[data-baseweb="tab"] {
  background:#171a24; border:1px solid var(--line); border-radius:12px !important;
  padding: 6px 14px; color:#aeb4c6;
}
button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(120deg, var(--accent), #4f46e5); color:#fff; border-color: transparent;
  box-shadow: 0 6px 18px rgba(124,58,237,.4);
}
div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] { display:none; }

/* Tedavi & timeline rozet/X */
.badge { display:inline-block; padding:3px 10px; border-radius:999px; font-size:.78rem; font-weight:700; }
.b-active { background: rgba(34,197,94,.16); color:#4ade80; border:1px solid rgba(34,197,94,.4); }
.b-done   { background: rgba(148,163,184,.14); color:#cbd5e1; border:1px solid rgba(148,163,184,.35); }
.b-soon   { background: rgba(245,158,11,.16); color:#fbbf24; border:1px solid rgba(245,158,11,.4); }
.tcard { background:#181b26; border:1px solid var(--line); border-radius:14px; padding:12px 14px; margin-bottom:10px; }
.tcard .name { font-weight:700; color:#f1f3f8; font-size:1.02rem; }
.tcard .meta { color:#9aa0b4; font-size:.86rem; margin-top:2px; }

.tl { border-left: 2px solid var(--line); margin-left: 8px; padding-left: 16px; }
.tl-item { position: relative; margin-bottom: 14px; }
.tl-item:before { content:""; position:absolute; left:-23px; top:4px; width:12px; height:12px;
  border-radius:50%; background: var(--dot,#7c3aed); box-shadow:0 0 0 3px rgba(124,58,237,.18); }
.tl-item .d { color:#c7ccda; font-weight:700; font-size:.92rem; }
.tl-item .t { color:#f1f3f8; font-weight:600; }
.tl-item .x { color:#8b90a3; font-size:.85rem; }

section[data-testid="stSidebar"] { background:#12141c; border-right:1px solid var(--line); }
h2, h3 { color:#eef0f6 !important; }
hr { border-color: var(--line); }
</style>
"""


# ----------------------------------------------------------------------------
# Veri yukleme (salt-okunur)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv(rel, parse_dt=True):
    p = ROOT / rel
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, dtype=str).fillna("")
    if parse_dt and "tarih" in df.columns:
        saat = df["saat"] if "saat" in df.columns else "00:00"
        df["_dt"] = pd.to_datetime(df["tarih"] + " " + saat.replace("", "00:00"),
                                   errors="coerce", format="mixed")
        df["_dt"] = df["_dt"].fillna(pd.to_datetime(df["tarih"], errors="coerce"))
    return df

@st.cache_data(show_spinner=False)
def load_kan():
    df = load_csv("veri/kan_degerleri.csv")
    if df.empty:
        return df
    df["deger_num"] = pd.to_numeric(
        df["deger"].str.replace("<", "", regex=False).str.replace(">", "", regex=False),
        errors="coerce")
    for c in ("ref_alt", "ref_ust"):
        df[c + "_num"] = pd.to_numeric(df[c], errors="coerce")
    return df


def ilac_durumu(bas, bit, bugun):
    if bugun < bas:
        return "başlamadı", "b-soon", f"başlangıç {bas:%d.%m}"
    if bugun > bit:
        return "tamamlandı", "b-done", f"{bas:%d.%m}–{bit:%d.%m}"
    gun = (bugun - bas).days + 1
    return f"aktif · {gun}. gün", "b-active", f"{bas:%d.%m}–{bit:%d.%m}"


def _yekseni_araligi(vals, oran=0.10):
    """Veri min-max'ine gore hafif paylı y-ekseni aralığı (auto-scale)."""
    v = vals.dropna()
    if v.empty:
        return None
    lo, hi = float(v.min()), float(v.max())
    if hi == lo:
        pad = abs(hi) * 0.15 or 1.0
    else:
        pad = (hi - lo) * oran
    return [lo - pad, hi + pad]


def sparkline(sub, slug, n=16):
    """Kucuk trend sparkline (eksensiz); y ekseni veri aralığına oturur."""
    s = sub.dropna(subset=["deger_num"]).sort_values("_dt").tail(n)
    fig = go.Figure(go.Scatter(
        x=s["_dt"], y=s["deger_num"], mode="lines",
        line=dict(color=renk(slug), width=2, shape="spline")))
    fig.update_layout(
        height=54, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=_yekseni_araligi(s["deger_num"], 0.15)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def kucuk_grafik(kan, slug, d1, d2, height=190):
    """Özet için kompakt trend grafiği (ref bantli, tedavi gölgeli, veri-aralığına oturur)."""
    sub = kan[kan["parametre"] == slug]
    sub = sub[(sub["_dt"].dt.date >= d1) & (sub["_dt"].dt.date <= d2)].sort_values("_dt")
    sub = sub[sub["deger_num"].notna()]
    fig = go.Figure()
    for bas, bit, rr in [(datetime(2026,6,15), datetime(2026,6,25), "rgba(34,197,94,0.08)"),
                         (datetime(2026,6,16), datetime(2026,7,4),  "rgba(168,85,247,0.08)")]:
        fig.add_vrect(x0=bas, x1=bit, fillcolor=rr, line_width=0, layer="below")
    r_alt, r_ust = sub["ref_alt_num"].dropna(), sub["ref_ust_num"].dropna()
    ref_alt = r_alt.iloc[-1] if not r_alt.empty else None
    ref_ust = r_ust.iloc[-1] if not r_ust.empty else None
    if ref_alt is not None and ref_ust is not None:
        fig.add_hrect(y0=ref_alt, y1=ref_ust, fillcolor="rgba(34,197,94,0.10)", line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=sub["_dt"], y=sub["deger_num"], mode="lines+markers",
                             line=dict(width=2, color=renk(slug), shape="spline"),
                             marker=dict(size=4, color=renk(slug))))
    dmin = sub["deger_num"].min() if not sub.empty else None
    dmax = sub["deger_num"].max() if not sub.empty else None
    if ref_alt is not None and dmin is not None:
        dmin, dmax = min(dmin, ref_alt), max(dmax, ref_ust)
    if dmin is not None and pd.notna(dmin) and pd.notna(dmax):
        pad = (dmax - dmin) * 0.10 if dmax > dmin else (abs(dmax) * 0.15 or 1.0)
        fig.update_yaxes(range=[dmin - pad, dmax + pad])
    fig.update_layout(template="plotly_dark", height=height,
                      margin=dict(l=6, r=6, t=30, b=6), showlegend=False,
                      hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(255,255,255,0.02)",
                      title=dict(text=baslik(slug), font=dict(size=11, color="#eef0f6")),
                      font=dict(color="#c7ccda", size=10))
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def style_fig(fig, renk_ana=VARSAYILAN_RENK):
    fig.update_layout(
        template="plotly_dark", height=300,
        margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
        hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#c7ccda", size=12),
        title=dict(font=dict(size=15, color="#eef0f6")))
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", showspikes=True,
                     spikethickness=1, spikecolor="#555")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Hasta [gizli] — M.A.B.", page_icon="🩺",
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)

    kan = load_kan()
    ilac = load_csv("veri/ilac_tedavi.csv")
    notlar = load_csv("veri/gunluk_notlar.csv")
    olay = load_csv("veri/surec_olaylari.csv")
    sorular = load_csv("veri/sorular.csv", parse_dt=False)
    nitel = load_csv("veri/lab_nitel.csv")

    son_kan_t = kan["_dt"].max() if (not kan.empty and kan["_dt"].notna().any()) else None
    acik_n = int((sorular["durum"] == "acik").sum()) if not sorular.empty else 0
    ven = next((x for x in PROTOKOL_ILAC if x[1] == "akıllı ilaç"), None)
    bugun = datetime.now()
    ven_durum = ilac_durumu(ven[2], ven[3], bugun)[0] if ven else "—"

    # ---- HERO ----
    st.markdown(f"""
    <div class="hero">
      <h1>🩺 Hasta [gizli]</h1>
      <div class="sub">MAB · AML tedavi takibi</div>
      <div class="chips">
        <span class="chip">📅 Açılış {bugun:%d.%m.%Y %H:%M}</span>
        <span class="chip">🩸 Son kan {('%s' % son_kan_t.strftime('%d.%m.%Y')) if son_kan_t is not None else '—'}</span>
        <span class="chip">💊 {PROTOKOL_AD}</span>
        <span class="chip">🎯 Venetoclax: {ven_durum}</span>
        <span class="chip">❓ {acik_n} açık soru</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="alert">🚑 <b>Acil belirti</b> (ateş >38°C, titreme, nefes darlığı, kanama,
    bilinç bulanıklığı) → vakit kaybetmeden tedavi ekibine/hasta[gizli] Bu pano yalnızca
    kayıtlı verinin <b>betimlemesidir</b>; renkler dekoratiftir, klinik yorum içermez.</div>
    """, unsafe_allow_html=True)

    # ---- Sidebar ----
    st.sidebar.header("⚙️ Filtreler")
    if st.sidebar.button("🔄 Verileri yenile", width="stretch",
                         help="CSV/rapor değiştiyse önbelleği temizler"):
        st.cache_data.clear()
        st.rerun()
    if son_kan_t is not None:
        dmin, dmax = kan["_dt"].min().date(), kan["_dt"].max().date()
    else:
        dmin = dmax = bugun.date()
    varsayilan_bas = max(dmin, dmax - timedelta(days=30))
    aralik = st.sidebar.date_input("Tarih aralığı", value=(varsayilan_bas, dmax),
                                   min_value=dmin, max_value=dmax)
    d1, d2 = (aralik[0], aralik[1]) if isinstance(aralik, (list, tuple)) and len(aralik) == 2 else (dmin, dmax)
    st.sidebar.caption(f"Kan verisi aralığı:\n{dmin:%d.%m.%Y} – {dmax:%d.%m.%Y}")
    st.sidebar.divider()
    st.sidebar.caption("Salt-okunur görüntüleyici · dosya[gizli] yazmaz.\nKaynak: `veri/*.csv`, `raporlar/`")

    def aralikta(df):
        if df.empty or "_dt" not in df.columns:
            return df
        return df[(df["_dt"].dt.date >= d1) & (df["_dt"].dt.date <= d2)]

    sekmeler = st.tabs(["📊 Özet", "🩸 Kan Değerleri", "💊 Tedavi",
                        "🗓️ Zaman Çizelgesi", "📝 Notlar", "📄 Raporlar", "❓ Sorular"])

    # ================= ÖZET =================
    with sekmeler[0]:
        st.markdown("### Kilit değerler")
        kilit = ["hemoglobin", "trombosit", "wbc", "notrofil",
                 "crp", "potasyum", "kalsiyum", "magnezyum",
                 "egfr", "kreatinin", "ure_bun", "urik_asit"]
        for row in [kilit[i:i+4] for i in range(0, len(kilit), 4)]:
            cols = st.columns(4)
            for col, slug in zip(cols, row):
                sub = kan[kan["parametre"] == slug].sort_values("_dt") if not kan.empty else pd.DataFrame()
                with col:
                    box = st.container(border=True)
                    if sub.empty:
                        _t = ACIKLAMA.get(slug, "")
                        box.markdown(f"<div class='kpi'><div class='lab'>{etiket(slug)}</div>"
                                     + (f"<div class='tanim'>{_t}</div>" if _t else "")
                                     + "<div class='val'>—</div></div>", unsafe_allow_html=True)
                        continue
                    son = sub.iloc[-1]
                    cls, arrow_txt = "flat", "0"
                    if len(sub) > 1 and pd.notna(son["deger_num"]) and pd.notna(sub.iloc[-2]["deger_num"]):
                        d = round(son["deger_num"] - sub.iloc[-2]["deger_num"], 2)
                        cls = "up" if d > 0 else "down" if d < 0 else "flat"
                        arrow_txt = f"{abs(d):g}"
                    # referans konumu (BETİMLEYİCİ; klinik/aciliyet hükmü değil)
                    val, ra, ru = son["deger_num"], son["ref_alt_num"], son["ref_ust_num"]
                    kart_cls, refbadge, refrange = "", "", ""
                    if pd.notna(ra) and pd.notna(ru):
                        refrange = f"<div class='refrange'>Referans: {son['ref_alt']}–{son['ref_ust']} {son['birim']}</div>"
                    if pd.notna(val) and pd.notna(ra) and val < ra:
                        kart_cls = "dikkat"
                        refbadge = "<span class='refbadge low'>↓ referans altı</span>"
                    elif pd.notna(val) and pd.notna(ru) and val > ru:
                        kart_cls = "dikkat-ust"
                        refbadge = "<span class='refbadge high'>↑ referans üstü</span>"
                    tanim = ACIKLAMA.get(slug, "")
                    tanim_html = f"<div class='tanim'>{tanim}</div>" if tanim else ""
                    box.markdown(f"""
                    <div class='kpi {kart_cls}'>
                      <div class='lab'>{etiket(slug)}</div>
                      {tanim_html}
                      <div class='val'>{son['deger']}<span class='u'>{son['birim']}</span></div>
                      <span class='chip {cls}'>{arrow_txt}</span>
                      <span class='dt'>· {son['_dt']:%d.%m %H:%M}</span>
                      {refbadge}{refrange}
                    </div>""", unsafe_allow_html=True)
                    box.plotly_chart(sparkline(sub, slug), width="stretch",
                                     config={"displayModeBar": False}, key=f"sp_{slug}")

        st.caption("↓ referans altı / ↑ referans üstü işaretleri yalnızca lab [gizli] "
                   "referans aralığına göre **betimleyicidir** — iyi/kötü ya da acil hükmü "
                   "değildir. Acil durum belirtilerle tanımlanır (üstteki uyarı). "
                   "Değerlendirme tedavi ekibine aittir.")

        st.markdown("### 📈 Eğilim / Değişim")
        egilim_slug = ["crp", "pct", "notrofil", "trombosit", "hemoglobin", "potasyum",
                       "kalsiyum", "magnezyum", "kreatinin", "egfr", "ure_bun"]
        satir = []
        for slug in egilim_slug:
            if kan.empty or slug not in kan["parametre"].values:
                continue
            sub = kan[kan["parametre"] == slug].sort_values("_dt")
            seri = []
            for _, r in sub.iterrows():
                if pd.isna(r["deger_num"]):
                    continue
                ra = r["ref_alt_num"] if pd.notna(r["ref_alt_num"]) else None
                ru = r["ref_ust_num"] if pd.notna(r["ref_ust_num"]) else None
                seri.append((r["_dt"], float(r["deger_num"]), ra, ru))
            a = analiz(seri)
            if not a:
                continue
            yon_s, hiz_s, ref_s = ozet_metin(a)
            satir.append({"Parametre": etiket(slug), "Son": f"{a['son']:g}",
                          "Yön (ardışık)": yon_s, "Günlük değişim": hiz_s,
                          "Referans dışı": ref_s})
        if satir:
            st.dataframe(pd.DataFrame(satir), width="stretch", hide_index=True)
            st.caption("Verinin **son günlerdeki hareketini** betimler — öngörü/uyarı değildir. "
                       "⚡ = son ölçümde hızlı değişim · ardışık yön = kaç gündür aynı yönde. "
                       "Anlam ve aksiyon tedavi ekibine aittir; belirti varsa acil uyarı geçerlidir.")

        st.markdown("### 🩺 Böbrek fonksiyonu")
        bobrek = [p for p in PANELLER["🩺 Böbrek fonksiyonu"] if not kan.empty and p in kan["parametre"].values]
        if bobrek:
            bcols = st.columns(len(bobrek))
            for c, slug in zip(bcols, bobrek):
                c.plotly_chart(kucuk_grafik(kan, slug, d1, d2), width="stretch",
                               config={"displayModeBar": False}, key=f"ozet_bobrek_{slug}")
            st.caption("Yeşil bant = referans aralığı (eGFR'de kaynakta yok). "
                       "Yeşil/mor gölge = kemoterapi/Venetoclax dönemi. Betimleyicidir.")

        st.markdown("### Aktif tedavi & son gelişmeler")
        c1, c2 = st.columns([1, 1])
        with c1:
            box = st.container(border=True)
            box.markdown(f"**💊 {PROTOKOL_AD}**")
            for ad, tur, bas, bit, doz in PROTOKOL_ILAC:
                dur, bcls, ek = ilac_durumu(bas, bit, bugun)
                box.markdown(f"<div class='tcard'><span class='name'>{ad}</span> "
                             f"<span class='badge {bcls}'>{dur}</span>"
                             f"<div class='meta'>{doz} · {ek}</div></div>", unsafe_allow_html=True)
            kur2 = KUR1_D1 + timedelta(days=28)
            box.caption(f"Kür 1 başı {KUR1_D1:%d.%m.%Y} · sonraki kür (tahmini) ~{kur2:%d.%m.%Y}")
        with c2:
            box = st.container(border=True)
            box.markdown("**🗓️ Son olaylar**")
            if not olay.empty:
                for _, r in olay.sort_values("tarih").tail(7)[::-1].iterrows():
                    box.markdown(f"<div style='margin-bottom:7px'><span class='d' "
                                 f"style='color:#c7ccda;font-weight:700'>{r['tarih']}</span> "
                                 f"<span style='color:#f1f3f8'>{r['baslik']}</span></div>",
                                 unsafe_allow_html=True)

    # ================= KAN DEGERLERI =================
    with sekmeler[1]:
        st.markdown("### 🩸 İnteraktif kan trendleri")
        if kan.empty:
            st.warning("Kan verisi bulunamadı.")
        else:
            mevcut = list(kan["parametre"].unique())
            panel_secenek = list(PANELLER.keys()) + ["✏️ Serbest seçim"]
            panel = st.radio("Panel", panel_secenek, horizontal=True, index=0)
            if panel == "✏️ Serbest seçim":
                oncelik = [p for p in ["trombosit", "hemoglobin", "wbc", "notrofil", "crp"] if p in mevcut]
                secim = st.multiselect("Parametre(ler)", options=sorted(mevcut, key=etiket),
                                       default=oncelik, format_func=etiket)
            else:
                secim = [p for p in PANELLER[panel] if p in mevcut]
                eksik = [etiket(p) for p in PANELLER[panel] if p not in mevcut]
                if eksik:
                    st.caption("Veride bulunmayan parametreler atlandı: " + ", ".join(eksik))
            gc1, gc2, gc3 = st.columns(3)
            goster_transf = gc1.toggle("Transfüzyon günleri", value=True)
            goster_tedavi = gc2.toggle("Tedavi dönemleri (gölge)", value=True)
            goster_ref = gc3.toggle("Referans aralığı", value=True,
                                    help="Olması gereken aralığı grafikte gösterir (y eksenini genişletebilir)")

            transf = []
            if not ilac.empty:
                tx = ilac[ilac["tur"] == "transfuzyon"]
                transf = [(r["_dt"], r["ad"]) for _, r in tx.iterrows()
                          if pd.notna(r["_dt"]) and d1 <= r["_dt"].date() <= d2]

            ikili = st.columns(2)
            for i, slug in enumerate(secim):
                sub = aralikta(kan[kan["parametre"] == slug]).sort_values("_dt")
                sub = sub[sub["deger_num"].notna()]
                if sub.empty:
                    continue
                fig = go.Figure()
                if goster_tedavi:
                    for bas, bit, rr in [(datetime(2026,6,15), datetime(2026,6,25), "rgba(34,197,94,0.10)"),
                                         (datetime(2026,6,16), datetime(2026,7,6),  "rgba(168,85,247,0.10)")]:
                        fig.add_vrect(x0=bas, x1=bit, fillcolor=rr, line_width=0, layer="below")
                r_alt = sub["ref_alt_num"].dropna()
                r_ust = sub["ref_ust_num"].dropna()
                ref_alt = r_alt.iloc[-1] if not r_alt.empty else None
                ref_ust = r_ust.iloc[-1] if not r_ust.empty else None
                if goster_ref and ref_alt is not None and ref_ust is not None:
                    # "olması gereken" aralık: bant + kesikli sınır çizgileri + etiket
                    fig.add_hrect(y0=ref_alt, y1=ref_ust, fillcolor="rgba(34,197,94,0.10)",
                                  line_width=0, layer="below",
                                  annotation_text=f"referans {sub.iloc[-1]['ref_alt']}–{sub.iloc[-1]['ref_ust']}",
                                  annotation_position="top left",
                                  annotation_font_color="#7dd3fc", annotation_font_size=11)
                    for y in (ref_alt, ref_ust):
                        fig.add_hline(y=y, line=dict(color="rgba(125,211,252,0.55)", dash="dash", width=1))
                fig.add_trace(go.Scatter(
                    x=sub["_dt"], y=sub["deger_num"], mode="lines+markers",
                    line=dict(width=2.5, color=renk(slug), shape="spline"),
                    marker=dict(size=6, color=renk(slug)), name=etiket(slug)))
                if goster_transf and slug in ("trombosit", "hemoglobin"):
                    anahtar = "trombosit" if slug == "trombosit" else "eritrosit"
                    for gun, ad in transf:
                        if anahtar in ad.lower():
                            fig.add_vline(x=gun, line=dict(color="#f59e0b", dash="dot", width=1.5))
                style_fig(fig, renk(slug))
                # y ekseni: veri aralığına oturur; referans açıksa onu da kapsar
                dmin = sub["deger_num"].min()
                dmax = sub["deger_num"].max()
                if goster_ref and ref_alt is not None and ref_ust is not None:
                    dmin = min(dmin, ref_alt)
                    dmax = max(dmax, ref_ust)
                if pd.notna(dmin) and pd.notna(dmax):
                    pad = (dmax - dmin) * 0.10 if dmax > dmin else (abs(dmax) * 0.15 or 1.0)
                    fig.update_yaxes(range=[dmin - pad, dmax + pad])
                fig.update_layout(title=baslik(slug, sub.iloc[-1]["birim"]))
                ikili[i % 2].plotly_chart(fig, width="stretch", key=f"tr_{slug}")

            st.caption("Yeşil bant + kesikli çizgiler = lab [gizli] aralığı (**bilgi amaçlı**, "
                       "normal/anormal hükmü değil). Mor/yeşil dikey gölge = Venetoclax/kemoterapi "
                       "dönemi. Turuncu çizgi = transfüzyon. Referans bandı y eksenini genişletirse "
                       "'Referans aralığı' anahtarını kapatıp veriye yakınlaşabilirsiniz.")
            with st.expander("📋 Filtrelenmiş ham tablo"):
                tab = aralikta(kan[kan["parametre"].isin(secim)]) if secim else pd.DataFrame()
                if not tab.empty:
                    st.dataframe(tab[["tarih", "saat", "parametre", "deger", "birim",
                                      "ref_alt", "ref_ust", "kaynak_pdf"]].sort_values(["tarih", "parametre"]),
                                 width="stretch", hide_index=True)

    # ================= TEDAVI =================
    with sekmeler[2]:
        st.markdown(f"### 💊 Aktif Tedavi Protokolü")
        st.markdown(f"<div class='tcard'><span class='name'>{PROTOKOL_AD}</span>"
                    f"<div class='meta'>Hastane Hematoloji · 28 günde bir tekrarlanır</div></div>",
                    unsafe_allow_html=True)
        for ad, tur, bas, bit, doz in PROTOKOL_ILAC:
            dur, bcls, ek = ilac_durumu(bas, bit, bugun)
            st.markdown(f"<div class='tcard'><span class='name'>{ad}</span> "
                        f"<span class='badge {bcls}'>{dur}</span>"
                        f"<span style='color:#7c8299'> · {tur}</span>"
                        f"<div class='meta'>{doz} · {ek}</div></div>", unsafe_allow_html=True)
        kur2 = KUR1_D1 + timedelta(days=28)
        st.caption(f"Kür 1 başı {KUR1_D1:%d.%m.%Y} · sonraki kür (28 günde bir, tahmini) "
                   f"~{kur2:%d.%m.%Y} — ekipçe teyit edilecek.")
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🩹 Transfüzyonlar")
            if not ilac.empty:
                for _, r in aralikta(ilac[ilac["tur"] == "transfuzyon"]).sort_values("tarih")[::-1].iterrows():
                    doz = f" · {r['doz']} {r['birim']}".rstrip() if r['doz'] else ""
                    st.markdown(f"<div class='tcard'><span class='name'>{r['tarih']}</span>"
                                f"<div class='meta'>{r['ad']}{doz}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown("#### 💉 İlaç / Destek")
            if not ilac.empty:
                for _, r in aralikta(ilac[ilac["tur"] != "transfuzyon"]).sort_values("tarih")[::-1].iterrows():
                    st.markdown(f"<div class='tcard'><span class='name'>{r['tarih']}</span>"
                                f"<span style='color:#7c8299'> · {r['tur']}</span>"
                                f"<div class='meta'>{r['ad']}</div></div>", unsafe_allow_html=True)

    # ================= ZAMAN CIZELGESI =================
    with sekmeler[3]:
        st.markdown("### 🗓️ Zaman Çizelgesi")
        if not olay.empty:
            dot = {"teshis": "#ef4444", "yatis": "#3b82f6", "taburcu": "#22c55e",
                   "kur_baslangic": "#a855f7", "kur_bitis": "#14b8a6", "onemli": "#f59e0b"}
            html = "<div class='tl'>"
            for _, r in olay.sort_values("tarih")[::-1].iterrows():
                c = dot.get(r["tur"], "#7c3aed")
                html += (f"<div class='tl-item' style='--dot:{c}'>"
                         f"<span class='d'>{r['tarih']}</span> · <span class='t'>{r['baslik']}</span>"
                         f"<div class='x'>{r['aciklama']}</div></div>")
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

    # ================= NOTLAR =================
    with sekmeler[4]:
        st.markdown("### 📝 Günlük Notlar")
        if not notlar.empty:
            kats = sorted(notlar["kategori"].unique())
            sec = st.multiselect("Kategori", kats, default=kats)
            nf = aralikta(notlar[notlar["kategori"].isin(sec)]).sort_values("_dt")
            for _, r in nf[::-1].iterrows():
                st.markdown(f"<div class='tcard'><span class='name'>{r['tarih']}</span>"
                            f"<span style='color:#7c8299'> · {r['kategori']}</span>"
                            f"<div class='meta'>{r['not']}</div></div>", unsafe_allow_html=True)
        st.markdown("### 🧪 Niteliksel Lab")
        if not nitel.empty:
            st.dataframe(aralikta(nitel).sort_values("_dt")[["tarih", "kategori", "test", "sonuc", "birim"]],
                         width="stretch", hide_index=True)

    # ================= RAPORLAR =================
    with sekmeler[5]:
        st.markdown("### 📄 Raporlar")
        kategoriler = {"Görüntüleme": "goruntuleme", "Patoloji / Kemik İliği": "patoloji",
                       "Epikriz": "epikriz", "Tedavi Protokolü": "tedavi-protokolu"}
        c1, c2 = st.columns([1, 2])
        kat = c1.selectbox("Kategori", list(kategoriler.keys()))
        klasor = ROOT / "raporlar" / kategoriler[kat]
        dosyalar = sorted(klasor.glob("*.md")) if klasor.exists() else []
        if not dosyalar:
            st.info("Bu kategoride rapor yok.")
        else:
            secilen = c2.selectbox("Rapor", dosyalar, format_func=lambda p: p.stem)
            metin = secilen.read_text(encoding="utf-8")
            terimler = rapor_terimleri(metin)
            if terimler:
                st.caption("💡 Altı noktalı çizili terimlerin **üstüne gelince** sade açıklaması "
                           "belirir. Tanımlar genel-eğiticidir; kesin anlam tedavi ekibinde (Bölüm 0).")
            with st.container(border=True):
                st.markdown(terimleri_tooltiple(metin), unsafe_allow_html=True)
            if terimler:
                gorunen = {"kto": "KTO", "hrct": "HRCT"}
                with st.expander(f"📖 Tüm terimlerin listesi ({len(terimler)})", expanded=False):
                    for k, v in terimler:
                        st.markdown(f"- **{gorunen.get(k, k)}** — {v}")

    # ================= SORULAR =================
    with sekmeler[6]:
        st.markdown("### ❓ Doktora Sorulacaklar")
        if not sorular.empty:
            durumlar = sorted(sorular["durum"].unique())
            sec = st.multiselect("Durum", durumlar,
                                 default=["acik"] if "acik" in durumlar else durumlar)
            for _, r in sorular[sorular["durum"].isin(sec)].iterrows():
                isaret = "🟣" if r["durum"] == "acik" else "✅"
                cev = (f"<div class='meta'>↳ {r['cevap_notu']}</div>"
                       if r["durum"] != "acik" and r["cevap_notu"] else "")
                st.markdown(f"<div class='tcard'>{isaret} <span style='color:#f1f3f8'>{r['soru']}</span>"
                            f"<div class='meta' style='color:#7c8299'>{r['olusturma_tarihi']} · {r['durum']}</div>"
                            f"{cev}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
