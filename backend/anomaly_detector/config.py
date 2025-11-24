"""
Anomali Tespit Konfigürasyon Modülü
Sistem parametrelerini ve eşik değerlerini yönetir
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AnomalyConfig:
    """
    Anomali tespit sistemi için konfigürasyon sınıfı
    
    Attributes:
        window_size: Geçmiş veri pencere boyutu (gün cinsinden)
        z_score_threshold: Z-Score eşik değeri (standart: 2.0 veya 3.0)
        min_data_points: Anomali tespiti için minimum veri noktası sayısı
        alert_message: Anomali tespit edildiğinde gösterilecek mesaj
    """
    window_size: int = 30  # Son 30 gün
    z_score_threshold: float = 2.0  # 95% güven aralığı için 2.0, 99.7% için 3.0
    min_data_points: int = 7  # İstatistik hesaplamak için minimum veri
    min_training_size: int = 20 # Alarm üretmeye başlamak için minimum veri (Eğitim süresi)
    alert_message: str = "⚠️ ANOMALİ TESPİT EDİLDİ!"
    sensors: dict = None
    
    def __post_init__(self):
        """Konfigürasyon değerlerini doğrula"""
        if self.sensors is None:
            self.sensors = {}

        if self.window_size < 1:
            raise ValueError("window_size en az 1 olmalıdır")
        
        if self.z_score_threshold <= 0:
            raise ValueError("z_score_threshold pozitif olmalıdır")
        
        if self.min_data_points < 2:
            raise ValueError("min_data_points en az 2 olmalıdır")
            
        if self.min_training_size < self.min_data_points:
            raise ValueError("min_training_size, min_data_points'ten küçük olamaz")
        
        if self.min_data_points > self.window_size:
            raise ValueError("min_data_points, window_size'dan büyük olamaz")
    
    def to_dict(self) -> dict:
        """Konfigürasyonu dictionary'e dönüştür"""
        return {
            "window_size": self.window_size,
            "z_score_threshold": self.z_score_threshold,
            "min_data_points": self.min_data_points,
            "min_training_size": self.min_training_size,
            "sensors": self.sensors,
            "alert_message": self.alert_message
        }
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'AnomalyConfig':
        """Dictionary'den konfigürasyon oluştur"""
        return cls(**config_dict)
    
    @classmethod
    def conservative(cls) -> 'AnomalyConfig':
        """
        Konservatif konfigürasyon (daha az alarm)
        99.7% güven aralığı - sadece çok aşırı sapmalarda alarm
        """
        return cls(z_score_threshold=3.0)
    
    @classmethod
    def sensitive(cls) -> 'AnomalyConfig':
        """
        Hassas konfigürasyon (daha fazla alarm)
        90% güven aralığı - küçük sapmalarda bile alarm
        """
        return cls(z_score_threshold=1.645)
    
    @classmethod
    def balanced(cls) -> 'AnomalyConfig':
        """
        Dengeli konfigürasyon (standart)
        95% güven aralığı - dengeli yaklaşım
        """
        return cls(z_score_threshold=2.0)
