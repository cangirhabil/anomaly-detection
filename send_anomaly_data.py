"""
Anomali Simülatörü - Hata Enjeksiyonu
Sisteme kasıtlı olarak hatalı veriler göndererek anomali tespitini test eder.
"""

import requests
import random
import time
from datetime import datetime
import sys

API_URL = "http://localhost:8000/api/v1/analyze"

# CountSort Cihazına Özel Sensörler ve Anomali Değerleri
SENSORS = {
    "ejector_pressure": {
        "unit": "bar",
        "normal_range": (6.8, 7.2),
        "anomaly_values": [4.5, 8.5, 2.0, 0], # Düşük basınç, aşırı basınç, kaçak
        "description": "Ejektör Hava Basıncı"
    },
    "conveyor_speed": {
        "unit": "m/s",
        "normal_range": (2.4, 2.6),
        "anomaly_values": [1.5, 3.5, 0, 0.5], # Bant sıkışması, aşırı hız
        "description": "Konveyör Hızı"
    },
    "main_motor_load": {
        "unit": "%",
        "normal_range": (65, 75),
        "anomaly_values": [90, 95, 10, 100], # Aşırı yük, boşta çalışma
        "description": "Ana Motor Yükü"
    },
    "separation_rate": {
        "unit": "obj/s",
        "normal_range": (140, 160),
        "anomaly_values": [80, 50, 10, 0], # Tıkanıklık, besleme sorunu
        "description": "Ayrıştırma Hızı"
    },
    "optical_sensor_temp": {
        "unit": "°C",
        "normal_range": (35, 42),
        "anomaly_values": [55, 60, 65], # Aşırı ısınma
        "description": "Optik Sensör Isısı"
    },
    "vibration_bearing_x": {
        "unit": "mm/s",
        "normal_range": (0.8, 1.5),
        "anomaly_values": [3.5, 5.0, 8.0], # Rulman arızası
        "description": "Rulman Titreşimi (X)"
    }
}

def send_reading(sensor_type, value, sensor_id="ANOMALY-TESTER"):
    """Sensör verisini API'ye gönder"""
    data = {
        "sensor_id": sensor_id,
        "sensor_type": sensor_type,
        "value": value,
        "unit": SENSORS[sensor_type]["unit"],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(API_URL, json=data, timeout=5)
        result = response.json()
        
        status = "🚨 ANOMALİ" if result.get("is_anomaly") else "✅ Normal"
        color = "\033[91m" if result.get("is_anomaly") else "\033[92m" # Kırmızı/Yeşil
        reset = "\033[0m"
        
        print(f"{color}{status}{reset} | {SENSORS[sensor_type]['description']:20s} | "
              f"Değer: {value:6.2f} | Z-Score: {result.get('z_score', 0):6.2f}")
        return result
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None

def simulate_single_anomaly():
    """Rastgele bir sensörde tekil anomali oluştur"""
    sensor_type = random.choice(list(SENSORS.keys()))
    value = random.choice(SENSORS[sensor_type]["anomaly_values"])
    # Biraz rastgelelik ekle
    value += random.uniform(-1, 1)
    
    print(f"\n⚡ TEKİL ANOMALİ ENJEKTE EDİLİYOR: {sensor_type}")
    send_reading(sensor_type, value)

def simulate_burst_anomaly():
    """Bir sensörde ardışık anomaliler oluştur (Kalıcı arıza simülasyonu)"""
    sensor_type = random.choice(list(SENSORS.keys()))
    base_anomaly = random.choice(SENSORS[sensor_type]["anomaly_values"])
    
    count = random.randint(3, 8)
    print(f"\n🔥 ANOMALİ PATLAMASI BAŞLATILIYOR: {sensor_type} ({count} veri)")
    
    for i in range(count):
        # Değer biraz dalgalansın
        value = base_anomaly + random.uniform(-2, 2)
        send_reading(sensor_type, value)
        time.sleep(0.05)

def simulate_system_failure():
    """Tüm sensörlerde aynı anda anomali (Sistem çökmesi)"""
    print(f"\n💥 SİSTEM ÇÖKMESİ SİMÜLASYONU")
    for sensor_type in SENSORS.keys():
        value = random.choice(SENSORS[sensor_type]["anomaly_values"])
        send_reading(sensor_type, value)
        time.sleep(0.02)

def main():
    print("=" * 70)
    print("💀 ANOMALİ SİMÜLATÖRÜ (HIZLI MOD)")
    print("=" * 70)
    print("1. Rastgele Tekil Anomali (Her 0.5-1 saniyede bir)")
    print("2. Anomali Patlaması (Sensör Arızası Simülasyonu)")
    print("3. Sistem Çökmesi (Tüm Sensörler)")
    print("4. Karışık Mod (Rastgele senaryolar)")
    print("=" * 70)
    
    try:
        choice = input("Seçiminiz (1-4): ").strip()
        
        if choice == "1":
            while True:
                simulate_single_anomaly()
                time.sleep(random.uniform(0.5, 1.0))
                
        elif choice == "2":
            while True:
                simulate_burst_anomaly()
                time.sleep(random.uniform(1.0, 3.0))
                
        elif choice == "3":
            while True:
                simulate_system_failure()
                time.sleep(2.0)
                
        elif choice == "4":
            while True:
                scenario = random.random()
                if scenario < 0.6:
                    simulate_single_anomaly()
                elif scenario < 0.9:
                    simulate_burst_anomaly()
                else:
                    simulate_system_failure()
                
                time.sleep(random.uniform(0.5, 2.0))
        else:
            print("Geçersiz seçim!")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Simülasyon durduruldu.")

if __name__ == "__main__":
    main()
