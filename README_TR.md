# 🚀 Anomali Tespit Mikroservisi

**İstatistiksel anomali tespiti için production-ready mikroservis**

Z-Score metodolojisi kullanarak günlük hata sayılarındaki anormal artışları otomatik tespit eden, plug-and-play FastAPI mikroservisi.

---

## ✨ Özellikler

- ✅ **İstatistiksel Tespit:** Z-Score algoritması ile bilimsel anomali tespiti
- ✅ **REST API:** 8 endpoint ile tam özellikli API
- ✅ **Plug-and-Play:** Docker ile tek komutla çalışır
- ✅ **Dil Bağımsız:** Python, JavaScript, Java, C# vb. her dilden kullanılabilir
- ✅ **Production-Ready:** Kubernetes, AWS, GCP, Azure desteği
- ✅ **Interactive Docs:** Swagger UI ile API dokümantasyonu
- ✅ **Python Client:** Hazır client kütüphanesi
- ✅ **Güvenli:** Non-root container, health checks, resource limits

---

## 🚀 Hızlı Başlangıç

### Docker ile (Önerilen) ⚡

```powershell
# Servisi başlat
docker-compose up -d

# API'yi test et
curl http://localhost:8000/api/v1/health

# API dokümantasyonunu aç
# http://localhost:8000/api/docs
```

### Python ile 🐍

```powershell
# Bağımlılıkları yükle
pip install -r requirements.txt

# Servisi başlat
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## 💡 Kullanım Örnekleri

### Python Client ile:

```python
from anomaly_client import AnomalyClient

# Client oluştur
client = AnomalyClient("http://localhost:8000")

# Hata kaydı ekle
response = client.log_error(
    error_count=42,
    timestamp="2024-01-15"
)
print(f"Kayıt eklendi: {response.message}")

# Anomali tespit et
result = client.detect_anomaly(
    current_value=150,
    timestamp="2024-01-16"
)

if result.is_anomaly:
    print(f"⚠️ ANOMALİ TESPİT EDİLDİ!")
    print(f"Z-Score: {result.z_score:.2f}")
    print(f"Şiddet: {result.severity}")
else:
    print(f"✅ Normal değer (Z-Score: {result.z_score:.2f})")

# İstatistikleri getir
stats = client.get_stats()
print(f"Ortalama: {stats.mean:.2f}")
print(f"Std Sapma: {stats.std_dev:.2f}")
print(f"Toplam kayıt: {stats.total_records}")
```

### REST API ile (JavaScript):

```javascript
// Hata kaydı ekle
const logResponse = await fetch('http://localhost:8000/api/v1/log', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    error_count: 42,
    timestamp: '2024-01-15'
  })
});

// Anomali tespit et
const detectResponse = await fetch('http://localhost:8000/api/v1/detect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    current_value: 150,
    timestamp: '2024-01-16'
  })
});

const result = await detectResponse.json();
if (result.is_anomaly) {
  console.log(`⚠️ Anomali! Z-Score: ${result.z_score}`);
}
```

### cURL ile:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Hata kaydı ekle
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 42, "timestamp": "2024-01-15"}'

# Anomali tespit et
curl -X POST http://localhost:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{"current_value": 150, "timestamp": "2024-01-16"}'

# İstatistikleri getir
curl http://localhost:8000/api/v1/stats
```

---

## 📡 API Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `POST` | `/api/v1/log` | Hata kaydı ekle |
| `POST` | `/api/v1/detect` | Anomali tespit et |
| `GET` | `/api/v1/stats` | İstatistikleri getir |
| `GET` | `/api/v1/health` | Servis sağlık kontrolü |
| `POST` | `/api/v1/bulk-log` | Toplu kayıt ekle |
| `GET` | `/api/v1/history` | Geçmiş kayıtları getir |
| `DELETE` | `/api/v1/clear` | Tüm verileri temizle |
| `PUT` | `/api/v1/config` | Konfigürasyonu güncelle |

**Interactive API Dokümantasyonu:** http://localhost:8000/api/docs

---

## ⚙️ Konfigürasyon

### Environment Variables (.env):

```bash
# API Ayarları
ANOMALY_API_HOST=0.0.0.0
ANOMALY_API_PORT=8000

# Anomali Tespit Parametreleri
ANOMALY_WINDOW_SIZE=30           # Sliding window boyutu (gün)
ANOMALY_Z_THRESHOLD=2.0          # Z-Score eşik değeri
ANOMALY_MIN_DATA_POINTS=7        # Minimum veri sayısı
ANOMALY_ALERT_MESSAGE=⚠️ ANOMALİ TESPİT EDİLDİ!

# Log Seviyesi
ANOMALY_LOG_LEVEL=INFO
```

### config.yaml:

```yaml
detector:
  window_size: 30              # Sliding window (gün)
  z_score_threshold: 2.0       # Z-Score eşiği (1.645, 2.0, 3.0)
  min_data_points: 7           # Minimum veri sayısı
  alert_message: "⚠️ ANOMALİ TESPİT EDİLDİ!"

api:
  host: "0.0.0.0"
  port: 8000
  log_level: "INFO"
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:8080"
```

---

## 📊 Z-Score Metodolojisi

```
Z-Score = (X - μ) / σ
```

- **X:** Güncel değer
- **μ:** Ortalama (son N gün)
- **σ:** Standart sapma

### Anomali Seviyeleri:

| Z-Score | Seviye | Olasılık | Açıklama |
|---------|--------|----------|----------|
| < 1.645 | Normal | %90 | Normal davranış |
| 1.645-2.0 | Düşük | %90-95 | Hafif sapma |
| 2.0-3.0 | Orta | %95-99.7 | Orta seviye anomali |
| > 3.0 | Yüksek | > %99.7 | Ciddi anomali |

---

## 🐳 Docker Deployment

### Docker Compose (Önerilen):

```powershell
# Servisi başlat
docker-compose up -d

# Logları takip et
docker-compose logs -f

# Servisi durdur
docker-compose down
```

### Manuel Docker:

```powershell
# Image build et
docker build -t anomaly-detector:latest .

# Container çalıştır
docker run -d \
  --name anomaly-detector \
  -p 8000:8000 \
  -e ANOMALY_Z_THRESHOLD=2.0 \
  anomaly-detector:latest
```

---

## 🚢 Production Deployment

### Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anomaly-detector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: anomaly-detector
  template:
    metadata:
      labels:
        app: anomaly-detector
    spec:
      containers:
      - name: anomaly-detector
        image: anomaly-detector:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANOMALY_Z_THRESHOLD
          value: "2.0"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

**Detaylı deployment bilgileri için:** `DEPLOYMENT.md`

---

## 📁 Proje Yapısı

```
anomali-tespiti/
├── anomaly_detector/          # Core modül
│   ├── __init__.py
│   ├── config.py             # Konfigürasyon yönetimi
│   ├── detector.py           # Z-Score tespit motoru
│   └── models.py             # Veri modelleri
├── app.py                    # FastAPI mikroservis
├── anomaly_client.py         # Python client kütüphanesi
├── Dockerfile                # Container image
├── docker-compose.yml        # Docker orchestration
├── config.yaml               # Servis konfigürasyonu
├── requirements.txt          # Python bağımlılıkları
├── .env.example              # Environment değişkenleri
├── .gitignore                # Git ignore kuralları
├── README_TR.md              # Bu dosya
├── README_MICROSERVICE.md    # Mikroservis detayları
├── DEPLOYMENT.md             # Deployment rehberi
├── INTEGRATION_GUIDE.md      # Entegrasyon örnekleri
├── MICROSERVICE_OZET.txt     # Türkçe özet
├── demo.py                   # Demo senaryoları
├── test_api.py               # API testleri
└── test_system.py            # Sistem testleri
```

---

## 🧪 Test

```powershell
# Sistem testlerini çalıştır
python test_system.py

# API testlerini çalıştır (servis çalışır durumda olmalı)
python test_api.py

# Demo senaryolarını çalıştır
python demo.py
```

---

## 📚 Dokümantasyon

- **README_TR.md** _(bu dosya)_ - Türkçe kullanım kılavuzu
- **README_MICROSERVICE.md** - Mikroservis detayları (İngilizce)
- **DEPLOYMENT.md** - Production deployment rehberi
- **INTEGRATION_GUIDE.md** - Çoklu dil entegrasyon örnekleri
- **MICROSERVICE_OZET.txt** - Türkçe detaylı özet
- **http://localhost:8000/api/docs** - Interactive API dokümantasyonu

---

## 🔧 Geliştirme

### Lokal Geliştirme:

```powershell
# Virtual environment oluştur
python -m venv venv
.\venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Development modunda başlat (auto-reload)
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Yeni Özellik Eklemek:

1. `anomaly_detector/detector.py` - Core algoritma değişiklikleri
2. `app.py` - Yeni API endpoints
3. `anomaly_client.py` - Client kütüphanesi güncellemeleri
4. Test ekle: `test_api.py` veya `test_system.py`

---

## ⚡ Performans

- **Throughput:** ~1000 request/saniye
- **Latency:** <50ms (P95)
- **Memory:** ~100MB (base)
- **CPU:** Minimal (statistical calculations)

---

## 🔒 Güvenlik

- ✅ Non-root container kullanıcısı
- ✅ CORS koruması
- ✅ Input validation (Pydantic)
- ✅ Health check endpoints
- ✅ Resource limits (Docker)
- ✅ Environment variable injection

---

## 🤝 Katkıda Bulunma

Projeye katkıda bulunmak için:

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

---

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

---

## 💬 Destek

Sorularınız için:
- 📖 Dokümantasyonu inceleyin
- 🐛 Issue açın
- 💡 Feature request gönderin

---

## 🎯 Kullanım Senaryoları

### 1. Backend Error Monitoring
```python
# Günlük hata sayılarını izle
client.log_error(error_count=daily_errors)
result = client.detect_anomaly(current_value=today_errors)
```

### 2. API Rate Limiting
```python
# Anormal trafik artışlarını tespit et
client.log_error(error_count=api_requests)
if client.detect_anomaly(current_value=current_requests).is_anomaly:
    # Rate limiting uygula
    apply_rate_limit()
```

### 3. System Health Monitoring
```python
# Sistem metriklerini izle
client.log_error(error_count=system_errors)
if client.detect_anomaly(current_value=latest_errors).is_anomaly:
    # Alert gönder
    send_alert()
```

---

**🚀 Projenizde Başarılar!**
