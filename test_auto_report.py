"""
Otomatik raporlama test scripti
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_auto_report():
    print("=" * 60)
    print("Otomatik Raporlama Test")
    print("=" * 60)
    
    # 0. Önce sistemi sıfırla
    print("\n0. Sistem sıfırlanıyor...")
    requests.post(f"{BASE_URL}/api/v1/reset")
    requests.post(f"{BASE_URL}/api/v1/auto-report/clear-buffer")
    print("   Sistem sıfırlandı")
    
    # 1. Önce normal veriler göndererek baseline oluştur
    print("\n1. Normal veriler gönderiliyor (baseline)...")
    for i in range(60):
        r = requests.post(f"{BASE_URL}/api/v1/analyze", json={
            "sensor_id": "sensor1",
            "sensor_type": "temperature",
            "value": 25 + (i % 3) - 1,  # 24-27 arası normal değerler
            "unit": "C"
        })
    print("   60 normal veri gönderildi (temperature: 24-27°C)")
    
    # 2. Auto report durumunu kontrol et
    print("\n2. Auto Report durumu kontrol ediliyor...")
    r = requests.get(f"{BASE_URL}/api/v1/auto-report/status")
    status = r.json()
    print(f"   Enabled: {status['config']['enabled']}")
    print(f"   Buffer size: {status['buffer_size']}")
    print(f"   Current score: {status['current_score']}")
    print(f"   Reports sent: {status['reports_sent']}")
    
    # 3. E-posta durumunu kontrol et
    print("\n3. E-posta durumu kontrol ediliyor...")
    r = requests.get(f"{BASE_URL}/api/v1/email/config")
    email = r.json()
    print(f"   Configured: {email['is_configured']}")
    
    r = requests.get(f"{BASE_URL}/api/v1/email/recipients")
    recipients = r.json()
    print(f"   Recipients: {recipients['count']}")
    for rec in recipients.get('recipients', []):
        print(f"   - {rec['email']}")
    
    # 4. LLM durumunu kontrol et
    print("\n4. LLM durumu kontrol ediliyor...")
    r = requests.get(f"{BASE_URL}/api/v1/llm/status")
    llm = r.json()
    print(f"   Available: {llm['available']}")
    print(f"   Model: {llm['model']}")
    
    # 5. Anomali verileri gönder (aynı sensör tipinde çok yüksek değerler)
    print("\n5. Anomali verileri gönderiliyor...")
    print("   (temperature sensöründe 150-250°C arası değerler)")
    for i in range(10):
        r = requests.post(f"{BASE_URL}/api/v1/analyze", json={
            "sensor_id": f"sensor{i+1}",
            "sensor_type": "temperature",  # Aynı sensör tipi
            "value": 150 + i*10,  # 150-240°C (çok yüksek)
            "unit": "C"
        })
        result = r.json()
        is_anomaly = result['is_anomaly']
        z_score = result['z_score']
        severity = result['severity']
        marker = "🚨" if is_anomaly else "✓"
        print(f"   {marker} Anomali {i+1}: is_anomaly={is_anomaly}, z_score={z_score:.2f}, severity={severity}")
        time.sleep(0.3)
    
    # 6. Tekrar durumu kontrol et
    print("\n6. Son durum kontrol ediliyor...")
    r = requests.get(f"{BASE_URL}/api/v1/auto-report/status")
    status = r.json()
    print(f"   Total anomalies processed: {status['total_anomalies_processed']}")
    print(f"   Buffer size: {status['buffer_size']}")
    print(f"   Current score: {status['current_score']}")
    print(f"   Score threshold: {status['score_threshold']}")
    print(f"   Reports sent: {status['reports_sent']}")
    print(f"   Reports skipped (cooldown): {status['reports_skipped_cooldown']}")
    print(f"   Last report sent: {status['last_report_sent']}")
    
    # 7. Anomali loglarını kontrol et
    print("\n7. Anomali logları kontrol ediliyor...")
    r = requests.get(f"{BASE_URL}/api/v1/logs/anomalies?limit=5")
    logs = r.json()
    print(f"   Son {logs['count']} anomali:")
    for log in logs.get('anomalies', [])[:5]:
        print(f"   - {log.get('sensor_type')}: {log.get('current_value'):.1f}, z={log.get('z_score'):.2f}")
    
    print("\n" + "=" * 60)
    print("Test tamamlandı!")
    print("=" * 60)
    
    # Sonuç özeti
    print("\n📊 SONUÇ ÖZETİ:")
    print(f"   E-posta yapılandırıldı: {'✅' if email['is_configured'] else '❌'}")
    print(f"   Alıcı var: {'✅' if recipients['count'] > 0 else '❌'}")
    print(f"   LLM aktif: {'✅' if llm['available'] else '❌'}")
    print(f"   Otomatik rapor aktif: {'✅' if status['config']['enabled'] else '❌'}")
    print(f"   Anomali tespit edildi: {'✅' if status['total_anomalies_processed'] > 0 else '❌'}")
    print(f"   Rapor gönderildi: {'✅' if status['reports_sent'] > 0 else '❌'}")

if __name__ == "__main__":
    test_auto_report()
