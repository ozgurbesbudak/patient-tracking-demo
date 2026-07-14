#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egilim.py — kan değeri serilerinden BETİMLEYİCİ eğilim/değişim özeti.

Öngörü/uyarı DEĞİLDİR (CLAUDE.md Bölüm 0). Yalnızca verinin son günlerde ne
yaptığını özetler: ardışık yön (kaç gündür ↑/↓), günlük değişim hızı, hızlı
değişim işareti ve referans dışı süre. Klinik anlam tedavi ekibine aittir.

Hem `durum_ozeti.py` (csv) hem `pano_app.py` (pandas) buradan çağırır; bağımsız
kalması için girdi sade bir listedir: [(datetime, deger, ref_alt, ref_ust)].
"""

def _gunluk(seri):
    """Günde birden fazla ölçüm varsa günün SON değerini al; (date, v, ra, ru) sıralı."""
    by = {}
    for dt, v, ra, ru in seri:
        if v is None:
            continue
        d = dt.date() if hasattr(dt, "date") else dt
        by[d] = (v, ra, ru)  # sıralı geldiği varsayımıyla son kazanır
    return [(d, *by[d]) for d in sorted(by)]


def _ref_disi(v, ra, ru):
    if ra is not None and v < ra:
        return "alt"
    if ru is not None and v > ru:
        return "ust"
    return None


def analiz(seri, pencere=3):
    """seri: [(datetime, deger(float|None), ref_alt(float|None), ref_ust(float|None))].
    Dönüş: dict veya None. Alanlar betimleyicidir."""
    g = _gunluk(seri)
    if not g:
        return None
    d_son, v_son, ra, ru = g[-1]

    # ardışık yön (kaç gündür aynı yönde)
    yon, streak = "▬", 0
    if len(g) >= 2:
        diff = v_son - g[-2][1]
        yon = "▲" if diff > 0 else "▼" if diff < 0 else "▬"
        if diff != 0:
            streak = 1
            for i in range(len(g) - 2, 0, -1):
                d2 = g[i][1] - g[i - 1][1]
                if d2 != 0 and (d2 > 0) == (diff > 0):
                    streak += 1
                else:
                    break

    # günlük değişim hızı — ardışık yön penceresi üzerinden (işaret yön ile tutarlı);
    # streak yoksa son tek güne göre.
    n = max(streak, 1)
    ref_i = max(0, len(g) - 1 - n)
    span = (g[-1][0] - g[ref_i][0]).days or 1
    gunluk_degisim = (v_son - g[ref_i][1]) / span

    # referans dışı konum + süre (ardışık son günler)
    konum = _ref_disi(v_son, ra, ru)
    ref_disi_gun = 0
    if konum:
        for d, v, a, u in reversed(g):
            if _ref_disi(v, a, u) == konum:
                ref_disi_gun += 1
            else:
                break

    # hızlı değişim: son gün-günlük değişim referans genişliğinin yarısını aşarsa
    # (referans yoksa %30 göreli değişim)
    hizli = False
    if len(g) >= 2:
        son_delta = abs(v_son - g[-2][1])
        if ra is not None and ru is not None and ru > ra:
            hizli = son_delta >= 0.5 * (ru - ra)
        elif g[-2][1]:
            hizli = son_delta / abs(g[-2][1]) >= 0.30

    return dict(son=v_son, tarih=d_son, ref_alt=ra, ref_ust=ru,
                yon=yon, streak=streak, gunluk_degisim=gunluk_degisim,
                ref_konum=konum, ref_disi_gun=ref_disi_gun, hizli=hizli)


def ozet_metin(a):
    """analiz() dict'inden kısa Türkçe betimleme parçaları (yon, hız, ref) döndürür."""
    if not a:
        return "", "", ""
    yon_s = f"{a['yon']} {a['streak']} gün" if a["streak"] >= 2 else a["yon"]
    gd = a["gunluk_degisim"]
    hiz_s = f"{'+' if gd > 0 else ''}{gd:.2g}/gün" + (" ⚡" if a["hizli"] else "")
    if a["ref_konum"] == "alt":
        ref_s = f"referans altı · {a['ref_disi_gun']} gün"
    elif a["ref_konum"] == "ust":
        ref_s = f"referans üstü · {a['ref_disi_gun']} gün"
    else:
        ref_s = "referans içinde"
    return yon_s, hiz_s, ref_s
