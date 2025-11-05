"""
Anomali Tespit Mikroservisi - Python Client
Kendi projenizde kullanmak için hazır client kütüphanesi

Kullanım:
    from anomaly_client import AnomalyClient
    
    client = AnomalyClient("http://localhost:8000")
    result = client.log_error(25)
    
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
    current_value: int
    mean: float
    std_dev: float
    z_score: float
    threshold: float
    message: str
    date: str
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AnomalyResult':
        """Dictionary'den AnomalyResult oluştur"""
        return cls(**data)


@dataclass
class Stats:
    """İstatistik bilgileri"""
    data_points: int
    mean: float
    std_dev: float
    min: int
    max: int
    latest: Optional[int]
    threshold: float
    window_size: int
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
        
        # Hata ekle ve kontrol et
        result = client.log_error(25)
        if result.is_anomaly:
            print("Anomali tespit edildi!")
        
        # İstatistikleri al
        stats = client.get_stats()
        print(f"Ortalama: {stats.mean}")
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
    
    def log_error(
        self,
        error_count: int,
        date: Optional[str] = None
    ) -> AnomalyResult:
        """
        Hata logu ekle ve anomali kontrolü yap
        
        Args:
            error_count: Günlük hata sayısı
            date: Tarih (ISO format, opsiyonel)
        
        Returns:
            Anomali tespit sonucu
        
        Example:
            >>> result = client.log_error(25)
            >>> if result.is_anomaly:
            ...     print(f"Anomali! Z-Score: {result.z_score}")
        """
        data = {"error_count": error_count}
        if date:
            data["date"] = date
        
        response = self._request("POST", "/api/v1/log", json_data=data)
        return AnomalyResult.from_dict(response)
    
    def detect_anomaly(
        self,
        value: int,
        date: Optional[str] = None
    ) -> AnomalyResult:
        """
        Anomali kontrolü yap (geçmişe eklenmez)
        What-if analizi için kullanılır
        
        Args:
            value: Kontrol edilecek değer
            date: Tarih (ISO format, opsiyonel)
        
        Returns:
            Anomali tespit sonucu
        
        Example:
            >>> result = client.detect_anomaly(30)
            >>> print(f"30 hata anomali mi? {result.is_anomaly}")
        """
        data = {"value": value}
        if date:
            data["date"] = date
        
        response = self._request("POST", "/api/v1/detect", json_data=data)
        return AnomalyResult.from_dict(response)
    
    def get_stats(self) -> Stats:
        """
        Sistem istatistiklerini al
        
        Returns:
            İstatistik bilgileri
        
        Example:
            >>> stats = client.get_stats()
            >>> print(f"Ortalama: {stats.mean}, Std: {stats.std_dev}")
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
        
        Example:
            >>> client.update_config(z_score_threshold=2.5)
        """
        data = {}
        if window_size is not None:
            data["window_size"] = window_size
        if z_score_threshold is not None:
            data["z_score_threshold"] = z_score_threshold
        if min_data_points is not None:
            data["min_data_points"] = min_data_points
        
        return self._request("PUT", "/api/v1/config", json_data=data)
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Veri geçmişini al
        
        Args:
            limit: Maksimum kayıt sayısı
        
        Returns:
            Geçmiş kayıtlar listesi
        
        Example:
            >>> history = client.get_history(limit=10)
            >>> for record in history:
            ...     print(f"{record['date']}: {record['error_count']}")
        """
        params = {}
        if limit:
            params["limit"] = limit
        
        response = self._request("GET", "/api/v1/history", params=params)
        return response.get("data", [])
    
    def reset(self) -> Dict:
        """
        Sistemi sıfırla (tüm geçmiş veriyi sil)
        
        Returns:
            Başarı mesajı
        
        Warning:
            Bu işlem geri alınamaz!
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
    
    def wait_until_ready(self, max_wait: int = 60) -> bool:
        """
        Servis hazır olana kadar bekle
        
        Args:
            max_wait: Maksimum bekleme süresi (saniye)
        
        Returns:
            True ise hazır, False ise timeout
        """
        import time
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                health = self.health_check()
                if health.get("ready"):
                    return True
            except Exception:
                pass
            
            time.sleep(1)
        
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
    
    # 2. İstatistikler
    print("\n2. Mevcut İstatistikler:")
    stats = client.get_stats()
    print(f"   Veri Sayısı: {stats.data_points}")
    print(f"   Ortalama: {stats.mean:.2f}")
    print(f"   Std Sapma: {stats.std_dev:.2f}")
    
    # 3. Normal hata ekle
    print("\n3. Normal Hata Ekleme:")
    result = client.log_error(18)
    print(f"   18 hata → Anomali: {result.is_anomaly}")
    print(f"   Z-Score: {result.z_score:.2f}")
    
    # 4. Anormal hata ekle
    print("\n4. Anormal Hata Ekleme:")
    result = client.log_error(35)
    print(f"   35 hata → Anomali: {result.is_anomaly}")
    if result.is_anomaly:
        print(f"   ⚠️  {result.message}")
    
    # 5. What-if analizi
    print("\n5. What-If Analizi:")
    for value in [20, 25, 30, 40]:
        result = client.detect_anomaly(value)
        status = "🔴 ANOMALİ" if result.is_anomaly else "🟢 Normal"
        print(f"   {value} hata → Z={result.z_score:5.2f} → {status}")
    
    # 6. Geçmiş
    print("\n6. Son 5 Kayıt:")
    history = client.get_history(limit=5)
    for i, record in enumerate(history, 1):
        print(f"   {i}. {record['error_count']} hata")
    
    print("\n" + "=" * 60)
    print("✅ TÜM İŞLEMLER TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    example_usage()
