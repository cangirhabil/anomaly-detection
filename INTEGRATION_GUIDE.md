# 🎯 Anomali Tespit Mikroservisi - Kendi Projenize Entegre Edin

## 🚀 Hızlı Başlangıç (Plug-and-Play)

### Seçenek 1: Docker ile Başlatma (ÖNERİLEN)

```bash
# 1. Proje klasörünü kopyalayın
cp -r anomali-tespiti /path/to/your/project/

# 2. Docker Compose ile başlatın
cd anomali-tespiti
docker-compose up -d

# 3. API hazır!
curl http://localhost:8000/api/v1/health
```

### Seçenek 2: Manuel Başlatma

```bash
# 1. Bağımlılıkları yükleyin
cd anomali-tespiti
pip install -r requirements.txt

# 2. Servisi başlatın
uvicorn app:app --host 0.0.0.0 --port 8000

# 3. Test edin
curl http://localhost:8000/api/v1/health
```

---

## 📡 API Kullanımı - Hızlı Referans

### Base URL
```
http://localhost:8000
```

### 1. Hata Ekle ve Anomali Kontrol Et

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/log",
    json={"error_count": 25}
)
result = response.json()

if result['is_anomaly']:
    print(f"⚠️ Anomali! Z-Score: {result['z_score']}")
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/log', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ error_count: 25 })
});
const result = await response.json();

if (result.is_anomaly) {
  console.log(`⚠️ Anomali! Z-Score: ${result.z_score}`);
}
```

**cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 25}'
```

### 2. İstatistikleri Al

```bash
curl http://localhost:8000/api/v1/stats
```

### 3. Sadece Kontrol Et (Geçmişe Eklenmez)

```bash
curl -X POST http://localhost:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{"value": 30}'
```

---

## 🔌 Kendi Projenize Entegrasyon Örnekleri

### Python Flask/FastAPI Projesi

```python
# your_project/monitoring.py
import requests

class AnomalyMonitor:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
    
    def log_error(self, count: int):
        """Hata sayısını logla ve anomali kontrol et"""
        response = requests.post(
            f"{self.api_url}/api/v1/log",
            json={"error_count": count}
        )
        result = response.json()
        
        if result['is_anomaly']:
            # Alarm mekanizması
            self.send_alert(result)
        
        return result
    
    def send_alert(self, anomaly_data):
        """Anomali durumunda alarm gönder"""
        # Email, Slack, SMS vb.
        print(f"🚨 ALARM: {anomaly_data['message']}")

# Kullanım
monitor = AnomalyMonitor()

# Günlük hata sayınızı gönderin
daily_errors = get_daily_error_count()
result = monitor.log_error(daily_errors)
```

### Node.js/Express Projesi

```javascript
// monitoring.js
const axios = require('axios');

class AnomalyMonitor {
  constructor(apiUrl = 'http://localhost:8000') {
    this.apiUrl = apiUrl;
  }

  async logError(count) {
    try {
      const response = await axios.post(`${this.apiUrl}/api/v1/log`, {
        error_count: count
      });
      
      if (response.data.is_anomaly) {
        await this.sendAlert(response.data);
      }
      
      return response.data;
    } catch (error) {
      console.error('Anomali servisi hatası:', error);
    }
  }

  async sendAlert(anomalyData) {
    console.log('🚨 ALARM:', anomalyData.message);
    // Email, Slack notification vb.
  }
}

// Kullanım
const monitor = new AnomalyMonitor();

setInterval(async () => {
  const errorCount = await getDailyErrorCount();
  await monitor.logError(errorCount);
}, 3600000); // Her saat
```

### Java/Spring Boot Projesi

```java
// AnomalyMonitor.java
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.*;

@Service
public class AnomalyMonitor {
    private static final String API_URL = "http://localhost:8000";
    private RestTemplate restTemplate = new RestTemplate();

    public AnomalyResult logError(int errorCount) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        
        Map<String, Integer> request = new HashMap<>();
        request.put("error_count", errorCount);
        
        HttpEntity<Map<String, Integer>> entity = 
            new HttpEntity<>(request, headers);
        
        ResponseEntity<AnomalyResult> response = 
            restTemplate.exchange(
                API_URL + "/api/v1/log",
                HttpMethod.POST,
                entity,
                AnomalyResult.class
            );
        
        AnomalyResult result = response.getBody();
        
        if (result.isAnomaly()) {
            sendAlert(result);
        }
        
        return result;
    }
    
    private void sendAlert(AnomalyResult result) {
        // Email, Slack vb.
        logger.warn("🚨 ALARM: {}", result.getMessage());
    }
}
```

---

## 🎮 Kullanım Senaryoları

### 1. Web Uygulaması Error Monitoring

```python
# app.py (Flask örneği)
from flask import Flask
from monitoring import AnomalyMonitor

app = Flask(__name__)
monitor = AnomalyMonitor()

@app.errorhandler(Exception)
def handle_error(e):
    # Hata sayısını artır ve anomali kontrol et
    daily_errors = increment_error_count()
    result = monitor.log_error(daily_errors)
    
    if result['is_anomaly']:
        notify_devops_team(result)
    
    return str(e), 500
```

### 2. Scheduled Job ile Periyodik Kontrol

```python
# cron_job.py
import schedule
import time
from monitoring import AnomalyMonitor

monitor = AnomalyMonitor()

def check_daily_errors():
    error_count = get_error_count_last_24h()
    result = monitor.log_error(error_count)
    
    if result['is_anomaly']:
        send_email_alert(result)

# Her gün saat 00:00'da çalış
schedule.every().day.at("00:00").do(check_daily_errors)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 3. Real-time Stream Processing

```python
# kafka_consumer.py
from kafka import KafkaConsumer
from monitoring import AnomalyMonitor
from collections import Counter
from datetime import datetime, timedelta

monitor = AnomalyMonitor()
error_counter = Counter()

consumer = KafkaConsumer('error-logs')

for message in consumer:
    error = message.value
    
    # Son 1 saatteki hataları say
    error_counter[datetime.now().hour] += 1
    
    # Saatlik kontrol
    if datetime.now().minute == 0:
        hourly_errors = error_counter[datetime.now().hour]
        result = monitor.log_error(hourly_errors)
        
        if result['is_anomaly']:
            trigger_alert(result)
```

---

## ⚙️ Konfigürasyon

### Environment Variables

```bash
# .env dosyanızda
ANOMALY_API_URL=http://localhost:8000
ANOMALY_Z_THRESHOLD=2.0
ANOMALY_WINDOW_SIZE=30
```

### Runtime Konfigürasyon Değiştirme

```python
import requests

# Eşik değerini güncelle
requests.put(
    "http://localhost:8000/api/v1/config",
    json={"z_score_threshold": 2.5}
)
```

---

## 🐳 Docker ile Production Deployment

### docker-compose.yml (Kendi Projenizle Birlikte)

```yaml
version: '3.8'

services:
  # Kendi uygulamanız
  your-app:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - anomaly-detector
    environment:
      - ANOMALY_API_URL=http://anomaly-detector:8000

  # Anomali mikroservisi
  anomaly-detector:
    image: anomaly-detector:latest
    ports:
      - "8000:8000"
    environment:
      - ANOMALY_Z_THRESHOLD=2.0
      - ANOMALY_WINDOW_SIZE=30
    restart: unless-stopped
```

---

## 📊 Monitoring Dashboard Entegrasyonu

### Grafana ile Görselleştirme

```python
# metrics_exporter.py
import requests
from prometheus_client import Gauge

anomaly_score = Gauge('anomaly_z_score', 'Current Z-Score')
is_anomaly = Gauge('is_anomaly', 'Anomaly detected')

def export_metrics():
    response = requests.get("http://localhost:8000/api/v1/stats")
    stats = response.json()
    
    # Prometheus'a export et
    anomaly_score.set(stats.get('latest_z_score', 0))
    is_anomaly.set(1 if stats.get('has_recent_anomaly') else 0)
```

---

## 🔒 Güvenlik (Production)

### API Key ile Koruma

```python
# your_project/config.py
ANOMALY_API_KEY = "your-secret-api-key"

# İstek gönderirken
import requests

response = requests.post(
    "http://localhost:8000/api/v1/log",
    headers={"X-API-Key": ANOMALY_API_KEY},
    json={"error_count": 25}
)
```

---

## 🧪 Test Etme

### Unit Test

```python
import unittest
from monitoring import AnomalyMonitor

class TestAnomalyMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = AnomalyMonitor()
    
    def test_log_error(self):
        result = self.monitor.log_error(20)
        self.assertIsNotNone(result)
        self.assertIn('is_anomaly', result)
```

---

## 📞 Troubleshooting

### Servis Çalışmıyor

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Docker logs
docker-compose logs anomaly-detector

# Manuel başlatma
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Port Çakışması

```bash
# Farklı port kullanın
PORT=8001 uvicorn app:app --host 0.0.0.0 --port 8001
```

---

## 📚 Ek Kaynaklar

- **API Dokümantasyonu:** http://localhost:8000/api/docs
- **Interactive API Test:** http://localhost:8000/api/docs
- **Health Check:** http://localhost:8000/api/v1/health
- **Deployment Kılavuzu:** DEPLOYMENT.md

---

**🎉 Mikroservis kendi projenize entegre edilmeye hazır!**

Sadece:
1. Servisi başlatın (Docker veya manuel)
2. API'yi çağırın
3. Anomali sonuçlarını alın ve işleyin
