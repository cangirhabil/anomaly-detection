# 🔍 Anomali Tespit Sistemi

**Z-Score Tabanlı İstatistiksel Anomali Tespit Modülü**

Günlük hata sayılarını izleyen ve istatistiksel olarak anormal sapmaları tespit eden profesyonel, genişletilebilir backend modülü.

---

## 📋 Özellikler

- ✅ **Z-Score Yöntemi**: İstatistiksel olarak kanıtlanmış anomali tespiti
- ✅ **Dinamik Öğrenme**: Son 30 günün verisine göre otomatik güncellenen eşikler
- ✅ **Modüler Yapı**: Kolayca backend sistemlere entegre edilebilir
- ✅ **Esnek Konfigürasyon**: Hassasiyet seviyesi ayarlanabilir (Hassas/Dengeli/Konservatif)
- ✅ **Kapsamlı Demo**: 5 farklı kullanım senaryosu ile örnek kod
- ✅ **Profesyonel Kod**: Tip ipuçları, docstring'ler ve kapsamlı yorumlar

---

## 🚀 Hızlı Başlangıç

### Kurulum

```bash
# Gereksinimleri yükle
pip install -r requirements.txt
```

### Temel Kullanım

```python
from anomaly_detector import AnomalyDetector

# Dedektör oluştur
detector = AnomalyDetector()

# Geçmiş veri yükle (örnek: son 20 gün)
for i in range(20):
    detector.add_error_log(error_count=17)  # Normal: 15-20 arası

# Yeni gün - anomali kontrolü
result = detector.add_error_log(error_count=35)

if result.is_anomaly:
    print(f"⚠️ {result.message}")
    # Alarm gönder, log kaydet, vb.
```

---

## 📊 Çalışma Prensibi

### Z-Score Yöntemi

Z-Score, bir değerin ortalamadan kaç standart sapma uzakta olduğunu ölçer:

```
Z = (X - μ) / σ

X  = Mevcut hata sayısı
μ  = Ortalama hata sayısı (son 30 gün)
σ  = Standart sapma
```

**Eşik Değerleri:**
- `Z = 1.645` → %90 güven aralığı (Hassas)
- `Z = 2.0` → %95 güven aralığı (Dengeli) ✅ **Önerilen**
- `Z = 3.0` → %99.7 güven aralığı (Konservatif)

---

## 🎯 Kullanım Senaryoları

### 1️⃣ Basit Kullanım

```python
from anomaly_detector import AnomalyDetector

detector = AnomalyDetector()

# Her gün hata sayısı ekle
result = detector.add_error_log(error_count=18)

print(result.message)
# ✓ Normal davranış. Hata sayısı: 18, Z-Score: 0.32
```

### 2️⃣ Hassasiyet Ayarı

```python
from anomaly_detector import AnomalyDetector, AnomalyConfig

# Hassas mod: Küçük sapmalarda bile alarm
config = AnomalyConfig.sensitive()  # Z = 1.645
detector = AnomalyDetector(config)

# Konservatif mod: Sadece çok büyük sapmalarda alarm
config = AnomalyConfig.conservative()  # Z = 3.0
detector = AnomalyDetector(config)

# Özel ayar
config = AnomalyConfig(
    window_size=30,        # Son 30 gün
    z_score_threshold=2.5,  # Özel eşik
    min_data_points=7       # Minimum 7 gün veri
)
detector = AnomalyDetector(config)
```

### 3️⃣ Geçmiş Veri Yükleme

```python
from datetime import datetime, timedelta
from anomaly_detector import AnomalyDetector

detector = AnomalyDetector()

# Toplu veri yükleme
historical_data = [
    (datetime(2024, 1, 1), 15),
    (datetime(2024, 1, 2), 17),
    (datetime(2024, 1, 3), 19),
    # ...
]

detector.load_historical_data(historical_data)

# Şimdi yeni veri ekle ve kontrol et
result = detector.add_error_log(error_count=30)
```

### 4️⃣ İstatistik Analizi

```python
# Mevcut durumu görüntüle
stats = detector.get_statistics_summary()

print(f"Veri Sayısı: {stats['data_points']}")
print(f"Ortalama: {stats['mean']:.2f}")
print(f"Standart Sapma: {stats['std_dev']:.2f}")
print(f"Min-Max: {stats['min']}-{stats['max']}")

# Pandas DataFrame olarak al
df = detector.get_history_dataframe()
print(df.describe())
```

### 5️⃣ Backend Entegrasyonu

```python
# Flask/FastAPI örneği
from anomaly_detector import AnomalyDetector

# Global dedektör (singleton pattern önerilir)
detector = AnomalyDetector()

# API endpoint
@app.post("/log-error")
def log_error(error_count: int):
    result = detector.add_error_log(error_count)
    
    if result.is_anomaly:
        # Alarm sistemi tetikle
        send_alert(result.message)
        log_to_database(result.to_dict())
    
    return {
        "is_anomaly": result.is_anomaly,
        "z_score": result.z_score,
        "message": result.message
    }
```

---

## 🎬 Demo Çalıştırma

5 farklı senaryo ile kapsamlı demo:

```bash
python demo.py
```

**Demo İçeriği:**
1. **Temel Kullanım** - Basit anomali tespiti
2. **Farklı Konfigürasyonlar** - Hassas/Dengeli/Konservatif karşılaştırma
3. **Gerçek Zamanlı İzleme** - Gün gün anomali simülasyonu
4. **Toplu Veri Analizi** - 30 günlük veri üzerinde anomali arama
5. **Dinamik Öğrenme** - Sistemin kendini nasıl güncellediği

---

## 📁 Proje Yapısı

```
anomali-tespiti/
│
├── anomaly_detector/          # Ana paket
│   ├── __init__.py           # Paket başlatıcı
│   ├── detector.py           # Ana anomali tespit motoru
│   ├── config.py             # Konfigürasyon yönetimi
│   └── models.py             # Veri modelleri (ErrorLog, AnomalyResult)
│
├── demo.py                   # Kapsamlı demo ve örnekler
├── requirements.txt          # Python bağımlılıkları
└── README.md                # Bu dosya
```

---

## 🔧 API Referansı

### AnomalyDetector

**Ana Metodlar:**

- `add_error_log(error_count, date=None)` → Yeni hata ekle ve kontrol et
- `detect_anomaly(current_value, date=None)` → Sadece kontrol et (geçmişe ekleme)
- `get_statistics_summary()` → İstatistik özetini al
- `get_history_dataframe()` → Geçmişi pandas DataFrame olarak al
- `load_historical_data(data)` → Toplu veri yükle
- `clear_history()` → Geçmişi temizle

### AnomalyConfig

**Hazır Konfigürasyonlar:**

- `AnomalyConfig.sensitive()` → Hassas (Z=1.645)
- `AnomalyConfig.balanced()` → Dengeli (Z=2.0) ✅
- `AnomalyConfig.conservative()` → Konservatif (Z=3.0)

**Parametreler:**

- `window_size`: Veri pencere boyutu (varsayılan: 30 gün)
- `z_score_threshold`: Anomali eşiği (varsayılan: 2.0)
- `min_data_points`: Minimum veri sayısı (varsayılan: 7)

### AnomalyResult

**Özellikler:**

- `is_anomaly`: bool - Anomali tespit edildi mi?
- `current_value`: int - Mevcut hata sayısı
- `mean`: float - Ortalama
- `std_dev`: float - Standart sapma
- `z_score`: float - Hesaplanan Z-Score
- `threshold`: float - Kullanılan eşik
- `message`: str - Açıklayıcı mesaj

---

## 💡 Best Practices

### 1. Yeterli Veri Toplayın
```python
# En az 7 günlük veri ile başlayın
# İlk günlerde anomali tespiti güvenilir olmayabilir
if len(detector.error_history) < 7:
    print("Yetersiz veri - daha fazla gün bekleyin")
```

### 2. Doğru Eşik Seçin
```python
# Genel sistemler için Z=2.0
detector = AnomalyDetector(AnomalyConfig.balanced())

# Kritik sistemler için Z=3.0 (daha az false positive)
detector = AnomalyDetector(AnomalyConfig.conservative())
```

### 3. Periyodik Kontrol
```python
# Her gün sonunda toplu kontrol
daily_errors = get_daily_error_count()
result = detector.add_error_log(daily_errors)

if result.is_anomaly:
    notify_team(result)
```

### 4. Veri Saklama
```python
# Uzun vadeli analiz için veriyi kaydedin
import json

with open('history.json', 'w') as f:
    json.dump(detector.export_history(), f)
```

---

## 🧪 Test Senaryosu

Normal koşullarda günde 15-20 hata bekleniyorsa:

```python
detector = AnomalyDetector()

# Normal dönem
for _ in range(20):
    detector.add_error_log(random.randint(15, 20))

# Anormal artış
result = detector.add_error_log(35)
# ⚠️ ANOMALİ TESPİT EDİLDİ! Hata sayısı: 35, Z-Score: 5.2
```

---

## 📈 Genişletme Önerileri

### Dakikalık/Saatlik Frekans
```python
# window_size'ı saat cinsine çevirin
config = AnomalyConfig(window_size=24*30)  # Son 30 gün (saatlik)
```

### Çoklu Metrik
```python
# Her metrik için ayrı dedektör
error_detector = AnomalyDetector()
latency_detector = AnomalyDetector()
memory_detector = AnomalyDetector()
```

### Veritabanı Entegrasyonu
```python
# PostgreSQL, MongoDB vb. ile geçmiş saklama
result = detector.add_error_log(error_count)
if result.is_anomaly:
    db.save_anomaly(result.to_dict())
```

---

## 📞 Destek

- **Dokümantasyon**: Bu README
- **Örnekler**: `demo.py` dosyasında 5 detaylı senaryo
- **Kod İncelemeleri**: Tüm kodlar yorumlanmış ve tip ipuçları eklenmiş

---

## 📄 Lisans

Bu proje açık kaynak kodludur ve eğitim/ticari amaçlarla kullanılabilir.

---

## 🎓 Teknik Detaylar

**Gereksinimler:**
- Python 3.8+
- NumPy >= 1.21.0
- Pandas >= 1.3.0

**Performans:**
- O(1) anomali kontrolü
- O(n) istatistik hesaplama (n = window_size)
- Hafıza kullanımı: O(window_size)

**Güvenilirlik:**
- Standart sapma 0 durumları ele alınmış
- Yetersiz veri kontrolü
- Tip güvenliği (dataclass)
- Validasyon kontrolleri

---

**Geliştirici:** Profesyonel Anomali Tespit Sistemi v1.0.0  
**Tarih:** Kasım 2025
