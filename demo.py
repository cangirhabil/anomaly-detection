"""
Anomali Tespit Sistemi - Demo Senaryosu
Çoklu sensör verisi simülasyonu
"""

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