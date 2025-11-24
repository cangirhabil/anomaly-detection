"""
Anomali Tespit Mikroservisi - Python Client
Kendi projenizde kullanmak için hazır client kütüphanesi

Kullanım:
    from anomaly_client import AnomalyClient
    
    client = AnomalyClient("http://localhost:8000")
    result = client.analyze(sensor_type="vibration", value=2.5, unit="G")
    
    if result.is_anomaly:
        send_alert(result.message)
"""

import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AnomalyResult:
    """Anomali tespit sonucu"""
    is_anomaly: bool
    sensor_type: str
    current_value: float
    mean: float
    std_dev: float
    z_score: float
    threshold: float
    message: str
    timestamp: str
    severity: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AnomalyResult':
        """Dictionary'den AnomalyResult oluştur"""
        return cls(**data)


@dataclass
class Stats:
    """İstatistik bilgileri"""
    total_sensors: int
    sensors: Dict[str, Any]
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Stats':
        """Dictionary'den Stats oluştur"""
        return cls(**data)


class AnomalyClient:
    """
    Anomali Tespit Mikroservisi Python İstemcisi
    
    Kullanım:
        client = AnomalyClient("http://localhost:8000")
        
        # Veri analiz et
        result = client.analyze("temperature", 85.5, "C")
        if result.is_anomaly:
            print("Anomali tespit edildi!")
        
        # İstatistikleri al
        stats = client.get_stats()
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        """
        Args:
            base_url: Mikroservis URL'i
            timeout: İstek timeout süresi (saniye)
            api_key: API anahtarı (opsiyonel)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.api_key = api_key
        self.session = requests.Session()
        
        # API key varsa header'a ekle
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
    
    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        HTTP isteği gönder
        
        Args:
            method: HTTP metodu (GET, POST, PUT, vb.)
            endpoint: API endpoint
            json_data: JSON gövdesi
            params: Query parametreleri
        
        Returns:
            API yanıtı (dict)
        
        Raises:
            requests.RequestException: İstek hatası
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"API isteği başarısız: {e}")
    
    def health_check(self) -> Dict:
        """
        Servis sağlık kontrolü
        
        Returns:
            Sağlık durumu bilgileri
        """
        return self._request("GET", "/api/v1/health")
    
    def analyze(
        self,
        sensor_type: str,
        value: float,
        unit: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> AnomalyResult:
        """
        Sensör verisini analiz et ve kaydet
        
        Args:
            sensor_type: Sensör tipi (örn: vibration)
            value: Okunan değer
            unit: Birim (örn: G)
            timestamp: Zaman damgası (ISO format, opsiyonel)
        
        Returns:
            Anomali tespit sonucu
        """
        data = {
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit
        }
        if timestamp:
            data["timestamp"] = timestamp
        
        response = self._request("POST", "/api/v1/analyze", json_data=data)
        return AnomalyResult.from_dict(response)
    
    def get_stats(self) -> Stats:
        """
        Sistem istatistiklerini al
        
        Returns:
            İstatistik bilgileri
        """
        response = self._request("GET", "/api/v1/stats")
        return Stats.from_dict(response)
    
    def get_config(self) -> Dict:
        """
        Mevcut konfigürasyonu al
        
        Returns:
            Konfigürasyon bilgileri
        """
        return self._request("GET", "/api/v1/config")
    
    def update_config(
        self,
        window_size: Optional[int] = None,
        z_score_threshold: Optional[float] = None,
        min_data_points: Optional[int] = None
    ) -> Dict:
        """
        Konfigürasyonu güncelle
        
        Args:
            window_size: Veri pencere boyutu
            z_score_threshold: Z-Score eşiği
            min_data_points: Minimum veri sayısı
        
        Returns:
            Güncellenmiş konfigürasyon
        """
        data = {}
        if window_size is not None:
            data["window_size"] = window_size
        if z_score_threshold is not None:
            data["z_score_threshold"] = z_score_threshold
        if min_data_points is not None:
            data["min_data_points"] = min_data_points
        
        return self._request("PUT", "/api/v1/config", json_data=data)
    
    def get_history(self, limit: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Veri geçmişini al
        
        Args:
            limit: Maksimum kayıt sayısı (opsiyonel)
        
        Returns:
            Geçmiş kayıtlar (sensör bazlı)
        """
        params = {}
        if limit:
            params["limit"] = limit
        
        response = self._request("GET", "/api/v1/history", params=params)
        return response.get("data", {})
    
    def reset(self) -> Dict:
        """
        Sistemi sıfırla (tüm geçmiş veriyi sil)
        
        Returns:
            Başarı mesajı
        """
        return self._request("POST", "/api/v1/reset")
    
    def is_healthy(self) -> bool:
        """
        Servis sağlıklı mı kontrol et
        
        Returns:
            True ise sağlıklı, False ise sorunlu
        """
        try:
            health = self.health_check()
            return health.get("status") == "healthy"
        except Exception:
            return False


# ============================================================================
# KONSOLİDE EDİLMİŞ ÖRNEK KULLANIM
# ============================================================================

def example_usage():
    """Örnek kullanım senaryoları"""
    
    # Client oluştur
    client = AnomalyClient("http://localhost:8000")
    
    print("=" * 60)
    print("ANOMALİ TESPİT CLIENT - ÖRNEK KULLANIM")
    print("=" * 60)
    
    # 1. Health check
    print("\n1. Servis Sağlık Kontrolü:")
    if client.is_healthy():
        print("   ✅ Servis sağlıklı ve hazır")
    else:
        print("   ❌ Servis çalışmıyor!")
        return
    
    # 2. Normal veri ekle
    print("\n2. Normal Veri Ekleme:")
    result = client.analyze("vibration", 1.2, "G")
    print(f"   Vibration: 1.2 G → Anomali: {result.is_anomaly}")
    print(f"   Z-Score: {result.z_score:.2f}")
    
    # 3. Anormal veri ekle
    print("\n3. Anormal Veri Ekleme:")
    result = client.analyze("vibration", 4.5, "G")
    print(f"   Vibration: 4.5 G → Anomali: {result.is_anomaly}")
    if result.is_anomaly:
        print(f"   ⚠️  {result.message}")
    
    # 4. İstatistikler
    print("\n4. Mevcut İstatistikler:")
    stats = client.get_stats()
    print(f"   Aktif Sensörler: {stats.total_sensors}")
    
    print("\n" + "=" * 60)
    print("✅ TÜM İŞLEMLER TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    example_usage()
