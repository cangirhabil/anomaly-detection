"""
API Test Scripti
Mikroservis fonksiyonelliğini test eder
"""

import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000"


def test_health():
    """Health check testi"""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_log_errors():
    """Hata loglama testi"""
    print("=" * 60)
    print("TEST 2: Hata Loglama")
    print("=" * 60)
    
    # Normal veriler ekle
    print("\nNormal günlük hatalar ekleniyor...")
    for i in range(20):
        response = requests.post(
            f"{BASE_URL}/api/v1/log",
            json={"error_count": 17 + (i % 4)}
        )
        result = response.json()
        print(f"  Gün {i+1}: {result['current_value']} hata - Anomali: {result['is_anomaly']}")
    
    print()


def test_stats():
    """İstatistik testi"""
    print("=" * 60)
    print("TEST 3: İstatistikler")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    stats = response.json()
    
    print(f"Veri Sayısı: {stats['data_points']}")
    print(f"Ortalama: {stats['mean']:.2f}")
    print(f"Std Sapma: {stats['std_dev']:.2f}")
    print(f"Min-Max: {stats['min']}-{stats['max']}")
    print(f"Z-Score Eşiği: ±{stats['threshold']}")
    print()


def test_anomaly_detection():
    """Anomali tespit testi"""
    print("=" * 60)
    print("TEST 4: Anomali Tespiti")
    print("=" * 60)
    
    # Anormal değer
    print("\nAnormal hata sayısı testi (35 hata):")
    response = requests.post(
        f"{BASE_URL}/api/v1/log",
        json={"error_count": 35}
    )
    result = response.json()
    
    print(f"Hata Sayısı: {result['current_value']}")
    print(f"Z-Score: {result['z_score']:.2f}")
    print(f"Anomali: {'✅ EVET' if result['is_anomaly'] else '❌ HAYIR'}")
    print(f"Mesaj: {result['message']}")
    print()


def test_detect_only():
    """Sadece kontrol testi (geçmişe eklenmez)"""
    print("=" * 60)
    print("TEST 5: What-If Analizi")
    print("=" * 60)
    
    test_values = [15, 20, 25, 30, 40]
    
    print("\nFarklı değerler için anomali kontrolü:")
    for value in test_values:
        response = requests.post(
            f"{BASE_URL}/api/v1/detect",
            json={"value": value}
        )
        result = response.json()
        
        status = "🔴 ANOMALİ" if result['is_anomaly'] else "🟢 Normal"
        print(f"  {value} hata → Z-Score: {result['z_score']:6.2f} → {status}")
    
    print()


def test_config_update():
    """Konfigürasyon güncelleme testi"""
    print("=" * 60)
    print("TEST 6: Konfigürasyon Güncelleme")
    print("=" * 60)
    
    # Mevcut config
    response = requests.get(f"{BASE_URL}/api/v1/config")
    print(f"Mevcut: {json.dumps(response.json(), indent=2)}")
    
    # Güncelle
    print("\nKonfigürasyon güncelleniyor (Z=2.5)...")
    response = requests.put(
        f"{BASE_URL}/api/v1/config",
        json={"z_score_threshold": 2.5}
    )
    print(f"Yeni: {json.dumps(response.json(), indent=2)}")
    print()


def test_history():
    """Geçmiş veri testi"""
    print("=" * 60)
    print("TEST 7: Geçmiş Veri")
    print("=" * 60)
    
    # Son 5 kayıt
    response = requests.get(f"{BASE_URL}/api/v1/history?limit=5")
    history = response.json()
    
    print(f"Toplam Kayıt: {history['total']}")
    print(f"\nSon 5 Kayıt:")
    for i, record in enumerate(history['data'], 1):
        print(f"  {i}. {record['date']}: {record['error_count']} hata")
    
    print()


def test_full_workflow():
    """Tam entegrasyon testi"""
    print("\n" + "=" * 60)
    print("🚀 TAM ENTEGRASYON TESTİ")
    print("=" * 60)
    
    # 1. Health check
    response = requests.get(f"{BASE_URL}/api/v1/health")
    assert response.status_code == 200
    print("✅ Health check başarılı")
    
    # 2. Konfigürasyon
    response = requests.get(f"{BASE_URL}/api/v1/config")
    assert response.status_code == 200
    print("✅ Konfigürasyon okundu")
    
    # 3. İstatistik
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    assert response.status_code == 200
    print("✅ İstatistikler alındı")
    
    # 4. Hata loglama
    response = requests.post(
        f"{BASE_URL}/api/v1/log",
        json={"error_count": 18}
    )
    assert response.status_code == 200
    print("✅ Hata loglama çalışıyor")
    
    # 5. Anomali tespiti
    response = requests.post(
        f"{BASE_URL}/api/v1/detect",
        json={"value": 50}
    )
    assert response.status_code == 200
    assert response.json()['is_anomaly'] == True
    print("✅ Anomali tespiti çalışıyor")
    
    # 6. Geçmiş
    response = requests.get(f"{BASE_URL}/api/v1/history")
    assert response.status_code == 200
    print("✅ Geçmiş veri alındı")
    
    print("\n" + "=" * 60)
    print("✅ TÜM TESTLER BAŞARILI!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("     MİKROSERVİS API TEST SÜİTİ")
    print("🧪" * 30 + "\n")
    
    try:
        test_health()
        test_log_errors()
        test_stats()
        test_anomaly_detection()
        test_detect_only()
        test_config_update()
        test_history()
        test_full_workflow()
        
        print("\n" + "=" * 60)
        print("🎉 TÜM API TESTLERİ TAMAMLANDI")
        print("=" * 60)
        print("\n📚 API Dokümantasyonu: http://localhost:8000/api/docs")
        print("🔧 Interactive API Test: http://localhost:8000/api/docs\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ HATA: API servisi çalışmıyor!")
        print("Servisi başlatmak için: python app.py\n")
    except Exception as e:
        print(f"\n❌ HATA: {e}\n")
