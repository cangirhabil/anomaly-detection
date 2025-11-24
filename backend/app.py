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
    window_size: Optional[int] = Field(None, ge=1, le=1000)
    z_score_threshold: Optional[float] = Field(None, gt=0, le=10)
    min_data_points: Optional[int] = Field(None, ge=2, le=100)
    
    class Config:
        schema_extra = {
            "example": {
                "window_size": 100,
                "z_score_threshold": 3.0,
                "min_data_points": 10
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
        
        # Analiz et ve kaydet
        result = detector.add_reading(reading)
        
        # Loglama
        if result.is_anomaly:
            logger.warning(f"🚨 ANOMALİ: {result.message}")
        else:
            logger.info(f"Normal: {reading.sensor_type}={reading.value}")
        
        # WebSocket üzerinden yayınla
        await manager.broadcast({
            "type": "reading",
            "data": result.to_dict()
        })
        
        return AnomalyResponse(**result.to_dict())
        
    except Exception as e:
        logger.error(f"Analiz hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
    logger.info(f"✅ Dedektör başlatıldı: {detector.config.to_dict()}")
    logger.info(f"📊 API Dokümantasyonu: http://localhost:8000/api/docs")
    logger.info("=" * 70)


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
