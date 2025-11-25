"""
Veri Kayıt Modülü
Tüm sensör verilerini ve anomalileri dosyaya kaydeder
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from collections import deque

class DataLogger:
    def __init__(self, log_dir="logs", max_memory_logs=1000):
        """
        Args:
            log_dir: Log dosyalarının kaydedileceği dizin
            max_memory_logs: Bellekte tutulacak maksimum log sayısı
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Bellekte son N kaydı tut
        self.recent_logs = deque(maxlen=max_memory_logs)
        self.anomaly_logs = deque(maxlen=max_memory_logs)
        
        # Log dosyaları
        self.all_data_file = self.log_dir / "all_readings.csv"
        self.anomaly_file = self.log_dir / "anomalies.csv"
        
        # CSV başlıklarını oluştur
        self._init_csv_files()
    
    def _init_csv_files(self):
        """CSV dosyalarını başlat"""
        # Tüm veriler için
        if not self.all_data_file.exists():
            with open(self.all_data_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'sensor_id', 'sensor_type', 'value', 'unit',
                    'mean', 'std_dev', 'z_score', 'threshold', 'is_anomaly', 'severity'
                ])
        
        # Anomaliler için
        if not self.anomaly_file.exists():
            with open(self.anomaly_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'sensor_id', 'sensor_type', 'value', 'unit',
                    'mean', 'std_dev', 'z_score', 'threshold', 'severity', 'message'
                ])
    
    def log_reading(self, reading_data: Dict[str, Any]):
        """
        Bir okumayı kaydet
        
        Args:
            reading_data: Sensör okuma verisi (AnomalyResult.to_dict() çıktısı)
        """
        # Bellekteki loglara ekle
        log_entry = {
            **reading_data,
            'logged_at': datetime.now().isoformat()
        }
        self.recent_logs.append(log_entry)
        
        # Anomali ise ayrıca anomali listesine ekle
        if reading_data.get('is_anomaly', False):
            self.anomaly_logs.append(log_entry)
            self._write_anomaly(reading_data)
        
        # CSV'ye yaz
        self._write_to_csv(reading_data)
    
    def _write_to_csv(self, data: Dict[str, Any]):
        """Tüm verileri CSV'ye yaz"""
        try:
            with open(self.all_data_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data.get('timestamp', ''),
                    data.get('sensor_id', ''),
                    data.get('sensor_type', ''),
                    data.get('current_value', 0),
                    data.get('unit', ''),
                    data.get('mean', 0),
                    data.get('std_dev', 0),
                    data.get('z_score', 0),
                    data.get('threshold', 0),
                    data.get('is_anomaly', False),
                    data.get('severity', 'normal')
                ])
        except Exception as e:
            print(f"CSV yazma hatası: {e}")
    
    def _write_anomaly(self, data: Dict[str, Any]):
        """Anomalileri ayrı bir dosyaya yaz"""
        try:
            with open(self.anomaly_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data.get('timestamp', ''),
                    data.get('sensor_id', ''),
                    data.get('sensor_type', ''),
                    data.get('current_value', 0),
                    data.get('unit', ''),
                    data.get('mean', 0),
                    data.get('std_dev', 0),
                    data.get('z_score', 0),
                    data.get('threshold', 0),
                    data.get('severity', 'warning'),
                    data.get('message', '')
                ])
        except Exception as e:
            print(f"Anomali yazma hatası: {e}")
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """Son N kaydı getir"""
        return list(self.recent_logs)[-limit:]
    
    def get_anomalies(self, limit: int = 100) -> list:
        """Son N anomaliyi getir"""
        return list(self.anomaly_logs)[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri getir"""
        total_readings = len(self.recent_logs)
        total_anomalies = len(self.anomaly_logs)
        
        return {
            'total_readings_in_memory': total_readings,
            'total_anomalies_in_memory': total_anomalies,
            'anomaly_rate': (total_anomalies / total_readings * 100) if total_readings > 0 else 0,
            'log_files': {
                'all_data': str(self.all_data_file),
                'anomalies': str(self.anomaly_file)
            }
        }
    
    def clear_memory(self):
        """Bellekteki logları temizle (dosyalar korunur)"""
        self.recent_logs.clear()
        self.anomaly_logs.clear()
