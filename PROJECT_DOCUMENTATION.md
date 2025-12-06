# İpekGPT - Proje Dokümantasyonu

## Genel Bakış

İpekGPT, "İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi" için geliştirilmiş bir RAG (Retrieval-Augmented Generation) tabanlı yapay zeka asistanıdır. Türkçe doğal dil işleme kullanarak merkez hakkında sorulara yanıt verir.

## Teknoloji Yığını

| Bileşen | Teknoloji |
|---------|-----------|
| **Backend Framework** | FastAPI |
| **Database** | SQLite (SQLAlchemy ORM) |
| **Vector Database** | ChromaDB |
| **LLM** | Turkish-Gemma-9b-T1-GGUF (llama-cpp-python) |
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
│   ├── main.py                  # FastAPI uygulama giriş noktası
│   ├── models.py                # Pydantic request/response modelleri
│   ├── rag_engine.py            # RAG sistemi (ChromaDB + Gemma LLM)
│   ├── rate_limiter.py          # Günlük istek limitleme
│   ├── recaptcha.py             # Google reCAPTCHA doğrulama
│   └── static/                  # Frontend dosyaları
│       ├── index.html           # Ana HTML sayfası
│       ├── style.css            # CSS stilleri
│       ├── script.js            # JavaScript mantığı
│       ├── logo.png             # Logo resmi
│       └── logo.svg             # SVG logo
├── chroma_db/                   # ChromaDB vektör veritabanı
│   └── chroma.sqlite3           # Vektörleştirilmiş Q&A verileri
├── IPEKYOLU_RAG_VERISETI/       # Ham Q&A JSON dosyaları
├── data/                        # Eski format veri dosyaları
├── ipekgpt.db                   # SQLite veritabanı (sessions, messages)
├── requirements.txt             # Python bağımlılıkları
└── İpekGPT.ipynb               # Orijinal Jupyter notebook
```

---

## Backend Modülleri

### 1. config.py - Konfigürasyon

Tüm uygulama ayarlarını içerir:

```python
class Settings:
    # Veritabanı
    DATABASE_URL = "sqlite:///ipekgpt.db"
    
    # reCAPTCHA (opsiyonel)
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")
    
    # Rate Limiting
    DAILY_REQUEST_LIMIT = 100  # Günlük maksimum AI isteği
    USER_TOKEN_LIMIT = 1024    # Kullanıcı bağlam penceresi
    
    # Vector Database
    VECTOR_DB_PATH = "chroma_db"
    COLLECTION_NAME = "org_knowledge_turkish"
    
    # Embedding Model
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # LLM (Turkish Gemma)
    GEMMA_REPO_ID = "ytu-ce-cosmos/Turkish-Gemma-9b-T1-GGUF"
    GEMMA_FILENAME = "*Q4_K.gguf"
    
    # Gemma parametreleri
    GEMMA_PARAMS = {
        "n_gpu_layers": -1,   # Tüm katmanları GPU'da çalıştır
        "n_threads": 4,
        "n_ctx": 8192,        # Context window
        "n_predict": 2048,    # Maksimum çıktı tokeni
        "top_k": 40,
        "top_p": 0.90,
        "temp": 0.1,
        "repeat_penalty": 1.1,
    }
    
    # Retrieval
    TOP_K_RESULTS = 10  # Benzer doküman sayısı
    
    # Server
    HOST = "127.0.0.1"
    PORT = 8000
```

---

### 2. database.py - Veritabanı Katmanı

SQLite veritabanı şeması ve CRUD operasyonları:

**Tablolar:**

| Tablo | Açıklama |
|-------|----------|
| `sessions` | Sohbet oturumları (UUID, created_at, last_activity) |
| `messages` | Mesajlar (session_id, role, content, response_time_ms) |
| `feedback` | Kullanıcı geri bildirimi (message_id, rating: 1/-1) |
| `rate_limits` | Günlük istek sayısı (date, request_count) |

**Fonksiyonlar:**
- `create_session()` - Yeni oturum oluştur
- `add_message()` - Mesaj ekle
- `add_feedback()` - Geri bildirim ekle
- `check_rate_limit()` - Limit kontrolü
- `increment_request_count()` - İstek sayacını artır

---

### 3. main.py - FastAPI Uygulama

**API Endpoints:**

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/` | GET | Frontend HTML sayfası |
| `/api/config` | GET | Frontend konfigürasyonu |
| `/api/session` | POST | Yeni oturum oluştur |
| `/api/chat` | POST | AI'a mesaj gönder |
| `/api/feedback` | POST | Geri bildirim gönder |
| `/api/rate-limit` | GET | Rate limit durumu |
| `/api/verify-captcha` | POST | reCAPTCHA doğrula |
| `/health` | GET | Sağlık kontrolü |

**Chat Request:**
```json
{
    "session_id": "uuid-string",
    "message": "Kullanıcı mesajı",
    "recaptcha_token": "optional-token"
}
```

**Chat Response:**
```json
{
    "message_id": 123,
    "response": "AI yanıtı",
    "response_time_ms": 1500,
    "sources_count": 5
}
```

---

### 4. rag_engine.py - RAG Sistemi

**Bileşenler:**

1. **VectorStore** - ChromaDB yönetimi
   - Mevcut vektör veritabanını yükler
   - HuggingFace embeddings kullanır

2. **TurkishGemmaLLM** - LLM wrapper
   - llama-cpp-python ile Gemma modeli
   - Türkçe yanıt temizleme

3. **TurkishRAGChatbot** - RAG zinciri
   - Soru → Benzer doküman bulma → Prompt oluşturma → LLM yanıtı

4. **RAGSystem** - Singleton orkestratör
   - Tüm bileşenleri yönetir
   - `ask(question)` metodu ile soru yanıtlama

**Prompt Template:**
```
<bos><start_of_turn>user
Sen İpekyolu Girişimci Kuluçka Merkezi'nin resmi yapay zeka asistanısın.
Adın: İpekGPT.

GÖREVİN:
Sana verilen bilgileri *kendi bilginmiş gibi* kabul et ve kullanıcıya doğrudan cevap ver.

KURALLAR:
1. "Bağlamdaki bilgilere göre" gibi ifadeler KESİNLİKLE KULLANMA.
2. Doğrudan cevabı ver.
3. Listeleri madde işaretleri ile düzenle.
4. Bilgi yoksa, "Bu konuda şu an güncel bilgim bulunmuyor" de.

VERİLER:
{context}

SORU: {question}<end_of_turn>
<start_of_turn>model
```

---

### 5. models.py - Pydantic Modeller

**Request Modelleri:**
- `ChatRequest` - session_id, message, recaptcha_token
- `FeedbackRequest` - message_id, rating (-1, 1)
- `RecaptchaVerifyRequest` - token

**Response Modelleri:**
- `SessionResponse` - session_id, created_at
- `ChatResponse` - message_id, response, response_time_ms, sources_count
- `FeedbackResponse` - success, message
- `RateLimitResponse` - remaining_requests, reset_time

---

### 6. rate_limiter.py - Rate Limiting

- Günlük 100 istek limiti
- Gece yarısı sıfırlanır
- `get_reset_time()` - Sonraki sıfırlama zamanı

### 7. recaptcha.py - reCAPTCHA

- Google reCAPTCHA v3 entegrasyonu
- `verify_recaptcha(token)` - Token doğrulama
- `is_captcha_configured()` - Aktif mi kontrolü

---

## Frontend

### index.html
- Semantic HTML5 yapısı
- Responsive tasarım
- Erişilebilirlik özellikleri

### style.css
- Modern minimalist tasarım
- Beyaz arka plan
- Navy mavi asistan mesaj baloncukları
- Açık mavi kullanıcı mesaj baloncukları
- Cyan gönder butonu

### script.js
- Session yönetimi
- API çağrıları (`fetch`)
- Mesaj gönderme/alma
- Geri bildirim (thumbs up/down)
- reCAPTCHA entegrasyonu
- Rate limit gösterimi
- Typing indicator animasyonu

---

## Çalıştırma

### Gereksinimler
```bash
pip install fastapi uvicorn sqlalchemy langchain langchain-core langchain-chroma langchain-huggingface chromadb sentence-transformers llama-cpp-python
```

### GPU Desteği (Opsiyonel)
CUDA 12.4 + Visual Studio 2022 Build Tools gerekli:
```bash
$env:CMAKE_ARGS="-DGGML_CUDA=on"
pip install llama-cpp-python --no-cache-dir
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
2. Frontend POST /api/chat
   ↓
3. Rate limit kontrolü
   ↓
4. reCAPTCHA doğrulama (aktifse)
   ↓
5. Session doğrulama
   ↓
6. Kullanıcı mesajı DB'ye kaydet
   ↓
7. RAG sistemi:
   a. ChromaDB'den benzer dokümanlar bul (top-k)
   b. Prompt oluştur (context + soru)
   c. Turkish Gemma LLM'e gönder
   d. Yanıtı temizle
   ↓
8. AI yanıtı DB'ye kaydet
   ↓
9. Response döndür
   ↓
10. Frontend mesajı göster
```

---

## Güvenlik

1. **SQL Injection Koruması** - SQLAlchemy ORM ile parametrik sorgular
2. **Rate Limiting** - Günlük 100 istek limiti
3. **reCAPTCHA** - Bot koruması (opsiyonel)
4. **Input Validation** - Pydantic ile veri doğrulama
5. **CORS** - Geliştirme için açık, production'da kısıtlanmalı

---

## Önemli Notlar

1. **İlk çalıştırma** - Turkish Gemma modeli (~5.76GB) indirilir
2. **ChromaDB** - Önceden oluşturulmuş olmalı (`chroma_db/` klasörü)
3. **GPU kullanımı** - `n_gpu_layers: -1` tüm katmanları GPU'da çalıştırır
4. **CPU modu** - GPU yoksa CPU'da çalışır (yavaş)

---

## Dosya İlişkileri

```
main.py
  ├── imports: config, database, models, recaptcha, rate_limiter
  └── lazy import: rag_engine (ilk chat isteğinde)

rag_engine.py
  ├── imports: config
  ├── uses: langchain, chromadb, llama_cpp
  └── loads: chroma_db/, Turkish Gemma model

database.py
  ├── imports: config
  └── creates: ipekgpt.db (sessions, messages, feedback, rate_limits)
```

---

## API Kullanım Örneği

```javascript
// 1. Session oluştur
const session = await fetch('/api/session', { method: 'POST' });
const { session_id } = await session.json();

// 2. Mesaj gönder
const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id: session_id,
        message: "Merkez ne zaman kuruldu?"
    })
});
const { response: answer, message_id } = await response.json();

// 3. Geri bildirim gönder
await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message_id: message_id,
        rating: 1  // Thumbs up
    })
});
```

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| UnicodeEncodeError | Print ifadelerindeki emoji'leri kaldır |
| CUDA toolset not found | Visual Studio 2022 Build Tools kur |
| ChromaDB not found | `chroma_db/` klasörünün var olduğundan emin ol |
| Model indirme yavaş | İlk çalıştırmada ~5.76GB indirilir, bekle |
| Out of memory | `n_gpu_layers` değerini düşür veya CPU kullan |
