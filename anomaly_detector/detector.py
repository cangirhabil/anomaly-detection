"""
Anomali Tespit Motoru
Z-Score tabanlı istatistiksel anomali tespit sistemi
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from collections import deque

from .config import AnomalyConfig
from .models import ErrorLog, AnomalyResult


class AnomalyDetector:
    """
    Z-Score yöntemi ile anomali tespiti yapan ana sınıf
    
    Bu sınıf, günlük hata sayılarını izler ve istatistiksel olarak
    beklenen aralığın dışında kalan değerleri tespit eder.
    
    Çalışma Prensibi:
    1. Son N günün hata verisi tutulur (varsayılan: 30 gün)
    2. Her yeni veri için ortalama ve standart sapma hesaplanır
    3. Z-Score = (X - μ) / σ formülü ile sapma ölçülür
    4. Z-Score > eşik ise anomali kabul edilir
    
    Attributes:
        config: Anomali tespit konfigürasyonu
        error_history: Hata geçmişi (deque ile sınırlı boyut)
    """
    
    def __init__(self, config: Optional[AnomalyConfig] = None):
        """
        Anomali tespit sistemi başlatıcı
        
        Args:
            config: Konfigürasyon objesi (None ise varsayılan kullanılır)
        """
        self.config = config or AnomalyConfig()
        self.error_history: deque[ErrorLog] = deque(maxlen=self.config.window_size)
    
    def add_error_log(self, error_count: int, date: Optional[datetime] = None) -> AnomalyResult:
        """
        Yeni hata logu ekle ve anomali kontrolü yap
        
        Args:
            error_count: Günlük hata sayısı
            date: Hata tarihi (None ise bugün)
        
        Returns:
            AnomalyResult: Anomali tespit sonucu
        """
        if date is None:
            date = datetime.now()
        
        # Yeni hata logu oluştur
        error_log = ErrorLog(date=date, error_count=error_count)
        
        # Anomali kontrolü yap (geçmiş verilere göre)
        result = self.detect_anomaly(error_count, date)
        
        # Geçmişe ekle (kontrol sonrasında ekleniyor ki mevcut veri analizi etkilemesin)
        self.error_history.append(error_log)
        
        return result
    
    def detect_anomaly(self, current_value: int, date: Optional[datetime] = None) -> AnomalyResult:
        """
        Mevcut değer için anomali tespiti yap
        
        Args:
            current_value: Kontrol edilecek hata sayısı
            date: Analiz tarihi
        
        Returns:
            AnomalyResult: Anomali tespit sonucu
        """
        if date is None:
            date = datetime.now()
        
        # Yeterli veri yoksa anomali yok
        if len(self.error_history) < self.config.min_data_points:
            return AnomalyResult(
                is_anomaly=False,
                current_value=current_value,
                mean=current_value,
                std_dev=0.0,
                z_score=0.0,
                threshold=self.config.z_score_threshold,
                date=date,
                message=f"⚡ Yetersiz veri: {len(self.error_history)}/{self.config.min_data_points} - Normal kabul edildi"
            )
        
        # İstatistiksel değerleri hesapla
        mean, std_dev = self._calculate_statistics()
        
        # Z-Score hesapla
        z_score = self._calculate_z_score(current_value, mean, std_dev)
        
        # Anomali kontrolü
        is_anomaly = abs(z_score) > self.config.z_score_threshold
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            current_value=current_value,
            mean=mean,
            std_dev=std_dev,
            z_score=z_score,
            threshold=self.config.z_score_threshold,
            date=date
        )
    
    def _calculate_statistics(self) -> Tuple[float, float]:
        """
        Geçmiş verilerden istatistiksel değerleri hesapla
        
        Returns:
            Tuple[float, float]: (ortalama, standart sapma)
        """
        error_counts = [log.error_count for log in self.error_history]
        
        mean = np.mean(error_counts)
        std_dev = np.std(error_counts, ddof=1)  # Örnek standart sapma (n-1)
        
        # Standart sapma 0 ise küçük bir değer kullan (bölme hatasını önle)
        if std_dev == 0:
            std_dev = 1e-10
        
        return float(mean), float(std_dev)
    
    def _calculate_z_score(self, value: int, mean: float, std_dev: float) -> float:
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
        Mevcut istatistiklerin özetini al
        
        Returns:
            dict: İstatistik özet bilgileri
        """
        if len(self.error_history) == 0:
            return {
                "data_points": 0,
                "mean": 0.0,
                "std_dev": 0.0,
                "min": 0,
                "max": 0,
                "latest": None
            }
        
        error_counts = [log.error_count for log in self.error_history]
        mean, std_dev = self._calculate_statistics()
        
        return {
            "data_points": len(self.error_history),
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "min": min(error_counts),
            "max": max(error_counts),
            "latest": error_counts[-1] if error_counts else None,
            "threshold": self.config.z_score_threshold,
            "window_size": self.config.window_size
        }
    
    def get_history_dataframe(self) -> pd.DataFrame:
        """
        Hata geçmişini pandas DataFrame olarak al
        
        Returns:
            pd.DataFrame: Hata geçmişi
        """
        if len(self.error_history) == 0:
            return pd.DataFrame(columns=["date", "error_count"])
        
        data = [
            {"date": log.date, "error_count": log.error_count}
            for log in self.error_history
        ]
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def load_historical_data(self, data: List[Tuple[datetime, int]]):
        """
        Geçmiş veriyi toplu yükle
        
        Args:
            data: (tarih, hata_sayısı) tuple listesi
        """
        for date, error_count in data:
            error_log = ErrorLog(date=date, error_count=error_count)
            self.error_history.append(error_log)
    
    def clear_history(self):
        """Tüm geçmiş veriyi temizle"""
        self.error_history.clear()
    
    def export_history(self) -> List[dict]:
        """
        Geçmişi JSON formatında dışa aktar
        
        Returns:
            List[dict]: Hata geçmişi
        """
        return [log.to_dict() for log in self.error_history]
