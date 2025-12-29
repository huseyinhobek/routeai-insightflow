# 🧪 Test Öncelik Sırası

## ✅ Tamamlanan Testler

1. ✅ **RAG Mode** - "What do female respondents think about Virgin brand?"
   - LLM synthesis çalışıyor
   - Themes üretiliyor
   - "Data mismatch" hatası yok

2. ✅ **Structured Distribution** - "What is the distribution of QV3_10 for female respondents?"
   - Mode: structured
   - Chart ve narrative çalışıyor

---

## 🎯 Şimdi Test Edilmesi Gerekenler (Öncelik Sırası)

### 1. 🔴 YÜKSEK ÖNCELİK: Comparison Testi (Yeni Özellik)

**Soru:**
```
Compare female vs total sample for QV1_1
```

**Kontrol Listesi:**
- [ ] Mode = `structured`
- [ ] Evidence JSON'da `comparison_type: "audience_vs_total"` var
- [ ] Evidence JSON'da `audience` key'i var (audience aggregation)
- [ ] Evidence JSON'da `total` key'i var (total sample aggregation)
- [ ] Narrative: Comparison narrative (iki grup karşılaştırması)
- [ ] Mapping Debug'da `comparison_audience_id` set edilmiş
- [ ] Chart: Comparison chart gösteriliyor mu?

**Alternatif Soru:**
```
Compare QV1_1 for female respondents vs total sample
```

---

### 2. 🟡 ORTA ÖNCELİK: Breakdown Testi (2D Aggregation)

**Soru:**
```
What is the distribution of QV3_10 by D2?
```

veya

```
QV1_1 breakdown by D2
```

**Kontrol Listesi:**
- [ ] Mode = `structured`
- [ ] Evidence JSON'da `breakdown_type` var
- [ ] Evidence JSON'da `cells` array var (2D breakdown data)
- [ ] Mapping Debug'da `group_by_variable_id` set edilmiş
- [ ] Chart: Breakdown chart gösteriliyor mu?

**Not:** Eğer D2 demographic değişkeni yoksa, başka bir demographic variable kullanın (ör: yaş grubu, bölge, vb.)

---

### 3. 🟢 DÜŞÜK ÖNCELİK: RAG Varyasyonları

**Soru 1:**
```
Why do customers prefer Apple over Amazon?
```

**Soru 2:**
```
What are the main themes in customer feedback?
```

**Kontrol:**
- Mode = `rag`
- Themes üretiliyor
- "Data mismatch" hatası yok

---

### 4. 🟢 DÜŞÜK ÖNCELİK: Structured Regresyon Testi

**Soru:**
```
What is the distribution of QV1_1?
```

**Kontrol:**
- Mode = `structured`
- Normal structured response
- Chart ve narrative çalışıyor
- Evidence JSON'da `comparison_type` YOK (normal yapı)

---

## 📝 Test Sonuçlarını Kaydetme

Her test için şunları kaydedin:

1. **Soru metni**
2. **Mode** (structured/rag)
3. **Evidence JSON yapısı** (kritik key'ler var mı?)
4. **Narrative** (hata var mı?)
5. **Mapping Debug** (comparison_audience_id, group_by_variable_id, vb.)
6. **Chart** (gösteriliyor mu?)
7. **Hata varsa:** Hata mesajı

---

## 🐛 Sorun Tespit Edilirse

### Comparison çalışmıyorsa:
- Mapping Debug'da `comparison_audience_id` null mu?
- Thread'de `audience_id` set edilmiş mi?
- Soruda "vs total" veya "vs total sample" geçiyor mu?

### Breakdown çalışmıyorsa:
- Mapping Debug'da `group_by_variable_id` null mu?
- "by" kelimesi soruda var mı?
- `aggregate_with_breakdown` fonksiyonu çağrılıyor mu?

---

## ✅ Başarı Kriterleri

1. ✅ Comparison soruları comparison mode ile çalışıyor
2. ✅ Breakdown soruları breakdown mode ile çalışıyor
3. ✅ Evidence JSON structure doğru (comparison için `comparison_type`, `audience`, `total` var)
4. ✅ Narrative'ler doğru format ve içerikte
5. ✅ Chart'lar gösteriliyor

