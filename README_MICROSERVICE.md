# 🔍 Anomali Tespit Mikroservisi

**Z-Score Tabanlı İstatistiksel Anomali Tespit REST API**

Production-ready mikroservis - Kendi projenize entegre edilmeye hazır!

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚡ Hızlı Başlangıç (2 Dakika)

### Docker ile (Önerilen)

```bash
docker-compose up -d
```

### Manuel

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

**API Hazır!** → http://localhost:8000/api/docs

---

## 🎯 Özellikler

✅ **REST API** - FastAPI ile yüksek performanslı HTTP endpoint'ler  
✅ **Docker Ready** - Tek komutla başlatma  
✅ **Plug & Play** - Herhangi bir projeye entegre edilebilir  
✅ **Real-time** - Gerçek zamanlı anomali tespiti  
✅ **Auto-learning** - Sistem kendini otomatik günceller  
✅ **Production Ready** - Logging, health check, monitoring  

---

## 📡 API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `POST` | `/api/v1/log` | Hata ekle ve anomali kontrol et |
| `POST` | `/api/v1/detect` | Sadece anomali kontrolü (geçmişe eklenmez) |
| `GET` | `/api/v1/stats` | İstatistikleri getir |
| `GET` | `/api/v1/health` | Sağlık kontrolü |
| `GET` | `/api/v1/config` | Konfigürasyon bilgisi |
| `PUT` | `/api/v1/config` | Konfigürasyon güncelle |
| `GET` | `/api/v1/history` | Geçmiş veriyi getir |
| `POST` | `/api/v1/reset` | Sistemi sıfırla |

**İnteraktif API Docs:** http://localhost:8000/api/docs

---

## 🚀 Kullanım Örnekleri

### Python

```python
import requests

# Hata ekle
response = requests.post(
    "http://localhost:8000/api/v1/log",
    json={"error_count": 25}
)
result = response.json()

if result['is_anomaly']:
    print(f"⚠️ Anomali! Z-Score: {result['z_score']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/log', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ error_count: 25 })
});

const result = await response.json();
if (result.is_anomaly) {
  console.log('⚠️ Anomali tespit edildi!');
}
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 25}'
```

---

## 🐳 Docker Deployment

### Tek Container

```bash
docker build -t anomaly-detector .
docker run -d -p 8000:8000 anomaly-detector
```

### Docker Compose

```bash
docker-compose up -d
```

### Kendi Projenizle Birlikte

```yaml
# docker-compose.yml
services:
  your-app:
    build: .
    depends_on:
      - anomaly-detector
  
  anomaly-detector:
    image: anomaly-detector:latest
    ports:
      - "8000:8000"
    environment:
      - ANOMALY_Z_THRESHOLD=2.0
```

---

## ⚙️ Konfigürasyon

### Environment Variables

```bash
ANOMALY_WINDOW_SIZE=30        # Veri pencere boyutu (gün)
ANOMALY_Z_THRESHOLD=2.0       # Z-Score eşiği
ANOMALY_MIN_POINTS=7          # Minimum veri sayısı
PORT=8000                     # Servis portu
LOG_LEVEL=INFO                # Log seviyesi
```

### Runtime Güncelleme

```bash
curl -X PUT http://localhost:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{"z_score_threshold": 2.5}'
```

---

## 📊 Response Örneği

```json
{
  "is_anomaly": true,
  "current_value": 35,
  "mean": 17.5,
  "std_dev": 2.1,
  "z_score": 8.33,
  "threshold": 2.0,
  "message": "⚠️ ANOMALİ TESPİT EDİLDİ!",
  "timestamp": "2025-11-05T10:30:00"
}
```

---

## 🔌 Entegrasyon Örnekleri

### Flask/FastAPI Projesi

```python
from monitoring import AnomalyMonitor

monitor = AnomalyMonitor("http://localhost:8000")

@app.route('/api/data')
def handle_data():
    # Hata sayınızı gönderin
    result = monitor.log_error(error_count)
    
    if result['is_anomaly']:
        send_alert_to_team(result)
    
    return result
```

### Scheduled Job

```python
import schedule

def daily_check():
    errors = get_last_24h_errors()
    result = monitor.log_error(errors)
    
    if result['is_anomaly']:
        notify_team(result)

schedule.every().day.at("00:00").do(daily_check)
```

Daha fazla örnek için: [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

---

## 📁 Proje Yapısı

```
anomali-tespiti/
├── anomaly_detector/        # Core paket
│   ├── detector.py          # Ana motor
│   ├── config.py            # Konfigürasyon
│   └── models.py            # Veri modelleri
├── app.py                   # ⭐ FastAPI mikroservis
├── Dockerfile               # Docker build
├── docker-compose.yml       # Docker compose
├── requirements.txt         # Python dependencies
├── DEPLOYMENT.md            # Deployment kılavuzu
├── INTEGRATION_GUIDE.md     # Entegrasyon rehberi
└── README.md                # Bu dosya
```

---

## 🧪 Test

```bash
# API testi
python test_api.py

# Health check
curl http://localhost:8000/api/v1/health

# Interactive test
# http://localhost:8000/api/docs
```

---

## 📖 Dokümantasyon

- **API Docs (Swagger):** http://localhost:8000/api/docs
- **API Docs (ReDoc):** http://localhost:8000/api/redoc
- **Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Integration Guide:** [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)

---

## 🔬 Z-Score Metodolojisi

```
Z = (X - μ) / σ

X = Mevcut hata sayısı
μ = Ortalama (son N gün)
σ = Standart sapma
```

**Eşik Değerleri:**
- `Z = 2.0` → %95 güven (Önerilen)
- `Z = 2.5` → %98.8 güven
- `Z = 3.0` → %99.7 güven (Konservatif)

---

## 🏭 Production Deployment

### AWS ECS

```bash
# ECR'a push
docker tag anomaly-detector:latest YOUR_ECR/anomaly-detector:latest
docker push YOUR_ECR/anomaly-detector:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anomaly-detector
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: anomaly-detector
        image: anomaly-detector:latest
        ports:
        - containerPort: 8000
```

### Cloud Run (GCP)

```bash
gcloud run deploy anomaly-detector \
  --image gcr.io/PROJECT_ID/anomaly-detector \
  --platform managed
```

---

## 📊 Monitoring

### Prometheus Metrics (Gelecek)

```yaml
- job_name: 'anomaly-detector'
  static_configs:
    - targets: ['localhost:8000']
```

### Logging

```bash
# Docker logs
docker-compose logs -f anomaly-detector

# JSON formatında
docker-compose logs anomaly-detector | jq
```

---

## 🔒 Güvenlik

### API Key Protection (Opsiyonel)

```python
headers = {
    "X-API-Key": "your-secret-key"
}
requests.post(url, headers=headers, json=data)
```

### Rate Limiting

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

---

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle karşılanır!

---

## 📝 Lisans

MIT License - İstediğiniz gibi kullanabilirsiniz!

---

## 📞 Destek

- **Issues:** GitHub Issues
- **API Docs:** http://localhost:8000/api/docs
- **Email:** support@example.com

---

## ⭐ Özellikler Roadmap

- [x] REST API
- [x] Docker support
- [x] Health checks
- [x] Logging
- [ ] Prometheus metrics
- [ ] Authentication
- [ ] Rate limiting
- [ ] Data persistence (Redis/PostgreSQL)
- [ ] WebSocket support
- [ ] Multi-model support (LSTM, Isolation Forest)

---

**🎉 Mikroservis hazır! Kendi projenize entegre edebilirsiniz.**

```bash
# 1. Başlatın
docker-compose up -d

# 2. Test edin
curl http://localhost:8000/api/v1/health

# 3. Kullanın
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 25}'
```

**Happy monitoring! 🚀**
