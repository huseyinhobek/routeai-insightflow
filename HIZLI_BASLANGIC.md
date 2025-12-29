# 🚀 Hızlı Başlangıç - Örnek Sorular

## 📋 Hazır Kopyala-Yapıştır Sorular

### Decision Soruları (decision_proxy mode)
```
hangisini seçmeli
which option is best
en iyi seçenek hangisi
S3_4 için hangisini seçmeli
Apple vs Amazon için hangisini seçmeli
```

### Structured Sorular (distribution)
```
What is the distribution of S3_1
S3_4'nin dağılımı nedir
D2 dağılımı nedir
Show me the distribution of S3_7
```

### Comparison Soruları
```
Compare S3_1 for female vs total
Female audience vs total for S3_4
Compare D2 for this audience vs total
```

### Breakdown Soruları
```
S3_4 by D2
D2 by D1_GEN
S3_7 by D1_GEN
Gender'a göre S3_1 dağılımı
```

### RAG Soruları
```
Why did they choose Apple
Neden Amazon'u seçtiler
What are the reasons for choosing option A
```

---

## 🎯 Tam Senaryo Örnekleri

### Senaryo 1: Smart Filter → Audience → Thread → Soru

```bash
# 1. Audience Oluştur (Female)
curl -X POST http://localhost:8000/api/research/audiences \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "name": "Female Respondents",
    "filter_json": {
      "D2": {"operator": "in", "values": ["2"]}
    }
  }'

# 2. Thread Oluştur
curl -X POST http://localhost:8000/api/research/threads \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "f433468b-9178-45ac-bf87-ff3d2f17c50e",
    "audience_id": "1407026d-b6c7-46d1-b120-2021e1be9d19",
    "title": "Female Analysis"
  }'

# 3. Decision Sor
curl -X POST http://localhost:8000/api/research/threads/{thread_id}/questions \
  -H "Content-Type: application/json" \
  -d '{"question_text": "hangisini seçmeli"}'
```

### Senaryo 2: Multiple Filters → Decision

```bash
# 1. Audience (Female + Gen Z)
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
# "hangisini seçmeli" → Decision proxy mode
```

---

## 🎨 Frontend'den Kullanım

### 1. ThreadChatPage'de Soru Sor
```
1. http://localhost:3000 adresine git
2. Bir thread aç veya yeni thread oluştur
3. Input'a soru yaz: "hangisini seçmeli"
4. Gönder butonuna tıkla
5. Decision proxy UI görünür:
   - Distribution chart
   - 3 decision rules (radio buttons)
   - Clarifying controls
   - Next best questions
```

### 2. Next Best Question'dan Seç
```
1. Decision proxy response'da "Next Best Questions" listesinden birini seç
2. Otomatik olarak o soru submit edilir
3. Structured/RAG mode'a göre response gösterilir
```

---

## 📊 Gerçek Variable Kodları

### Demographics
- `D2` = Gender
- `D1_GEN` = Generational Cohorts (Age groups)
- `D1_R1` = Age recode 1
- `D1_R3` = Age recode 3

### Activities/Behaviors
- `S3_1` = Gym/fitness class (past month)
- `S3_2` = International air travel (last 2 years)
- `S3_4` = TV/internet/phone subscription
- `S3_7` = Cell phone (personal use)
- `S3_10` = 4-5 star hotel (last 2 years)
- `S3_15` = Loyalty/rewards program member

### Preferences
- `QV2_R1_2` = Apple|Openness
- `QV2_R1_3` = Amazon|Openness
- `QV2_R2_2` = Apple|Preference

---

## 🔗 API Endpoints

### Audience
```
POST /api/research/audiences
GET /api/research/audiences?dataset_id={id}
GET /api/research/audiences/{audience_id}
PUT /api/research/audiences/{audience_id}
DELETE /api/research/audiences/{audience_id}
```

### Thread
```
POST /api/research/threads
GET /api/research/threads?dataset_id={id}
GET /api/research/threads/{thread_id}
PUT /api/research/threads/{thread_id}
DELETE /api/research/threads/{thread_id}
```

### Question
```
POST /api/research/threads/{thread_id}/questions
Body: {"question_text": "hangisini seçmeli"}
```

---

## ✅ Test Checklist

- [ ] Decision question sor → decision_proxy mode görünmeli
- [ ] Distribution chart render edilmeli
- [ ] 3 decision rules görünmeli
- [ ] Decision rule seçimi çalışmalı
- [ ] Clarifying controls görünmeli
- [ ] Next best questions listelenmeli
- [ ] Next best question click → auto-submit çalışmalı
- [ ] Audience oluştur → thread'e ekle → soru sor çalışmalı
- [ ] Comparison sor → comparison chart görünmeli
- [ ] Breakdown sor → breakdown chart görünmeli

