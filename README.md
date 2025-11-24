# Endüstriyel Anomali Tespit Sistemi

Bu proje, endüstriyel sensör verilerindeki anomalileri tespit etmek için geliştirilmiş tam kapsamlı bir web uygulamasıdır.

## Özellikler

- **Backend**: Python FastAPI, WebSocket, Z-Score Anomali Tespiti
- **Frontend**: Next.js 14, Tailwind CSS, shadcn/ui, Recharts
- **Özellikler**:
  - Gerçek zamanlı veri akışı (WebSocket)
  - Canlı grafik izleme
  - Anomali alarmları
  - Simülasyon modları (Normal, Şişe Sıkışması, Güç Dalgalanması)
  - Dinamik konfigürasyon yönetimi

## Kurulum ve Çalıştırma

Sistemi çalıştırmak için Docker ve Docker Compose gereklidir.

1. Proje dizininde terminali açın.
2. Aşağıdaki komutu çalıştırın:

```bash
docker-compose up --build
```

3. Uygulamalara erişin:
   - **Dashboard (Frontend)**: [http://localhost:3000](http://localhost:3000)
   - **API (Backend)**: [http://localhost:8000](http://localhost:8000)
   - **API Dokümantasyonu**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Geliştirme

### Backend
`backend/` klasöründe bulunur.
- `app.py`: Ana API uygulaması
- `anomaly_detector/`: Tespit algoritmaları

### Frontend
`frontend/` klasöründe bulunur.
- `app/page.tsx`: Ana dashboard sayfası

## Simülasyon

Dashboard üzerinden "Trigger Bottle Jam" veya "Power Fluctuation" butonlarını kullanarak sisteme yapay anomali verileri gönderebilir ve sistemin tepkisini test edebilirsiniz.
