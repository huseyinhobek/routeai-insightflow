# SAV Insight Studio - Kullanım Rehberi

## 🔴 ADIM 1: Eski Verileri Silme (History Sayfası)

### Ne Yapmalısınız:
1. **Frontend'e girin**: `http://localhost:3000` adresine gidin
2. **History sayfasına gidin**: Sol üstteki "Home" butonuna tıklayın veya direkt `/history` URL'sine gidin
3. **Datasets listesini görün**: Daha önce yüklediğiniz tüm dataset'leri burada göreceksiniz
4. **Silme işlemi**:
   - Silmek istediğiniz dataset'in sağındaki **çöp kutusu ikonuna** (🗑️) tıklayın
   - **"Confirm"** butonuna tıklayarak silme işlemini onaylayın
   - İşlem başarılı olursa, dataset listeden kaybolacak

### Silme İşlemi Ne Yapar:
- ✅ Dataset kaydını veritabanından siler
- ✅ Tüm bağlı kayıtları otomatik siler:
  - Variables (değişkenler)
  - ValueLabels (değer etiketleri)
  - Respondents (katılımcılar)
  - Responses (yanıtlar)
  - Utterances (ifade cümleleri)
  - Embeddings (vektör gösterimleri)
  - Audiences (hedef kitleler)
  - Threads (sohbet konuları)
  - Cache entries (önbellek kayıtları)
  - Transform jobs (dönüşüm işleri)
- ✅ Fiziksel dosyayı diskten siler
- ✅ localStorage'dan ilgili kayıtları temizler

### Hata Durumları:
- Eğer bir transform job çalışıyorsa, önce onu durdurmanız gerekir
- Hata mesajı görürseniz, backend loglarını kontrol edin

---

## 🟢 ADIM 2: Yeni Data Yükleme

### Ne Yapmalısınız:
1. **Home sayfasına gidin**: `/` veya ana sayfaya gidin
2. **Dosya seçin**:
   - **Yöntem 1**: Dosyayı sürükleyip bırakın (drag & drop)
   - **Yöntem 2**: "Choose File" butonuna tıklayıp dosyayı seçin
3. **Desteklenen formatlar**: `.sav`, `.xlsx`, `.xls`, `.csv`
4. **Upload edin**: Dosya seçildikten sonra otomatik olarak yüklenmeye başlar

### Upload Sonrası Ne Olur:
1. ✅ Dosya parse edilir (SPSS/Excel/CSV okunur)
2. ✅ Dataset metadata'sı oluşturulur
3. ✅ Quality report hesaplanır
4. ✅ Dataset kaydı veritabanına kaydedilir
5. ✅ Otomatik olarak **Celery background jobs** başlar:
   - `generate_utterances_for_dataset`: Utterance'ları oluşturur
   - `generate_embeddings_for_variables`: Variable embedding'lerini oluşturur
   - `generate_embeddings_for_utterances`: Utterance embedding'lerini oluşturur (utterance'lar hazır olduktan sonra)

6. ✅ Otomatik olarak **Overview sayfasına** yönlendirilirsiniz (`/overview`)

---

## 🔵 ADIM 3: Dataset Overview Sayfası (İlk Yükleme Sonrası)

### Ne Görmelisiniz:
1. **Dataset Bilgileri**:
   - Dosya adı
   - Toplam satır sayısı (respondents)
   - Toplam sütun sayısı (variables)
   - Quality Score (%)
   - Digital Twin Readiness durumu (green/yellow/red)

2. **Sidebar Menü**:
   - **Overview**: Dataset genel bilgileri (şu an buradasınız)
   - **Quality Report**: Detaylı kalite raporu
   - **Variables**: Değişkenleri keşfetme
   - **Smart Filters**: Akıllı filtreler
   - **Twin Transformer**: Dönüşüm işlemleri
   - **Audiences**: Hedef kitleler oluşturma
   - **Threads**: Soru-cevap sohbetleri
   - **Digital Insight**: AI ile analiz

### İlk Kontroller:
- ✅ Dataset başarıyla yüklendi mi? (Quality Score > 0)
- ✅ Variables görünüyor mu? (Variables sekmesine bakın)
- ⏳ Embedding'ler hazır mı? (Birkaç dakika sürebilir, arka planda çalışıyor)

---

## 🟡 ADIM 4: Dataset Populate Data (Eğer Gerekirse)

**Not**: Yeni yüklenen dataset'lerde otomatik olarak populate edilir. Ancak eski dataset'lerde veya sorun varsa:

### Ne Zaman Gerekir:
- Variables, Respondents, Responses tabloları boşsa
- Quality report gösterilmiyorsa
- Dataset Overview'da veri görünmüyorsa

### Nasıl Yapılır (Şimdilik Manuel - İleride UI'ya eklenecek):
1. Backend API'yi kullanın: `POST /api/research/datasets/{dataset_id}/populate-data`
2. Veya backend loglarını kontrol edin, populate işlemi otomatik olarak başlamış olabilir

---

## 🟣 ADIM 5: Research Workflow Özelliklerini Kullanma

### 5.1. Audiences (Hedef Kitleler) Oluşturma:
1. **Audiences** sayfasına gidin
2. **"Create Audience"** butonuna tıklayın
3. Smart filter'ları kullanarak kitle tanımlayın (örn: "60+ yaş", "Kadın katılımcılar")
4. Audience oluşturulduğunda, otomatik olarak **AudienceMember** kayıtları oluşturulur

### 5.2. Threads (Soru-Cevap Sohbetleri):
1. **Threads** sayfasına gidin
2. **"New Thread"** butonuna tıklayın
3. Dataset ve (opsiyonel) Audience seçin
4. Thread oluşturulduktan sonra **ThreadChatPage**'e yönlendirilirsiniz
5. Soru sorun (örn: "What is the distribution of QV3_10?")
6. Sistem otomatik olarak:
   - Soruyu router'dan geçirir (Structured vs RAG)
   - Cevabı hesaplar/generates eder
   - ThreadResult olarak kaydeder
   - Cache'e ekler

### 5.3. Soru Tipleri:

#### Structured Sorular (Sayısal/İstatistiksel):
- ✅ "What is the distribution of QV3_10?"
- ✅ "How many people selected option 1?"
- ✅ "Compare Baby Boomers vs total sample"
- ✅ "QV3_10'in dağılımı nedir? Sayı ve yüzde göster."

**Ne Beklemelisiniz**:
- Chart/grafik görüntüleme
- Sayısal sonuçlar (counts, percentages)
- Evidence JSON (kanıt verileri)

#### RAG Sorular (Nitel/Açıklayıcı):
- ✅ "Why do respondents mention frustrations?"
- ✅ "What themes do they discuss about customer service?"
- ✅ "Kullanıcılar marka hakkında ne düşünüyor?"

**Ne Beklemelisiniz**:
- Tema özetleri (themes)
- Alıntılar (citations/quotes)
- Narrative açıklama

---

## ⚠️ ÖNEMLİ NOTLAR

### Celery Worker Durumu:
- Celery worker çalışıyor mu kontrol edin: `docker-compose ps` komutuyla
- Eğer worker çalışmıyorsa: `docker-compose up -d celery-worker`
- Loglar: `docker-compose logs celery-worker --tail 50`

### Embedding'ler Hazır Olmadan:
- RAG soruları çalışmayabilir
- "Embeddings not ready" mesajı görebilirsiniz
- Embedding generation 5-10 dakika sürebilir (dataset boyutuna göre)

### Database Temizliği:
- Dataset silme işlemi **tüm bağlı kayıtları** otomatik olarak temizler
- PostgreSQL foreign key constraint'leri CASCADE olarak ayarlı
- Cache kayıtları da temizlenir

### Hata Ayıklama:
1. Backend logları: `docker-compose logs backend --tail 100`
2. Frontend console: Browser Developer Tools (F12)
3. Database kontrolü: PostgreSQL'e bağlanıp tabloları kontrol edin

---

## 📋 ADIM ADIM CHECKLIST

### Dataset Yükleme Sonrası:
- [ ] Overview sayfasında dataset bilgileri görünüyor mu?
- [ ] Quality Score hesaplanmış mı?
- [ ] Variables sayfasında değişkenler listeleniyor mu?
- [ ] Celery worker loglarında utterance generation job başladı mı?
- [ ] Birkaç dakika sonra embedding generation başladı mı?

### Research Workflow Kullanımı:
- [ ] Audience oluşturulabiliyor mu?
- [ ] Thread oluşturulabiliyor mu?
- [ ] Soru sorulabiliyor mu?
- [ ] Structured sorular için chart/grafik görünüyor mu?
- [ ] RAG sorular için themes/citations görünüyor mu?

---

## 🚀 Hızlı Başlangıç Senaryosu

1. **Eski verileri temizle**: `/history` → Dataset'leri sil
2. **Yeni data yükle**: `/` → Dosya seç → Upload
3. **Overview'ı kontrol et**: Dataset bilgilerini görüntüle
4. **Variables'ı keşfet**: `/variables` → Değişkenleri incele
5. **Audience oluştur**: `/audiences` → Filter tanımla
6. **Thread başlat**: `/threads` → New Thread → Soru sor
7. **Sonuçları incele**: Chart, narrative, citations görüntüle

---

**Sorularınız için**: Backend loglarını ve frontend console'unu kontrol edin!

