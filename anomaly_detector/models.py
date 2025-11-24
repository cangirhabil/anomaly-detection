"""
Veri Modelleri
Hata logları ve anomali sonuçları için veri yapıları
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SensorReading:
    """
    Sensör okuma veri modeli
    
    Attributes:
        sensor_type: Sensör tipi (örn: vibration, temperature)
        value: Okunan değer
        timestamp: Okuma zamanı (opsiyonel)
        unit: Ölçü birimi (opsiyonel)
    """
    sensor_type: str
    value: float
    timestamp: Optional[datetime] = None
    unit: Optional[str] = None
    
    def __post_init__(self):
        """Model doğrulaması ve varsayılan değer ataması"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Dictionary'e dönüştür"""
        return {
            "sensor_type": self.sensor_type,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "unit": self.unit
        }


@dataclass
class AnomalyResult:
    """
    Anomali tespit sonucu
    
    Attributes:
        is_anomaly: Anomali tespit edildi mi?
        sensor_type: Sensör tipi
        current_value: Mevcut değer
        mean: Geçmiş verinin ortalaması
        std_dev: Standart sapma
        z_score: Hesaplanan Z-Score değeri
        threshold: Kullanılan eşik değeri
        timestamp: Analiz zamanı
        severity: Şiddet (Normal, Low, Medium, High)
        message: Sonuç mesajı
    """
    is_anomaly: bool
    sensor_type: str
    current_value: float
    mean: float
    std_dev: float
    z_score: float
    threshold: float
    timestamp: datetime
    severity: str = "Normal"
    system_status: str = "Active" # Initializing, Learning, Active
    message: str = ""
    
    def __post_init__(self):
        """Mesaj oluştur"""
        if not self.message:
            if self.system_status == "Initializing":
                self.message = f"⏳ Sistem başlatılıyor... [{self.sensor_type}]"
            elif self.system_status == "Learning":
                self.message = f"🧠 Sistem öğreniyor... [{self.sensor_type}] ({self.current_value})"
            elif self.is_anomaly:
                self.message = (
                    f"⚠️ ANOMALİ TESPİT EDİLDİ! [{self.sensor_type}] "
                    f"Değer: {self.current_value}, "
                    f"Beklenen: {self.mean:.2f} ± {self.std_dev:.2f}, "
                    f"Z-Score: {self.z_score:.2f}"
                )
            else:
                self.message = (
                    f"✓ Normal davranış. [{self.sensor_type}] "
                    f"Değer: {self.current_value}, "
                    f"Z-Score: {self.z_score:.2f}"
                )
    
    def to_dict(self) -> dict:
        """Dictionary'e dönüştür"""
        return {
            "is_anomaly": self.is_anomaly,
            "sensor_type": self.sensor_type,
            "current_value": self.current_value,
            "mean": round(self.mean, 2),
            "std_dev": round(self.std_dev, 2),
            "z_score": round(self.z_score, 2),
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "system_status": self.system_status,
            "message": self.message
        }
    
    def __str__(self) -> str:
        """Kullanıcı dostu string formatı"""
        return self.message
