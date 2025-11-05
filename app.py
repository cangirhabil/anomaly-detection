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

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os

from anomaly_detector import AnomalyDetector, AnomalyConfig

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI uygulaması
app = FastAPI(
    title="Anomali Tespit Mikroservisi",
    description="Z-Score tabanlı istatistiksel anomali tespit REST API",
    version="1.0.0",
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
        # Environment variable'lardan konfigürasyon oku
        window_size = int(os.getenv("ANOMALY_WINDOW_SIZE", "30"))
        z_threshold = float(os.getenv("ANOMALY_Z_THRESHOLD", "2.0"))
        min_points = int(os.getenv("ANOMALY_MIN_POINTS", "7"))
        
        config = AnomalyConfig(
            window_size=window_size,
            z_score_threshold=z_threshold,
            min_data_points=min_points
        )
        _detector = AnomalyDetector(config)
        logger.info(f"Anomali dedektörü başlatıldı: {config.to_dict()}")
    
    return _detector


# ============================================================================
# PYDANTIC MODELLER (Request/Response)
# ============================================================================

class DetectRequest(BaseModel):
    """Anomali kontrol isteği"""
    value: int = Field(..., ge=0, description="Kontrol edilecek hata sayısı")
    date: Optional[str] = Field(None, description="Tarih (ISO format)")
    
    @validator('value')
    def validate_value(cls, v):
        if v < 0:
            raise ValueError('Hata sayısı negatif olamaz')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "value": 25,
                "date": "2025-11-05T10:30:00"
            }
        }


class LogRequest(BaseModel):
    """Hata logu ekleme isteği"""
    error_count: int = Field(..., ge=0, description="Günlük hata sayısı")
    date: Optional[str] = Field(None, description="Tarih (ISO format)")
    
    class Config:
        schema_extra = {
            "example": {
                "error_count": 18,
                "date": "2025-11-05"
            }
        }


class ConfigUpdateRequest(BaseModel):
    """Konfigürasyon güncelleme isteği"""
    window_size: Optional[int] = Field(None, ge=1, le=365)
    z_score_threshold: Optional[float] = Field(None, gt=0, le=10)
    min_data_points: Optional[int] = Field(None, ge=2, le=100)
    
    class Config:
        schema_extra = {
            "example": {
                "window_size": 30,
                "z_score_threshold": 2.5,
                "min_data_points": 7
            }
        }


class AnomalyResponse(BaseModel):
    """Anomali tespit yanıtı"""
    is_anomaly: bool
    current_value: int
    mean: float
    std_dev: float
    z_score: float
    threshold: float
    date: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class StatsResponse(BaseModel):
    """İstatistik yanıtı"""
    data_points: int
    mean: float
    std_dev: float
    min: int
    max: int
    latest: Optional[int]
    threshold: float
    window_size: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı"""
    status: str
    version: str
    data_points: int
    ready: bool
    uptime_seconds: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Kök endpoint - API bilgileri"""
    return {
        "service": "Anomali Tespit Mikroservisi",
        "version": "1.0.0",
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
            version="1.0.0",
            data_points=stats["data_points"],
            ready=stats["data_points"] >= detector.config.min_data_points
        )
    except Exception as e:
        logger.error(f"Health check hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Servis sağlıksız: {str(e)}"
        )


@app.post("/api/v1/detect", response_model=AnomalyResponse, tags=["Detection"])
async def detect_anomaly(request: DetectRequest):
    """
    Anomali tespiti yap (geçmişe eklenmeden)
    
    Args:
        request: Kontrol edilecek değer ve tarih
    
    Returns:
        Anomali tespit sonucu
    """
    try:
        detector = get_detector()
        
        # Tarih parse
        date = datetime.fromisoformat(request.date) if request.date else datetime.now()
        
        # Anomali kontrolü
        result = detector.detect_anomaly(request.value, date)
        
        logger.info(f"Anomali kontrolü: value={request.value}, anomaly={result.is_anomaly}, z={result.z_score:.2f}")
        
        return AnomalyResponse(**result.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Anomali tespit hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/log", response_model=AnomalyResponse, tags=["Detection"])
async def log_error(request: LogRequest):
    """
    Hata logu ekle ve anomali kontrolü yap
    
    Args:
        request: Hata sayısı ve tarih
    
    Returns:
        Anomali tespit sonucu
    """
    try:
        detector = get_detector()
        
        # Tarih parse
        date = datetime.fromisoformat(request.date) if request.date else datetime.now()
        
        # Hata ekle ve kontrol et
        result = detector.add_error_log(request.error_count, date)
        
        logger.info(f"Hata eklendi: count={request.error_count}, anomaly={result.is_anomaly}")
        
        # Anomali varsa uyarı
        if result.is_anomaly:
            logger.warning(f"🚨 ANOMALİ TESPİT EDİLDİ: {result.message}")
        
        return AnomalyResponse(**result.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Hata loglama hatası: {e}")
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
    Konfigürasyonu güncelle
    
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
        if detector.error_history:
            historical_data = [(log.date, log.error_count) for log in detector.error_history]
            new_detector.load_historical_data(historical_data)
        
        _detector = new_detector
        
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
async def get_history(limit: Optional[int] = None):
    """
    Veri geçmişini getir
    
    Args:
        limit: Maksimum kayıt sayısı (opsiyonel)
    
    Returns:
        Geçmiş veriler
    """
    try:
        detector = get_detector()
        history = detector.export_history()
        
        if limit and limit > 0:
            history = history[-limit:]
        
        return {
            "total": len(history),
            "data": history,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Geçmiş veri hatası: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
