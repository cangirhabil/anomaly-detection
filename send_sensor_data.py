"""
CountSort Cihazı Veri Simülatörü - Uzun Süreli Çalışma Modu
Saniyede 1 veri gönderir, haftalarca çalışmaya uygundur.
"""

import requests
import random
import time
from datetime import datetime

API_URL = "http://localhost:8000/api/v1/analyze"

# CountSort Cihazına Özel Sensörler
SENSORS = {
    "ejector_pressure": {
        "unit": "bar",
        "normal_range": (6.8, 7.2), # Pnömatik valfler genelde 7 bar civarı çalışır
        "description": "Ejektör Hava Basıncı"
    },
    "conveyor_speed": {
        "unit": "m/s",
        "normal_range": (2.4, 2.6), # Bant hızı sabittir
        "description": "Konveyör Hızı"
    },
    "main_motor_load": {
        "unit": "%",
        "normal_range": (65, 75), # Motor yükü
        "description": "Ana Motor Yükü"
    },
    "separation_rate": {
        "unit": "obj/s",
        "normal_range": (140, 160), # Saniyede ayrıştırılan parça
        "description": "Ayrıştırma Hızı"
    },
    "optical_sensor_temp": {
        "unit": "°C",
        "normal_range": (35, 42), # Kamera/Sensör sıcaklığı
        "description": "Optik Sensör Isısı"
    },
    "vibration_bearing_x": {
        "unit": "mm/s",
        "normal_range": (0.8, 1.5), # Rulman titreşimi
        "description": "Rulman Titreşimi (X)"
    }
}

def generate_normal_value(sensor_type):
    """Normal aralıkta rastgele değer üret"""
    min_val, max_val = SENSORS[sensor_type]["normal_range"]
    return round(random.uniform(min_val, max_val), 2)

def send_sensor_reading(sensor_type, value, sensor_id="COUNTSORT-01"):
    """Sensör verisini API'ye gönder"""
    data = {
        "sensor_id": sensor_id,
        "sensor_type": sensor_type,
        "value": value,
        "unit": SENSORS[sensor_type]["unit"],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Timeout süresi kısa tutulur
        response = requests.post(API_URL, json=data, timeout=2)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Bağlantı Hatası: {e}")
        return False

def main():
    print("=" * 100)
    print("🏭 COUNTSORT MAKİNESİ - UZUN SÜRELİ İZLEME MODU")
    print("=" * 100)
    print(f"Hedef: {API_URL}")
    print("Periyot: Her 1.0 saniyede bir veri paketi")
    print("Sensörler: Ejektör, Konveyör, Motor, Optik, Titreşim")
    print("=" * 100)
    
    counter = 0
    start_time = time.time()
    
    try:
        while True:
            loop_start = time.time()
            counter += 1
            
            # Tüm sensörlerden veri topla ve gönder
            for sensor_type in SENSORS.keys():
                val = generate_normal_value(sensor_type)
                send_sensor_reading(sensor_type, val)
            
            # Geçen süreyi hesapla
            elapsed = time.time() - loop_start
            
            # Tam 1 saniye döngü süresi tutturmak için bekleme ayarı
            sleep_time = max(0, 1.0 - elapsed)
            
            if counter % 10 == 0:
                uptime = int(time.time() - start_time)
                print(f"✅ {datetime.now().strftime('%H:%M:%S')} | Paket: {counter} | Çalışma Süresi: {uptime}sn")
            
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nSimülasyon durduruldu.")

if __name__ == "__main__":
    main()
