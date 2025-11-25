# 🏭 Endüstriyel IoT Anomali Tespit Mikroservisi

**Endüstriyel sensör verileri için istatistiksel anomali tespiti + AI Raporlama**

Z-Score metodolojisi kullanarak titreşim, sıcaklık, ses, motor akımı ve üretim hızı gibi sensör verilerindeki anormallikleri otomatik tespit eden, **Gemini AI ile profesyonel raporlar oluşturan** ve **e-posta bildirimleri gönderen** FastAPI mikroservisi.

---

## ✨ Özellikler

- ✅ **Çoklu Sensör Desteği:** Titreşim (X,Y,Z), Sıcaklık, Ses, Motor Akımı, Üretim Hızı
- ✅ **İstatistiksel Tespit:** Z-Score algoritması ile bilimsel anomali tespiti
- ✅ **🤖 AI Raporlama:** Gemini 2.5 Flash ile profesyonel anomali analizi
- ✅ **📧 E-posta Bildirimleri:** Otomatik rapor gönderimi (SMTP)
- ✅ **REST API:** Tam özellikli sensör veri analizi API'si
- ✅ **Plug-and-Play:** Docker ile tek komutla çalışır
- ✅ **Dil Bağımsız:** Python, JavaScript, Java, C# vb. her dilden kullanılabilir
- ✅ **Production-Ready:** Kubernetes, AWS, GCP, Azure desteği
- ✅ **Interactive Docs:** Swagger UI ile API dokümantasyonu
- ✅ **Python Client:** Hazır client kütüphanesi

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

# Sensör verisi gönder ve analiz et
result = client.send_reading(
    sensor_type="vibration_z",
    value=2.45,
    unit="G",
    timestamp="2024-01-16T10:00:00"
)

if result.is_anomaly:
    print(f"⚠️ ANOMALİ TESPİT EDİLDİ! ({result.sensor_type})")
    print(f"Değer: {result.value} {result.unit}")
    print(f"Z-Score: {result.z_score:.2f}")
    print(f"Beklenen: {result.expected_range['mean']:.2f} ± {result.expected_range['std_dev']:.2f}")
else:
    print(f"✅ Normal değer (Z-Score: {result.z_score:.2f})")

# İstatistikleri getir
stats = client.get_stats()
print(stats)
```

### REST API ile (JavaScript):

```javascript
// Sensör verisi analizi
const response = await fetch('http://localhost:8000/api/v1/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sensor_type: "motor_current",
    value: 25.5,
    unit: "Amps",
    timestamp: new Date().toISOString()
  })
});

const result = await response.json();
if (result.is_anomaly) {
  console.log(`⚠️ Motor Akımı Anormalliği! Z-Score: ${result.z_score}`);
}
```

### cURL ile:

```bash
# Sensör verisi analizi
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"sensor_type": "temperature", "value": 85.5, "unit": "C"}'

# İstatistikleri getir
curl http://localhost:8000/api/v1/stats
```

---

## 📡 API Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `POST` | `/api/v1/analyze` | Sensör verisi gönder ve anomali kontrolü yap |
| `GET` | `/api/v1/stats` | Tüm sensörlerin istatistiklerini getir |
| `GET` | `/api/v1/health` | Servis sağlık kontrolü |
| `DELETE` | `/api/v1/clear` | Tüm verileri temizle |

**Interactive API Dokümantasyonu:** http://localhost:8000/api/docs

---

## ⚙️ Konfigürasyon

### Environment Variables (.env):

```bash
# API Ayarları
ANOMALY_API_HOST=0.0.0.0
ANOMALY_API_PORT=8000

# Anomali Tespit Parametreleri
ANOMALY_WINDOW_SIZE=50           # Sliding window boyutu (veri noktası)
ANOMALY_Z_THRESHOLD=2.0          # Z-Score eşik değeri
ANOMALY_MIN_DATA_POINTS=10       # Minimum veri sayısı
```

### config.yaml:

```yaml
detector:
  window_size: 50              # Sliding window (veri noktası)
  z_score_threshold: 2.0       # Z-Score eşiği (1.645, 2.0, 3.0)
  min_data_points: 10          # Minimum veri sayısı

api:
  host: "0.0.0.0"
  port: 8000
```

---

## 📊 Z-Score Metodolojisi

```
Z-Score = (X - μ) / σ
```

- **X:** Güncel sensör değeri
- **μ:** Ortalama (son N veri)
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

---

## 🎯 Kullanım Senaryoları

### 1. Kestirimci Bakım (Predictive Maintenance)
```python
# Titreşim verilerini izle
client.send_reading(sensor_type="vibration_z", value=current_vibration)
# Anomali durumunda bakım ekibine haber ver
```

### 2. Kalite Kontrol
```python
# Üretim hattı hızını ve sıcaklığını izle
client.send_reading(sensor_type="throughput", value=bottles_per_minute)
# Hız düşerse veya sıcaklık artarsa operatörü uyar
```

### 3. Enerji Verimliliği
```python
# Motor akımını izle
client.send_reading(sensor_type="motor_current", value=amps)
# Beklenmedik akım artışlarında (sıkışma vb.) sistemi durdur
```

---

## 🤖 AI Raporlama (Gemini)

Tespit edilen anomalileri Gemini 2.5 Flash ile analiz ederek profesyonel raporlar oluşturabilirsiniz.

### Kurulum

1. **Google AI Studio'dan API key alın:** https://aistudio.google.com/apikey

2. **Backend `.env` dosyasına ekleyin:**
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

3. **Backend'i yeniden başlatın**

### API Kullanımı

```python
import requests

# Rapor oluştur
response = requests.post(
    "http://localhost:8000/api/v1/report/generate",
    json={"limit": 50, "include_llm_analysis": True}
)
report = response.json()

print(f"Risk Seviyesi: {report['report']['risk_level']}")
print(f"Özet: {report['report']['summary']}")
print(f"AI Analizi: {report['report']['llm_analysis']}")
```

### Rapor İçeriği

- **Yönetici Özeti:** Kısa ve öz anomali özeti
- **Risk Seviyesi:** LOW, MEDIUM, HIGH, CRITICAL
- **Detaylı Analiz:** Her sensör için ne oldu, neden önemli
- **Kök Neden Analizi:** Anomalilerin muhtemel sebepleri
- **Önerilen Aksiyonlar:** Acil ve uzun vadeli aksiyonlar

---

## 📧 E-posta Bildirimleri

Anomali raporlarını otomatik olarak e-posta ile gönderebilirsiniz.

### SMTP Kurulumu (Gmail)

1. **Google Hesabında 2FA aktif edin**

2. **Uygulama Şifresi oluşturun:** https://myaccount.google.com/apppasswords

3. **Backend `.env` dosyasına ekleyin:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
SMTP_SENDER_EMAIL=your_email@gmail.com
SMTP_USE_TLS=true
```

4. **Varsayılan alıcıları ekleyin (opsiyonel):**
```bash
EMAIL_RECIPIENTS=admin@example.com,operator@example.com
```

### API Kullanımı

```python
import requests

# Alıcı ekle
requests.post(
    "http://localhost:8000/api/v1/email/recipients",
    json={
        "email": "muhendis@example.com",
        "name": "Bakım Mühendisi",
        "notify_on_critical": True,
        "notify_on_high": True,
        "notify_on_medium": False,
        "notify_on_low": False
    }
)

# Rapor oluştur ve gönder
response = requests.post(
    "http://localhost:8000/api/v1/report/send",
    json={"limit": 50}
)

print(f"Gönderildi: {response.json()['recipients']}")
```

### Test E-postası

```python
# E-posta yapılandırmasını test et
requests.post(
    "http://localhost:8000/api/v1/email/test?recipient=test@example.com"
)
```
