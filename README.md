# 🚀 Anomaly Detection Microservice

**Statistical anomaly detection using Z-Score methodology**

Production-ready FastAPI microservice that automatically detects abnormal increases in error counts using Z-Score statistical analysis.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[🇹🇷 Türkçe](README_TR.md) | [📊 Project Info](PROJE_OZETI.md)

---

## ✨ Features

- ✅ **Statistical Detection** - Z-Score algorithm for scientific anomaly detection
- ✅ **REST API** - 8 endpoints with full functionality
- ✅ **Plug-and-Play** - Docker one-command deployment
- ✅ **Language Agnostic** - Python, JavaScript, Java, C#, etc.
- ✅ **Production-Ready** - Kubernetes, AWS, GCP, Azure support
- ✅ **Interactive Docs** - Swagger UI for API documentation
- ✅ **Python Client** - Ready-to-use client library
- ✅ **100% Tested** - Complete test coverage

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

### Python Client

```python
from anomaly_client import AnomalyClient

client = AnomalyClient("http://localhost:8000")

# Log error
client.log_error(error_count=25)

# Detect anomaly
result = client.detect_anomaly(current_value=150)

if result.is_anomaly:
    print(f"⚠️ Anomaly! Z-Score: {result.z_score:.2f}")
```

### REST API

```bash
# Log error
curl -X POST http://localhost:8000/api/v1/log \
  -H "Content-Type: application/json" \
  -d '{"error_count": 25}'

# Detect anomaly
curl -X POST http://localhost:8000/api/v1/detect \
  -H "Content-Type: application/json" \
  -d '{"current_value": 150}'
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/log` | Log error count |
| `POST` | `/api/v1/detect` | Detect anomaly |
| `GET` | `/api/v1/stats` | Get statistics |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/bulk-log` | Bulk log entries |
| `GET` | `/api/v1/history` | Get history |
| `DELETE` | `/api/v1/clear` | Clear data |
| `PUT` | `/api/v1/config` | Update config |

---

## 📊 Z-Score Methodology

```
Z-Score = (X - μ) / σ
```

| Z-Score | Severity | Confidence |
|---------|----------|------------|
| < 1.645 | Normal | 90% |
| 1.645-2.0 | Low | 90-95% |
| 2.0-3.0 | Medium | 95-99.7% |
| > 3.0 | High | >99.7% |

---

## 🐳 Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
```

### Cloud Platforms
- **AWS ECS** - Amazon Elastic Container Service
- **GCP Cloud Run** - Google Cloud Platform
- **Azure ACI** - Azure Container Instances

---

## ⚙️ Configuration

```bash
ANOMALY_Z_THRESHOLD=2.0      # Z-Score threshold
ANOMALY_WINDOW_SIZE=30       # Days to analyze
ANOMALY_MIN_DATA_POINTS=7    # Minimum data required
ANOMALY_API_PORT=8000        # API port
```

---

## 🧪 Testing

```bash
python test_system.py    # System tests (100%)
python test_api.py       # API tests
python demo.py           # Demo scenarios
```

---

## 📁 Structure

```
anomaly-detector/
├── anomaly_detector/    # Core engine
│   ├── detector.py     # Z-Score algorithm
│   ├── config.py       # Configuration
│   └── models.py       # Data models
├── app.py              # FastAPI service
├── anomaly_client.py   # Python client
├── Dockerfile          # Container image
└── docker-compose.yml  # Orchestration
```

---

## 🎯 Use Cases

- Backend Error Monitoring
- API Rate Monitoring
- System Health Monitoring
- Security Monitoring
- Business Metrics Analysis

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Built With

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [NumPy](https://numpy.org/) - Scientific computing
- [Pandas](https://pandas.pydata.org/) - Data analysis
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation

---

**⭐ Star this repo if you find it useful!**
