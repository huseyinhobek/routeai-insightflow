# Decision Proxy - Kritik İyileştirmeler ✅

## Yapılan 5 Kritik Düzeltme

### 1. ✅ Decision Proxy Header (Öncelik: YÜKSEK)
**Sorun:** Kullanıcı proxy'nin ne olduğunu bilmiyor, direkt cevap sanıyor.

**Çözüm:**
- Header eklendi: "Not directly measured → using proxy"
- Proxy variable code gösteriliyor (örn: `QV1_2`)
- Confidence score gösteriliyor (örn: 62%)
- Alternatif adaylar listeleniyor (top 3)

**Frontend:** Turuncu uyarı kutusu, en üstte görünüyor.

### 2. ✅ Base N Küçükse Otomatik Risk-Averse (Öncelik: YÜKSEK)
**Sorun:** N=29 gibi küçük örneklerde "top option" önerisi yanıltıcı.

**Çözüm:**
- `base_n < 100` ise otomatik: "Gather more data / widen audience"
- `top2 gap < 5pp` ise: "Gather more data / widen audience"
- Preview'da net sebep gösteriliyor: "Base n: 29 (too small for reliable decision)"

### 3. ✅ Segment-Fit Min Eşikler (Öncelik: ORTA)
**Sorun:** Segment-fit kuralı her zaman öneri veriyor, istatistiksel anlamlılık kontrolü yok.

**Çözüm:**
- Min threshold: `base_n >= 100` VE `abs(delta_pp) >= 5pp`
- Eşikler karşılanmazsa warning gösteriliyor
- Preview'da: "⚠️ Thresholds not met: N=29, |delta|=5.0pp"

### 4. ✅ Takip Soruları Dataset Kontrolü (Öncelik: ORTA)
**Sorun:** "Top reasons" gibi sorular öneriliyor ama dataset'te open-end yok.

**Çözüm:**
- Open-end/verbatim variable kontrolü yapılıyor
- Sadece dataset'te varsa "reasons/themes" soruları öneriliyor
- Age, price sensitivity, satisfaction gibi variable'lar kontrol ediliyor
- Sadece gerçekten var olan variable tiplerine göre sorular üretiliyor

### 5. ✅ Mapping Debug Özet (Öncelik: DÜŞÜK)
**Sorun:** Debug bilgisi accordion içinde ama özet yok.

**Çözüm:**
- Accordion'un en üstüne 1 satır özet eklendi
- Format: "Mode: decision_proxy | Variable: QV1_2 | Confidence: 62%"
- Detaylar altında JSON olarak duruyor

---

## Backend Değişiklikleri

### `decision_proxy_service.py`

1. **`identify_proxy_target_variable`** artık tuple döndürüyor:
   - `(variable_id, confidence, alternatives)`
   - Confidence: 0.0-1.0 arası
   - Alternatives: Top 3 alternatif aday

2. **`generate_decision_rules`** güncellendi:
   - Risk-averse: Base N < 100 ise otomatik "Gather more data"
   - Segment-fit: Min threshold kontrolü (N>=100, |delta|>=5pp)

3. **`generate_next_best_questions`** güncellendi:
   - Dataset'te variable varlığı kontrol ediliyor
   - Open-end yoksa "reasons" soruları önerilmiyor

4. **`answer_decision_question`** güncellendi:
   - `proxy_header` eklendi (is_proxy, message, var_code, confidence, alternatives)
   - Narrative text'e proxy disclaimer eklendi

---

## Frontend Değişiklikleri

### `ThreadChatPage.tsx`

1. **Proxy Header Bölümü:**
   - Turuncu uyarı kutusu
   - "Not directly measured → using proxy" mesajı
   - Proxy var code + confidence
   - Alternatif adaylar listesi

2. **Decision Rules:**
   - Warning gösterimi eklendi (eşikler karşılanmazsa)
   - Reason gösterimi eklendi

3. **Mapping Debug:**
   - En üstte 1 satır özet
   - Format: "Mode: X | Variable: Y | Confidence: Z%"

---

## Test Senaryoları

### Senaryo 1: Küçük N (N=29)
```
Soru: "Why do customers prefer Apple over Amazon?"
Beklenen:
- Proxy header: "Not directly measured → using proxy"
- Risk-averse preview: "Gather more data / widen audience"
- Reason: "Base n: 29 (too small for reliable decision)"
```

### Senaryo 2: Segment-Fit Eşikler
```
Soru: "hangisini seçmeli" (audience var, N=29, delta=5pp)
Beklenen:
- Segment-fit warning: "⚠️ Thresholds not met: N=29, |delta|=5.0pp"
- Kural gösteriliyor ama warning ile
```

### Senaryo 3: Open-End Yok
```
Dataset'te open-end variable yok
Beklenen:
- "Top reasons" sorusu ÖNERİLMİYOR
- Sadece structured sorular öneriliyor
```

---

## Sonuç

✅ **Tüm 5 kritik düzeltme tamamlandı!**

Sistem artık:
- Kullanıcıyı yanıltmıyor (proxy açıkça belirtiliyor)
- Küçük örneklerde uyarı veriyor
- İstatistiksel eşikleri kontrol ediyor
- Sadece gerçekten var olan soruları öneriyor
- Debug bilgisi erişilebilir

**Durum:** Production-ready! 🎉

