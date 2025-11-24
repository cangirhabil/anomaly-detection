#!/usr/bin/env python3
"""
Canlı Test Scripti - Anomali Tespit Sistemi
Adım adım mock data ile test eder
"""

import requests
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step, text):
    print(f"\n[ADIM {step}] {text}")

def send_reading(sensor_type, value, sensor_id="test_01"):
    """Sensör verisi gönder"""
    data = {
        "sensor_id": sensor_id,
        "sensor_type": sensor_type,
        "value": value,
        "unit": "unit",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f"{BASE_URL}/analyze", json=data)
        result = response.json()
        
        status = "🚨 ANOMALİ!" if result.get('is_anomaly') else "✅ Normal"
        print(f"  {status} | {sensor_type}={value:.2f} | Z-Score={result.get('z_score', 0):.2f}")
        
        return result
    except Exception as e:
        print(f"  ❌ Hata: {e}")
        return None

def get_stats():
    """İstatistikleri getir"""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        return response.json()
    except Exception as e:
        print(f"  ❌ İstatistik hatası: {e}")
        return None

def simulate_scenario(scenario_name):
    """Hazır senaryoyu çalıştır"""
    try:
        response = requests.post(f"{BASE_URL}/simulate/{scenario_name}")
        result = response.json()
        print(f"  ✅ {result.get('message', 'Senaryo başlatıldı')}")
        return result
    except Exception as e:
        print(f"  ❌ Hata: {e}")
        return None

# ============================================================================
# TEST SENARYOLARı
# ============================================================================

def test_1_normal_data():
    """Test 1: Normal veri gönder (Baseline oluştur)"""
    print_header("TEST 1: Normal Veri Gönderme (Baseline)")
    print_step(1, "Motor akımı için 20 adet normal veri gönderiyoruz...")
    
    for i in range(20):
        value = 5.0 + random.uniform(-0.3, 0.3)  # 4.7 - 5.3 arası
        send_reading("motor_current", value)
        time.sleep(0.1)
    
    print("\n  ✅ Baseline oluşturuldu!")
    
    # İstatistikleri göster
    print_step(2, "Mevcut istatistikleri kontrol ediyoruz...")
    stats = get_stats()
    if stats:
        print(f"\n  Toplam Sensör: {stats.get('total_sensors', 0)}")
        for sensor, data in stats.get('sensors', {}).items():
            print(f"  - {sensor}: {data.get('count', 0)} okuma, "
                  f"Ortalama={data.get('mean', 0):.2f}, "
                  f"Std Dev={data.get('std_dev', 0):.2f}")

def test_2_single_anomaly():
    """Test 2: Tek bir anomali gönder"""
    print_header("TEST 2: Tek Anomali Testi")
    print_step(1, "Normal aralığın dışında bir değer gönderiyoruz...")
    
    # Önce 5 normal veri daha
    print("\n  Normal veriler:")
    for i in range(5):
        value = 5.0 + random.uniform(-0.2, 0.2)
        send_reading("motor_current", value)
        time.sleep(0.1)
    
    # Şimdi anomali
    print("\n  Anomali verisi:")
    send_reading("motor_current", 8.5)  # Normalden çok yüksek
    time.sleep(0.5)
    
    # Tekrar normal
    print("\n  Tekrar normal veri:")
    for i in range(3):
        value = 5.0 + random.uniform(-0.2, 0.2)
        send_reading("motor_current", value)
        time.sleep(0.1)

def test_3_multiple_sensors():
    """Test 3: Birden fazla sensör tipi"""
    print_header("TEST 3: Çoklu Sensör Testi")
    print_step(1, "Farklı sensör tiplerinden veri gönderiyoruz...")
    
    sensors = {
        "motor_current": 5.0,
        "system_voltage": 24.0,
        "acoustic_noise": 60.0,
        "vibration_level": 2.5,
        "throughput": 100.0
    }
    
    # Her sensör için normal veri
    print("\n  Normal veriler:")
    for _ in range(15):
        for sensor_type, base_value in sensors.items():
            value = base_value + random.uniform(-base_value*0.05, base_value*0.05)
            send_reading(sensor_type, value)
            time.sleep(0.05)
    
    # İstatistikleri göster
    print_step(2, "Tüm sensörler için istatistikler:")
    stats = get_stats()
    if stats:
        for sensor, data in stats.get('sensors', {}).items():
            print(f"\n  {sensor}:")
            print(f"    Okuma Sayısı: {data.get('count', 0)}")
            print(f"    Ortalama: {data.get('mean', 0):.2f}")
            print(f"    Std Dev: {data.get('std_dev', 0):.2f}")
            print(f"    Min: {data.get('min', 0):.2f}")
            print(f"    Max: {data.get('max', 0):.2f}")

def test_4_bottle_jam_scenario():
    """Test 4: Şişe sıkışması senaryosu"""
    print_header("TEST 4: Şişe Sıkışması Senaryosu")
    print_step(1, "Hazır senaryoyu çalıştırıyoruz...")
    
    simulate_scenario("bottle_jam")
    
    print_step(2, "Senaryo sonuçlarını bekliyoruz...")
    time.sleep(3)
    
    print("\n  ✅ Senaryo tamamlandı!")

def test_5_broken_bottle_scenario():
    """Test 5: Kırık şişe senaryosu"""
    print_header("TEST 5: Kırık Şişe Senaryosu")
    print_step(1, "Acoustic noise sensöründe anomali oluşturuyoruz...")
    
    # Önce normal veri
    print("\n  Normal gürültü seviyeleri:")
    for i in range(10):
        value = 60.0 + random.uniform(-2, 2)
        send_reading("acoustic_noise", value)
        time.sleep(0.1)
    
    # Kırık şişe sesi (ani artış)
    print("\n  🔊 Kırık şişe sesi!")
    send_reading("acoustic_noise", 95.0)
    time.sleep(0.2)
    send_reading("acoustic_noise", 92.0)
    time.sleep(0.2)
    
    # Tekrar normale dönüş
    print("\n  Normale dönüş:")
    for i in range(5):
        value = 60.0 + random.uniform(-2, 2)
        send_reading("acoustic_noise", value)
        time.sleep(0.1)

def test_6_power_fluctuation():
    """Test 6: Güç dalgalanması"""
    print_header("TEST 6: Güç Dalgalanması Senaryosu")
    print_step(1, "Sistem voltajında dalgalanma simüle ediyoruz...")
    
    # Normal voltaj
    print("\n  Normal voltaj seviyeleri:")
    for i in range(15):
        value = 24.0 + random.uniform(-0.2, 0.2)
        send_reading("system_voltage", value)
        time.sleep(0.1)
    
    # Voltaj düşüşü
    print("\n  ⚡ Voltaj düşüşü!")
    send_reading("system_voltage", 20.5)
    time.sleep(0.2)
    send_reading("system_voltage", 20.8)
    time.sleep(0.2)
    send_reading("system_voltage", 21.0)
    time.sleep(0.2)
    
    # Normale dönüş
    print("\n  Voltaj normale dönüyor:")
    for i in range(5):
        value = 24.0 + random.uniform(-0.2, 0.2)
        send_reading("system_voltage", value)
        time.sleep(0.1)

def show_final_stats():
    """Final istatistikler"""
    print_header("FINAL İSTATİSTİKLER")
    stats = get_stats()
    
    if stats:
        print(f"\nToplam Sensör Sayısı: {stats.get('total_sensors', 0)}")
        print("\nDetaylı İstatistikler:")
        print("-" * 70)
        
        for sensor, data in stats.get('sensors', {}).items():
            print(f"\n📊 {sensor.upper()}")
            print(f"   Toplam Okuma  : {data.get('count', 0)}")
            print(f"   Ortalama      : {data.get('mean', 0):.2f}")
            print(f"   Std Sapma     : {data.get('std_dev', 0):.2f}")
            print(f"   Min - Max     : {data.get('min', 0):.2f} - {data.get('max', 0):.2f}")
            print(f"   Anomali Sayısı: {data.get('anomaly_count', 0)}")

# ============================================================================
# ANA PROGRAM
# ============================================================================

def main():
    print_header("ANOMALİ TESPİT SİSTEMİ - CANLI TEST")
    print("\nBackend: http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("\nTest başlıyor...\n")
    
    try:
        # Testleri sırayla çalıştır
        test_1_normal_data()
        input("\n[Enter] tuşuna basarak devam edin...")
        
        test_2_single_anomaly()
        input("\n[Enter] tuşuna basarak devam edin...")
        
        test_3_multiple_sensors()
        input("\n[Enter] tuşuna basarak devam edin...")
        
        test_4_bottle_jam_scenario()
        input("\n[Enter] tuşuna basarak devam edin...")
        
        test_5_broken_bottle_scenario()
        input("\n[Enter] tuşuna basarak devam edin...")
        
        test_6_power_fluctuation()
        input("\n[Enter] tuşuna basarak devam edin...")
        
        show_final_stats()
        
        print_header("TEST TAMAMLANDI!")
        print("\n✅ Tüm testler başarıyla tamamlandı!")
        print("📊 Frontend'i http://localhost:3000 adresinden kontrol edebilirsiniz.")
        print("📚 API Dokümantasyonu: http://localhost:8000/api/docs\n")
        
    except KeyboardInterrupt:
        print("\n\n❌ Test kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n\n❌ Hata: {e}")

if __name__ == "__main__":
    main()
