"""
Anomali Tespit Mikroservisi - FastAPI
REST API ile anomali tespit servisi

Kullanım:
    uvicorn app:app --host 0.0.0.0 --port 8000
    
Endpoints:
    POST /api/v1/detect          - Anomali kontrolü yap
    POST /api/v1/log             - Hata ekle ve kontrol et
    GET  /api/v1/stats           - İstatistikleri getir
    GET  /api/v1/health          - Sağlık kontrolü
    GET  /api/v1/config          - Mevcut konfigürasyon
    PUT  /api/v1/config          - Konfigürasyon güncelle
    POST /api/v1/reset           - Sistemi sıfırla
    GET  /api/v1/history         - Veri geçmişi
"""

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import deque, defaultdict
import logging
import os
import yaml
import asyncio
import random

from anomaly_detector import AnomalyDetector, AnomalyConfig
from anomaly_detector.models import SensorReading, AnomalyResult
from data_logger import DataLogger
from llm_analyzer import get_llm_analyzer, configure_llm_analyzer, AnomalyReport
from email_service import get_email_service, EmailRecipient, SMTPConfig
from auto_reporter import get_auto_reporter, ReportingConfig

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket Yöneticisi
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket gönderim hatası: {e}")
                # Bağlantı kopmuş olabilir, listeden çıkar
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

# FastAPI uygulaması
app = FastAPI(
    title="Endüstriyel Anomali Tespit Servisi",
    description="Çoklu sensör verisi için Z-Score tabanlı anomali tespiti",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da spesifik origin'ler kullanın
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dedektör instance (Singleton)
_detector: Optional[AnomalyDetector] = None
_data_logger: Optional[DataLogger] = None


def get_logger() -> DataLogger:
    """Global data logger instance'ını getir veya oluştur"""
    global _data_logger
    if _data_logger is None:
        _data_logger = DataLogger(log_dir="logs", max_memory_logs=1000)
        logger.info("Data logger başlatıldı")
    return _data_logger


def get_detector() -> AnomalyDetector:
    """Global dedektör instance'ını getir veya oluştur"""
    global _detector
    if _detector is None:
        config = None
        
        # 1. config.yaml'dan okumayı dene
        try:
            if os.path.exists("config.yaml"):
                with open("config.yaml", "r") as f:
                    yaml_config = yaml.safe_load(f)
                    anomaly_conf = yaml_config.get("anomaly", {})
                    
                    config = AnomalyConfig(
                        window_size=anomaly_conf.get("window_size", 1000),
                        z_score_threshold=anomaly_conf.get("z_score_threshold", 2.0),
                        min_data_points=anomaly_conf.get("min_data_points", 10),
                        min_training_size=anomaly_conf.get("min_training_size", 50),
                        alert_message=anomaly_conf.get("alert_message", "⚠️ ANOMALİ TESPİT EDİLDİ!"),
                        sensors=anomaly_conf.get("sensors", {})
                    )
                    logger.info("Konfigürasyon config.yaml dosyasından yüklendi")
        except Exception as e:
            logger.error(f"config.yaml okunamadı: {e}")

        # 2. Eğer config yüklenemediyse env vars veya default kullan
        if config is None:
            # Environment variable'lardan konfigürasyon oku
            window_size = int(os.getenv("ANOMALY_WINDOW_SIZE", "100"))
            z_threshold = float(os.getenv("ANOMALY_Z_THRESHOLD", "3.0"))
            min_points = int(os.getenv("ANOMALY_MIN_POINTS", "10"))
            
            config = AnomalyConfig(
                window_size=window_size,
                z_score_threshold=z_threshold,
                min_data_points=min_points
            )
            logger.info("Varsayılan konfigürasyon kullanılıyor")
            
        _detector = AnomalyDetector(config)
        logger.info(f"Anomali dedektörü başlatıldı: {config.to_dict()}")
    
    return _detector


# ============================================================================
# PYDANTIC MODELLER (Request/Response)
# ============================================================================

class ConfigUpdateRequest(BaseModel):
    """Konfigürasyon güncelleme isteği"""
    window_size: Optional[int] = Field(None, ge=1, le=100000)
    z_score_threshold: Optional[float] = Field(None, gt=0, le=10)
    min_data_points: Optional[int] = Field(None, ge=2, le=50000)
    min_training_size: Optional[int] = Field(None, ge=2, le=100000)
    alert_message: Optional[str] = Field(None, min_length=1, max_length=200)
    
    class Config:
        schema_extra = {
            "example": {
                "window_size": 100,
                "z_score_threshold": 3.0,
                "min_data_points": 10,
                "min_training_size": 20,
                "alert_message": "⚠️ ANOMALİ TESPİT EDİLDİ!"
            }
        }


class AnomalyResponse(BaseModel):
    """Anomali tespit yanıtı"""
    is_anomaly: bool
    sensor_type: str
    current_value: float
    mean: float
    std_dev: float
    z_score: float
    threshold: float
    timestamp: str
    severity: str
    message: str


class StatsResponse(BaseModel):
    """İstatistik yanıtı"""
    total_sensors: int
    sensors: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı"""
    status: str
    version: str
    active_sensors: int
    uptime_seconds: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Kök endpoint - API bilgileri"""
    return {
        "service": "Endüstriyel Anomali Tespit Servisi",
        "version": "2.0.0",
        "status": "running",
        "docs": "/api/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Servis sağlık kontrolü
    
    Returns:
        Servis durumu ve temel metrikler
    """
    try:
        detector = get_detector()
        stats = detector.get_statistics_summary()
        
        return HealthResponse(
            status="healthy",
            version="2.0.0",
            active_sensors=stats["total_sensors"]
        )
    except Exception as e:
        logger.error(f"Health check hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Servis sağlıksız: {str(e)}"
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Client'dan mesaj bekle (şimdilik sadece keep-alive için)
            data = await websocket.receive_text()
            # await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/v1/analyze", response_model=AnomalyResponse, tags=["Detection"])
async def analyze_sensor_data(reading: SensorReading):
    """
    Sensör verisini analiz et ve kaydet
    
    Args:
        reading: Sensör okuma verisi
    
    Returns:
        Anomali tespit sonucu
    """
    try:
        detector = get_detector()
        data_logger = get_logger()
        auto_reporter = get_auto_reporter()
        
        # Analiz et ve kaydet
        result = detector.add_reading(reading)
        
        # Veriyi logla (hem normal hem anomali)
        data_logger.log_reading(result.to_dict())
        
        # Loglama
        if result.is_anomaly:
            logger.warning(f"🚨 ANOMALİ: {result.sensor_type}={result.current_value:.2f} | Z-Score={result.z_score:.2f} | {result.message}")
            
            # Otomatik raporlama sistemine bildir
            if auto_reporter.config.enabled:
                try:
                    decision = auto_reporter.add_anomaly(result.to_dict())
                    if decision:
                        logger.warning(f"📧 Otomatik rapor kararı: {decision.trigger_type} - {decision.reason}")
                        # Callback'i burada async olarak çağır
                        asyncio.create_task(trigger_auto_report(decision, auto_reporter))
                except Exception as e:
                    logger.error(f"AutoReporter hatası: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.debug("Otomatik raporlama devre dışı")
        else:
            logger.debug(f"✅ Normal: {reading.sensor_type}={reading.value:.2f} | Z-Score={result.z_score:.2f}")
        
        # WebSocket üzerinden yayınla
        await manager.broadcast({
            "type": "reading",
            "data": result.to_dict()
        })
        
        return AnomalyResponse(**result.to_dict())
        
    except Exception as e:
        logger.error(f"Analiz hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def trigger_auto_report(decision, auto_reporter):
    """
    Otomatik rapor tetikleyici
    Auto_reporter'dan gelen karar ile rapor oluşturup mail gönderir
    """
    try:
        logger.warning(f"🚀 ============================================")
        logger.warning(f"🚀 OTOMATİK RAPOR TETİKLENDİ!")
        logger.warning(f"🚀 Karar: {decision.reason}")
        logger.warning(f"🚀 Risk: {decision.risk_level}")
        logger.warning(f"🚀 ============================================")
        
        # Son anomalileri al
        from datetime import datetime, timedelta
        now = datetime.now()
        window_start = now - timedelta(minutes=auto_reporter.config.anomaly_window_minutes)
        
        recent_anomalies = [
            {k: v for k, v in a.items() if k != "added_at"}
            for a in auto_reporter.anomaly_buffer 
            if a.get("added_at", datetime.min) >= window_start
        ]
        
        if not recent_anomalies:
            logger.warning("⚠️ Anomali buffer boş, rapor oluşturulamadı")
            auto_reporter._report_pending = False
            return
        
        logger.warning(f"📊 {len(recent_anomalies)} anomali ile rapor oluşturuluyor...")
        
        # Callback'i çağır - rapor oluştur ve mail gönder
        await auto_report_callback(recent_anomalies, decision)
        
        # İstatistikleri güncelle
        auto_reporter.mark_report_triggered(decision)
        
        logger.warning(f"✅ Otomatik rapor başarıyla tamamlandı!")
        
    except Exception as e:
        logger.error(f"❌ Otomatik rapor tetikleme hatası: {e}")
        auto_reporter._report_pending = False
        import traceback
        traceback.print_exc()


@app.get("/api/v1/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_statistics():
    """
    Mevcut sistem istatistiklerini getir
    
    Returns:
        İstatistik özeti
    """
    try:
        detector = get_detector()
        stats = detector.get_statistics_summary()
        
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"İstatistik hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/config", tags=["Configuration"])
async def get_config():
    """
    Mevcut konfigürasyonu getir
    
    Returns:
        Aktif konfigürasyon
    """
    try:
        detector = get_detector()
        return detector.config.to_dict()
        
    except Exception as e:
        logger.error(f"Konfigürasyon okuma hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/config", tags=["Configuration"])
async def update_config(request: ConfigUpdateRequest):
    """
    Konfigürasyonu güncelle ve kaydet
    
    Args:
        request: Yeni konfigürasyon parametreleri
    
    Returns:
        Güncellenmiş konfigürasyon
    """
    try:
        global _detector
        detector = get_detector()
        
        # Mevcut değerleri al
        current_config = detector.config.to_dict()
        
        # Yeni değerleri güncelle
        if request.window_size is not None:
            current_config["window_size"] = request.window_size
        if request.z_score_threshold is not None:
            current_config["z_score_threshold"] = request.z_score_threshold
        if request.min_data_points is not None:
            current_config["min_data_points"] = request.min_data_points
        if request.min_training_size is not None:
            current_config["min_training_size"] = request.min_training_size
        if request.alert_message is not None:
            current_config["alert_message"] = request.alert_message
        
        # Yeni dedektör oluştur
        new_config = AnomalyConfig(**current_config)
        new_detector = AnomalyDetector(new_config)
        
        # Geçmiş veriyi aktar
        new_detector.history = defaultdict(lambda: deque(maxlen=new_config.window_size))
        for sensor_type, readings in detector.history.items():
            for reading in readings:
                new_detector.history[sensor_type].append(reading)
        
        _detector = new_detector
        
        # config.yaml dosyasına kaydet
        try:
            if os.path.exists("config.yaml"):
                with open("config.yaml", "r") as f:
                    yaml_config = yaml.safe_load(f) or {}
                
                if "anomaly" not in yaml_config:
                    yaml_config["anomaly"] = {}
                
                # Değerleri güncelle
                if request.window_size is not None:
                    yaml_config["anomaly"]["window_size"] = request.window_size
                if request.z_score_threshold is not None:
                    yaml_config["anomaly"]["z_score_threshold"] = request.z_score_threshold
                if request.min_data_points is not None:
                    yaml_config["anomaly"]["min_data_points"] = request.min_data_points
                if request.min_training_size is not None:
                    yaml_config["anomaly"]["min_training_size"] = request.min_training_size
                if request.alert_message is not None:
                    yaml_config["anomaly"]["alert_message"] = request.alert_message
                
                with open("config.yaml", "w") as f:
                    yaml.dump(yaml_config, f, default_flow_style=False)
                
                logger.info("Konfigürasyon config.yaml dosyasına kaydedildi")
        except Exception as e:
            logger.error(f"Konfigürasyon kaydetme hatası: {e}")
        
        logger.info(f"Konfigürasyon güncellendi: {new_config.to_dict()}")
        
        return new_config.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Konfigürasyon güncelleme hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/reset", tags=["Management"])
async def reset_system():
    """
    Sistemi sıfırla (tüm geçmiş veriyi temizle)
    
    Returns:
        Başarı mesajı
    """
    try:
        detector = get_detector()
        detector.clear_history()
        
        logger.warning("Sistem sıfırlandı - tüm geçmiş veri silindi")
        
        return {
            "status": "success",
            "message": "Sistem başarıyla sıfırlandı",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Sistem sıfırlama hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/history", tags=["Statistics"])
async def get_history():
    """
    Veri geçmişini getir
    
    Returns:
        Geçmiş veriler
    """
    try:
        detector = get_detector()
        history = detector.export_history()
        
        return {
            "total_sensors": len(history),
            "data": history,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Geçmiş veri hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/logs/recent", tags=["Logs"])
async def get_recent_logs(limit: int = 100):
    """
    Son N kaydı getir
    
    Args:
        limit: Getirilecek kayıt sayısı (varsayılan 100)
    
    Returns:
        Son kayıtlar
    """
    try:
        data_logger = get_logger()
        logs = data_logger.get_recent_logs(limit=limit)
        
        return {
            "count": len(logs),
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Log getirme hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/logs/anomalies", tags=["Logs"])
async def get_anomaly_logs(limit: int = 100):
    """
    Son N anomaliyi getir
    
    Args:
        limit: Getirilecek anomali sayısı (varsayılan 100)
    
    Returns:
        Anomali logları
    """
    try:
        data_logger = get_logger()
        anomalies = data_logger.get_anomalies(limit=limit)
        
        return {
            "count": len(anomalies),
            "anomalies": anomalies,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Anomali log getirme hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/logs/stats", tags=["Logs"])
async def get_log_stats():
    """
    Log istatistiklerini getir
    
    Returns:
        Log istatistikleri
    """
    try:
        data_logger = get_logger()
        stats = data_logger.get_stats()
        
        return stats
    except Exception as e:
        logger.error(f"Log istatistik hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/simulate/{scenario}", tags=["Simulation"])
async def simulate_scenario(scenario: str):
    """
    Anomali senaryosu simüle et
    
    Args:
        scenario: Senaryo adı (bottle_jam, broken_bottle, power_fluctuation)
    """
    detector = get_detector()
    
    scenarios = {
        "bottle_jam": {
            "sensor_type": "motor_current",
            "base_value": 5.0,
            "anomaly_value": 8.5,
            "message": "Şişe sıkışması simüle ediliyor"
        },
        "broken_bottle": {
            "sensor_type": "acoustic_noise",
            "base_value": 60.0,
            "anomaly_value": 95.0,
            "message": "Kırık şişe sesi simüle ediliyor"
        },
        "power_fluctuation": {
            "sensor_type": "system_voltage",
            "base_value": 24.0,
            "anomaly_value": 20.5,
            "message": "Güç dalgalanması simüle ediliyor"
        }
    }
    
    if scenario not in scenarios:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
        
    config = scenarios[scenario]
    
    # Simülasyonu arka planda çalıştır
    async def run_simulation():
        # 5 adet anomali verisi gönder
        for _ in range(5):
            reading = SensorReading(
                sensor_id="sim_01",
                sensor_type=config["sensor_type"],
                value=config["anomaly_value"] + random.uniform(-0.5, 0.5),
                unit="unit",
                timestamp=datetime.now()
            )
            
            # Analiz et
            result = detector.add_reading(reading)
            
            # WebSocket'ten yayınla
            await manager.broadcast({
                "type": "reading",
                "data": result.to_dict()
            })
            
            await asyncio.sleep(0.5)
            
    asyncio.create_task(run_simulation())
    
    return {"status": "started", "message": config["message"]}


# ============================================================================
# RAPOR VE E-POSTA ENDPOİNTLERİ
# ============================================================================

class ReportGenerateRequest(BaseModel):
    """Rapor oluşturma isteği"""
    limit: int = Field(default=50, ge=1, le=500, description="Analiz edilecek anomali sayısı")
    include_llm_analysis: bool = Field(default=True, description="LLM analizi dahil edilsin mi")
    
    class Config:
        schema_extra = {
            "example": {
                "limit": 50,
                "include_llm_analysis": True
            }
        }


class EmailRecipientRequest(BaseModel):
    """E-posta alıcısı ekleme isteği"""
    email: str = Field(..., description="E-posta adresi")
    name: str = Field(default="", description="Alıcı adı")
    notify_on_critical: bool = Field(default=True, description="Kritik anomalilerde bildirim")
    notify_on_high: bool = Field(default=True, description="Yüksek seviye anomalilerde bildirim")
    notify_on_medium: bool = Field(default=False, description="Orta seviye anomalilerde bildirim")
    notify_on_low: bool = Field(default=False, description="Düşük seviye anomalilerde bildirim")


class SendReportRequest(BaseModel):
    """Rapor gönderme isteği"""
    recipients: Optional[List[str]] = Field(default=None, description="Alıcı e-posta adresleri (boş ise kayıtlı alıcılara gönderilir)")
    limit: int = Field(default=50, ge=1, le=500, description="Rapora dahil edilecek anomali sayısı")


class EmailConfigRequest(BaseModel):
    """E-posta yapılandırma isteği"""
    host: str = Field(default="smtp.gmail.com", description="SMTP sunucu adresi")
    port: int = Field(default=587, ge=1, le=65535, description="SMTP port")
    username: str = Field(..., description="SMTP kullanıcı adı")
    password: str = Field(..., description="SMTP şifresi")
    sender_email: str = Field(default="", description="Gönderen e-posta adresi")
    sender_name: str = Field(default="Anomali Tespit Sistemi", description="Gönderen adı")
    use_tls: bool = Field(default=True, description="TLS kullan")
    use_ssl: bool = Field(default=False, description="SSL kullan")


class LLMConfigRequest(BaseModel):
    """LLM yapılandırma isteği"""
    api_key: str = Field(..., description="Gemini API anahtarı")
    model_name: str = Field(default="gemini-2.5-flash", description="Model adı")


@app.post("/api/v1/report/generate", tags=["Reports"])
async def generate_anomaly_report(request: ReportGenerateRequest):
    """
    Anomali raporu oluştur
    
    LLM kullanarak tespit edilen anomalileri analiz eder ve detaylı rapor üretir.
    
    Args:
        request: Rapor oluşturma parametreleri
    
    Returns:
        Oluşturulan anomali raporu
    """
    try:
        data_logger = get_logger()
        llm_analyzer = get_llm_analyzer()
        
        # Son anomalileri al
        anomalies = data_logger.get_anomalies(limit=request.limit)
        
        if not anomalies:
            return {
                "success": False,
                "message": "Analiz edilecek anomali bulunamadı",
                "report": None
            }
        
        # LLM analizi yap
        if request.include_llm_analysis and llm_analyzer.is_available():
            report = await llm_analyzer.analyze_anomalies(anomalies)
            logger.info(f"Rapor oluşturuldu: {report.report_id}")
        else:
            # LLM olmadan basit rapor
            from datetime import datetime, timedelta
            now = datetime.now()
            report = AnomalyReport(
                report_id=f"RPT-{now.strftime('%Y%m%d%H%M%S')}",
                generated_at=now,
                period_start=now - timedelta(hours=24),
                period_end=now,
                total_anomalies=len(anomalies),
                anomalies=anomalies,
                affected_sensors=list(set(a.get("sensor_type", "unknown") for a in anomalies)),
                summary=f"Toplam {len(anomalies)} anomali tespit edildi.",
                llm_analysis="LLM analizi devre dışı veya yapılandırılmamış."
            )
        
        return {
            "success": True,
            "message": "Rapor başarıyla oluşturuldu",
            "report": report.to_dict(),
            "llm_available": llm_analyzer.is_available()
        }
        
    except Exception as e:
        logger.error(f"Rapor oluşturma hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/report/send", tags=["Reports"])
async def send_anomaly_report(request: SendReportRequest):
    """
    Anomali raporunu e-posta ile gönder
    
    Rapor oluşturur ve belirtilen alıcılara e-posta olarak gönderir.
    
    Args:
        request: Gönderim parametreleri
    
    Returns:
        Gönderim sonucu
    """
    try:
        data_logger = get_logger()
        llm_analyzer = get_llm_analyzer()
        email_service = get_email_service()
        
        # E-posta servisi yapılandırma kontrolü
        if not email_service.is_configured():
            return {
                "success": False,
                "message": "E-posta servisi yapılandırılmamış. SMTP ayarlarını kontrol edin.",
                "smtp_configured": False
            }
        
        # Son anomalileri al
        anomalies = data_logger.get_anomalies(limit=request.limit)
        
        if not anomalies:
            return {
                "success": False,
                "message": "Gönderilecek anomali bulunamadı",
                "report_sent": False
            }
        
        # Rapor oluştur
        if llm_analyzer.is_available():
            report = await llm_analyzer.analyze_anomalies(anomalies)
        else:
            from datetime import datetime, timedelta
            now = datetime.now()
            report = AnomalyReport(
                report_id=f"RPT-{now.strftime('%Y%m%d%H%M%S')}",
                generated_at=now,
                period_start=now - timedelta(hours=24),
                period_end=now,
                total_anomalies=len(anomalies),
                anomalies=anomalies,
                affected_sensors=list(set(a.get("sensor_type", "unknown") for a in anomalies)),
                summary=f"Toplam {len(anomalies)} anomali tespit edildi."
            )
        
        # E-posta gönder
        result = await email_service.send_report(
            report=report.to_dict(),
            recipients=request.recipients
        )
        
        return {
            "success": result.get("success", False),
            "message": "Rapor e-posta olarak gönderildi" if result.get("success") else result.get("error", "Gönderim başarısız"),
            "report_id": report.report_id,
            "recipients": result.get("recipients", []),
            "sent_at": result.get("sent_at")
        }
        
    except Exception as e:
        logger.error(f"Rapor gönderme hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/email/test", tags=["Email"])
async def send_test_email(recipient: str):
    """
    Test e-postası gönder
    
    E-posta yapılandırmasını test etmek için kullanılır.
    
    Args:
        recipient: Test e-postası alıcısı
    
    Returns:
        Gönderim sonucu
    """
    try:
        email_service = get_email_service()
        
        if not email_service.is_configured():
            return {
                "success": False,
                "message": "E-posta servisi yapılandırılmamış"
            }
        
        result = await email_service.send_test_email(recipient)
        
        return {
            "success": result.get("success", False),
            "message": "Test e-postası gönderildi" if result.get("success") else result.get("error", "Gönderim başarısız"),
            "recipient": recipient
        }
        
    except Exception as e:
        logger.error(f"Test e-posta hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/email/recipients", tags=["Email"])
async def get_email_recipients():
    """
    E-posta alıcı listesini getir
    
    Returns:
        Kayıtlı alıcılar
    """
    email_service = get_email_service()
    return {
        "recipients": email_service.get_recipients(),
        "count": len(email_service.recipients)
    }


@app.post("/api/v1/email/recipients", tags=["Email"])
async def add_email_recipient(request: EmailRecipientRequest):
    """
    E-posta alıcısı ekle
    
    Args:
        request: Alıcı bilgileri
    
    Returns:
        Ekleme sonucu
    """
    email_service = get_email_service()
    
    recipient = EmailRecipient(
        email=request.email,
        name=request.name,
        notify_on_critical=request.notify_on_critical,
        notify_on_high=request.notify_on_high,
        notify_on_medium=request.notify_on_medium,
        notify_on_low=request.notify_on_low
    )
    
    email_service.add_recipient(recipient)
    
    return {
        "success": True,
        "message": f"Alıcı eklendi: {request.email}",
        "recipients": email_service.get_recipients()
    }


@app.delete("/api/v1/email/recipients/{email}", tags=["Email"])
async def remove_email_recipient(email: str):
    """
    E-posta alıcısını kaldır
    
    Args:
        email: Kaldırılacak e-posta adresi
    
    Returns:
        Kaldırma sonucu
    """
    email_service = get_email_service()
    email_service.remove_recipient(email)
    
    return {
        "success": True,
        "message": f"Alıcı kaldırıldı: {email}",
        "recipients": email_service.get_recipients()
    }


@app.get("/api/v1/email/config", tags=["Email"])
async def get_email_config():
    """
    E-posta yapılandırmasını getir (şifre hariç)
    
    Returns:
        Aktif e-posta yapılandırması
    """
    email_service = get_email_service()
    return {
        "config": email_service.config.to_dict(),
        "is_configured": email_service.is_configured()
    }


@app.put("/api/v1/email/config", tags=["Email"])
async def update_email_config(request: EmailConfigRequest):
    """
    E-posta yapılandırmasını güncelle
    
    Args:
        request: Yeni yapılandırma
    
    Returns:
        Güncelleme sonucu
    """
    email_service = get_email_service()
    
    email_service.update_config(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password,
        sender_email=request.sender_email or request.username,
        sender_name=request.sender_name,
        use_tls=request.use_tls,
        use_ssl=request.use_ssl
    )
    
    return {
        "success": True,
        "message": "E-posta yapılandırması güncellendi",
        "config": email_service.config.to_dict()
    }


@app.get("/api/v1/llm/status", tags=["LLM"])
async def get_llm_status():
    """
    LLM servis durumunu getir
    
    Returns:
        LLM servis durumu
    """
    llm_analyzer = get_llm_analyzer()
    return {
        "available": llm_analyzer.is_available(),
        "model": llm_analyzer.model_name,
        "provider": "gemini"
    }


@app.put("/api/v1/llm/config", tags=["LLM"])
async def update_llm_config(request: LLMConfigRequest):
    """
    LLM yapılandırmasını güncelle
    
    Args:
        request: Yeni yapılandırma
    
    Returns:
        Güncelleme sonucu
    """
    try:
        analyzer = configure_llm_analyzer(
            api_key=request.api_key,
            model_name=request.model_name
        )
        
        return {
            "success": True,
            "message": "LLM yapılandırması güncellendi",
            "available": analyzer.is_available(),
            "model": request.model_name
        }
        
    except Exception as e:
        logger.error(f"LLM yapılandırma hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# OTOMATİK RAPORLAMA ENDPOİNTLERİ
# ============================================================================

class AutoReportConfigRequest(BaseModel):
    """Otomatik raporlama yapılandırma isteği"""
    enabled: bool = Field(default=True, description="Otomatik raporlama aktif mi")
    min_anomalies_for_report: int = Field(default=3, ge=1, le=50, description="Rapor için minimum anomali sayısı")
    anomaly_window_minutes: int = Field(default=5, ge=1, le=60, description="Değerlendirme penceresi (dakika)")
    instant_report_on_critical: bool = Field(default=True, description="Kritik anomalide anında rapor")
    cooldown_minutes: int = Field(default=15, ge=1, le=120, description="Aynı seviye için bekleme süresi")
    critical_cooldown_minutes: int = Field(default=5, ge=1, le=60, description="Kritik için bekleme süresi")
    multi_sensor_threshold: int = Field(default=2, ge=2, le=10, description="Çoklu sensör eşiği")


@app.get("/api/v1/auto-report/status", tags=["Auto Report"])
async def get_auto_report_status():
    """
    Otomatik raporlama durumunu getir
    
    Returns:
        Otomatik raporlama durumu ve istatistikleri
    """
    auto_reporter = get_auto_reporter()
    return auto_reporter.get_stats()


@app.get("/api/v1/auto-report/config", tags=["Auto Report"])
async def get_auto_report_config():
    """
    Otomatik raporlama yapılandırmasını getir
    
    Returns:
        Aktif yapılandırma
    """
    auto_reporter = get_auto_reporter()
    return {
        "config": auto_reporter.config.to_dict(),
        "enabled": auto_reporter.config.enabled
    }


@app.put("/api/v1/auto-report/config", tags=["Auto Report"])
async def update_auto_report_config(request: AutoReportConfigRequest):
    """
    Otomatik raporlama yapılandırmasını güncelle
    
    Args:
        request: Yeni yapılandırma
    
    Returns:
        Güncelleme sonucu
    """
    auto_reporter = get_auto_reporter()
    
    auto_reporter.update_config(
        enabled=request.enabled,
        min_anomalies_for_report=request.min_anomalies_for_report,
        anomaly_window_minutes=request.anomaly_window_minutes,
        instant_report_on_critical=request.instant_report_on_critical,
        cooldown_minutes=request.cooldown_minutes,
        critical_cooldown_minutes=request.critical_cooldown_minutes,
        multi_sensor_threshold=request.multi_sensor_threshold
    )
    
    # Config dosyasına kaydet
    try:
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
            
            yaml_config["auto_reporting"] = auto_reporter.config.to_dict()
            
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(yaml_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("Otomatik raporlama ayarları kaydedildi")
    except Exception as e:
        logger.error(f"Config kaydetme hatası: {e}")
    
    return {
        "success": True,
        "message": "Otomatik raporlama yapılandırması güncellendi",
        "config": auto_reporter.config.to_dict()
    }


@app.post("/api/v1/auto-report/toggle", tags=["Auto Report"])
async def toggle_auto_report(enabled: bool):
    """
    Otomatik raporlamayı aç/kapat
    
    Args:
        enabled: Aktif mi
    
    Returns:
        Durum
    """
    auto_reporter = get_auto_reporter()
    auto_reporter.config.enabled = enabled
    
    return {
        "success": True,
        "message": f"Otomatik raporlama {'aktif' if enabled else 'devre dışı'}",
        "enabled": enabled
    }


@app.post("/api/v1/auto-report/clear-buffer", tags=["Auto Report"])
async def clear_auto_report_buffer():
    """
    Anomali tamponunu temizle
    
    Returns:
        Başarı durumu
    """
    auto_reporter = get_auto_reporter()
    auto_reporter.clear_buffer()
    
    return {
        "success": True,
        "message": "Anomali tamponu temizlendi"
    }


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında çalışır"""
    logger.info("=" * 70)
    logger.info("🚀 Anomali Tespit Mikroservisi Başlatılıyor...")
    logger.info("=" * 70)
    
    # Dedektörü başlat
    detector = get_detector()
    logger.info(f"✅ Dedektör başlatıldı: Z-Score={detector.config.z_score_threshold}")
    
    # LLM servisini kontrol et
    llm_analyzer = get_llm_analyzer()
    if llm_analyzer.is_available():
        logger.info(f"🤖 LLM Servisi aktif: {llm_analyzer.model_name}")
    else:
        logger.warning("⚠️ LLM Servisi yapılandırılmamış. GEMINI_API_KEY ayarlayın.")
    
    # E-posta servisini kontrol et
    email_service = get_email_service()
    if email_service.is_configured():
        logger.info(f"📧 E-posta Servisi aktif: {email_service.config.host}")
        logger.info(f"   Alıcı sayısı: {len(email_service.recipients)}")
    else:
        logger.warning("⚠️ E-posta Servisi yapılandırılmamış. SMTP ayarlarını kontrol edin.")
    
    # Otomatik raporlama sistemini başlat
    auto_reporter = get_auto_reporter()
    auto_reporter.set_report_callback(auto_report_callback)
    
    logger.info(f"🔄 Otomatik Raporlama: {'✅ Aktif' if auto_reporter.config.enabled else '❌ Devre Dışı'}")
    if auto_reporter.config.enabled:
        logger.info(f"   Min. anomali: {auto_reporter.config.min_anomalies_for_report}")
        logger.info(f"   Pencere: {auto_reporter.config.anomaly_window_minutes} dk")
        logger.info(f"   Cooldown: {auto_reporter.config.cooldown_minutes} dk")
        logger.info(f"   Kritik anında rapor: {auto_reporter.config.instant_report_on_critical}")
    
    logger.info(f"📊 API Dokümantasyonu: http://localhost:8000/api/docs")
    logger.info("=" * 70)


async def auto_report_callback(anomalies: list, decision):
    """
    Otomatik rapor callback fonksiyonu
    Anomali eşiği aşıldığında çağrılır ve rapor oluşturup mail gönderir
    
    Bu fonksiyon AutoReporter tarafından otomatik olarak çağrılır.
    """
    try:
        logger.warning(f"📧 ================================")
        logger.warning(f"📧 CALLBACK ÇAĞRILDI!")
        logger.warning(f"📧 Anomali sayısı: {len(anomalies)}")
        logger.warning(f"📧 Risk: {decision.risk_level}")
        logger.warning(f"📧 Sebep: {decision.reason}")
        logger.warning(f"📧 ================================")
        
        llm_analyzer = get_llm_analyzer()
        email_service = get_email_service()
        
        # E-posta servisi kontrolü
        if not email_service.is_configured():
            logger.error("❌ E-posta servisi yapılandırılmamış, rapor gönderilemedi!")
            logger.error(f"   SMTP Host: {email_service.smtp_host}")
            logger.error(f"   SMTP User: {email_service.smtp_user}")
            return
        
        if not email_service.recipients:
            logger.error("❌ E-posta alıcısı tanımlı değil, rapor gönderilemedi!")
            return
        
        logger.warning(f"📧 Email servisi hazır - Alıcılar: {email_service.recipients}")
        
        # LLM ile analiz yap
        report = None
        if llm_analyzer.is_available():
            try:
                logger.warning("🤖 LLM analizi başlıyor...")
                report = await llm_analyzer.analyze_anomalies(anomalies)
                # Decision'dan gelen risk seviyesini kullan
                report.risk_level = decision.risk_level
                logger.warning(f"✅ LLM analizi tamamlandı: {report.report_id}")
            except Exception as llm_error:
                logger.error(f"❌ LLM analiz hatası: {llm_error}")
                import traceback
                traceback.print_exc()
                report = None
        else:
            logger.warning("⚠️ LLM kullanılamıyor, basit rapor oluşturulacak")
        
        # LLM yoksa veya hata oluştuysa basit rapor oluştur
        if report is None:
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # Sensör bazında özet oluştur
            sensor_summary = {}
            for a in anomalies:
                sensor = a.get("sensor_type", "unknown")
                if sensor not in sensor_summary:
                    sensor_summary[sensor] = {"count": 0, "max_z": 0}
                sensor_summary[sensor]["count"] += 1
                sensor_summary[sensor]["max_z"] = max(sensor_summary[sensor]["max_z"], abs(a.get("z_score", 0)))
            
            summary_text = f"Son {len(anomalies)} anomali otomatik olarak tespit edildi.\n\n"
            summary_text += "Sensör Bazında Özet:\n"
            for sensor, data in sensor_summary.items():
                summary_text += f"- {sensor}: {data['count']} anomali (max Z-Score: {data['max_z']:.2f})\n"
            
            report = AnomalyReport(
                report_id=f"AUTO-{now.strftime('%Y%m%d%H%M%S')}",
                generated_at=now,
                period_start=now - timedelta(minutes=5),
                period_end=now,
                total_anomalies=len(anomalies),
                anomalies=anomalies,
                affected_sensors=decision.affected_sensors,
                summary=decision.reason,
                risk_level=decision.risk_level,
                llm_analysis=summary_text
            )
            logger.warning(f"📝 Basit rapor oluşturuldu: {report.report_id}")
        
        # E-posta gönder
        try:
            risk_labels = {
                "CRITICAL": "KRİTİK",
                "HIGH": "YÜKSEK",
                "MEDIUM": "ORTA",
                "LOW": "DÜŞÜK"
            }
            risk_label = risk_labels.get(decision.risk_level, decision.risk_level)
            
            logger.warning(f"📧 E-posta gönderiliyor...")
            logger.warning(f"   Alıcılar: {email_service.recipients}")
            logger.warning(f"   Konu: 🚨 [{risk_label}] Otomatik Anomali Raporu - {report.report_id}")
            
            result = await email_service.send_report(
                report=report.to_dict(),
                subject=f"🚨 [{risk_label}] Otomatik Anomali Raporu - {report.report_id}"
            )
            
            if result.get("success"):
                logger.warning(f"✅✅✅ OTOMATİK RAPOR E-POSTASI GÖNDERİLDİ! ✅✅✅")
                logger.warning(f"    Alıcılar: {result.get('recipients')}")
            else:
                logger.error(f"❌ Rapor e-postası gönderilemedi: {result.get('error')}")
                
        except Exception as email_error:
            logger.error(f"❌ E-posta gönderim hatası: {email_error}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        logger.error(f"❌ Otomatik rapor callback hatası: {e}")
        import traceback
        traceback.print_exc()
            
    except Exception as e:
        logger.error(f"❌ Otomatik rapor callback hatası: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapatılırken çalışır"""
    logger.info("🛑 Anomali Tespit Mikroservisi Kapatılıyor...")


# ============================================================================
# MAIN - Geliştirme için
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Environment variable'lardan port al
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Geliştirme modunda otomatik reload
        log_level="info"
    )
