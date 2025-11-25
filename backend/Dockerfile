# Anomali Tespit Mikroservisi
FROM python:3.11-slim

# Metadata
LABEL maintainer="your-email@example.com"
LABEL description="Z-Score tabanlı anomali tespit mikroservisi"
LABEL version="1.0.0"

# Çalışma dizini
WORKDIR /app

# Python bağımlılıklarını kopyala
COPY requirements.txt .

# Sistem bağımlılıkları ve Python paketlerini yükle
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY anomaly_detector/ ./anomaly_detector/
COPY app.py .
COPY data_logger.py .
COPY llm_analyzer.py .
COPY email_service.py .
COPY auto_reporter.py .
COPY config.yaml .

# Non-root user oluştur (güvenlik için)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')" || exit 1

# Başlatma komutu
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
