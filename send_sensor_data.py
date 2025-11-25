"""
Sensör Verisi Gönderici - Sürekli Veri Akışı
Gerçek zamanlı olarak endpoint'e sensör verileri gönderir
"""

import requests
import random
import time
from datetime import datetime
import json

API_URL = "http://localhost:8000/api/v1/analyze"

# Sensör tipleri ve normal değer aralıkları
SENSORS = {
    "temperature": {
        "unit": "°C",
        "normal_range": (18, 25),
        "anomaly_value": 45,
        "description": "Ortam Sıcaklığı"
    },
    "vibration_level": {
        "unit": "mm/s",
        "normal_range": (0.5, 2.0),
        "anomaly_value": 5.5,
        "description": "Titreşim Seviyesi"
    },
    "motor_current": {
        "unit": "A",
        "normal_range": (4.5, 5.5),
        "anomaly_value": 8.5,
        "description": "Motor Akımı"
    },
    "system_voltage": {
        "unit": "V",
        "normal_range": (23.5, 24.5),
        "anomaly_value": 20.0,
        "description": "Sistem Voltajı"
    },
    "acoustic_noise": {
        "unit": "dB",
        "normal_range": (55, 65),
        "anomaly_value": 95,
        "description": "Akustik Gürültü"
    },
    "pressure": {
        "unit": "bar",
        "normal_range": (2.0, 3.0),
        "anomaly_value": 5.5,
        "description": "Basınç"
    },
    "throughput": {
        "unit": "units/min",
        "normal_range": (45, 55),
        "anomaly_value": 20,
        "description": "Üretim Hızı"
    }
}

def generate_normal_value(sensor_type):
    """Normal aralıkta rastgele değer üret"""
    min_val, max_val = SENSORS[sensor_type]["normal_range"]
    return round(random.uniform(min_val, max_val), 2)

def generate_anomaly_value(sensor_type):
    """Anomali değeri üret"""
    anomaly = SENSORS[sensor_type]["anomaly_value"]
    # Küçük varyasyon ekle
    return round(anomaly + random.uniform(-0.5, 0.5), 2)

def send_sensor_reading(sensor_type, value, sensor_id="SENSOR-001"):
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
        response.raise_for_status()
        result = response.json()
        
        # Sonucu renkli yazdır
        status = "🚨 ANOMALİ" if result["is_anomaly"] else "✅ Normal"
        color = "\033[91m" if result["is_anomaly"] else "\033[92m"
        reset = "\033[0m"
        
        print(f"{color}{status}{reset} | {SENSORS[sensor_type]['description']:20s} | "
              f"Değer: {value:6.2f} {SENSORS[sensor_type]['unit']:8s} | "
              f"Z-Score: {result['z_score']:6.2f} | "
              f"Ortalama: {result['mean']:6.2f}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Hata: {e}")
        return None

def main():
    """Ana döngü - Sürekli veri gönder"""
    print("=" * 100)
    print("🚀 SENSÖR VERİSİ GÖNDERİCİ BAŞLATILDI")
    print("=" * 100)
    print(f"API Endpoint: {API_URL}")
    print(f"Toplam Sensör Tipi: {len(SENSORS)}")
    print("=" * 100)
    print()
    
    iteration = 0
    anomaly_counter = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n--- İterasyon #{iteration} - {datetime.now().strftime('%H:%M:%S')} ---")
            
            # Her sensör tipinden veri gönder
            for sensor_type in SENSORS.keys():
                # %95 normal, %5 anomali
                if random.random() < 0.95:
                    value = generate_normal_value(sensor_type)
                else:
                    value = generate_anomaly_value(sensor_type)
                    anomaly_counter += 1
                
                result = send_sensor_reading(sensor_type, value)
                
                # Sensörler arası kısa bekleme
                time.sleep(0.3)
            
            # İstatistik
            if iteration % 5 == 0:
                print(f"\n📊 İstatistik: {iteration} iterasyon, {anomaly_counter} anomali tespit edildi")
            
            # Bir sonraki iterasyon için bekleme
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Veri gönderimi durduruldu!")
        print(f"Toplam {iteration} iterasyon, {anomaly_counter} anomali gönderildi")

if __name__ == "__main__":
    main()
