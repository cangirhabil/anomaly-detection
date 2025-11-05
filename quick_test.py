"""
Hızlı Test - Basit Kullanım Örneği
Anomali tespit sisteminin en temel kullanımı
"""

from datetime import datetime, timedelta
import random
from anomaly_detector import AnomalyDetector


def main():
    print("=" * 60)
    print("  ANOMALİ TESPİT SİSTEMİ - HIZLI TEST")
    print("=" * 60)
    
    # 1. Dedektör oluştur
    print("\n1️⃣  Anomali dedektörü oluşturuluyor...")
    detector = AnomalyDetector()
    print("   ✅ Hazır! (Z-Score eşiği: ±2.0, Pencere: 30 gün)")
    
    # 2. Normal günler - geçmiş veri
    print("\n2️⃣  Normal günlük veriler ekleniyor (15-20 hata/gün)...")
    base_date = datetime.now() - timedelta(days=20)
    
    for i in range(20):
        error_count = random.randint(15, 20)
        date = base_date + timedelta(days=i)
        detector.add_error_log(error_count, date)
    
    print(f"   ✅ 20 günlük normal veri eklendi")
    
    # 3. İstatistik özeti
    print("\n3️⃣  Mevcut sistem istatistikleri:")
    stats = detector.get_statistics_summary()
    print(f"   📊 Ortalama: {stats['mean']:.1f} hata/gün")
    print(f"   📊 Standart Sapma: {stats['std_dev']:.1f}")
    print(f"   📊 Veri Aralığı: {stats['min']}-{stats['max']}")
    
    # 4. Normal gün testi
    print("\n4️⃣  Normal gün testi (18 hata):")
    result = detector.add_error_log(18)
    print(f"   {result.message}")
    
    # 5. Şüpheli gün testi
    print("\n5️⃣  Şüpheli artış testi (25 hata):")
    result = detector.add_error_log(25)
    print(f"   {result.message}")
    
    if result.is_anomaly:
        print(f"   🔴 Anomali tespit edildi!")
    
    # 6. Kritik gün testi
    print("\n6️⃣  Kritik seviye testi (40 hata):")
    result = detector.add_error_log(40)
    print(f"   {result.message}")
    
    if result.is_anomaly:
        print(f"   🚨 ALARM! Z-Score: {result.z_score:.2f}")
        print(f"   💥 Beklenen aralık: {result.mean:.1f} ± {result.std_dev:.1f}")
        print(f"   💥 Gerçekleşen: {result.current_value}")
    
    # Özet
    print("\n" + "=" * 60)
    print("  ✅ TEST TAMAMLANDI")
    print("=" * 60)
    print("\n💡 Sonraki Adımlar:")
    print("   • Detaylı örnekler için: python demo.py")
    print("   • Dokümantasyon için: README.md")
    print("   • Backend entegrasyonu için kod örneklerini inceleyin\n")


if __name__ == "__main__":
    main()
