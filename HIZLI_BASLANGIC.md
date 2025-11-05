# ⚡ HIZLI BAŞLANGIÇ

## 🎯 3 Dakikada Kullanıma Başla

### 1️⃣ Docker ile Başlat (En Kolay)

```powershell
# Mikroservisi başlat
docker-compose up -d

# Health check
curl http://localhost:8000/api/v1/health
```

✅ **Hazır!** API şu adreste çalışıyor: http://localhost:8000

---

### 2️⃣ Python ile Kullan

```python
from anomaly_client import AnomalyClient

# Client oluştur
client = AnomalyClient("http://localhost:8000")

# Hata kaydı ekle
client.log_error(error_count=25, timestamp="2024-01-15")

# Anomali tespit et
result = client.detect_anomaly(current_value=150)

if result.is_anomaly:
    print(f"⚠️ ANOMALİ! Z-Score: {result.z_score}")
    print(f"Mesaj: {result.message}")
```

---

### 3️⃣ REST API ile Kullan

```bash
# Hata kaydı ekle
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 25}'

# Anomali tespit et
curl -X POST http://localhost:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{"current_value": 150}'
```

---

## 📚 Daha Fazla Bilgi

| Dosya | İçerik |
|-------|--------|
| **README_TR.md** | Türkçe kapsamlı kullanım kılavuzu |
| **README_MICROSERVICE.md** | Mikroservis detayları (İngilizce) |
| **DEPLOYMENT.md** | Production deployment rehberi |
| **INTEGRATION_GUIDE.md** | Çoklu dil entegrasyon örnekleri |
| **MICROSERVICE_OZET.txt** | Türkçe özellik özeti |

---

## 🧪 Test Et

```powershell
# Sistem testleri
python test_system.py

# Demo senaryoları
python demo.py
```

---

## 🎯 API Dokümantasyonu

Mikroservis çalışırken: **http://localhost:8000/api/docs**

---

## 🛠️ Konfigürasyon

### .env Dosyası Oluştur:

```bash
# .env.example dosyasını kopyala
cp .env.example .env

# Ayarları düzenle
ANOMALY_Z_THRESHOLD=2.0
ANOMALY_WINDOW_SIZE=30
```

### Konfigürasyon Seçenekleri:

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `ANOMALY_Z_THRESHOLD` | 2.0 | Z-Score eşiği (1.645, 2.0, 3.0) |
| `ANOMALY_WINDOW_SIZE` | 30 | Sliding window boyutu (gün) |
| `ANOMALY_MIN_DATA_POINTS` | 7 | Minimum veri sayısı |

---

## 🚀 Production'a Al

### Kubernetes:

```powershell
kubectl apply -f deployment.yaml
```

### Docker Swarm:

```powershell
docker stack deploy -c docker-compose.yml anomaly-detector
```

**Detaylar için:** `DEPLOYMENT.md`

---

## 💡 Örnekler

### Senaryo 1: Backend Error Monitoring

```python
# Her gün hata sayısını kaydet
client.log_error(error_count=daily_errors)

# Anomali kontrolü
if client.detect_anomaly(today_errors).is_anomaly:
    send_alert_to_team()
```

### Senaryo 2: API Rate Monitoring

```python
# API isteklerini izle
client.log_error(error_count=api_requests_count)

# Anormal trafik tespiti
result = client.detect_anomaly(current_requests)
if result.severity == "HIGH":
    enable_rate_limiting()
```

### Senaryo 3: Toplu Analiz

```python
# Geçmiş verileri ekle
historical_data = [
    {"error_count": 15, "timestamp": "2024-01-01"},
    {"error_count": 17, "timestamp": "2024-01-02"},
    # ... daha fazla veri
]
client.bulk_log(historical_data)

# Geçmişi analiz et
history = client.get_history(days=30)
anomalies = [h for h in history if h.is_anomaly]
```

---

## 🔍 Sorun Giderme

### Docker çalışmıyor:

```powershell
# Container loglarını kontrol et
docker-compose logs -f

# Yeniden başlat
docker-compose restart
```

### Port 8000 kullanımda:

```powershell
# .env dosyasında portu değiştir
ANOMALY_API_PORT=8001

# Yeniden başlat
docker-compose up -d
```

### Python hatası:

```powershell
# Bağımlılıkları yeniden yükle
pip install -r requirements.txt --force-reinstall
```

---

## ✅ Hazır!

Artık projenizde kullanabilirsiniz! 🎉

**Sorular için dokümantasyon dosyalarını inceleyin.**
