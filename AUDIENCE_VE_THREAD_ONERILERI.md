# 🎯 Audience ve Thread Önerileri

## 📊 Dataset Özeti
- **Dataset**: virgintest.sav
- **Variables**: 429
- **Respondents**: 50
- **Utterances**: 16,673 ✅
- **Variable Embeddings**: 806 ✅
- **Utterance Embeddings**: 6,327 ✅

---

## 🎯 ÖNERİ 1: Gender-Based Audience (En Basit)

### Audience Oluşturma:
**Frontend'de Smart Filters sayfasından:**
1. `/filters` sayfasına gidin
2. "Generate Smart Filters" butonuna tıklayın (veya manuel oluşturun)
3. **D2** (Gender) variable'ını seçin
4. "Save as Audience" tıklayın
5. **Name**: "Female Respondents" veya "Kadın Katılımcılar"
6. **Description**: "Female gender respondents only"
7. **Filter**: D2 = "0" (Female)

**Veya API ile direkt:**
```json
POST /api/research/audiences
{
  "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
  "name": "Female Respondents",
  "description": "Kadın katılımcılar",
  "filter_json": {
    "D2": {
      "operator": "eq",
      "values": ["0"]
    }
  }
}
```

### Thread Soruları (Female Audience için):
1. **Structured**: "What is the distribution of QV3_10 for female respondents?"
2. **RAG**: "What do female respondents think about Virgin brand?"
3. **Comparison**: "Compare female vs total sample for QV1_1"

---

## 🎯 ÖNERİ 2: Generational Cohorts (Baby Boomers)

### Audience Oluşturma:
**Name**: "Baby Boomers"
**Description**: "60+ yaş grubu (Baby Boomers)"
**Filter**: D1_GEN_US = "4"

```json
{
  "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
  "name": "Baby Boomers",
  "description": "60+ yaş grubu katılımcılar",
  "filter_json": {
    "D1_GEN_US": {
      "operator": "eq",
      "values": ["4"]
    }
  }
}
```

### Thread Soruları (Baby Boomers için):
1. **Structured**: "What is the brand awareness (QV1_1) for Baby Boomers?"
2. **Structured**: "Compare Baby Boomers vs total sample"
3. **RAG**: "What themes do Baby Boomers mention about Virgin brand?"

---

## 🎯 ÖNERİ 3: Millennials (Gen Y)

### Audience Oluşturma:
**Name**: "Millennials (Gen Y)"
**Description**: "28-43 yaş grubu"
**Filter**: D1_GEN_US = "2"

```json
{
  "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
  "name": "Millennials (Gen Y)",
  "description": "28-43 yaş grubu katılımcılar",
  "filter_json": {
    "D1_GEN_US": {
      "operator": "eq",
      "values": ["2"]
    }
  }
}
```

### Thread Soruları:
1. **Structured**: "What is the distribution of QV2_R2_2 for Millennials?" (Apple preference)
2. **Comparison**: "Compare Millennials vs Baby Boomers for QV1_1"
3. **RAG**: "Why do Millennials prefer Apple brand?"

---

## 🎯 ÖNERİ 4: Multi-Value Filter (Gender: Female OR Male)

**Name**: "All Genders (excluding others)"
**Filter**: D2 = "0" OR "1"

```json
{
  "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
  "name": "Female and Male Only",
  "description": "Female ve Male katılımcılar (diğerleri hariç)",
  "filter_json": {
    "D2": {
      "operator": "in",
      "values": ["0", "1"]
    }
  }
}
```

---

## 📝 Kullanılabilir Value Codes

### D2 - Gender:
- `"0"` = Female
- `"1"` = Male
- `"98"` = Another gender
- `"99"` = Prefer not to say

### D1_GEN_US - Generational Cohorts:
- `"1"` = Generation Z (≤27)
- `"2"` = Millennials/Generation Y (28-43)
- `"3"` = Generation X (44-59)
- `"4"` = Baby Boomers (60+)

---

## 🧵 Thread Oluşturma Adımları

### 1. Audience Oluşturun (Yukarıdaki önerilerden birini kullanın)

### 2. Thread Oluşturun:
**Frontend'de `/threads` sayfasından:**
1. "New Thread" butonuna tıklayın
2. **Title**: "Female Respondents Analysis"
3. **Dataset**: Seçili (virgintest.sav)
4. **Audience**: Oluşturduğunuz audience'ı seçin (opsiyonel)
5. "Create Thread" tıklayın

### 3. Soru Sorun:
Thread sayfasında soru sorabilirsiniz:

#### Structured Sorular (Sayısal/İstatistiksel):
- ✅ "What is the distribution of QV3_10?"
- ✅ "How many respondents selected option 1 in QV1_1?"
- ✅ "Compare Baby Boomers vs total sample for QV2_R2_2"
- ✅ "QV1_1'in dağılımı nedir? Sayı ve yüzde göster."

#### RAG Sorular (Nitel/Açıklayıcı):
- ✅ "What do respondents think about Virgin brand?"
- ✅ "Why do customers prefer Apple over Amazon?"
- ✅ "What themes do Millennials mention about brand awareness?"

---

## 🎯 Test Senaryosu Önerileri

### Senaryo 1: Gender Comparison
1. **Audience 1**: "Female Respondents" (D2 = "0")
2. **Audience 2**: "Male Respondents" (D2 = "1")
3. **Thread Questions**:
   - Structured: "Compare Female vs Male for QV1_1"
   - RAG: "What do female respondents say about Virgin brand?"

### Senaryo 2: Generational Analysis
1. **Audience 1**: "Baby Boomers" (D1_GEN_US = "4")
2. **Audience 2**: "Millennials" (D1_GEN_US = "2")
3. **Thread Questions**:
   - Structured: "What is the distribution of QV2_R2_2 for Baby Boomers?"
   - Comparison: "Compare Baby Boomers vs Millennials for QV1_1"
   - RAG: "Why do Millennials prefer different brands than Baby Boomers?"

### Senaryo 3: Brand Awareness Analysis
1. **Audience**: Total sample (audience seçmeden)
2. **Thread Questions**:
   - Structured: "What is the distribution of QV1_1?" (Virgin brand awareness)
   - Structured: "Compare QV1_1 vs QV1_2" (Virgin vs Apple awareness)
   - RAG: "What do respondents think about brand awareness?"

---

## 💡 İpuçları

1. **En Basit Test**: Gender filter ile başlayın (D2 = "0" veya "1")
2. **Karşılaştırma**: İki audience oluşturup comparison soruları sorun
3. **RAG Test**: En az bir RAG sorusu deneyin (utterance embedding'ler hazır!)
4. **Variable Codes**: QV ile başlayan variable'lar ana sorular (awareness, preference, satisfaction)
5. **Demographics**: D ile başlayan variable'lar demografik bilgiler (age, gender, region)

---

## ✅ Checklist

- [ ] Smart Filter oluştur (veya mevcut filter'ı kullan)
- [ ] Audience kaydet (Save as Audience)
- [ ] Thread oluştur
- [ ] Audience'ı thread'e bağla (opsiyonel)
- [ ] Structured soru sor (distribution, count, comparison)
- [ ] RAG soru sor (why, themes, feedback)
- [ ] Sonuçları incele (chart, narrative, citations)

