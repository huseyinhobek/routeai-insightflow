# Örnek Sorular - Veritabanından Gerçek Verilerle

## 🎯 Decision/Proxy Sorular (decision_proxy mode)

### 1. Plan/Seçenek Kararı
```
"hangisini seçmeli"
"which plan is best"
"en iyi seçenek hangisi"
"hangi planı seçmeliyim"
"should I choose plan A or B"
```

### 2. Variable Code ile Decision
```
"QV1_10 için hangisini seçmeli"
"which option is best for QV3_5"
"QV2_1 için en mantıklı seçenek hangisi"
```

### 3. Audience ile Decision
```
"Female respondents için hangisini seçmeli"
"for female audience, which option is best"
"kadın katılımcılar için en iyi seçenek hangisi"
```

---

## 📊 Structured Sorular (structured mode)

### 1. Distribution Soruları
```
"What is the distribution of D2"
"D2'nin dağılımı nedir"
"Gender distribution"
"Cinsiyet dağılımı nedir"
```

### 2. Variable Code ile Distribution (Gerçek Variable'larla)
```
"What is the distribution of S3_1"        // Gym/fitness
"QV2_R1_2'nin dağılımı nedir"            // Apple|Openness
"Show me the distribution of S3_4"       // TV/internet subscription
"What is the distribution of S3_7"       // Cell phone
"QV2_R1_3 dağılımı nedir"                // Amazon|Openness
```

### 3. Audience ile Distribution
```
"What is the distribution of D2 for female respondents"
"Female audience için D2 dağılımı"
"for female, what is the distribution of QV1_10"
```

### 4. Comparison Soruları
```
"Compare D2 for female vs total"
"Female audience vs total sample for QV1_10"
"Kadın katılımcılar vs toplam örnek için D2 karşılaştırması"
```

### 5. Breakdown Soruları (Gerçek Variable'larla)
```
"D2 by D1_GEN"                    // Gender by age group
"Age by gender"                    // Age by gender
"S3_1 by D2"                       // Gym membership by gender
"S3_4 by D1_GEN"                   // TV subscription by age group
"QV2_R1_2 by D2"                   // Apple preference by gender
"Gender'a göre S3_7 dağılımı"      // Cell phone by gender
```

### 6. Percentage/Count Soruları
```
"What percentage chose option 1 in QV1_10"
"QV3_5'te kaç kişi seçenek 2'yi seçti"
"How many people selected option A"
```

---

## 🔍 RAG Soruları (rag mode)

### 1. Why/Reason Soruları
```
"Why did they choose option A"
"Neden seçenek A'yı seçtiler"
"What are the reasons for choosing plan B"
"Plan B'yi seçme nedenleri neler"
```

### 2. Feedback/Open-end Soruları
```
"What feedback did they give about option C"
"Seçenek C hakkında ne dediler"
"Describe the complaints about plan A"
"Plan A hakkındaki şikayetler neler"
```

### 3. Themes/Motivations
```
"What are the main themes in responses"
"Yanıtlardaki ana temalar neler"
"What motivates people to choose option B"
"Seçenek B'yi seçmeye iten faktörler neler"
```

---

## 🎯 Smart Filter + Audience + Soru Kombinasyonları

### Senaryo 1: Female Audience Oluştur + Distribution Sor
```bash
# 1. Smart Filter ile Audience Oluştur
curl -X POST http://localhost:8000/api/research/audiences \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "name": "Female Respondents",
    "filter_json": {
      "D2": {
        "operator": "in",
        "values": ["2", "Female"]
      }
    }
  }'

# Response: {"id": "1407026d-b6c7-46d1-b120-2021e1be9d19", ...}

# 2. Thread Oluştur (bu audience ile)
curl -X POST http://localhost:8000/api/research/threads \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "audience_id": "1407026d-b6c7-46d1-b120-2021e1be9d19",
    "title": "Female Analysis"
  }'

# Response: {"id": "thread-id-here", ...}

# 3. Soru Sor
curl -X POST http://localhost:8000/api/research/threads/{thread_id}/questions \
  -H "Content-Type: application/json" \
  -d '{
    "question_text": "What is the distribution of S3_1"
  }'

# → Otomatik olarak female audience için gym/fitness dağılımı gösterir
```

### Senaryo 2: Age Group Audience + Comparison Sor
```bash
# 1. Audience Oluştur (Gen Z)
curl -X POST http://localhost:8000/api/research/audiences \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "name": "Gen Z Respondents",
    "filter_json": {
      "D1_GEN": {
        "operator": "in",
        "values": ["Gen Z"]
      }
    }
  }'

# 2. Thread + Soru
# Thread oluştur (Gen Z audience ile)
# Soru: "Compare S3_7 for Gen Z vs total sample"
# → Cell phone ownership: Gen Z vs total comparison gösterir
```

### Senaryo 3: Multiple Filters + Decision Sor
```bash
# 1. Audience Oluştur (Female + Gen Z)
curl -X POST http://localhost:8000/api/research/audiences \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "name": "Female Gen Z",
    "filter_json": {
      "D2": {"operator": "in", "values": ["2"]},
      "D1_GEN": {"operator": "in", "values": ["Gen Z"]}
    }
  }'

# 2. Thread + Decision Sor
# Thread oluştur (Female Gen Z audience ile)
# Soru: "hangisini seçmeli"
# → Decision proxy mode
# → Female Gen Z için distribution chart
# → 3 decision rules (popularity-first, risk-averse, segment-fit)
# → Next best questions listesi
```

---

## 📝 Gerçek Kullanım Örnekleri

### Örnek 1: Plan Seçimi Analizi (Gerçek Variable ile)
```bash
# 1. Thread oluştur
curl -X POST http://localhost:8000/api/research/threads \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "title": "Plan Selection Analysis"
  }'

# 2. Decision Sor
curl -X POST http://localhost:8000/api/research/threads/{thread_id}/questions \
  -H "Content-Type: application/json" \
  -d '{"question_text": "hangisini seçmeli"}'

# Response:
# - mode: "decision_proxy"
# - Distribution chart (eğer proxy target variable bulunursa)
# - 3 decision rules (popularity-first, risk-averse, segment-fit)
# - Clarifying controls (dropdown + slider)
# - Next best questions (5-8 soru)

# 3. Next best question'dan birini seç:
# "What is the distribution of S3_4 in the total sample"
# → Structured mode, TV/internet subscription distribution gösterir
```

### Örnek 2: Audience Karşılaştırması (Gerçek Variable ile)
```bash
# 1. Female audience oluştur (zaten var: 1407026d-b6c7-46d1-b120-2021e1be9d19)

# 2. Thread oluştur (female audience ile)
curl -X POST http://localhost:8000/api/research/threads \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "audience_id": "1407026d-b6c7-46d1-b120-2021e1be9d19",
    "title": "Female vs Total Comparison"
  }'

# 3. Comparison Sor
curl -X POST http://localhost:8000/api/research/threads/{thread_id}/questions \
  -H "Content-Type: application/json" \
  -d '{"question_text": "Compare S3_1 for this audience vs total"}'

# Response:
# - mode: "structured"
# - Comparison chart (female vs total)
# - Delta percentage points gösterir
# - Gym/fitness membership: Female % vs Total %
```

### Örnek 3: Breakdown Analizi (Gerçek Variable'larla)
```bash
# 1. Thread oluştur
curl -X POST http://localhost:8000/api/research/threads \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "title": "Breakdown Analysis"
  }'

# 2. Breakdown Sor
curl -X POST http://localhost:8000/api/research/threads/{thread_id}/questions \
  -H "Content-Type: application/json" \
  -d '{"question_text": "S3_4 by D2"}'

# Response:
# - mode: "structured"
# - Breakdown chart (TV/internet subscription by gender)
# - Crosstab gösterir
# - Her gender için subscription % gösterir
```

### Örnek 4: RAG ile Feedback (Gerçek Variable ile)
```bash
# 1. Thread oluştur
curl -X POST http://localhost:8000/api/research/threads \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "title": "Feedback Analysis"
  }'

# 2. RAG Sor
curl -X POST http://localhost:8000/api/research/threads/{thread_id}/questions \
  -H "Content-Type: application/json" \
  -d '{"question_text": "Why did they choose Apple over Amazon"}'

# Response:
# - mode: "rag"
# - Relevant utterances retrieve eder
# - Themes ve quotes gösterir
# - Apple preference nedenleri
```

---

## 🎨 Frontend'den Kullanım

### 1. Smart Filter Oluştur
```typescript
// SmartFiltersPage'den
const createAudience = async () => {
  await apiService.createAudience({
    dataset_id: datasetId,
    name: "Female Respondents",
    filter_json: {
      D2: { operator: "in", values: ["2"] }
    }
  });
};
```

### 2. Thread Oluştur + Soru Sor
```typescript
// ThreadChatPage'den
const thread = await apiService.createThread({
  dataset_id: datasetId,
  audience_id: audienceId, // Opsiyonel
  title: "Analysis Thread"
});

await apiService.addThreadQuestion(thread.id, "hangisini seçmeli");
```

### 3. Decision Proxy Response
```typescript
// ThreadChatPage otomatik render eder:
// - Distribution chart
// - Comparison chart (if audience)
// - Decision rules (3 seçenek)
// - Clarifying controls
// - Next best questions
```

---

## 🔗 API Endpoint'leri

### Audience Oluştur
```
POST /api/research/audiences
Body: {
  "dataset_id": "...",
  "name": "Female Respondents",
  "filter_json": {
    "D2": {"operator": "in", "values": ["2"]}
  }
}
```

### Thread Oluştur
```
POST /api/research/threads
Body: {
  "dataset_id": "...",
  "audience_id": "...", // Opsiyonel
  "title": "My Analysis"
}
```

### Soru Sor
```
POST /api/research/threads/{thread_id}/questions
Body: {
  "question_text": "hangisini seçmeli"
}
```

---

## 💡 İpuçları

1. **Decision soruları için**: "hangisini", "en iyi", "should", "recommend" gibi kelimeler kullan
2. **Structured sorular için**: "distribution", "dağılım", "compare", "karşılaştır" gibi kelimeler kullan
3. **RAG soruları için**: "why", "neden", "describe", "açıkla" gibi kelimeler kullan
4. **Variable code kullan**: "S3_1", "D2", "QV2_R1_2" gibi kodlar direkt mapping yapar
5. **Audience belirt**: "for female", "kadın katılımcılar için" gibi ifadeler audience override yapar
6. **Gerçek Variable'lar**: 
   - `S3_1` = Gym/fitness
   - `S3_4` = TV/internet subscription
   - `S3_7` = Cell phone
   - `QV2_R1_2` = Apple|Openness
   - `QV2_R1_3` = Amazon|Openness
   - `D2` = Gender
   - `D1_GEN` = Age group/Generational cohorts

---

## 🎯 Test Senaryoları

### Test 1: Decision Question
```bash
# Soru: "hangisini seçmeli"
# Beklenen: decision_proxy mode
# - Distribution chart görünmeli (eğer proxy target variable bulunursa)
# - 3 decision rule seçeneği görünmeli (popularity-first, risk-averse, segment-fit)
# - Clarifying controls görünmeli (dropdown + slider)
# - Next best questions listelenmeli (5-8 soru)
# - Frontend'de tüm UI componentleri render edilmeli
```

### Test 2: Audience + Distribution
```bash
# 1. Female audience oluştur (zaten var veya yeni oluştur)
# 2. Thread oluştur (female audience ile)
# 3. Soru: "What is the distribution of S3_1"
# Beklenen: structured mode, female audience için gym/fitness dağılımı
# - Bar chart gösterir
# - Female audience için % gösterir
```

### Test 3: Comparison
```bash
# Soru: "Compare S3_4 for female vs total"
# Beklenen: structured mode, comparison chart
# - Audience vs total bars görünmeli (grouped bar chart)
# - Delta pp gösterilmeli (her option için)
# - TV/internet subscription: Female % vs Total %
```

### Test 4: Breakdown
```bash
# Soru: "S3_7 by D2"
# Beklenen: structured mode, breakdown chart
# - Cell phone ownership by gender crosstab
# - Her gender için cell phone % gösterir
# - Grouped bar chart
```

### Test 5: RAG
```bash
# Soru: "Why did they choose Apple over Amazon"
# Beklenen: rag mode
# - Relevant utterances retrieve eder
# - Themes ve quotes gösterir
# - Apple preference nedenleri
```

