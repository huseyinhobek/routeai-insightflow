# 🧪 Test Soruları - Düzeltmeler Sonrası

## ✅ Düzeltilen Sorunlar

1. **RAG Mode "Data mismatch" hatası** → RAG modunda sayı validasyonu kaldırıldı
2. **Comparison soruları çalışmıyordu** → "vs total" detection ve comparison handling eklendi

---

## 📝 Test Senaryoları

### Senaryo 1: RAG Soruları (Data mismatch hatası düzeltildi)

**Hedef**: RAG sorularının "Data mismatch" hatası olmadan çalışması

#### Soru 1.1: Genel RAG Sorusu
```
What do female respondents think about Virgin brand?
```

**Beklenen Sonuç**:
- ✅ Mode: `rag`
- ✅ Narrative: Theme'ler ve representative quotes içeren bir metin
- ✅ "Data mismatch—unable to generate safe narrative" HATASI OLMAMALI
- ✅ Citations: En az 1-2 citation olmalı

---

#### Soru 1.2: Başka bir RAG Sorusu
```
Why do customers prefer Apple over Amazon?
```

**Beklenen Sonuç**:
- ✅ Mode: `rag`
- ✅ Narrative: Synthesis result ile tema analizi
- ✅ "Data mismatch" HATASI OLMAMALI

---

### Senaryo 2: Comparison Soruları (Yeni özellik)

**Hedef**: "Compare X vs total sample" sorularının doğru çalışması

#### Soru 2.1: Comparison - Female vs Total
```
Compare female vs total sample for QV1_1
```

**Beklenen Sonuç**:
- ✅ Mode: `structured`
- ✅ Evidence JSON'da `comparison_type: "audience_vs_total"` olmalı
- ✅ `audience` ve `total` key'leri olmalı
- ✅ Narrative: Comparison narrative (ör: "For X category, audience shows Y% compared to Z% in total sample")
- ✅ Chart: Comparison chart (iki veri seti yan yana)

**Mapping Debug'da görecekleriniz**:
```json
{
  "comparison_audience_id": "<audience_id>",
  "mode_selected": "structured",
  ...
}
```

---

#### Soru 2.2: Comparison - Farklı Formülasyon
```
Compare QV1_1 for female respondents vs total sample
```

**Beklenen Sonuç**:
- ✅ Aynı şekilde comparison olarak algılanmalı ve çalışmalı

---

#### Soru 2.3: Comparison - Başka bir Variable
```
Compare female vs total sample for QV2_R2_2
```

**Beklenen Sonuç**:
- ✅ Comparison mode ile çalışmalı
- ✅ QV2_R2_2 variable'ı için audience vs total karşılaştırması

---

### Senaryo 3: Structured Sorular (Regresyon Testi)

**Hedef**: Normal structured soruların hala çalıştığından emin olmak

#### Soru 3.1: Basit Distribution
```
What is the distribution of QV3_10 for female respondents?
```

**Beklenen Sonuç**:
- ✅ Mode: `structured`
- ✅ Narrative: Dağılım bilgisi (örn: "X was selected by Y% of respondents")
- ✅ Chart: Distribution chart
- ✅ Evidence JSON: Normal structure (comparison_type yok)

---

#### Soru 3.2: Başka bir Structured
```
What is the distribution of QV1_1?
```

**Beklenen Sonuç**:
- ✅ Mode: `structured`
- ✅ Normal structured response

---

## 🔍 Kontrol Listesi

Her soru için şunları kontrol edin:

### ✅ RAG Soruları için:
- [ ] Mode = `rag`
- [ ] Narrative var ve "Data mismatch" hatası YOK
- [ ] Evidence JSON'da `citations` array var
- [ ] Evidence JSON'da `synthesis_result` var (themes, quotes)

### ✅ Comparison Soruları için:
- [ ] Mode = `structured`
- [ ] Evidence JSON'da `comparison_type: "audience_vs_total"` var
- [ ] Evidence JSON'da `audience` key'i var (audience aggregation)
- [ ] Evidence JSON'da `total` key'i var (total sample aggregation)
- [ ] Narrative: Comparison narrative (iki grup karşılaştırması)
- [ ] Mapping Debug'da `comparison_audience_id` var

### ✅ Normal Structured Sorular için:
- [ ] Mode = `structured`
- [ ] Evidence JSON'da `comparison_type` YOK
- [ ] Evidence JSON'da `categories` array var
- [ ] Narrative: Normal structured narrative
- [ ] Chart: Normal chart

---

## 📊 Örnek Test Akışı

1. **Audience Oluştur**: "Female Respondents" (D2 = "0")
2. **Thread Oluştur**: "Test Thread" → Female Respondents audience'ı seç
3. **Soruları Sırayla Sor**:
   - Soru 1.1: RAG testi
   - Soru 2.1: Comparison testi
   - Soru 3.1: Structured regression testi
4. **Her Soru için**:
   - Mode'u kontrol et
   - Narrative'i kontrol et (hata var mı?)
   - Evidence JSON'u kontrol et (structure doğru mu?)
   - Mapping Debug'ı kontrol et (comparison_audience_id var mı?)

---

## 🐛 Olası Sorunlar ve Çözümler

### Problem: RAG sorularında hala "Data mismatch" hatası
- **Kontrol**: `narration_service.py` değişiklikleri uygulandı mı?
- **Çözüm**: Backend'i restart edin

### Problem: Comparison soruları normal structured gibi çalışıyor
- **Kontrol**: Mapping Debug'da `comparison_audience_id` var mı?
- **Kontrol**: Thread'de `audience_id` set edilmiş mi?
- **Kontrol**: Soruda "vs total" veya "vs total sample" geçiyor mu?

### Problem: Comparison narrative çok basit
- **Normal**: Comparison narrative şu an basit bir format kullanıyor (top category farkını gösteriyor)
- **Geliştirme**: İleride daha detaylı comparison narrative eklenebilir

---

## ✅ Başarı Kriterleri

1. ✅ Tüm RAG soruları "Data mismatch" hatası olmadan çalışıyor
2. ✅ "Compare X vs total sample" soruları comparison mode ile çalışıyor
3. ✅ Normal structured sorular hala normal çalışıyor (regresyon yok)
4. ✅ Evidence JSON structure doğru (comparison için `comparison_type`, `audience`, `total` var)

