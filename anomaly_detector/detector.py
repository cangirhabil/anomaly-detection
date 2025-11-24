"""
Anomali Tespit Motoru
Z-Score tabanlı istatistiksel anomali tespit sistemi
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from collections import deque

from .config import AnomalyConfig
from .models import SensorReading, AnomalyResult
from collections import defaultdict


class AnomalyDetector:
    """
    Z-Score yöntemi ile çoklu sensör anomali tespiti yapan ana sınıf
    
    Bu sınıf, sensör verilerini izler ve istatistiksel olarak
    beklenen aralığın dışında kalan değerleri tespit eder.
    
    Çalışma Prensibi:
    1. Her sensör tipi için son N veri tutulur
    2. Her yeni veri için o sensör tipine ait ortalama ve standart sapma hesaplanır
    3. Z-Score = (X - μ) / σ formülü ile sapma ölçülür
    4. Z-Score > eşik ise anomali kabul edilir
    
    Attributes:
        config: Anomali tespit konfigürasyonu
        history: Sensör geçmişi (sensor_type -> deque)
    """
    
    def __init__(self, config: Optional[AnomalyConfig] = None):
        """
        Anomali tespit sistemi başlatıcı
        
        Args:
            config: Konfigürasyon objesi (None ise varsayılan kullanılır)
        """
        self.config = config or AnomalyConfig()
        # Her sensör tipi için ayrı bir deque tutuyoruz
        self.history = defaultdict(lambda: deque(maxlen=self.config.window_size))
    
    def add_reading(self, reading: SensorReading) -> AnomalyResult:
        """
        Yeni sensör verisi ekle ve anomali kontrolü yap
        
        Args:
            reading: Sensör okuma verisi
        
        Returns:
            AnomalyResult: Anomali tespit sonucu
        """
        # Anomali kontrolü yap (geçmiş verilere göre)
        result = self.detect(reading)
        
        # Geçmişe ekle (kontrol sonrasında ekleniyor ki mevcut veri analizi etkilemesin)
        self.history[reading.sensor_type].append(reading)
        
        return result
    
    def detect(self, reading: SensorReading) -> AnomalyResult:
        """
        Mevcut değer için anomali tespiti yap
        
        Args:
            reading: Sensör okuma verisi
        
        Returns:
            AnomalyResult: Anomali tespit sonucu
        """
        sensor_history = self.history[reading.sensor_type]
        
        # Sensör bazlı konfigürasyonları al
        sensor_config = self.config.sensors.get(reading.sensor_type, {})
        threshold = sensor_config.get('threshold', self.config.z_score_threshold)
        min_training_size = sensor_config.get('min_training_size', self.config.min_training_size)
        
        # Yeterli veri yoksa anomali yok
        if len(sensor_history) < self.config.min_data_points:
            return AnomalyResult(
                is_anomaly=False,
                sensor_type=reading.sensor_type,
                current_value=reading.value,
                mean=reading.value,
                std_dev=0.0,
                z_score=0.0,
                threshold=threshold,
                timestamp=reading.timestamp or datetime.now(),
                severity="Normal",
                system_status="Initializing",
                message=f"⚡ Yetersiz veri ({reading.sensor_type}): {len(sensor_history)}/{self.config.min_data_points}",
                window_size=len(sensor_history)
            )
        
        # İstatistiksel değerleri hesapla
        mean, std_dev = self._calculate_statistics(reading.sensor_type)
        
        # Z-Score hesapla
        z_score = self._calculate_z_score(reading.value, mean, std_dev)
        
        # Sistem durumu kontrolü (Eğitim vs Aktif)
        system_status = "Active"
        if len(sensor_history) < min_training_size:
            system_status = "Learning"
            # Eğitim modunda anomali tespiti yapılmaz (veya sadece loglanır ama alarm verilmez)
            is_anomaly = False
            severity = "Normal"
        else:
            # Anomali kontrolü
            is_anomaly = abs(z_score) > threshold
            
            # Şiddet belirle
            severity = "Normal"
            if is_anomaly:
                if abs(z_score) > threshold * 1.5: severity = "High"
                elif abs(z_score) > threshold: severity = "Medium"
                else: severity = "Low"
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            sensor_type=reading.sensor_type,
            current_value=reading.value,
            mean=mean,
            std_dev=std_dev,
            z_score=z_score,
            threshold=threshold,
            timestamp=reading.timestamp or datetime.now(),
            severity=severity,
            system_status=system_status,
            window_size=len(sensor_history)
        )
    
    def _calculate_statistics(self, sensor_type: str) -> Tuple[float, float]:
        """
        Geçmiş verilerden istatistiksel değerleri hesapla
        
        Returns:
            Tuple[float, float]: (ortalama, standart sapma)
        """
        readings = [r.value for r in self.history[sensor_type]]
        
        if not readings:
            return 0.0, 0.0
            
        mean = np.mean(readings)
        std_dev = np.std(readings, ddof=1)  # Örnek standart sapma (n-1)
        
        # Standart sapma 0 ise küçük bir değer kullan (bölme hatasını önle)
        if std_dev == 0:
            std_dev = 1e-10
        
        return float(mean), float(std_dev)
    
    def _calculate_z_score(self, value: float, mean: float, std_dev: float) -> float:
        """
        Z-Score hesapla
        
        Z-Score = (X - μ) / σ
        
        Args:
            value: Kontrol edilecek değer
            mean: Ortalama (μ)
            std_dev: Standart sapma (σ)
        
        Returns:
            float: Z-Score değeri
        """
        return (value - mean) / std_dev
    
    def get_statistics_summary(self) -> dict:
        """
        Mevcut istatistiklerin özetini al (Tüm sensörler için)
        
        Returns:
            dict: İstatistik özet bilgileri
        """
        summary = {
            "total_sensors": len(self.history),
            "sensors": {}
        }
        
        for sensor_type, readings in self.history.items():
            if not readings:
                continue
                
            values = [r.value for r in readings]
            mean = np.mean(values)
            std_dev = np.std(values, ddof=1) if len(values) > 1 else 0.0
            
            summary["sensors"][sensor_type] = {
                "data_points": len(readings),
                "mean": round(float(mean), 2),
                "std_dev": round(float(std_dev), 2),
                "min": min(values),
                "max": max(values),
                "latest": values[-1]
            }
            
        return summary
    
    def clear_history(self):
        """Tüm geçmiş veriyi temizle"""
        self.history.clear()
    
    def export_history(self) -> Dict[str, List[dict]]:
        """
        Geçmişi JSON formatında dışa aktar
        
        Returns:
            Dict[str, List[dict]]: Sensör bazlı geçmiş
        """
        export = {}
        for sensor_type, readings in self.history.items():
            export[sensor_type] = [r.to_dict() for r in readings]
        return export
