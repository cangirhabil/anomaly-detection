"""
Profesyonel Otomatik Raporlama Modülü - State-Based & Adaptive Threshold

Bu modül endüstriyel standartlarda bir State-Based (Durum Bazlı) ve 
Adaptive Threshold (Dinamik Eşik) sistemi implementasyonu içerir.

Temel Özellikler:
1. SystemState Enum: NORMAL, WARNING, CRITICAL durumları
2. Leaky Bucket Algorithm: Puan biriktirme ve zamanla sızdırma
3. Adaptive Threshold: Ortama göre dinamik eşik belirleme
4. State Transition: Durum geçişlerinde rapor tetikleme

Profesyonel Karar Mekanizması:
- Her anomali için severity'e göre puan eklenir (Leaky Bucket)
- Puan zamanla sızar (decay), sistem normal duruma dönebilir
- Puan eşikleri dinamik olarak hesaplanır (Adaptive Threshold)
- Sadece durum değişikliklerinde rapor gönderilir (State Transition)
- Spam koruması için state bazlı cooldown uygulanır
"""

import os
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import yaml
import time

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """Sistem durumu enum'u - Endüstriyel standart seviyeler"""
    NORMAL = "NORMAL"
    WARNING = "WARNING" 
    CRITICAL = "CRITICAL"
    
    def __str__(self):
        return self.value
    
    @property
    def severity_order(self) -> int:
        """Durum önem sırası (düşükten yükseğe)"""
        return {
            SystemState.NORMAL: 0,
            SystemState.WARNING: 1,
            SystemState.CRITICAL: 2
        }[self]
    
    @property
    def turkish_label(self) -> str:
        """Türkçe etiket"""
        return {
            SystemState.NORMAL: "NORMAL",
            SystemState.WARNING: "UYARI",
            SystemState.CRITICAL: "KRİTİK"
        }[self]
    
    @property
    def color(self) -> str:
        """Durum rengi"""
        return {
            SystemState.NORMAL: "green",
            SystemState.WARNING: "yellow",
            SystemState.CRITICAL: "red"
        }[self]


@dataclass
class LeakyBucketConfig:
    """Leaky Bucket algoritması konfigürasyonu"""
    # Anomali puanları (severity'e göre)
    critical_points: float = 15.0      # CRITICAL anomali için eklenecek puan
    high_points: float = 8.0           # HIGH anomali için eklenecek puan  
    medium_points: float = 3.0         # MEDIUM anomali için eklenecek puan
    low_points: float = 1.0            # LOW anomali için eklenecek puan
    
    # Sızıntı (Decay) parametreleri
    decay_rate: float = 5.0            # Dakikada sızan puan miktarı
    decay_interval_seconds: float = 10.0  # Her kaç saniyede decay uygulansın
    
    # Kova kapasitesi
    max_bucket_capacity: float = 100.0  # Maksimum puan kapasitesi
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "critical_points": self.critical_points,
            "high_points": self.high_points,
            "medium_points": self.medium_points,
            "low_points": self.low_points,
            "decay_rate": self.decay_rate,
            "decay_interval_seconds": self.decay_interval_seconds,
            "max_bucket_capacity": self.max_bucket_capacity
        }


@dataclass  
class AdaptiveThresholdConfig:
    """Adaptive Threshold konfigürasyonu"""
    # Temel eşikler
    base_warning_threshold: float = 20.0    # WARNING durumuna geçiş için temel puan
    base_critical_threshold: float = 40.0   # CRITICAL durumuna geçiş için temel puan
    
    # Adaptasyon parametreleri
    adaptation_window_minutes: int = 30     # Adaptasyon için bakılan süre penceresi
    min_samples_for_adaptation: int = 10    # Adaptasyon için minimum örnek sayısı
    
    # Adaptasyon limitleri (temel eşiğin kaç katı olabilir)
    min_threshold_multiplier: float = 0.5   # Eşik en az temel * 0.5 olabilir
    max_threshold_multiplier: float = 2.0   # Eşik en fazla temel * 2.0 olabilir
    
    # Hysteresis (durum geçişlerinde salınımı önlemek için)
    hysteresis_margin: float = 0.2          # %20 marj
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_warning_threshold": self.base_warning_threshold,
            "base_critical_threshold": self.base_critical_threshold,
            "adaptation_window_minutes": self.adaptation_window_minutes,
            "min_samples_for_adaptation": self.min_samples_for_adaptation,
            "min_threshold_multiplier": self.min_threshold_multiplier,
            "max_threshold_multiplier": self.max_threshold_multiplier,
            "hysteresis_margin": self.hysteresis_margin
        }


@dataclass
class StateTransitionConfig:
    """State Transition (Durum Geçişi) konfigürasyonu"""
    # Rapor tetikleme kuralları
    report_on_warning_entry: bool = True    # WARNING'e girince rapor gönder
    report_on_critical_entry: bool = True   # CRITICAL'e girince rapor gönder
    report_on_critical_exit: bool = True    # CRITICAL'den çıkınca rapor gönder
    report_on_normal_return: bool = False   # NORMAL'e dönünce rapor gönder
    
    # Cooldown süreleri (state bazlı)
    normal_cooldown_minutes: int = 60       # NORMAL durumda min rapor aralığı
    warning_cooldown_minutes: int = 15      # WARNING durumda min rapor aralığı
    critical_cooldown_minutes: int = 5      # CRITICAL durumda min rapor aralığı
    
    # Durum stabilitesi (hemen geçiş yapmasın, confirm etsin)
    state_confirmation_seconds: int = 30    # Yeni durumun onaylanması için bekleme
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_on_warning_entry": self.report_on_warning_entry,
            "report_on_critical_entry": self.report_on_critical_entry,
            "report_on_critical_exit": self.report_on_critical_exit,
            "report_on_normal_return": self.report_on_normal_return,
            "normal_cooldown_minutes": self.normal_cooldown_minutes,
            "warning_cooldown_minutes": self.warning_cooldown_minutes,
            "critical_cooldown_minutes": self.critical_cooldown_minutes,
            "state_confirmation_seconds": self.state_confirmation_seconds
        }


@dataclass
class ReportingConfig:
    """Otomatik raporlama ana konfigürasyonu"""
    enabled: bool = True
    
    # Alt konfigürasyonlar
    leaky_bucket: LeakyBucketConfig = field(default_factory=LeakyBucketConfig)
    adaptive_threshold: AdaptiveThresholdConfig = field(default_factory=AdaptiveThresholdConfig)
    state_transition: StateTransitionConfig = field(default_factory=StateTransitionConfig)
    
    # Anomali penceresi (rapor için bakılan süre)
    anomaly_window_minutes: int = 10
    
    # Multi-sensor korelasyonu
    multi_sensor_threshold: int = 3         # Kaç farklı sensörde anomali olunca sistemik sorun
    
    # Çalışma saatleri (isteğe bağlı)
    working_hours_only: bool = False
    working_hours_start: int = 8
    working_hours_end: int = 18
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportingConfig':
        """Dictionary'den oluştur"""
        config = cls()
        
        # Ana parametreler
        config.enabled = data.get("enabled", True)
        config.anomaly_window_minutes = data.get("anomaly_window_minutes", 10)
        config.multi_sensor_threshold = data.get("multi_sensor_threshold", 3)
        config.working_hours_only = data.get("working_hours_only", False)
        config.working_hours_start = data.get("working_hours_start", 8)
        config.working_hours_end = data.get("working_hours_end", 18)
        
        # Leaky Bucket config
        lb_data = data.get("leaky_bucket", {})
        config.leaky_bucket = LeakyBucketConfig(
            critical_points=lb_data.get("critical_points", 15.0),
            high_points=lb_data.get("high_points", 8.0),
            medium_points=lb_data.get("medium_points", 3.0),
            low_points=lb_data.get("low_points", 1.0),
            decay_rate=lb_data.get("decay_rate", 5.0),
            decay_interval_seconds=lb_data.get("decay_interval_seconds", 10.0),
            max_bucket_capacity=lb_data.get("max_bucket_capacity", 100.0)
        )
        
        # Adaptive Threshold config
        at_data = data.get("adaptive_threshold", {})
        config.adaptive_threshold = AdaptiveThresholdConfig(
            base_warning_threshold=at_data.get("base_warning_threshold", 20.0),
            base_critical_threshold=at_data.get("base_critical_threshold", 40.0),
            adaptation_window_minutes=at_data.get("adaptation_window_minutes", 30),
            min_samples_for_adaptation=at_data.get("min_samples_for_adaptation", 10),
            min_threshold_multiplier=at_data.get("min_threshold_multiplier", 0.5),
            max_threshold_multiplier=at_data.get("max_threshold_multiplier", 2.0),
            hysteresis_margin=at_data.get("hysteresis_margin", 0.2)
        )
        
        # State Transition config
        st_data = data.get("state_transition", {})
        config.state_transition = StateTransitionConfig(
            report_on_warning_entry=st_data.get("report_on_warning_entry", True),
            report_on_critical_entry=st_data.get("report_on_critical_entry", True),
            report_on_critical_exit=st_data.get("report_on_critical_exit", True),
            report_on_normal_return=st_data.get("report_on_normal_return", False),
            normal_cooldown_minutes=st_data.get("normal_cooldown_minutes", 60),
            warning_cooldown_minutes=st_data.get("warning_cooldown_minutes", 15),
            critical_cooldown_minutes=st_data.get("critical_cooldown_minutes", 5),
            state_confirmation_seconds=st_data.get("state_confirmation_seconds", 30)
        )
        
        # Geriye uyumluluk: Eski config parametrelerini map et
        if "min_anomalies_for_report" in data:
            # Eski sistemden geçiş: min_anomalies_for_report -> base thresholds
            min_anomalies = data.get("min_anomalies_for_report", 3)
            # Her anomali ortalama 5 puan varsayarak hesapla
            config.adaptive_threshold.base_warning_threshold = min_anomalies * 5.0
            
        if "cooldown_minutes" in data:
            config.state_transition.warning_cooldown_minutes = data.get("cooldown_minutes", 15)
            
        if "critical_cooldown_minutes" in data:
            config.state_transition.critical_cooldown_minutes = data.get("critical_cooldown_minutes", 5)
            
        if "instant_report_on_critical" in data:
            config.state_transition.report_on_critical_entry = data.get("instant_report_on_critical", True)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'e dönüştür"""
        return {
            "enabled": self.enabled,
            "anomaly_window_minutes": self.anomaly_window_minutes,
            "multi_sensor_threshold": self.multi_sensor_threshold,
            "working_hours_only": self.working_hours_only,
            "working_hours_start": self.working_hours_start,
            "working_hours_end": self.working_hours_end,
            "leaky_bucket": self.leaky_bucket.to_dict(),
            "adaptive_threshold": self.adaptive_threshold.to_dict(),
            "state_transition": self.state_transition.to_dict()
        }


@dataclass
class StateTransitionEvent:
    """Durum geçiş olayı"""
    timestamp: datetime
    from_state: SystemState
    to_state: SystemState
    bucket_score: float
    warning_threshold: float
    critical_threshold: float
    trigger_reason: str
    anomaly_count: int
    affected_sensors: List[str]


@dataclass
class ReportDecision:
    """Rapor gönderim kararı"""
    should_report: bool
    reason: str
    risk_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    anomaly_count: int
    affected_sensors: List[str]
    trigger_type: str  # "state_transition", "critical_entry", "warning_entry", "multi_sensor", "manual"
    
    # State bilgileri
    current_state: SystemState = SystemState.NORMAL
    previous_state: Optional[SystemState] = None
    bucket_score: float = 0.0
    warning_threshold: float = 0.0
    critical_threshold: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_report": self.should_report,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "anomaly_count": self.anomaly_count,
            "affected_sensors": self.affected_sensors,
            "trigger_type": self.trigger_type,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "bucket_score": self.bucket_score,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold
        }


class LeakyBucket:
    """
    Leaky Bucket Algoritması
    
    Puan biriktirme ve zamanla sızdırma mekanizması.
    Her anomali için severity'e göre puan eklenir, zaman geçtikçe puan sızar.
    """
    
    def __init__(self, config: LeakyBucketConfig):
        self.config = config
        self._score: float = 0.0
        self._last_decay_time: datetime = datetime.now()
        self._lock = threading.Lock()
    
    @property
    def score(self) -> float:
        """Mevcut puan (decay uygulanmış)"""
        self._apply_decay()
        return self._score
    
    def add_points(self, severity: str) -> float:
        """
        Anomali severity'sine göre puan ekle
        
        Returns:
            Eklenen puan miktarı
        """
        with self._lock:
            self._apply_decay()
            
            # Severity'e göre puan belirle
            severity_upper = severity.upper()
            if severity_upper == "CRITICAL":
                points = self.config.critical_points
            elif severity_upper == "HIGH":
                points = self.config.high_points
            elif severity_upper == "MEDIUM":
                points = self.config.medium_points
            else:
                points = self.config.low_points
            
            # Puanı ekle (max capacity'ye kadar)
            old_score = self._score
            self._score = min(self._score + points, self.config.max_bucket_capacity)
            actual_added = self._score - old_score
            
            logger.debug(f"🪣 Leaky Bucket: +{actual_added:.1f} puan ({severity}), toplam: {self._score:.1f}")
            
            return actual_added
    
    def _apply_decay(self):
        """Zamanla puan sızıntısını uygula"""
        now = datetime.now()
        elapsed = (now - self._last_decay_time).total_seconds()
        
        if elapsed >= self.config.decay_interval_seconds:
            # Dakikaya çevir ve decay uygula
            minutes_elapsed = elapsed / 60.0
            decay_amount = self.config.decay_rate * minutes_elapsed
            
            old_score = self._score
            self._score = max(0.0, self._score - decay_amount)
            self._last_decay_time = now
            
            if old_score != self._score:
                logger.debug(f"🪣 Leaky Bucket decay: -{decay_amount:.1f}, yeni skor: {self._score:.1f}")
    
    def reset(self):
        """Kovayı sıfırla"""
        with self._lock:
            self._score = 0.0
            self._last_decay_time = datetime.now()
            logger.info("🪣 Leaky Bucket sıfırlandı")
    
    def get_status(self) -> Dict[str, Any]:
        """Kova durumunu getir"""
        return {
            "score": self.score,
            "max_capacity": self.config.max_bucket_capacity,
            "fill_percentage": (self.score / self.config.max_bucket_capacity) * 100,
            "decay_rate_per_minute": self.config.decay_rate
        }


class AdaptiveThreshold:
    """
    Adaptive Threshold (Dinamik Eşik) Hesaplayıcı
    
    Ortama göre eşik değerlerini dinamik olarak hesaplar.
    Yüksek anomali yoğunluğu dönemlerinde eşikler yükselir,
    sakin dönemlerde düşer.
    """
    
    def __init__(self, config: AdaptiveThresholdConfig):
        self.config = config
        self._score_history: deque = deque(maxlen=1000)  # (timestamp, score) tuples
        self._current_warning_threshold = config.base_warning_threshold
        self._current_critical_threshold = config.base_critical_threshold
        self._lock = threading.Lock()
    
    def record_score(self, score: float):
        """Skor kaydı ekle (adaptasyon için)"""
        with self._lock:
            self._score_history.append((datetime.now(), score))
            self._recalculate_thresholds()
    
    def _recalculate_thresholds(self):
        """Eşikleri yeniden hesapla"""
        now = datetime.now()
        window_start = now - timedelta(minutes=self.config.adaptation_window_minutes)
        
        # Pencere içindeki skorları al
        recent_scores = [
            score for ts, score in self._score_history 
            if ts >= window_start
        ]
        
        if len(recent_scores) < self.config.min_samples_for_adaptation:
            # Yeterli veri yok, temel eşikleri kullan
            return
        
        # Ortalama ve standart sapma hesapla
        avg_score = sum(recent_scores) / len(recent_scores)
        
        if len(recent_scores) > 1:
            variance = sum((s - avg_score) ** 2 for s in recent_scores) / (len(recent_scores) - 1)
            std_dev = variance ** 0.5
        else:
            std_dev = 0
        
        # Adaptasyon faktörü hesapla
        # Yüksek ortalama = eşikleri yükselt, düşük ortalama = eşikleri düşür
        adaptation_factor = 1.0 + (avg_score / self.config.base_critical_threshold) * 0.3
        
        # Limitle
        adaptation_factor = max(
            self.config.min_threshold_multiplier,
            min(self.config.max_threshold_multiplier, adaptation_factor)
        )
        
        # Yeni eşikleri hesapla
        self._current_warning_threshold = self.config.base_warning_threshold * adaptation_factor
        self._current_critical_threshold = self.config.base_critical_threshold * adaptation_factor
    
    def get_thresholds(self, current_state: SystemState) -> Tuple[float, float]:
        """
        Hysteresis uygulayarak eşikleri getir
        
        Mevcut duruma göre geçiş eşikleri farklılaşır:
        - NORMAL -> WARNING: warning_threshold
        - WARNING -> CRITICAL: critical_threshold  
        - CRITICAL -> WARNING: critical_threshold * (1 - hysteresis)
        - WARNING -> NORMAL: warning_threshold * (1 - hysteresis)
        
        Returns:
            (warning_threshold, critical_threshold)
        """
        margin = self.config.hysteresis_margin
        
        # Yukarı geçişler için normal eşikler, aşağı geçişler için düşük eşikler
        if current_state == SystemState.CRITICAL:
            # CRITICAL'den çıkmak için daha düşük eşik gerekli (hysteresis)
            warning_th = self._current_warning_threshold
            critical_th = self._current_critical_threshold * (1 - margin)
        elif current_state == SystemState.WARNING:
            # WARNING'den NORMAL'e düşmek için daha düşük eşik
            warning_th = self._current_warning_threshold * (1 - margin)
            critical_th = self._current_critical_threshold
        else:
            # NORMAL durumda normal eşikler
            warning_th = self._current_warning_threshold
            critical_th = self._current_critical_threshold
        
        return warning_th, critical_th
    
    def get_base_thresholds(self) -> Tuple[float, float]:
        """Temel (adapt edilmemiş) eşikleri getir"""
        return self.config.base_warning_threshold, self.config.base_critical_threshold
    
    def get_current_thresholds(self) -> Tuple[float, float]:
        """Mevcut adapt edilmiş eşikleri getir"""
        return self._current_warning_threshold, self._current_critical_threshold
    
    def get_status(self) -> Dict[str, Any]:
        """Durum bilgisi"""
        base_w, base_c = self.get_base_thresholds()
        curr_w, curr_c = self.get_current_thresholds()
        
        return {
            "base_warning_threshold": base_w,
            "base_critical_threshold": base_c,
            "current_warning_threshold": curr_w,
            "current_critical_threshold": curr_c,
            "adaptation_factor": curr_w / base_w if base_w > 0 else 1.0,
            "samples_in_window": len(self._score_history)
        }


class AutoReporter:
    """
    Profesyonel Otomatik Anomali Raporlama Yöneticisi
    
    State-Based ve Adaptive Threshold sistemi ile anomalileri değerlendirir:
    - Leaky Bucket ile puan biriktirme/sızdırma
    - Adaptive Threshold ile dinamik eşik hesaplama
    - State Transition ile durum değişikliklerinde rapor tetikleme
    """
    
    def __init__(self, config: Optional[ReportingConfig] = None):
        self.config = config or ReportingConfig()
        
        # Alt sistemler
        self.leaky_bucket = LeakyBucket(self.config.leaky_bucket)
        self.adaptive_threshold = AdaptiveThreshold(self.config.adaptive_threshold)
        
        # Durum yönetimi
        self._current_state = SystemState.NORMAL
        self._pending_state: Optional[SystemState] = None
        self._pending_state_since: Optional[datetime] = None
        self._state_history: deque = deque(maxlen=100)  # StateTransitionEvent
        
        # Anomali tamponu
        self.anomaly_buffer: deque = deque(maxlen=1000)
        
        # Son rapor zamanları (state bazlı)
        self.last_report_times: Dict[SystemState, datetime] = {
            SystemState.NORMAL: datetime.min,
            SystemState.WARNING: datetime.min,
            SystemState.CRITICAL: datetime.min
        }
        
        # İstatistikler
        self.stats = {
            "total_anomalies_processed": 0,
            "reports_sent": 0,
            "reports_skipped_cooldown": 0,
            "state_transitions": 0,
            "last_report_sent": None,
            "last_state_change": None,
            "started_at": datetime.now().isoformat()
        }
        
        # Callback
        self._on_report_needed: Optional[Callable] = None
        
        # Thread safety
        self._lock = threading.Lock()
        self._report_pending = False
        
        logger.info(f"🚀 AutoReporter v2.0 başlatıldı (State-Based & Adaptive)")
        logger.info(f"   Leaky Bucket: decay={self.config.leaky_bucket.decay_rate}/dk")
        logger.info(f"   Thresholds: warning={self.config.adaptive_threshold.base_warning_threshold}, critical={self.config.adaptive_threshold.base_critical_threshold}")
    
    @property
    def current_state(self) -> SystemState:
        """Mevcut sistem durumu"""
        return self._current_state
    
    @property
    def bucket_score(self) -> float:
        """Mevcut kova puanı"""
        return self.leaky_bucket.score
    
    def set_report_callback(self, callback: Callable):
        """Rapor callback'i ayarla"""
        self._on_report_needed = callback
        logger.info("📧 AutoReporter callback ayarlandı")
    
    def add_anomaly(self, anomaly: Dict[str, Any]) -> Optional[ReportDecision]:
        """
        Yeni anomali ekle ve rapor gerekip gerekmediğine karar ver
        
        Args:
            anomaly: Anomali verisi
        
        Returns:
            ReportDecision: Rapor kararı (None ise rapor yok)
        """
        if not anomaly.get("is_anomaly", False):
            return None
        
        if not self.config.enabled:
            return None
        
        with self._lock:
            self.stats["total_anomalies_processed"] += 1
            
            # Timestamp ekle
            now = datetime.now()
            if "timestamp" not in anomaly:
                anomaly["timestamp"] = now.isoformat()
            
            # Buffer'a ekle
            self.anomaly_buffer.append({
                **anomaly,
                "added_at": now
            })
            
            # Severity belirle (z_score'a göre)
            z_score = abs(anomaly.get("z_score", 0))
            if z_score > 4.0:
                severity = "CRITICAL"
            elif z_score > 3.5:
                severity = "HIGH"
            elif z_score > 2.5:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            # Anomaly'nin kendi severity'si varsa onu da dikkate al
            anomaly_severity = anomaly.get("severity", "").upper()
            if anomaly_severity in ["CRITICAL", "HIGH"] and severity not in ["CRITICAL", "HIGH"]:
                severity = anomaly_severity
            
            # Leaky Bucket'a puan ekle
            added_points = self.leaky_bucket.add_points(severity)
            current_score = self.leaky_bucket.score
            
            # Adaptive Threshold'a kaydet
            self.adaptive_threshold.record_score(current_score)
            
            # Durum değişikliğini kontrol et
            decision = self._evaluate_state_transition(anomaly, current_score)
            
            if decision and decision.should_report:
                # Cooldown kontrolü
                if self._check_cooldown(decision.current_state):
                    self.stats["reports_skipped_cooldown"] += 1
                    logger.info(f"⏳ Rapor cooldown nedeniyle atlandı ({decision.current_state.value})")
                    return None
                
                # Çalışma saati kontrolü
                if not self._check_working_hours():
                    logger.info("⏰ Rapor çalışma saatleri dışında")
                    return None
                
                # Duplicate prevention
                if self._report_pending:
                    logger.debug("📧 Rapor zaten beklemede")
                    return None
                
                self._report_pending = True
                
                logger.warning(f"📧 RAPOR KARARI: {decision.reason}")
                logger.warning(f"   State: {decision.previous_state} -> {decision.current_state}")
                logger.warning(f"   Bucket: {decision.bucket_score:.1f}/{decision.critical_threshold:.1f}")
                
                return decision
            
            return None
    
    def _evaluate_state_transition(self, anomaly: Dict[str, Any], current_score: float) -> Optional[ReportDecision]:
        """
        Durum geçişini değerlendir ve karar ver
        """
        # Mevcut eşikleri al (hysteresis dahil)
        warning_th, critical_th = self.adaptive_threshold.get_thresholds(self._current_state)
        
        # Yeni durumu belirle
        if current_score >= critical_th:
            new_state = SystemState.CRITICAL
        elif current_score >= warning_th:
            new_state = SystemState.WARNING
        else:
            new_state = SystemState.NORMAL
        
        # Multi-sensor kontrolü (sistemik sorun)
        now = datetime.now()
        window_start = now - timedelta(minutes=self.config.anomaly_window_minutes)
        recent_anomalies = [a for a in self.anomaly_buffer if a.get("added_at", datetime.min) >= window_start]
        affected_sensors = list(set(a.get("sensor_type", "unknown") for a in recent_anomalies))
        
        if len(affected_sensors) >= self.config.multi_sensor_threshold:
            # Sistemik sorun - CRITICAL'e yükselt
            if new_state != SystemState.CRITICAL:
                logger.warning(f"⚠️ Sistemik anomali: {len(affected_sensors)} sensör etkilendi - CRITICAL'e yükseltiliyor")
                new_state = SystemState.CRITICAL
        
        # Durum değişimi var mı?
        state_changed = new_state != self._current_state
        
        if not state_changed:
            return None  # Durum değişmedi, rapor yok
        
        # State confirmation (anında geçiş yapmayıp onay bekleme)
        confirmation_time = self.config.state_transition.state_confirmation_seconds
        
        if new_state != self._pending_state:
            # Yeni bir pending state başlat
            self._pending_state = new_state
            self._pending_state_since = now
            logger.debug(f"⏳ Yeni state pending: {new_state.value}, {confirmation_time}s onay bekliyor...")
            return None
        
        # Pending state onaylanmış mı?
        if self._pending_state_since:
            elapsed = (now - self._pending_state_since).total_seconds()
            if elapsed < confirmation_time:
                # Henüz onaylanmadı
                logger.debug(f"⏳ State onay bekleniyor: {elapsed:.0f}/{confirmation_time}s")
                return None
        
        # Durum değişimi onaylandı!
        previous_state = self._current_state
        self._current_state = new_state
        self._pending_state = None
        self._pending_state_since = None
        
        self.stats["state_transitions"] += 1
        self.stats["last_state_change"] = now.isoformat()
        
        logger.warning(f"🔄 DURUM DEĞİŞİKLİĞİ: {previous_state.value} -> {new_state.value}")
        
        # State transition event kaydet
        transition_event = StateTransitionEvent(
            timestamp=now,
            from_state=previous_state,
            to_state=new_state,
            bucket_score=current_score,
            warning_threshold=warning_th,
            critical_threshold=critical_th,
            trigger_reason=f"Skor {current_score:.1f}, eşik aşıldı",
            anomaly_count=len(recent_anomalies),
            affected_sensors=affected_sensors
        )
        self._state_history.append(transition_event)
        
        # Rapor tetiklenmeli mi?
        should_report = False
        trigger_type = "state_transition"
        reason = ""
        
        st_config = self.config.state_transition
        
        # CRITICAL'e giriş
        if new_state == SystemState.CRITICAL and previous_state != SystemState.CRITICAL:
            if st_config.report_on_critical_entry:
                should_report = True
                trigger_type = "critical_entry"
                reason = f"🚨 KRİTİK SEVİYEYE GEÇİŞ! Skor: {current_score:.1f} >= {critical_th:.1f}"
        
        # WARNING'e giriş (NORMAL'den)
        elif new_state == SystemState.WARNING and previous_state == SystemState.NORMAL:
            if st_config.report_on_warning_entry:
                should_report = True
                trigger_type = "warning_entry"
                reason = f"⚠️ UYARI SEVİYESİNE GEÇİŞ! Skor: {current_score:.1f} >= {warning_th:.1f}"
        
        # CRITICAL'den çıkış
        elif previous_state == SystemState.CRITICAL and new_state != SystemState.CRITICAL:
            if st_config.report_on_critical_exit:
                should_report = True
                trigger_type = "critical_exit"
                reason = f"✅ Kritik durumdan çıkıldı ({previous_state.value} -> {new_state.value})"
        
        # NORMAL'e dönüş
        elif new_state == SystemState.NORMAL and previous_state != SystemState.NORMAL:
            if st_config.report_on_normal_return:
                should_report = True
                trigger_type = "normal_return"
                reason = f"✅ Sistem normale döndü ({previous_state.value} -> {new_state.value})"
        
        if not should_report:
            return None
        
        # Risk level belirle
        risk_level = {
            SystemState.CRITICAL: "CRITICAL",
            SystemState.WARNING: "HIGH",
            SystemState.NORMAL: "LOW"
        }.get(new_state, "MEDIUM")
        
        return ReportDecision(
            should_report=True,
            reason=reason,
            risk_level=risk_level,
            anomaly_count=len(recent_anomalies),
            affected_sensors=affected_sensors,
            trigger_type=trigger_type,
            current_state=new_state,
            previous_state=previous_state,
            bucket_score=current_score,
            warning_threshold=warning_th,
            critical_threshold=critical_th
        )
    
    def _check_cooldown(self, state: SystemState) -> bool:
        """Cooldown kontrolü (state bazlı)"""
        now = datetime.now()
        last_report = self.last_report_times.get(state, datetime.min)
        
        st_config = self.config.state_transition
        cooldown_minutes = {
            SystemState.NORMAL: st_config.normal_cooldown_minutes,
            SystemState.WARNING: st_config.warning_cooldown_minutes,
            SystemState.CRITICAL: st_config.critical_cooldown_minutes
        }.get(state, st_config.warning_cooldown_minutes)
        
        cooldown = timedelta(minutes=cooldown_minutes)
        in_cooldown = (now - last_report) < cooldown
        
        if in_cooldown:
            remaining = cooldown - (now - last_report)
            logger.debug(f"⏳ Cooldown: {state.value}, kalan: {remaining}")
        
        return in_cooldown
    
    def _check_working_hours(self) -> bool:
        """Çalışma saatleri kontrolü"""
        if not self.config.working_hours_only:
            return True
        
        current_hour = datetime.now().hour
        return self.config.working_hours_start <= current_hour < self.config.working_hours_end
    
    def mark_report_triggered(self, decision: ReportDecision):
        """Rapor gönderildi olarak işaretle"""
        now = datetime.now()
        
        # State bazlı last report time güncelle
        self.last_report_times[decision.current_state] = now
        
        self.stats["reports_sent"] += 1
        self.stats["last_report_sent"] = now.isoformat()
        
        self._report_pending = False
        
        logger.info(f"📊 Rapor işaretlendi: {decision.trigger_type} ({decision.current_state.value})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Detaylı istatistikleri getir"""
        warning_th, critical_th = self.adaptive_threshold.get_current_thresholds()
        
        return {
            **self.stats,
            # Durum bilgileri
            "current_state": self._current_state.value,
            "current_state_turkish": self._current_state.turkish_label,
            "pending_state": self._pending_state.value if self._pending_state else None,
            
            # Leaky Bucket
            "bucket_score": self.leaky_bucket.score,
            "bucket_status": self.leaky_bucket.get_status(),
            
            # Adaptive Threshold
            "warning_threshold": warning_th,
            "critical_threshold": critical_th,
            "threshold_status": self.adaptive_threshold.get_status(),
            
            # Buffer
            "buffer_size": len(self.anomaly_buffer),
            
            # Config
            "config": self.config.to_dict()
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumu özeti (frontend için)"""
        warning_th, critical_th = self.adaptive_threshold.get_current_thresholds()
        score = self.leaky_bucket.score
        
        return {
            "state": self._current_state.value,
            "state_turkish": self._current_state.turkish_label,
            "state_color": self._current_state.color,
            "bucket_score": round(score, 1),
            "warning_threshold": round(warning_th, 1),
            "critical_threshold": round(critical_th, 1),
            "fill_percentage": round((score / self.config.leaky_bucket.max_bucket_capacity) * 100, 1),
            "decay_rate": self.config.leaky_bucket.decay_rate,
            "enabled": self.config.enabled
        }
    
    def update_config(self, **kwargs):
        """Konfigürasyonu güncelle"""
        # Ana parametreler
        for key in ["enabled", "anomaly_window_minutes", "multi_sensor_threshold", 
                    "working_hours_only", "working_hours_start", "working_hours_end"]:
            if key in kwargs:
                setattr(self.config, key, kwargs[key])
        
        # Leaky bucket parametreleri
        if "leaky_bucket" in kwargs:
            lb_data = kwargs["leaky_bucket"]
            for key in ["critical_points", "high_points", "medium_points", "low_points",
                       "decay_rate", "decay_interval_seconds", "max_bucket_capacity"]:
                if key in lb_data:
                    setattr(self.config.leaky_bucket, key, lb_data[key])
            # Bucket'ı yeniden oluştur
            self.leaky_bucket = LeakyBucket(self.config.leaky_bucket)
        
        # Adaptive threshold parametreleri
        if "adaptive_threshold" in kwargs:
            at_data = kwargs["adaptive_threshold"]
            for key in ["base_warning_threshold", "base_critical_threshold",
                       "adaptation_window_minutes", "min_samples_for_adaptation",
                       "min_threshold_multiplier", "max_threshold_multiplier", "hysteresis_margin"]:
                if key in at_data:
                    setattr(self.config.adaptive_threshold, key, at_data[key])
            # Threshold calculator'ı yeniden oluştur
            self.adaptive_threshold = AdaptiveThreshold(self.config.adaptive_threshold)
        
        # State transition parametreleri
        if "state_transition" in kwargs:
            st_data = kwargs["state_transition"]
            for key in ["report_on_warning_entry", "report_on_critical_entry",
                       "report_on_critical_exit", "report_on_normal_return",
                       "normal_cooldown_minutes", "warning_cooldown_minutes", 
                       "critical_cooldown_minutes", "state_confirmation_seconds"]:
                if key in st_data:
                    setattr(self.config.state_transition, key, st_data[key])
        
        logger.info(f"⚙️ AutoReporter config güncellendi: enabled={self.config.enabled}")
    
    def clear_buffer(self):
        """Anomali tamponunu temizle"""
        with self._lock:
            self.anomaly_buffer.clear()
            logger.info("🗑️ Anomali tamponu temizlendi")
    
    def reset(self):
        """Sistemi tamamen sıfırla"""
        with self._lock:
            self.anomaly_buffer.clear()
            self.leaky_bucket.reset()
            self._current_state = SystemState.NORMAL
            self._pending_state = None
            self._pending_state_since = None
            self.stats = {
                "total_anomalies_processed": 0,
                "reports_sent": 0,
                "reports_skipped_cooldown": 0,
                "state_transitions": 0,
                "last_report_sent": None,
                "last_state_change": None,
                "started_at": datetime.now().isoformat()
            }
            logger.info("🔄 AutoReporter sıfırlandı")
    
    def force_state(self, state: SystemState, reason: str = "Manual override"):
        """Durumu zorla değiştir (debug/test için)"""
        with self._lock:
            old_state = self._current_state
            self._current_state = state
            self._pending_state = None
            self._pending_state_since = None
            logger.warning(f"⚠️ State zorla değiştirildi: {old_state.value} -> {state.value} ({reason})")


# Singleton instance
_auto_reporter: Optional[AutoReporter] = None


def get_auto_reporter() -> AutoReporter:
    """Global AutoReporter instance'ını getir veya oluştur"""
    global _auto_reporter
    if _auto_reporter is None:
        config = ReportingConfig()
        
        try:
            config_path = "config.yaml"
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f) or {}
                    auto_report_config = yaml_config.get("auto_reporting", {})
                    if auto_report_config:
                        config = ReportingConfig.from_dict(auto_report_config)
                        logger.info("✅ AutoReporter config dosyadan yüklendi")
        except Exception as e:
            logger.error(f"❌ Config yükleme hatası: {e}")
        
        _auto_reporter = AutoReporter(config)
    
    return _auto_reporter


def configure_auto_reporter(config: ReportingConfig) -> AutoReporter:
    """AutoReporter'ı yapılandır"""
    global _auto_reporter
    _auto_reporter = AutoReporter(config)
    return _auto_reporter
