#!/usr/bin/env python3
"""
Otomatik Test - Tüm senaryoları sırayla çalıştırır
"""

import requests
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 70)
print("  ANOMALİ TESPİT SİSTEMİ - OTOMATİK TEST")
print("=" * 70)
print("\nFrontend: http://localhost:3000")
print("Backend: http://localhost:8000\n")

def send_reading(sensor_type, value):
    """Sensör verisi gönder"""
    data = {
        "sensor_id": "auto_test",
        "sensor_type": sensor_type,
        "value": value,
        "unit": "unit",
        "timestamp": datetime.now().isoformat()
    }
    
    response = requests.post(f"{BASE_URL}/analyze", json=data)
    result = response.json()
    
    status = "🚨" if result.get('is_anomaly') else "✅"
    print(f"{status} {sensor_type}={value:.2f} | Z-Score={result.get('z_score', 0):.2f}")
    return result

# SENARYO 1: Normal Baseline (Motor Akımı)
print("\n[1/6] Normal baseline oluşturuluyor (motor_current)...")
for i in range(30):
    value = 5.0 + random.uniform(-0.3, 0.3)
    send_reading("motor_current", value)
    time.sleep(0.05)

time.sleep(1)

# SENARYO 2: Şişe Sıkışması (Motor akımı yükselir)
print("\n[2/6] ⚠️  ŞİŞE SIKIŞMASI simülasyonu...")
for i in range(3):
    send_reading("motor_current", 8.5 + random.uniform(-0.2, 0.2))
    time.sleep(0.2)

# Normal'e dönüş
for i in range(5):
    value = 5.0 + random.uniform(-0.2, 0.2)
    send_reading("motor_current", value)
    time.sleep(0.1)

time.sleep(1)

# SENARYO 3: Sistem Voltajı (Normal baseline)
print("\n[3/6] Normal baseline oluşturuluyor (system_voltage)...")
for i in range(20):
    value = 24.0 + random.uniform(-0.3, 0.3)
    send_reading("system_voltage", value)
    time.sleep(0.05)

time.sleep(1)

# SENARYO 4: Güç Dalgalanması
print("\n[4/6] ⚡ GÜÇ DALGALANMASI simülasyonu...")
for i in range(3):
    send_reading("system_voltage", 20.5 + random.uniform(-0.3, 0.3))
    time.sleep(0.2)

# Normal'e dönüş
for i in range(5):
    value = 24.0 + random.uniform(-0.2, 0.2)
    send_reading("system_voltage", value)
    time.sleep(0.1)

time.sleep(1)

# SENARYO 5: Acoustic Noise (Normal baseline)
print("\n[5/6] Normal baseline oluşturuluyor (acoustic_noise)...")
for i in range(20):
    value = 60.0 + random.uniform(-3, 3)
    send_reading("acoustic_noise", value)
    time.sleep(0.05)

time.sleep(1)

# SENARYO 6: Kırık Şişe (Ani gürültü artışı)
print("\n[6/6] 💥 KIRIK ŞİŞE simülasyonu...")
for i in range(3):
    send_reading("acoustic_noise", 95.0 + random.uniform(-2, 2))
    time.sleep(0.2)

# Normal'e dönüş
for i in range(5):
    value = 60.0 + random.uniform(-2, 2)
    send_reading("acoustic_noise", value)
    time.sleep(0.1)

time.sleep(1)

# Final istatistikler
print("\n" + "=" * 70)
print("  FINAL İSTATİSTİKLER")
print("=" * 70)

response = requests.get(f"{BASE_URL}/stats")
stats = response.json()

print(f"\nToplam Sensör: {stats.get('total_sensors', 0)}")
print("\nDetaylı İstatistikler:")
print("-" * 70)

for sensor, data in stats.get('sensors', {}).items():
    print(f"\n📊 {sensor.upper()}")
    print(f"   Toplam Okuma  : {data.get('count', 0)}")
    print(f"   Ortalama      : {data.get('mean', 0):.2f}")
    print(f"   Std Sapma     : {data.get('std_dev', 0):.2f}")
    print(f"   Min - Max     : {data.get('min', 0):.2f} - {data.get('max', 0):.2f}")
    print(f"   Anomali Sayısı: {data.get('anomaly_count', 0)}")

print("\n" + "=" * 70)
print("  ✅ TEST TAMAMLANDI!")
print("=" * 70)
print("\n📊 Frontend: http://localhost:3000")
print("📚 API Docs: http://localhost:8000/api/docs\n")
