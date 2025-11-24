
"""
Şişe Sınıflandırma Sistemi - Anomali Tespit Simülasyonu
Count Sort Sistemi için Sensör Verisi Simülasyonu
"""

import requests
import time
import random
import math
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"

# Sensör Konfigürasyonları (Simülasyon için)
SENSORS = {
    "motor_current": {"base": 5.0, "noise": 0.2, "unit": "A"},      # Motor Akımı
    "system_voltage": {"base": 24.0, "noise": 0.1, "unit": "V"},    # Sistem Voltajı
    "acoustic_noise": {"base": 60.0, "noise": 2.0, "unit": "dB"},   # Akustik Gürültü
    "vibration_level": {"base": 0.5, "noise": 0.05, "unit": "g"},   # Titreşim
    "throughput": {"base": 1200.0, "noise": 50.0, "unit": "BPM"}    # Şişe Akış Hızı
}

def print_header(text):
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)

def send_reading(sensor_type, value, unit=None):
    payload = {
        "sensor_type": sensor_type,
        "value": value,
        "unit": unit,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f"{API_URL}/analyze", json=payload)
        if response.status_code == 200:
            result = response.json()
            
            sys_status = result.get("system_status", "Active")
            window_size = result.get("window_size", 0)
            
            status_icon = "🟢"
            if result["is_anomaly"]:
                status_icon = "🔴"
            elif sys_status == "Learning":
                status_icon = "🧠"
            elif sys_status == "Initializing":
                status_icon = "⏳"
                
            print(f"[{status_icon} {sys_status}] {sensor_type:<15}: {value:>6.2f} {unit} | Z: {result['z_score']:>5.2f} | Win: {window_size}")
            
            if result["is_anomaly"]:
                print(f"   └─ ⚠️  ANOMALİ: {result['message']}")
        else:
            print(f"❌ Hata: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")

def simulate_normal_operation(duration_sec=10):
    print_header(f"Normal Operasyon Simülasyonu ({duration_sec}s)")
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        for sensor, config in SENSORS.items():
            # Normal dağılım ile rastgele veri üret
            value = random.gauss(config["base"], config["noise"])
            send_reading(sensor, value, config["unit"])
        time.sleep(0.1) # Hızlı veri akışı

def simulate_anomaly(anomaly_type):
    print_header(f"Anomali Senaryosu: {anomaly_type}")
    
    if anomaly_type == "bottle_jam":
        # Şişe sıkışması: Motor akımı artar, titreşim artar, akış düşer
        print("⚠️  Şişe sıkışması simüle ediliyor...")
        send_reading("motor_current", 8.5, "A")      # Yüksek akım
        send_reading("vibration_level", 1.5, "g")    # Yüksek titreşim
        send_reading("throughput", 200, "BPM")       # Düşük akış
        
    elif anomaly_type == "broken_bottle":
        # Kırık şişe: Ani ses artışı
        print("⚠️  Kırık şişe sesi simüle ediliyor...")
        send_reading("acoustic_noise", 95.0, "dB")   # Çok yüksek ses
        
    elif anomaly_type == "power_fluctuation":
        # Güç dalgalanması: Voltaj düşüşü
        print("⚠️  Güç dalgalanması simüle ediliyor...")
        send_reading("system_voltage", 20.5, "V")    # Düşük voltaj

def main():
    print_header("Şişe Sınıflandırma Sistemi Başlatılıyor")
    
    # 1. Isınma Turu (Veri toplama)
    print("Veri toplanıyor (Learning Phase)...")
    simulate_normal_operation(duration_sec=5)
    
    # 2. Normal Çalışma
    print("\nSistem aktif, izleme devam ediyor...")
    simulate_normal_operation(duration_sec=5)
    
    # 3. Anomali Senaryoları
    simulate_anomaly("bottle_jam")
    time.sleep(1)
    simulate_anomaly("broken_bottle")
    time.sleep(1)
    simulate_anomaly("power_fluctuation")
    
    # 4. Normale Dönüş
    print("\nNormale dönülüyor...")
    simulate_normal_operation(duration_sec=3)

if __name__ == "__main__":
    main()


import requests
import time
import random
import json
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"

def print_header(text):
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)

def send_reading(sensor_type, value, unit=None):
    payload = {
        "sensor_type": sensor_type,
        "value": value,
        "unit": unit,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f"{API_URL}/analyze", json=payload)
        if response.status_code == 200:
            result = response.json()
            
            # Sistem durumunu al (Learning, Active, Initializing)
            sys_status = result.get("system_status", "Active")
            
            status_icon = "🟢"
            if result["is_anomaly"]:
                status_icon = "🔴"
            elif sys_status == "Learning":
                status_icon = "🧠"
            elif sys_status == "Initializing":
                status_icon = "⏳"
                
            print(f"[{status_icon} {sys_status}] {sensor_type}: {value:.2f} (Z: {result['z_score']:.2f})")
            
            if result["is_anomaly"]:
                print(f"   └─ {result['message']}")
        else:
            print(f"❌ Hata: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")

def run_demo():
    print_header("DEMO BAŞLATILIYOR: Endüstriyel Sensör Simülasyonu")
    
    # 1. Sistem Sıfırlama
    print("\n1. Sistem sıfırlanıyor...")
    try:
        requests.post(f"{API_URL}/reset")
    except:
        print("❌ API'ye ulaşılamadı. Lütfen servisi başlatın.")
        return
    
    # 2. Normal Çalışma (Öğrenme Aşaması)
    print("\n2. Normal çalışma verileri gönderiliyor (Öğrenme)...")
    print("   Not: İlk 50 veri 'Learning' modunda işlenecek.")
    
    # Titreşim (X, Y, Z): 0.1 - 0.5 G (Normal motor titreşimi)
    # Sıcaklık: 60 - 70 C
    # Ses: 70 - 80 dB
    # Motor Akımı: 10 - 12 Amper
    # Hız (Throughput): 100 - 110 Şişe/Dakika
    
    # 60 veri gönderiyoruz (50 tanesi eğitim, son 10 tanesi normal izleme)
    for i in range(60):
        # Titreşim (3 Eksen)
        send_reading("vibration_x", random.uniform(0.1, 0.3), "G")
        send_reading("vibration_y", random.uniform(0.1, 0.3), "G")
        send_reading("vibration_z", random.uniform(0.2, 0.5), "G") # Z ekseni genelde daha yüksektir
        
        # Diğer Sensörler
        send_reading("temperature", random.uniform(60, 65), "C")
        send_reading("sound", random.uniform(70, 75), "dB")
        send_reading("motor_current", random.uniform(10, 12), "A")
        send_reading("throughput", random.randint(100, 110), "bpm") # bottles per minute
        
        # Hızlı geçmesi için bekleme süresini kısalttık
        if i % 10 == 0:
            print(f"... {i} veri işlendi ...")
        # time.sleep(0.01) 
        
    print("\n✅ Öğrenme tamamlandı. İstatistikler oluştu.")
    
    # 3. Senaryo: Rulman Hatası (Titreşim ve Sıcaklık Artışı)
    print_header("SENARYO 1: Rulman Hatası")
    print("Belirtiler: Z ekseninde titreşim artıyor, Sıcaklık yükseliyor")
    
    for i in range(5):
        # Z ekseni anomali veriyor
        send_reading("vibration_z", random.uniform(1.5, 2.5), "G")
        # Sıcaklık yavaşça artıyor
        send_reading("temperature", random.uniform(70, 75), "C")
        
        time.sleep(0.2)
        
    # 4. Senaryo: Bant Sıkışması / Zorlanma
    print_header("SENARYO 2: Bant Sıkışması / Motor Zorlanma")
    print("Belirtiler: Motor akımı fırlıyor, Üretim hızı düşüyor")
    
    # Motor akımı tavan yapıyor (Zorlanma)
    send_reading("motor_current", 25.5, "A")
    
    # Üretim hızı düşüyor (Yavaşlama)
    send_reading("throughput", 45, "bpm")
    
    # 5. Senaryo: Motor Durması
    print_header("SENARYO 3: Motor Durması")
    print("Belirtiler: Ses kesiliyor, Akım sıfırlanıyor")
    
    send_reading("sound", 10.0, "dB")     # Ses yok
    send_reading("motor_current", 0.5, "A") # Akım yok (rölanti)
    
    # 5. İstatistikleri Göster
    print_header("Sistem İstatistikleri")
    response = requests.get(f"{API_URL}/stats")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    # Servisin çalıştığından emin ol
    try:
        requests.get(f"{API_URL}/health")
        run_demo()
    except:
        print("❌ HATA: API servisi çalışmıyor!")
        print("Lütfen önce 'uvicorn app:app --reload' komutu ile servisi başlatın.")