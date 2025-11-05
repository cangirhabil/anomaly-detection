"""
Demo ve Test Scripti
Anomali tespit sisteminin kullanım örnekleri
"""

from datetime import datetime, timedelta
import random
from anomaly_detector import AnomalyDetector, AnomalyConfig


def demo_basic_usage():
    """Temel kullanım örneği"""
    print("=" * 70)
    print("DEMO 1: TEMEL KULLANIM")
    print("=" * 70)
    
    # Anomali dedektörü oluştur (varsayılan ayarlar)
    detector = AnomalyDetector()
    
    # Örnek veri: Normal günler (15-20 hata arası)
    print("\n📊 Normal günlük hata verileri ekleniyor...")
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(25):
        error_count = random.randint(15, 20)
        date = base_date + timedelta(days=i)
        result = detector.add_error_log(error_count, date)
        print(f"  Gün {i+1}: {error_count} hata - {result.message}")
    
    # İstatistik özeti
    print("\n📈 Mevcut İstatistikler:")
    stats = detector.get_statistics_summary()
    print(f"  Veri Sayısı: {stats['data_points']}")
    print(f"  Ortalama: {stats['mean']:.2f}")
    print(f"  Std Sapma: {stats['std_dev']:.2f}")
    print(f"  Min-Max: {stats['min']}-{stats['max']}")
    print(f"  Z-Score Eşiği: ±{stats['threshold']}")
    
    # Anormal gün - çok yüksek hata
    print("\n🚨 ANORMAL GÜN TESTİ:")
    anomaly_result = detector.add_error_log(35, datetime.now())
    print(f"  {anomaly_result}")
    
    if anomaly_result.is_anomaly:
        print(f"\n  ⚠️  Alarm! Hata sayısı normalin {abs(anomaly_result.z_score):.2f} standart sapma üzerinde!")


def demo_different_configs():
    """Farklı konfigürasyon örnekleri"""
    print("\n\n" + "=" * 70)
    print("DEMO 2: FARKLI KONFİGÜRASYONLAR")
    print("=" * 70)
    
    # Test verisi hazırla
    base_date = datetime.now() - timedelta(days=30)
    historical_data = [
        (base_date + timedelta(days=i), random.randint(15, 20))
        for i in range(28)
    ]
    
    configs = {
        "Hassas (Z=1.645)": AnomalyConfig.sensitive(),
        "Dengeli (Z=2.0)": AnomalyConfig.balanced(),
        "Konservatif (Z=3.0)": AnomalyConfig.conservative()
    }
    
    test_value = 26  # Test edilecek hata sayısı
    
    print(f"\n🧪 Test Değeri: {test_value} hata")
    print(f"   Normal Aralık: 15-20 hata\n")
    
    for config_name, config in configs.items():
        detector = AnomalyDetector(config)
        detector.load_historical_data(historical_data)
        
        result = detector.detect_anomaly(test_value, datetime.now())
        
        print(f"  {config_name}:")
        print(f"    Z-Score: {result.z_score:.2f}")
        print(f"    Anomali: {'✅ EVET' if result.is_anomaly else '❌ HAYIR'}")
        print()


def demo_realtime_monitoring():
    """Gerçek zamanlı izleme simülasyonu"""
    print("\n" + "=" * 70)
    print("DEMO 3: GERÇEK ZAMANLI İZLEME SİMÜLASYONU")
    print("=" * 70)
    
    detector = AnomalyDetector(AnomalyConfig(z_score_threshold=2.0))
    
    # 20 günlük normal veri
    print("\n📅 İlk 20 gün - Normal dönem (15-20 hata/gün):")
    base_date = datetime.now() - timedelta(days=25)
    for i in range(20):
        error_count = random.randint(15, 20)
        date = base_date + timedelta(days=i)
        detector.add_error_log(error_count, date)
    
    stats = detector.get_statistics_summary()
    print(f"   Ortalama: {stats['mean']:.1f} ± {stats['std_dev']:.1f}")
    
    # Şüpheli artış başlıyor
    print("\n⚡ 21-23. günler - Şüpheli artış:")
    suspicious_days = [
        (21, 22),
        (22, 24),
        (23, 26)
    ]
    
    for day, error_count in suspicious_days:
        date = base_date + timedelta(days=day-1)
        result = detector.add_error_log(error_count, date)
        
        status = "🔴 ANOMALİ" if result.is_anomaly else "🟢 Normal"
        print(f"   Gün {day}: {error_count} hata - Z-Score: {result.z_score:.2f} - {status}")
    
    # Kritik gün
    print("\n🚨 24. gün - Kritik seviye:")
    result = detector.add_error_log(35, base_date + timedelta(days=23))
    print(f"   {result.message}")
    
    if result.is_anomaly:
        print(f"\n   💥 SİSTEM ALARMI!")
        print(f"   Beklenen aralık: {result.mean - 2*result.std_dev:.1f} - {result.mean + 2*result.std_dev:.1f}")
        print(f"   Gerçekleşen: {result.current_value}")


def demo_batch_analysis():
    """Toplu veri analizi"""
    print("\n\n" + "=" * 70)
    print("DEMO 4: GEÇMİŞ VERİ ANALİZİ")
    print("=" * 70)
    
    detector = AnomalyDetector(AnomalyConfig(z_score_threshold=2.5))
    
    # Simülasyon verisi: Normalde 15-20, bazı günler anormal
    print("\n📊 30 günlük veri yükleniyor...")
    base_date = datetime.now() - timedelta(days=30)
    
    anomaly_days = [7, 15, 22, 28]  # Anormal olması beklenen günler
    anomaly_count = 0
    
    for i in range(30):
        if i in anomaly_days:
            error_count = random.randint(30, 40)  # Anormal yüksek
        else:
            error_count = random.randint(15, 20)  # Normal
        
        date = base_date + timedelta(days=i)
        result = detector.add_error_log(error_count, date)
        
        if result.is_anomaly:
            anomaly_count += 1
            print(f"  ⚠️  Gün {i+1}: {error_count} hata - ANOMALİ (Z={result.z_score:.2f})")
    
    print(f"\n📈 Analiz Özeti:")
    stats = detector.get_statistics_summary()
    print(f"  Toplam Gün: {stats['data_points']}")
    print(f"  Anomali Tespit: {anomaly_count}")
    print(f"  Ortalama Hata: {stats['mean']:.2f}")
    print(f"  Standart Sapma: {stats['std_dev']:.2f}")
    print(f"  Hata Aralığı: {stats['min']}-{stats['max']}")


def demo_incremental_learning():
    """Artımlı öğrenme - Sistemin kendini güncellemesi"""
    print("\n\n" + "=" * 70)
    print("DEMO 5: DİNAMİK ÖĞRENME - SİSTEM KENDİNİ GÜNCELLİYOR")
    print("=" * 70)
    
    detector = AnomalyDetector(AnomalyConfig(window_size=10))  # Küçük pencere
    
    # Faz 1: Düşük hata dönemi
    print("\n📉 Faz 1: Düşük hata dönemi (5-10 hata/gün)")
    base_date = datetime.now() - timedelta(days=15)
    for i in range(7):
        error_count = random.randint(5, 10)
        detector.add_error_log(error_count, base_date + timedelta(days=i))
    
    stats = detector.get_statistics_summary()
    print(f"   Ortalama: {stats['mean']:.1f}, Std: {stats['std_dev']:.1f}")
    
    # Test: 15 hata anomali mi?
    result = detector.detect_anomaly(15, datetime.now())
    print(f"   15 hata → {'ANOMALİ' if result.is_anomaly else 'Normal'} (Z={result.z_score:.2f})")
    
    # Faz 2: Sistemin normal seviyesi artıyor
    print("\n📈 Faz 2: Sistem trafiği artıyor (15-20 hata/gün)")
    for i in range(7, 14):
        error_count = random.randint(15, 20)
        detector.add_error_log(error_count, base_date + timedelta(days=i))
    
    stats = detector.get_statistics_summary()
    print(f"   YENİ Ortalama: {stats['mean']:.1f}, Std: {stats['std_dev']:.1f}")
    
    # Aynı test: 15 hata şimdi anomali mi?
    result = detector.detect_anomaly(15, datetime.now())
    print(f"   15 hata → {'ANOMALİ' if result.is_anomaly else 'Normal'} (Z={result.z_score:.2f})")
    print("\n   💡 Sistem kendini güncelledi - artık 15 hata normal kabul ediliyor!")


if __name__ == "__main__":
    print("\n")
    print("🔍" * 35)
    print("     ANOMALİ TESPİT SİSTEMİ - DEMO VE TESTLER")
    print("🔍" * 35)
    print("\nZ-Score Tabanlı İstatistiksel Anomali Tespiti")
    print("Python 3.8+ | NumPy | Pandas\n")
    
    # Tüm demoları çalıştır
    demo_basic_usage()
    demo_different_configs()
    demo_realtime_monitoring()
    demo_batch_analysis()
    demo_incremental_learning()
    
    print("\n\n" + "=" * 70)
    print("✅ TÜM DEMOLAR TAMAMLANDI")
    print("=" * 70)
    print("\n💡 Kullanım İpuçları:")
    print("  • Normal trafik için Z=2.0 (95% güven) önerilir")
    print("  • Kritik sistemler için Z=3.0 (99.7% güven) kullanın")
    print("  • Minimum 7 günlük veri ile güvenilir sonuçlar alırsınız")
    print("  • Sistem otomatik olarak kendini günceller (son 30 gün)")
    print("\n")
