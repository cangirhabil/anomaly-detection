# 🚀 Anomali Tespit Mikroservisi - Deployment Kılavuzu

## 📋 İçindekiler

1. [Hızlı Başlangıç](#hızlı-başlangıç)
2. [Docker ile Çalıştırma](#docker-ile-çalıştırma)
3. [Manuel Kurulum](#manuel-kurulum)
4. [Konfigürasyon](#konfigürasyon)
5. [API Kullanımı](#api-kullanımı)
6. [Production Deployment](#production-deployment)
7. [Monitoring ve Logging](#monitoring-ve-logging)

---

## 🚀 Hızlı Başlangıç

### Docker Compose ile (ÖNERİLEN)

```bash
# 1. Projeyi klonla veya kopyala
cd anomali-tespiti

# 2. Servisi başlat
docker-compose up -d

# 3. Health check
curl http://localhost:8000/api/v1/health

# 4. API dokümantasyonunu aç
# http://localhost:8000/api/docs
```

### Manuel Başlatma

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Servisi başlat
uvicorn app:app --host 0.0.0.0 --port 8000

# 3. Test et
curl http://localhost:8000/api/v1/health
```

---

## 🐳 Docker ile Çalıştırma

### Docker Build

```bash
# Image oluştur
docker build -t anomaly-detector:latest .

# Container çalıştır
docker run -d \
  --name anomaly-detector \
  -p 8000:8000 \
  -e ANOMALY_Z_THRESHOLD=2.5 \
  anomaly-detector:latest
```

### Docker Compose

```bash
# Başlat
docker-compose up -d

# Logları izle
docker-compose logs -f

# Durdur
docker-compose down

# Yeniden başlat
docker-compose restart
```

### Docker Hub'a Push (Opsiyonel)

```bash
# Tag ekle
docker tag anomaly-detector:latest your-username/anomaly-detector:1.0.0

# Push et
docker push your-username/anomaly-detector:1.0.0
```

---

## 🔧 Konfigürasyon

### Environment Variables

```bash
# .env dosyası oluştur
cp .env.example .env

# Düzenle
ANOMALY_WINDOW_SIZE=30        # Veri pencere boyutu
ANOMALY_Z_THRESHOLD=2.0       # Z-Score eşiği
ANOMALY_MIN_POINTS=7          # Minimum veri sayısı
PORT=8000                     # Servis portu
LOG_LEVEL=INFO                # Log seviyesi
```

### Config.yaml (Gelişmiş)

```yaml
anomaly:
  window_size: 30
  z_score_threshold: 2.0
  min_data_points: 7

logging:
  level: "INFO"
  format: "json"
```

---

## 📡 API Kullanımı

### Base URL
```
http://localhost:8000
```

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "data_points": 15,
  "ready": true,
  "timestamp": "2025-11-05T10:30:00"
}
```

### 2. Hata Logu Ekle ve Kontrol Et

```bash
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{
    "error_count": 25,
    "date": "2025-11-05T10:00:00"
  }'
```

**Response:**
```json
{
  "is_anomaly": true,
  "current_value": 25,
  "mean": 17.5,
  "std_dev": 2.1,
  "z_score": 3.57,
  "threshold": 2.0,
  "message": "⚠️ ANOMALİ TESPİT EDİLDİ!",
  "timestamp": "2025-11-05T10:30:00"
}
```

### 3. Sadece Anomali Kontrolü (Geçmişe Eklenmez)

```bash
curl -X POST http://localhost:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{
    "value": 30
  }'
```

### 4. İstatistikleri Getir

```bash
curl http://localhost:8000/api/v1/stats
```

**Response:**
```json
{
  "data_points": 20,
  "mean": 17.5,
  "std_dev": 2.1,
  "min": 15,
  "max": 20,
  "latest": 18,
  "threshold": 2.0,
  "window_size": 30
}
```

### 5. Konfigürasyonu Güncelle

```bash
curl -X PUT http://localhost:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "z_score_threshold": 2.5,
    "window_size": 45
  }'
```

### 6. Geçmiş Veriyi Getir

```bash
# Tüm veri
curl http://localhost:8000/api/v1/history

# Son 10 kayıt
curl http://localhost:8000/api/v1/history?limit=10
```

### 7. Sistemi Sıfırla

```bash
curl -X POST http://localhost:8000/api/v1/reset
```

---

## 🌐 Kendi Projenize Entegrasyon

### Python İstemci Örneği

```python
import requests

class AnomalyDetectorClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def log_error(self, error_count: int):
        """Hata ekle ve kontrol et"""
        response = requests.post(
            f"{self.base_url}/api/v1/log",
            json={"error_count": error_count}
        )
        return response.json()
    
    def check_anomaly(self, value: int):
        """Sadece kontrol et"""
        response = requests.post(
            f"{self.base_url}/api/v1/detect",
            json={"value": value}
        )
        return response.json()
    
    def get_stats(self):
        """İstatistikleri al"""
        response = requests.get(f"{self.base_url}/api/v1/stats")
        return response.json()

# Kullanım
client = AnomalyDetectorClient()

# Hata ekle
result = client.log_error(error_count=25)
if result['is_anomaly']:
    print(f"⚠️ Anomali: {result['message']}")

# İstatistik
stats = client.get_stats()
print(f"Ortalama: {stats['mean']}")
```

### JavaScript/TypeScript İstemci Örneği

```javascript
class AnomalyDetectorClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async logError(errorCount) {
    const response = await fetch(`${this.baseUrl}/api/v1/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error_count: errorCount })
    });
    return response.json();
  }

  async checkAnomaly(value) {
    const response = await fetch(`${this.baseUrl}/api/v1/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value })
    });
    return response.json();
  }

  async getStats() {
    const response = await fetch(`${this.baseUrl}/api/v1/stats`);
    return response.json();
  }
}

// Kullanım
const client = new AnomalyDetectorClient();

const result = await client.logError(25);
if (result.is_anomaly) {
  console.log('⚠️ Anomali:', result.message);
}
```

### cURL ile Test Scripti

```bash
#!/bin/bash

API_URL="http://localhost:8000"

# 20 gün normal veri ekle
for i in {1..20}; do
  curl -X POST $API_URL/api/v1/log \
    -H "Content-Type: application/json" \
    -d "{\"error_count\": $((15 + RANDOM % 6))}" \
    -s | jq '.is_anomaly'
  sleep 0.5
done

# Anormal veri
curl -X POST $API_URL/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 35}' | jq '.'
```

---

## 🏭 Production Deployment

### 1. AWS ECS ile Deployment

```bash
# ECR'a push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ECR_URL
docker tag anomaly-detector:latest YOUR_ECR_URL/anomaly-detector:latest
docker push YOUR_ECR_URL/anomaly-detector:latest

# ECS task definition
# task-definition.json kullanın
```

### 2. Kubernetes Deployment

```yaml
# deployment.yaml
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
```

### 3. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name anomaly-detector.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. SSL/TLS (Let's Encrypt)

```bash
# Certbot kurulumu
sudo apt-get install certbot python3-certbot-nginx

# SSL sertifikası
sudo certbot --nginx -d anomaly-detector.yourdomain.com
```

---

## 📊 Monitoring ve Logging

### Health Check

```bash
# Script ile otomatik kontrol
watch -n 10 curl http://localhost:8000/api/v1/health
```

### Logları İzleme

```bash
# Docker logs
docker-compose logs -f anomaly-detector

# Canlı log izleme
tail -f logs/anomaly-detector.log
```

### Prometheus Metrics (Gelecek Özellik)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'anomaly-detector'
    static_configs:
      - targets: ['localhost:9090']
```

---

## 🔒 Güvenlik

### API Key Koruması (Opsiyonel)

```python
# app.py'ye ekle
from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY", "your-secret-key")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Endpoint'e ekle
@app.post("/api/v1/log", dependencies=[Depends(verify_api_key)])
```

### Rate Limiting

```bash
# Nginx ile
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20;
}
```

---

## 🧪 Test Senaryoları

### Yük Testi

```bash
# Apache Bench
ab -n 1000 -c 10 -p data.json -T application/json http://localhost:8000/api/v1/log

# wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/health
```

### Integration Test

```python
import pytest
import requests

def test_full_workflow():
    base_url = "http://localhost:8000"
    
    # Health check
    response = requests.get(f"{base_url}/api/v1/health")
    assert response.status_code == 200
    
    # Log error
    response = requests.post(
        f"{base_url}/api/v1/log",
        json={"error_count": 20}
    )
    assert response.status_code == 200
    
    # Get stats
    response = requests.get(f"{base_url}/api/v1/stats")
    assert response.status_code == 200
    assert response.json()["data_points"] > 0
```

---

## 🐛 Sorun Giderme

### Port Çakışması

```bash
# Port 8000 kullanımda ise
PORT=8001 uvicorn app:app --host 0.0.0.0 --port 8001
```

### Container Çalışmıyor

```bash
# Logları kontrol et
docker logs anomaly-detector-service

# Container'ı yeniden başlat
docker-compose restart
```

### Bellek Problemi

```bash
# Docker resource limitlerini artır
# docker-compose.yml dosyasında memory limitini yükselt
```

---

## 📞 Destek

- **API Dokümantasyonu:** http://localhost:8000/api/docs
- **Health Endpoint:** http://localhost:8000/api/v1/health
- **Loglar:** `docker-compose logs -f`

---

**🎉 Mikroservis hazır! Kendi projenize entegre edebilirsiniz.**
