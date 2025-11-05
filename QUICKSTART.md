# 🚀 Başlangıç Kılavuzu

## Hızlı Kurulum (3 Adım)

### 1️⃣ Gereksinimleri Yükle
```bash
pip install -r requirements.txt
```

### 2️⃣ Hızlı Test Çalıştır
```bash
python quick_test.py
```

### 3️⃣ Detaylı Demo İncele
```bash
python demo.py
```

---

## 📋 Dosya Yapısı

```
anomali-tespiti/
│
├── 📁 anomaly_detector/          # Ana paket
│   ├── __init__.py              # Paket başlatıcı
│   ├── detector.py              # ⭐ Ana anomali tespit motoru
│   ├── config.py                # Konfigürasyon yönetimi
│   └── models.py                # Veri modelleri
│
├── 📄 quick_test.py             # ⚡ Hızlı test (başlamak için)
├── 📄 demo.py                   # 📊 5 detaylı demo senaryosu
├── 📄 backend_integration.py    # 🔌 Backend entegrasyon örnekleri
│
├── 📄 requirements.txt          # Python bağımlılıkları
├── 📄 README.md                 # Kapsamlı dokümantasyon
└── 📄 QUICKSTART.md            # Bu dosya
```

---

## 💻 Kod Örnekleri

### Minimal Kullanım (5 Satır)

```python
from anomaly_detector import AnomalyDetector

detector = AnomalyDetector()

# 20 gün normal veri
for _ in range(20):
    detector.add_error_log(17)

# Anormal gün
result = detector.add_error_log(35)
print(result.message)  # ⚠️ ANOMALİ TESPİT EDİLDİ!
```

### Özelleştirme

```python
from anomaly_detector import AnomalyDetector, AnomalyConfig

# Hassas mod (daha fazla alarm)
config = AnomalyConfig.sensitive()
detector = AnomalyDetector(config)

# Konservatif mod (daha az alarm)
config = AnomalyConfig.conservative()
detector = AnomalyDetector(config)

# Özel ayarlar
config = AnomalyConfig(
    window_size=30,         # Son 30 gün
    z_score_threshold=2.5,  # Z-Score eşiği
    min_data_points=7       # Minimum veri
)
detector = AnomalyDetector(config)
```

### Backend Entegrasyonu

```python
from backend_integration import ErrorMonitoringService

# Singleton servis
service = ErrorMonitoringService()

# API'den gelen veri
result = service.log_error(error_count=25)

if result['is_anomaly']:
    # Alarm gönder
    send_alert(result['message'])
```

---

## 🎯 Hangi Dosyayı Ne Zaman Kullanmalı?

| Amaç | Dosya | Açıklama |
|------|-------|----------|
| 🚀 Hızlı başlangıç | `quick_test.py` | 30 saniyede sistem testini görün |
| 📚 Detaylı örnekler | `demo.py` | 5 farklı kullanım senaryosu |
| 🔌 Backend entegrasyonu | `backend_integration.py` | Flask/FastAPI örnekleri |
| 📖 Dokümantasyon | `README.md` | Tüm API ve kullanım detayları |
| 💻 Kod yazma | `anomaly_detector/` | Asıl modül dosyaları |

---

## ⚙️ Temel Parametreler

### window_size (Pencere Boyutu)
- **Varsayılan:** 30 gün
- **Ne yapar:** Son N günün verisini tutar
- **Öneri:** En az 7 gün, ideal 30 gün

### z_score_threshold (Eşik)
- **1.645:** Hassas (90% güven) - Daha fazla alarm
- **2.0:** Dengeli (95% güven) - ✅ **Önerilen**
- **3.0:** Konservatif (99.7% güven) - Daha az alarm

### min_data_points (Minimum Veri)
- **Varsayılan:** 7 gün
- **Ne yapar:** Bu kadar veri olana kadar anomali kontrol yapmaz
- **Öneri:** En az 7 gün bekleyin

---

## 📊 Beklenen Çıktı Örnekleri

### Normal Durum
```
✓ Normal davranış. Hata sayısı: 18, Z-Score: 0.32
```

### Anomali Tespit
```
⚠️ ANOMALİ TESPİT EDİLDİ! 
Hata sayısı: 35, 
Beklenen: 17.5 ± 2.1, 
Z-Score: 8.33
```

### Yetersiz Veri
```
⚡ Yetersiz veri: 3/7 - Normal kabul edildi
```

---

## 🔧 Sorun Giderme

### "Import Error: numpy"
```bash
pip install -r requirements.txt
```

### "Anomali tespit edilmiyor"
- En az 7 gün veri ekleyin
- Z-Score eşiğini düşürün (örn: 1.645)
- Veriyi kontrol edin (yeterince varyans var mı?)

### "Çok fazla false positive"
- Z-Score eşiğini yükseltin (örn: 3.0)
- Daha fazla geçmiş veri ekleyin
- window_size'ı artırın

---

## 🎓 Sonraki Adımlar

1. ✅ `quick_test.py` ile sistemi test edin
2. ✅ `demo.py` ile tüm özellikleri inceleyin
3. ✅ `README.md` ile API'yi öğrenin
4. ✅ `backend_integration.py` ile entegrasyon örneklerini görün
5. ✅ Kendi projenize entegre edin

---

## 📞 Yardım

- **Kod yorumları:** Her fonksiyon detaylı yorumlanmış
- **Docstring'ler:** Python help() ile erişilebilir
- **Demo'lar:** 5 farklı senaryo ile öğrenin

```python
# Yardım almak için
from anomaly_detector import AnomalyDetector
help(AnomalyDetector)
```

---

**Kolay gelsin! 🚀**
