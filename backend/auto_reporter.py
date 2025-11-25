"""
Otomatik Anomali Raporlama Modülü
Akıllı karar mekanizması ile anomalileri değerlendirir ve gerektiğinde rapor gönderir

Karar Kriterleri:
1. Risk Seviyesi (CRITICAL/HIGH öncelikli)
2. Anomali Yoğunluğu (belirli sürede kaç anomali)
3. Sensör Çeşitliliği (farklı sensörlerde aynı anda anomali)
4. Cooldown Süresi (spam koruması)
5. Çalışma Saatleri (isteğe bağlı)

Profesyonel Karar Mekanizması:
- Score-based decision system
- Multiple trigger conditions
- Smart cooldown per risk level
- Rate limiting protection
"""

import os
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ReportingConfig:
    """Otomatik raporlama konfigürasyonu"""
    enabled: bool = True
    
    # Karar Eşikleri
    min_anomalies_for_report: int = 3  # Rapor için minimum anomali sayısı
    anomaly_window_minutes: int = 5     # Bu süre içindeki anomaliler değerlendirilir
    
    # Risk Bazlı Tetikleyiciler
    instant_report_on_critical: bool = True   # CRITICAL anomali anında rapor
    instant_report_on_high: bool = False       # HIGH anomali anında rapor
    min_high_anomalies: int = 3               # HIGH için minimum sayı
    min_medium_anomalies: int = 5             # MEDIUM için minimum sayı
    
    # Sensör Çeşitliliği
    multi_sensor_threshold: int = 2           # Farklı sensör sayısı eşiği
    
    # Cooldown (Spam Koruması)
    cooldown_minutes: int = 15                # Aynı seviye için bekleme süresi
    critical_cooldown_minutes: int = 5        # CRITICAL için daha kısa cooldown
    
    # Çalışma Saatleri (isteğe bağlı)
    working_hours_only: bool = False
    working_hours_start: int = 8              # Saat
    working_hours_end: int = 18               # Saat
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportingConfig':
        """Dictionary'den oluştur"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'e dönüştür"""
        return {
            "enabled": self.enabled,
            "min_anomalies_for_report": self.min_anomalies_for_report,
            "anomaly_window_minutes": self.anomaly_window_minutes,
            "instant_report_on_critical": self.instant_report_on_critical,
            "instant_report_on_high": self.instant_report_on_high,
            "min_high_anomalies": self.min_high_anomalies,
            "min_medium_anomalies": self.min_medium_anomalies,
            "multi_sensor_threshold": self.multi_sensor_threshold,
            "cooldown_minutes": self.cooldown_minutes,
            "critical_cooldown_minutes": self.critical_cooldown_minutes,
            "working_hours_only": self.working_hours_only,
            "working_hours_start": self.working_hours_start,
            "working_hours_end": self.working_hours_end,
        }


@dataclass
class ReportDecision:
    """Rapor gönderim kararı"""
    should_report: bool
    reason: str
    risk_level: str
    anomaly_count: int
    affected_sensors: List[str]
    trigger_type: str  # "critical", "high_count", "multi_sensor", "accumulated"


class AutoReporter:
    """
    Otomatik anomali raporlama yöneticisi
    
    Akıllı karar mekanizması ile anomalileri değerlendirir:
    - Her anomali geldiğinde değerlendirme yapar
    - Eşik aşıldığında otomatik rapor oluşturup mail gönderir
    - Spam koruması ile gereksiz mailleri engeller
    
    Profesyonel Score-Based Decision System:
    - Her anomali için risk puanı hesaplar
    - Birikimli puan eşiği aşılırsa rapor tetikler
    - Akıllı cooldown yönetimi
    """
    
    # Risk seviyesi ağırlıkları (puanlama için)
    SEVERITY_WEIGHTS = {
        "CRITICAL": 10,
        "HIGH": 5,
        "MEDIUM": 2,
        "LOW": 1
    }
    
    def __init__(self, config: Optional[ReportingConfig] = None):
        self.config = config or ReportingConfig()
        
        # Anomali tamponu (son X dakikadaki anomaliler)
        self.anomaly_buffer: deque = deque(maxlen=1000)
        
        # Risk score tracking
        self.current_score: float = 0.0
        self.score_threshold: float = 15.0  # Bu puanı aşınca rapor gönder
        
        # Son rapor zamanları (risk seviyesine göre)
        self.last_report_times: Dict[str, datetime] = {
            "CRITICAL": datetime.min,
            "HIGH": datetime.min,
            "MEDIUM": datetime.min,
            "LOW": datetime.min
        }
        
        # İstatistikler
        self.stats = {
            "total_anomalies_processed": 0,
            "reports_sent": 0,
            "reports_skipped_cooldown": 0,
            "reports_skipped_threshold": 0,
            "last_report_sent": None,
            "current_score": 0.0
        }
        
        # Callback fonksiyonu
        self._on_report_needed: Optional[Callable] = None
        
        # Event loop reference (for async callback)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Pending report flag (to avoid duplicate reports)
        self._report_pending = False
        
        logger.info(f"AutoReporter başlatıldı: enabled={self.config.enabled}")
    
    def set_report_callback(self, callback: Callable):
        """
        Rapor gönderilmesi gerektiğinde çağrılacak callback'i ayarla
        
        callback(anomalies: List[Dict], decision: ReportDecision) -> None
        """
        self._on_report_needed = callback
        logger.info("AutoReporter callback ayarlandı")
    
    def _calculate_anomaly_score(self, anomaly: Dict[str, Any]) -> float:
        """
        Tek bir anomali için risk puanı hesapla
        
        Faktörler:
        - Z-Score büyüklüğü
        - Severity seviyesi
        - Sensör kritikliği
        """
        score = 0.0
        
        # Z-Score bazlı puan (ne kadar yüksekse o kadar kritik)
        z_score = abs(anomaly.get("z_score", 0))
        if z_score > 4:
            score += 8  # Çok yüksek sapma
        elif z_score > 3.5:
            score += 5
        elif z_score > 3:
            score += 3
        elif z_score > 2.5:
            score += 2
        else:
            score += 1
        
        # Severity bazlı puan
        severity = anomaly.get("severity", "MEDIUM").upper()
        if severity == "HIGH":
            score += 3
        elif severity == "MEDIUM":
            score += 1
        
        return score
    
    def add_anomaly(self, anomaly: Dict[str, Any]) -> Optional[ReportDecision]:
        """
        Yeni anomali ekle ve rapor gerekip gerekmediğine karar ver
        
        Thread-safe implementation - callback işi app.py'de yapılır.
        
        Args:
            anomaly: Anomali verisi (is_anomaly, sensor_type, z_score, severity, timestamp, etc.)
        
        Returns:
            ReportDecision: Rapor gönderilecekse karar detayları, değilse None
        """
        if not anomaly.get("is_anomaly", False):
            return None
        
        if not self.config.enabled:
            return None
        
        with self._lock:
            self.stats["total_anomalies_processed"] += 1
            
            # Zaman damgası ekle
            now = datetime.now()
            if "timestamp" not in anomaly:
                anomaly["timestamp"] = now.isoformat()
            
            # Tampona ekle
            self.anomaly_buffer.append({
                **anomaly,
                "added_at": now
            })
            
            # Anomali puanını hesapla ve ekle
            anomaly_score = self._calculate_anomaly_score(anomaly)
            self.current_score += anomaly_score
            self.stats["current_score"] = self.current_score
            
            logger.debug(f"Anomali eklendi: score={anomaly_score:.1f}, total={self.current_score:.1f}")
            
            # Karar mekanizmasını çalıştır
            decision = self._evaluate()
            
            if decision and decision.should_report:
                # Cooldown kontrolü
                if self._check_cooldown(decision.risk_level):
                    self.stats["reports_skipped_cooldown"] += 1
                    logger.info(f"⏳ Rapor cooldown nedeniyle atlandı: {decision.risk_level}")
                    return None
                
                # Çalışma saati kontrolü
                if not self._check_working_hours():
                    logger.info("⏰ Rapor çalışma saatleri dışında, beklemeye alındı")
                    return None
                
                # Duplicate prevention
                if self._report_pending:
                    logger.debug("Rapor zaten beklemede, atlanıyor")
                    return None
                
                self._report_pending = True
                
                logger.warning(f"📧 Rapor kararı döndürülüyor: {decision.reason}")
                logger.warning(f"   Risk: {decision.risk_level}, Anomali: {decision.anomaly_count}, Sensörler: {decision.affected_sensors}")
                
                # Kararı döndür - callback işi app.py'de yapılacak
                return decision
            
            return None
    
    def _evaluate(self) -> Optional[ReportDecision]:
        """
        Mevcut anomali durumunu değerlendir ve karar ver
        
        Profesyonel karar mekanizması:
        1. Minimum anomali sayısı kontrolü (tüm kararlar için geçerli)
        2. Kritik anomali kontrolü (anında tetikleme)
        3. Çoklu sensör kontrolü (korelasyon)
        4. Birikimli skor kontrolü
        5. Zaman penceresi değerlendirmesi
        """
        now = datetime.now()
        window_start = now - timedelta(minutes=self.config.anomaly_window_minutes)
        
        # Son X dakikadaki anomalileri filtrele
        recent_anomalies = [
            a for a in self.anomaly_buffer 
            if a.get("added_at", datetime.min) >= window_start
        ]
        
        if not recent_anomalies:
            return None
        
        # İstatistikleri hesapla
        total_count = len(recent_anomalies)
        
        # ===== ÖN KONTROL: MİNİMUM ANOMALİ SAYISI =====
        # Tüm kararlar için minimum anomali sayısı gerekli
        if total_count < self.config.min_anomalies_for_report:
            logger.debug(f"Yeterli anomali yok: {total_count}/{self.config.min_anomalies_for_report}")
            return None
        
        # Z-Score analizi
        z_scores = [abs(a.get("z_score", 0)) for a in recent_anomalies]
        max_z_score = max(z_scores) if z_scores else 0
        avg_z_score = sum(z_scores) / len(z_scores) if z_scores else 0
        
        # Severity analizi
        high_count = sum(1 for a in recent_anomalies if a.get("severity", "").upper() == "HIGH")
        critical_count = sum(1 for a in recent_anomalies if max_z_score > 4)
        
        # Etkilenen sensörleri bul
        affected_sensors = list(set(a.get("sensor_type", "unknown") for a in recent_anomalies))
        
        # ===== KARAR 1: KRİTİK ANOMALİ (Anında Rapor) =====
        if self.config.instant_report_on_critical and max_z_score > 4:
            logger.warning(f"🚨 KRİTİK anomali tespit edildi! Z-Score: {max_z_score:.2f}")
            return ReportDecision(
                should_report=True,
                reason=f"KRİTİK anomali tespit edildi! Z-Score: {max_z_score:.2f} (eşik: 4.0)",
                risk_level="CRITICAL",
                anomaly_count=total_count,
                affected_sensors=affected_sensors,
                trigger_type="critical"
            )
        
        # ===== KARAR 2: ÇOKLU SENSÖR KORELASYONU =====
        if len(affected_sensors) >= self.config.multi_sensor_threshold:
            # Farklı sensörlerde eş zamanlı anomali = sistemik sorun
            logger.warning(f"⚠️ Çoklu sensör anomalisi: {len(affected_sensors)} sensör etkilendi")
            return ReportDecision(
                should_report=True,
                reason=f"Sistemik anomali: {len(affected_sensors)} farklı sensörde eş zamanlı sapma",
                risk_level="HIGH",
                anomaly_count=total_count,
                affected_sensors=affected_sensors,
                trigger_type="multi_sensor"
            )
        
        # ===== KARAR 3: YÜKSEK ŞİDDETLİ ANOMALİ BİRİKİMİ =====
        if self.config.instant_report_on_high and high_count >= self.config.min_high_anomalies:
            logger.warning(f"⚠️ Yüksek şiddetli anomali birikimi: {high_count} adet")
            return ReportDecision(
                should_report=True,
                reason=f"{high_count} adet yüksek şiddetli anomali ({self.config.anomaly_window_minutes} dakika içinde)",
                risk_level="HIGH",
                anomaly_count=total_count,
                affected_sensors=affected_sensors,
                trigger_type="high_count"
            )
        
        # ===== KARAR 4: BİRİKİMLİ SKOR KONTROLÜ =====
        if self.current_score >= self.score_threshold:
            # Risk seviyesini belirle
            if avg_z_score > 3.5:
                risk = "HIGH"
            elif avg_z_score > 2.5:
                risk = "MEDIUM"
            else:
                risk = "LOW"
            
            logger.info(f"📊 Skor eşiği aşıldı: {self.current_score:.1f} >= {self.score_threshold}")
            return ReportDecision(
                should_report=True,
                reason=f"Anomali skoru eşiği aşıldı: {self.current_score:.1f} puan ({total_count} anomali)",
                risk_level=risk,
                anomaly_count=total_count,
                affected_sensors=affected_sensors,
                trigger_type="accumulated"
            )
        
        # ===== KARAR 5: MİNİMUM ANOMALİ SAYISI =====
        if total_count >= self.config.min_anomalies_for_report:
            # Ek kontrol: ortalama Z-score yeterince yüksek mi?
            if avg_z_score >= 2.5:
                risk = "HIGH" if high_count > total_count * 0.3 else "MEDIUM"
                logger.info(f"📈 Minimum anomali sayısı aşıldı: {total_count}")
                return ReportDecision(
                    should_report=True,
                    reason=f"Son {self.config.anomaly_window_minutes} dakikada {total_count} anomali (ort. Z-Score: {avg_z_score:.2f})",
                    risk_level=risk,
                    anomaly_count=total_count,
                    affected_sensors=affected_sensors,
                    trigger_type="count_threshold"
                )
        
        return None
    
    def _check_cooldown(self, risk_level: str) -> bool:
        """Cooldown süresinde mi kontrol et"""
        now = datetime.now()
        last_report = self.last_report_times.get(risk_level, datetime.min)
        
        if risk_level == "CRITICAL":
            cooldown = timedelta(minutes=self.config.critical_cooldown_minutes)
        else:
            cooldown = timedelta(minutes=self.config.cooldown_minutes)
        
        in_cooldown = (now - last_report) < cooldown
        
        if in_cooldown:
            remaining = cooldown - (now - last_report)
            logger.debug(f"Cooldown aktif: {risk_level}, kalan: {remaining}")
        
        return in_cooldown
    
    def _check_working_hours(self) -> bool:
        """Çalışma saatleri kontrolü"""
        if not self.config.working_hours_only:
            return True
        
        now = datetime.now()
        current_hour = now.hour
        
        return self.config.working_hours_start <= current_hour < self.config.working_hours_end
    
    def mark_report_triggered(self, decision: ReportDecision):
        """
        Rapor tetiklendi olarak işaretle - app.py'den çağrılır
        
        Bu metod callback çağırma işini yapmaz, sadece istatistikleri günceller.
        Callback işi app.py'de yapılır.
        """
        now = datetime.now()
        
        # Son rapor zamanını güncelle
        self.last_report_times[decision.risk_level] = now
        self.stats["reports_sent"] += 1
        self.stats["last_report_sent"] = now.isoformat()
        
        # Skoru sıfırla
        self.current_score = 0.0
        self.stats["current_score"] = 0.0
        
        # Pending bayrağını temizle
        self._report_pending = False
        
        logger.info(f"📊 Rapor istatistikleri güncellendi: {decision.risk_level}")
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri getir"""
        return {
            **self.stats,
            "buffer_size": len(self.anomaly_buffer),
            "config": self.config.to_dict(),
            "score_threshold": self.score_threshold
        }
    
    def update_config(self, **kwargs):
        """Konfigürasyonu güncelle"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        logger.info(f"AutoReporter config güncellendi: enabled={self.config.enabled}")
    
    def clear_buffer(self):
        """Anomali tamponunu temizle"""
        with self._lock:
            self.anomaly_buffer.clear()
            self.current_score = 0.0
            self.stats["current_score"] = 0.0
        logger.info("Anomali tamponu temizlendi")
    
    def reset_score(self):
        """Risk skorunu sıfırla"""
        with self._lock:
            self.current_score = 0.0
            self.stats["current_score"] = 0.0
        logger.info("Risk skoru sıfırlandı")


# Singleton instance
_auto_reporter: Optional[AutoReporter] = None


def get_auto_reporter() -> AutoReporter:
    """Global AutoReporter instance'ını getir veya oluştur"""
    global _auto_reporter
    if _auto_reporter is None:
        # Config dosyasından yükle
        config = ReportingConfig()
        try:
            if os.path.exists("config.yaml"):
                with open("config.yaml", "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f) or {}
                    auto_report_config = yaml_config.get("auto_reporting", {})
                    if auto_report_config:
                        config = ReportingConfig.from_dict(auto_report_config)
        except Exception as e:
            logger.error(f"Config yükleme hatası: {e}")
        
        _auto_reporter = AutoReporter(config)
    return _auto_reporter


def configure_auto_reporter(config: ReportingConfig) -> AutoReporter:
    """AutoReporter'ı yapılandır"""
    global _auto_reporter
    _auto_reporter = AutoReporter(config)
    return _auto_reporter
