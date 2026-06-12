# İpekGPT - Proje Dokümantasyonu

## Genel Bakış

İpekGPT, "İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi" için geliştirilmiş bir RAG (Retrieval-Augmented Generation) tabanlı yapay zeka asistanıdır. Türkçe doğal dil işleme kullanarak merkez hakkında sorulara yanıt verir.

## Teknoloji Yığını

| Bileşen | Teknoloji |
|---------|-----------|
| **Backend Framework** | FastAPI |
| **Database** | SQLite (SQLAlchemy ORM) |
| **Vector Database** | ChromaDB |
| **LLM** | Google Gemini API (gemini-2.5-flash) |
| **Embeddings** | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| **Frontend** | Vanilla HTML/CSS/JavaScript |

---

## Proje Yapısı

```
ipekgpt/
├── app/                          # Ana uygulama paketi
│   ├── __init__.py              # Paket tanımı
│   ├── config.py                # Konfigürasyon ayarları
│   ├── database.py              # SQLite veritabanı işlemleri
│   ├── gemini_api.py            # Google Gemini API entegrasyonu
│   ├── main.py                  # FastAPI uygulama giriş noktası
│   ├── models.py                # Pydantic request/response modelleri
│   ├── rag_engine.py            # RAG sistemi (ChromaDB + Gemini)
│   ├── request_queue.py         # FIFO istek kuyruğu
│   ├── rate_limiter.py          # Günlük istek limitleme
│   └── static/                  # Frontend dosyaları
│       ├── index.html           # Ana HTML sayfası
│       ├── style.css            # CSS stilleri
│       ├── script.js            # JavaScript mantığı
│       ├── logo.png             # Logo resmi
│       └── logo.svg             # SVG logo (favicon)
├── chroma_db/                   # ChromaDB vektör veritabanı
│   └── chroma.sqlite3           # Vektörleştirilmiş Q&A verileri
├── data/                        # Veri klasörü
│   ├── processed/               # İşlenmiş JSON veri dosyaları
│   ├── rag_dataset/             # Ham Q&A JSON dosyaları (Kategorik)
│   ├── raw/                     # Ham metin verileri
│   └── mining/                  # Veri madenciliği çıktıları
├── scripts/                     # Yardımcı betikler
│   ├── check_db.py              # Veritabanı kontrol betiği
│   ├── rebuild_chromadb.py      # Vektör DB yeniden oluşturma betiği
│   └── ...                      # Diğer veri madenciliği vb. betikler
├── notebooks/                   # Jupyter Notebooklar
│   └── İpekGPT.ipynb            # Orijinal Jupyter notebook
├── docs/                        # Proje dokümantasyonu
├── ipekgpt.db                   # SQLite veritabanı (sessions, messages)
├── .env                         # Ortam değişkenleri (API keys)
└── requirements.txt             # Python bağımlılıkları
```

---

## Önemli Özellikler

### 1. Konuşma Hafızası
- AI son 6 mesajı (3 kullanıcı-asistan değişimi) hatırlar
- Bağlam korunarak takip sorularına yanıt verilir

### 2. Genel Bilgi Desteği
- Basit matematik soruları (2+2, 5*3 vb.)
- Genel kültür soruları (tarih, coğrafya, bilim)
- Selamlaşma ve kişisel sorulara samimi yanıtlar

### 3. Sabit Layout
- Üst header sabit (scroll etmez)
- Alt mesaj girişi sabit
- Sadece orta chat alanı scroll eder

### 4. Rating Sistemi
- 0 = Oy verilmemiş
- 1 = Olumlu (👍)
- -1 = Olumsuz (👎)

---

## Backend Modülleri

### 1. config.py - Konfigürasyon

```python
class Settings:
    # Veritabanı
    DATABASE_URL = "sqlite:///ipekgpt.db"
    
    # Gemini API (from .env)
    GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Rate Limiting
    DAILY_REQUEST_LIMIT = 300
    MAX_MESSAGE_LENGTH = 300
    
    # Vector Database
    VECTOR_DB_PATH = "chroma_db"
    COLLECTION_NAME = "org_knowledge_turkish"
    
    # Embedding Model
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Retrieval
    TOP_K_RESULTS = 10
```

---

### 2. database.py - Veritabanı

**Tablolar:**

| Tablo | Açıklama |
|-------|----------|
| `sessions` | Sohbet oturumları (UUID, created_at, last_activity) |
| `messages` | Mesajlar (session_id, role, content, response_time_ms) |
| `feedback` | Kullanıcı geri bildirimi (message_id, rating: -1/0/1) |
| `rate_limits` | Günlük istek sayısı (date, request_count) |

**Fonksiyonlar:**
- `create_session()` - Yeni oturum oluştur
- `add_message()` - Mesaj ekle
- `get_session_messages()` - Oturum geçmişi al (son 6 mesaj)
- `add_feedback()` - Geri bildirim ekle/güncelle
- `check_rate_limit()` - Limit kontrolü

---

### 3. gemini_api.py - Gemini API Yönetimi

- Birden fazla API key desteği (rotation)
- Başarısız key'leri günlük sıfırlama
- Rate limiting ve hata yönetimi

---

### 4. main.py - FastAPI Uygulama

**API Endpoints:**

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/` | GET | Frontend HTML sayfası |
| `/api/config` | GET | Frontend konfigürasyonu |
| `/api/session` | POST | Yeni oturum oluştur |
| `/ipekgpt/chat` | POST | AI'a mesaj gönder |
| `/api/feedback` | POST | Geri bildirim gönder |
| `/api/rate-limit` | GET | Rate limit durumu |
| `/health` | GET | Sağlık kontrolü |

**Chat Response:**
```json
{
    "message_id": 123,
    "response": "AI yanıtı",
    "response_time_ms": 1500,
    "sources_count": 5,
    "rating": 0
}
```

---

### 5. rag_engine.py - RAG Sistemi

**Bileşenler:**

1. **VectorStore** - ChromaDB yönetimi
2. **TurkishRAGChatbot** - RAG zinciri + konuşma hafızası
3. **RAGSystem** - Singleton orkestratör

**Prompt Template Özellikleri:**
- Selamlaşma yanıtları (Sa, Merhaba, Günaydın vb.)
- Kişisel sorular (Kimsin, Nerelisin, Ben kimim)
- Genel bilgi soruları (matematik, tarih, coğrafya)
- Merkez bilgileri (RAG context)
- Konuşma geçmişi (son 6 mesaj)

---

### 6. request_queue.py - FIFO Kuyruk

- Sıralı istek işleme
- Konuşma geçmişi desteği
- Async işleme

---

## Frontend

### index.html
- Responsive tasarım
- Favicon: logo.svg
- Sabit header ve input

### style.css
- Modern minimalist tasarım
- Navy mavi asistan mesajları
- Açık mavi kullanıcı mesajları
- Karakter sayacı (sağ alt)

### script.js
- Markdown formatlaması (headers, lists, bold, italic, links)
- Karakter sayacı (mesaj gönderince sıfırlanır)
- Konuşma geçmişi yönetimi
- Otomatik scroll

---

## Çalıştırma

### .env Dosyası
```
GEMINI_API_KEYS=key1,key2,key3
GEMINI_MODEL=gemini-2.5-flash
```

### Başlatma
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Erişim
Tarayıcıda: http://127.0.0.1:8000

---

## Veri Akışı

```
1. Kullanıcı mesaj yazar
   ↓
2. Frontend POST /ipekgpt/chat
   ↓
3. Rate limit kontrolü
   ↓
4. Session doğrulama
   ↓
5. Konuşma geçmişi al (son 6 mesaj)
   ↓
6. Kullanıcı mesajı DB'ye kaydet
   ↓
7. FIFO kuyruğa ekle
   ↓
8. RAG sistemi:
   a. ChromaDB'den benzer dokümanlar bul
   b. Prompt oluştur (context + history + soru)
   c. Gemini API'ye gönder
   ↓
9. AI yanıtı DB'ye kaydet
   ↓
10. Response döndür (rating: 0)
   ↓
11. Frontend mesajı göster
```

---

## Güvenlik

1. **SQL Injection Koruması** - SQLAlchemy ORM
2. **Rate Limiting** - Günlük 300 istek
3. **reCAPTCHA** - Bot koruması (opsiyonel)
4. **Input Validation** - Pydantic + max 300 karakter
5. **API Key Rotation** - Birden fazla Gemini key

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| API key hatası | .env dosyasında GEMINI_API_KEYS kontrol et |
| ChromaDB not found | `chroma_db/` klasörünün var olduğundan emin ol |
| Rate limit | Günde 100 istek limiti, gece yarısı sıfırlanır |
| Feedback kaydedilmiyor | Console'da [DB] loglarını kontrol et |
