# Kemoterapi Protokolü — CLAD + LDAC + VEN (28 günde bir)

> Kaynak: `gelen-pdf/ilac-programi/ilac-programi-1.jpeg` (hastane protokol [gizli],
> el yazısı doz notlarıyla). Bu belge tedavi ekibinin **uyguladığı** planı
> kaydeder; sistem doz/ilaç ÖNERMEZ, yalnızca ekibin kararını izler (bkz.
> CLAUDE.md Bölüm 0 ve 5.2). Aşağıdaki tarih çıkarımları yaklaşıktır.

## Kurum ve hasta
- **Kurum:** Hastane Uygulama ve Araştırma Hasta[gizli] —
  Hematoloji ve Kök Hücre Nakil Ünitesi
- **Hasta:** MAB
- **Boy:** 175 cm · **Kilo:** 84 kg (form üstünde el yazısı güncel: ~81,1 kg)
- **Vücut yüzey alanı (BSA):** 2 m²
- **Protokol adı:** **CLAD + LDAC + VEN**, döngü **28 günde bir** tekrarlanır.

## İlaçlar (formda yazıldığı gibi)

| # | İlaç | Protokol [gizli] | Hesaplanan/uygulanan | Yol | Sıklık | Günler |
|---|------|---------------|----------------------|-----|--------|--------|
| 1 | **Cladribine (CLAD)** | 5 mg/m² | **10 mg** (5×2 m²) | IV | QD (günde 1) | **D1–5** |
| 2 | **Cytarabine (LDAC, düşük doz)** | 20 mg | **2 × 20 mg** | SC (cilt altı) | BID (günde 2) | **D1–10** |
| 3 | **Venetoclax (VEN)** | 400 mg | kademeli (aşağıda) | PO (ağızdan) | QD (günde 1) | **D1–21** |

### Venetoclax kademeli doz artışı (ramp-up)
- **1. gün:** 100 mg
- **2. gün:** 200 mg
- **3. gün ve sonrası:** 400 mg

> Genel-eğitici not (klinik yorum değil): Venetoclax kademeli başlatılan bir
> **hedefe yönelik / "akıllı" ilaçtır** (BCL-2 proteinini hedefler). Bu, ailenin
> "akıllı ilaç" dediği ilaçtır. Cladribine ve düşük doz Cytarabine (LDAC) ise
> klasik kemoterapi ilaçlarıdır; "10 günlük kemoterapi" = Cytarabine D1–10.

## Takvim çıkarımı (Kür 1)
> Onaylanan kür başlangıcı (aile beyanı, 02.07): **D1 = 2026-06-15**
> (`surec_olaylari.csv`). Venetoclax için aile "17. gün 02.07" dediğinden onun
> D1'i ≈ **2026-06-16** olab[gizli] (kür D1'inden ~1 gün offset — belirsiz).

| İlaç | Günler | Yaklaşık takvim |
|------|--------|-----------------|
| Cladribine | D1–5 | 2026-06-15 → 06-19 |
| Cytarabine | D1–10 | 2026-06-15 → 06-24/25 |
| Venetoclax | D1–21 | 2026-06-15 → 07-05 *(ya da 06-16 → 07-06)* |

- **Bir sonraki kür (28 günde bir):** Kür 2 D1 ≈ **2026-07-13** (06-15 + 28 gün).
  Kesin tarih tedavi ekibince belirlenir.

## Açık / doğrulanacak noktalar
- Formda **Tarih / Kür / Tanı** alanları boş bırakılmış (el yazısıyla
  doldurulmamış); kür numarası ve resmi başlangıç tarihi ekipten doğrulanabilir.
- Venetoclax'ın kesin 1. gün tarihi (06-15 mi 06-16 mı) — aile "17. gün"
  beyanıyla ~1 gün oynuyor.
- Cytarabine bitişinin D10 = 06-24 mü yoksa kayıttaki kür bitiş 06-25 mi olduğu
  ±1 gün belirsiz.
