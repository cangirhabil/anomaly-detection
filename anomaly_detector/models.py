"""
Veri Modelleri
Hata logları ve anomali sonuçları için veri yapıları
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ErrorLog:
    """
    Hata logu veri modeli
    
    Attributes:
        date: Hata tarihi
        error_count: Günlük hata sayısı
        timestamp: Kayıt zamanı (opsiyonel)
    """
    date: datetime
    error_count: int
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Model doğrulaması ve varsayılan değer ataması"""
        if self.error_count < 0:
            raise ValueError("error_count negatif olamaz")
        
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Dictionary'e dönüştür"""
        return {
            "date": self.date.isoformat(),
            "error_count": self.error_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class AnomalyResult:
    """
    Anomali tespit sonucu
    
    Attributes:
        is_anomaly: Anomali tespit edildi mi?
        current_value: Mevcut hata sayısı
        mean: Geçmiş verinin ortalaması
        std_dev: Standart sapma
        z_score: Hesaplanan Z-Score değeri
        threshold: Kullanılan eşik değeri
        date: Analiz tarihi
        message: Sonuç mesajı
    """
    is_anomaly: bool
    current_value: int
    mean: float
    std_dev: float
    z_score: float
    threshold: float
    date: datetime
    message: str = ""
    
    def __post_init__(self):
        """Mesaj oluştur"""
        if not self.message:
            if self.is_anomaly:
                self.message = (
                    f"⚠️ ANOMALİ TESPİT EDİLDİ! "
                    f"Hata sayısı: {self.current_value}, "
                    f"Beklenen: {self.mean:.2f} ± {self.std_dev:.2f}, "
                    f"Z-Score: {self.z_score:.2f}"
                )
            else:
                self.message = (
                    f"✓ Normal davranış. "
                    f"Hata sayısı: {self.current_value}, "
                    f"Z-Score: {self.z_score:.2f}"
                )
    
    def to_dict(self) -> dict:
        """Dictionary'e dönüştür"""
        return {
            "is_anomaly": self.is_anomaly,
            "current_value": self.current_value,
            "mean": round(self.mean, 2),
            "std_dev": round(self.std_dev, 2),
            "z_score": round(self.z_score, 2),
            "threshold": self.threshold,
            "date": self.date.isoformat(),
            "message": self.message
        }
    
    def __str__(self) -> str:
        """Kullanıcı dostu string formatı"""
        return self.message
