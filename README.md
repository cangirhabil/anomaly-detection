# 🚀 Industrial Sensor Anomaly Detection

**Multi-sensor anomaly detection using Z-Score methodology**

Production-ready FastAPI microservice that automatically detects anomalies in industrial sensor data (Vibration, Temperature, Sound, etc.) using Z-Score statistical analysis.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[🇹🇷 Türkçe](README_TR.md) | [📊 Project Info](PROJE_OZETI.md)

---

## ✨ Features

- ✅ **Multi-Sensor Support** - Analyze Vibration (X/Y/Z), Temperature, Sound, Motor Current, Throughput
- ✅ **Statistical Detection** - Z-Score algorithm for scientific anomaly detection
- ✅ **REST API** - Unified endpoint for all sensor types
- ✅ **Plug-and-Play** - Docker one-command deployment
- ✅ **Language Agnostic** - Python, JavaScript, Java, C#, etc.
- ✅ **Production-Ready** - Kubernetes, AWS, GCP, Azure support
- ✅ **Interactive Docs** - Swagger UI for API documentation

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker-compose up -d
curl http://localhost:8000/api/v1/health
```

### Python

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

**API Docs:** http://localhost:8000/api/docs

---

## 💡 Usage

### Python Client Example

```python
import requests

# Send sensor data
payload = {
    "sensor_type": "vibration",
    "value": 2.5,
    "unit": "G"
}

response = requests.post("http://localhost:8000/api/v1/analyze", json=payload)
result = response.json()

if result["is_anomaly"]:
    print(f"⚠️ Anomaly Detected! Z-Score: {result['z_score']}")
```

### REST API

```bash
# Analyze Vibration Data
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "vibration",
    "value": 3.5,
    "unit": "G"
  }'
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyze` | Analyze and log sensor data |
| `GET` | `/api/v1/stats` | Get statistics for all sensors |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/reset` | Reset system history |
| `GET` | `/api/v1/history` | Get sensor history |
| `PUT` | `/api/v1/config` | Update config |

---

## 📊 Z-Score Methodology

```
Z-Score = (X - μ) / σ
```

| Z-Score | Severity | Confidence |
|---------|----------|------------|
| < 2.0 | Normal | 95% |
| 2.0-3.0 | Medium | 95-99.7% |
| > 3.0 | High | >99.7% |

---

## ⚙️ Configuration

```bash
ANOMALY_Z_THRESHOLD=3.0      # Z-Score threshold
ANOMALY_WINDOW_SIZE=100      # Data points to keep
ANOMALY_MIN_POINTS=10        # Minimum data required
```

---

## 🧪 Testing

```bash
python demo.py           # Run multi-sensor simulation
```

---

## 📁 Structure

```
anomaly-detector/
├── anomaly_detector/    # Core engine
│   ├── detector.py     # Multi-sensor Z-Score algorithm
│   ├── config.py       # Configuration
│   └── models.py       # Data models (SensorReading)
├── app.py              # FastAPI service
├── demo.py             # Simulation script
├── Dockerfile          # Container image
└── docker-compose.yml  # Orchestration
```
