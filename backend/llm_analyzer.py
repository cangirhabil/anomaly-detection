"""
LLM Anomali Yorumlama Modülü
Gemini 2.5 Flash ile anomali verilerini profesyonelce yorumlar

Kullanım:
    analyzer = LLMAnalyzer(api_key="YOUR_GEMINI_API_KEY")
    report = await analyzer.analyze_anomalies(anomalies)
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class AnomalyReport:
    """
    LLM tarafından oluşturulan anomali raporu
    
    Attributes:
        report_id: Benzersiz rapor kimliği
        generated_at: Rapor oluşturulma zamanı
        period_start: Analiz dönemi başlangıcı
        period_end: Analiz dönemi bitişi
        total_anomalies: Toplam anomali sayısı
        anomalies: Ham anomali verileri listesi
        llm_analysis: LLM tarafından üretilen analiz metni
        summary: Kısa özet
        risk_level: Risk seviyesi (LOW, MEDIUM, HIGH, CRITICAL)
        recommended_actions: Önerilen aksiyonlar listesi
        affected_sensors: Etkilenen sensörler
        root_cause_analysis: Kök neden analizi
    """
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_anomalies: int
    anomalies: List[Dict[str, Any]]
    llm_analysis: str = ""
    summary: str = ""
    risk_level: str = "MEDIUM"
    recommended_actions: List[str] = field(default_factory=list)
    affected_sensors: List[str] = field(default_factory=list)
    root_cause_analysis: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'e dönüştür"""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_anomalies": self.total_anomalies,
            "anomalies": self.anomalies,
            "llm_analysis": self.llm_analysis,
            "summary": self.summary,
            "risk_level": self.risk_level,
            "recommended_actions": self.recommended_actions,
            "affected_sensors": self.affected_sensors,
            "root_cause_analysis": self.root_cause_analysis
        }


class LLMAnalyzer:
    """
    Gemini 2.5 Flash ile anomali analizi yapan sınıf
    """
    
    # Sensör tipi açıklamaları (Türkçe)
    SENSOR_DESCRIPTIONS = {
        "ejector_pressure": {
            "name": "Ejektör Hava Basıncı",
            "unit": "bar",
            "description": "Pnömatik ejektör sisteminin hava basıncı",
            "critical_impact": "Ürün ayırma başarısızlığı, üretim durması"
        },
        "conveyor_speed": {
            "name": "Konveyör Hızı",
            "unit": "m/s",
            "description": "Ana taşıma bandı hızı",
            "critical_impact": "Üretim hızı düşüşü, ürün hasarı"
        },
        "main_motor_load": {
            "name": "Ana Motor Yükü",
            "unit": "%",
            "description": "Ana tahrik motorunun yük oranı",
            "critical_impact": "Motor arızası, aşırı ısınma"
        },
        "separation_rate": {
            "name": "Ayrıştırma Hızı",
            "unit": "obj/s",
            "description": "Saniyede ayrıştırılan nesne sayısı",
            "critical_impact": "Verimlilik kaybı, kalite sorunları"
        },
        "optical_sensor_temp": {
            "name": "Optik Sensör Sıcaklığı",
            "unit": "°C",
            "description": "Görüntü işleme sensörlerinin sıcaklığı",
            "critical_impact": "Görüntü kalitesi düşüşü, yanlış tespit"
        },
        "vibration_bearing_x": {
            "name": "Rulman Titreşimi (X)",
            "unit": "mm/s",
            "description": "Ana rulman X ekseni titreşim değeri",
            "critical_impact": "Rulman arızası, mekanik hasar"
        },
        "motor_current": {
            "name": "Motor Akımı",
            "unit": "A",
            "description": "Motor çektiği elektrik akımı",
            "critical_impact": "Elektrik arızası, motor yanması"
        },
        "acoustic_noise": {
            "name": "Akustik Gürültü",
            "unit": "dB",
            "description": "Ortam gürültü seviyesi",
            "critical_impact": "Mekanik arıza belirtisi"
        },
        "system_voltage": {
            "name": "Sistem Voltajı",
            "unit": "V",
            "description": "Elektrik beslemesi voltajı",
            "critical_impact": "Sistem kararsızlığı, ekipman hasarı"
        },
        "throughput": {
            "name": "Üretim Verimi",
            "unit": "pcs/h",
            "description": "Saatlik üretim miktarı",
            "critical_impact": "Üretim hedefi kaçırma"
        }
    }
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        """
        LLM Analyzer başlat
        
        Args:
            api_key: Gemini API anahtarı (None ise env'den alınır)
            model_name: Kullanılacak Gemini modeli
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.model = None
        
        if not GENAI_AVAILABLE:
            logger.warning("google-generativeai paketi yüklü değil. LLM özellikleri devre dışı.")
            return
            
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini model başlatıldı: {self.model_name}")
            except Exception as e:
                logger.error(f"Gemini başlatma hatası: {e}")
        else:
            logger.warning("GEMINI_API_KEY ayarlanmamış. LLM özellikleri devre dışı.")
    
    def _build_analysis_prompt(self, anomalies: List[Dict[str, Any]]) -> str:
        """
        Anomali analizi için detaylı prompt oluştur
        
        Args:
            anomalies: Anomali verileri listesi
        
        Returns:
            Gemini için hazırlanmış prompt
        """
        # Anomalileri sensör tipine göre grupla
        grouped = {}
        for a in anomalies:
            sensor = a.get("sensor_type", "unknown")
            if sensor not in grouped:
                grouped[sensor] = []
            grouped[sensor].append(a)
        
        # Anomali özetini hazırla
        anomaly_summary = []
        for sensor_type, items in grouped.items():
            sensor_info = self.SENSOR_DESCRIPTIONS.get(sensor_type, {
                "name": sensor_type,
                "unit": "",
                "description": "Bilinmeyen sensör",
                "critical_impact": "Belirsiz"
            })
            
            values = [item.get("current_value", 0) for item in items]
            z_scores = [abs(item.get("z_score", 0)) for item in items]
            severities = [item.get("severity", "Medium") for item in items]
            
            anomaly_summary.append({
                "sensor_type": sensor_type,
                "sensor_name": sensor_info["name"],
                "unit": sensor_info.get("unit", items[0].get("unit", "")),
                "description": sensor_info["description"],
                "critical_impact": sensor_info["critical_impact"],
                "anomaly_count": len(items),
                "min_value": min(values),
                "max_value": max(values),
                "avg_value": sum(values) / len(values),
                "mean": items[0].get("mean", 0),
                "std_dev": items[0].get("std_dev", 0),
                "max_z_score": max(z_scores),
                "avg_z_score": sum(z_scores) / len(z_scores),
                "severities": list(set(severities)),
                "high_severity_count": sum(1 for s in severities if s == "High")
            })
        
        # Prompt oluştur
        prompt = f"""Sen endüstriyel IoT sistemleri için uzman bir anomali analiz asistanısın. 
Aşağıdaki sensör anomali verilerini analiz ederek profesyonel bir rapor hazırla.

## BAĞLAM
Bu veriler bir CountSort endüstriyel ayırma makinesinden gelmektedir. Makine optik sensörler kullanarak ürünleri tanımlar ve pnömatik ejektörler ile ayırır.

## ANOMALİ VERİLERİ
Toplam Anomali Sayısı: {len(anomalies)}
Analiz Dönemi: Son {len(anomalies)} anomali kaydı

### Sensör Bazlı Özet:
{json.dumps(anomaly_summary, indent=2, ensure_ascii=False)}

## GÖREV
Aşağıdaki formatta detaylı bir analiz raporu oluştur:

### 1. YÖNETİCİ ÖZETİ
Kısa ve öz bir özet (2-3 cümle).

### 2. RİSK SEVİYESİ
Genel risk seviyesini belirle: DÜŞÜK, ORTA, YÜKSEK veya KRİTİK
Risk seviyesini belirlerken:
- Z-Score değerlerinin büyüklüğü
- Etkilenen sensör sayısı
- Yüksek şiddetli anomali sayısı
- Potansiyel üretim etkisi
faktörlerini değerlendir.

### 3. DETAYLI ANALİZ
Her sensör tipi için:
- Ne oldu?
- Neden önemli?
- Olası nedenler neler olabilir?

### 4. KÖK NEDEN ANALİZİ
Anomalilerin muhtemel kök nedenleri hakkında değerlendirme yap.
Sensörler arası korelasyonları değerlendir.

### 5. ÖNERİLEN AKSİYONLAR
Acil ve uzun vadeli aksiyonları listele.
Her aksiyon için öncelik belirt (ACIL, YÜKSEK, ORTA, DÜŞÜK).

### 6. TAKİP ÖNERİLERİ
İzlenmesi gereken metrikler ve kontrol noktaları.

NOT: Yanıtını Türkçe olarak ver. Teknik terimleri açıkla. Profesyonel ve anlaşılır bir dil kullan.
"""
        return prompt
    
    async def analyze_anomalies(
        self, 
        anomalies: List[Dict[str, Any]],
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> AnomalyReport:
        """
        Anomalileri LLM ile analiz et
        
        Args:
            anomalies: Anomali verileri listesi
            period_start: Analiz dönemi başlangıcı
            period_end: Analiz dönemi bitişi
        
        Returns:
            AnomalyReport: Oluşturulan rapor
        """
        now = datetime.now()
        report_id = f"RPT-{now.strftime('%Y%m%d%H%M%S')}"
        
        if not period_start:
            period_start = now - timedelta(hours=1)
        if not period_end:
            period_end = now
        
        # Etkilenen sensörleri bul
        affected_sensors = list(set(a.get("sensor_type", "unknown") for a in anomalies))
        
        # Varsayılan rapor (LLM yoksa)
        report = AnomalyReport(
            report_id=report_id,
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            total_anomalies=len(anomalies),
            anomalies=anomalies,
            affected_sensors=affected_sensors,
            risk_level=self._calculate_risk_level(anomalies),
            recommended_actions=self._generate_basic_actions(anomalies)
        )
        
        # LLM analizi yap
        if self.model and anomalies:
            try:
                prompt = self._build_analysis_prompt(anomalies)
                
                # Gemini API çağrısı
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )
                
                llm_text = response.text
                report.llm_analysis = llm_text
                
                # LLM çıktısından bilgileri parse et
                parsed = self._parse_llm_response(llm_text)
                report.summary = parsed.get("summary", "")
                report.risk_level = parsed.get("risk_level", report.risk_level)
                report.root_cause_analysis = parsed.get("root_cause", "")
                if parsed.get("actions"):
                    report.recommended_actions = parsed["actions"]
                
                logger.info(f"LLM analizi tamamlandı: {report_id}")
                
            except Exception as e:
                logger.error(f"LLM analiz hatası: {e}")
                report.llm_analysis = f"LLM analizi yapılamadı: {str(e)}"
                report.summary = self._generate_basic_summary(anomalies)
        else:
            report.summary = self._generate_basic_summary(anomalies)
            report.llm_analysis = "LLM servisi yapılandırılmamış. Temel analiz kullanılıyor."
        
        return report
    
    def _calculate_risk_level(self, anomalies: List[Dict[str, Any]]) -> str:
        """Anomalilere göre risk seviyesi hesapla"""
        if not anomalies:
            return "LOW"
        
        high_count = sum(1 for a in anomalies if a.get("severity") == "High")
        medium_count = sum(1 for a in anomalies if a.get("severity") == "Medium")
        max_z_score = max((abs(a.get("z_score", 0)) for a in anomalies), default=0)
        unique_sensors = len(set(a.get("sensor_type") for a in anomalies))
        
        # Risk hesaplama
        risk_score = 0
        risk_score += high_count * 3
        risk_score += medium_count * 1
        risk_score += min(max_z_score, 10)
        risk_score += unique_sensors * 2
        
        if risk_score >= 20 or high_count >= 5:
            return "CRITICAL"
        elif risk_score >= 12 or high_count >= 2:
            return "HIGH"
        elif risk_score >= 6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_basic_summary(self, anomalies: List[Dict[str, Any]]) -> str:
        """Temel özet oluştur"""
        if not anomalies:
            return "Analiz döneminde anomali tespit edilmedi."
        
        sensors = list(set(a.get("sensor_type", "unknown") for a in anomalies))
        high_count = sum(1 for a in anomalies if a.get("severity") == "High")
        
        return (
            f"Toplam {len(anomalies)} anomali tespit edildi. "
            f"Etkilenen sensörler: {', '.join(sensors)}. "
            f"Yüksek şiddetli anomali sayısı: {high_count}."
        )
    
    def _generate_basic_actions(self, anomalies: List[Dict[str, Any]]) -> List[str]:
        """Temel aksiyon önerileri oluştur"""
        actions = []
        sensors = set(a.get("sensor_type") for a in anomalies)
        
        for sensor in sensors:
            sensor_info = self.SENSOR_DESCRIPTIONS.get(sensor, {})
            name = sensor_info.get("name", sensor)
            impact = sensor_info.get("critical_impact", "sistem etkisi")
            
            actions.append(f"{name} sensörünü kontrol edin - Potansiyel etki: {impact}")
        
        if any(a.get("severity") == "High" for a in anomalies):
            actions.insert(0, "ACIL: Yüksek şiddetli anomaliler için sistem kontrolü yapın")
        
        return actions
    
    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """LLM yanıtından yapılandırılmış veri çıkar"""
        result = {
            "summary": "",
            "risk_level": "",
            "root_cause": "",
            "actions": []
        }
        
        try:
            # Yönetici özeti
            if "YÖNETİCİ ÖZETİ" in text:
                parts = text.split("YÖNETİCİ ÖZETİ")
                if len(parts) > 1:
                    summary_section = parts[1].split("###")[0].strip()
                    result["summary"] = summary_section[:500]  # İlk 500 karakter
            
            # Risk seviyesi
            risk_keywords = ["KRİTİK", "YÜKSEK", "ORTA", "DÜŞÜK", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
            for keyword in risk_keywords:
                if keyword in text.upper():
                    if keyword in ["KRİTİK", "CRITICAL"]:
                        result["risk_level"] = "CRITICAL"
                    elif keyword in ["YÜKSEK", "HIGH"]:
                        result["risk_level"] = "HIGH"
                    elif keyword in ["ORTA", "MEDIUM"]:
                        result["risk_level"] = "MEDIUM"
                    else:
                        result["risk_level"] = "LOW"
                    break
            
            # Kök neden
            if "KÖK NEDEN" in text:
                parts = text.split("KÖK NEDEN")
                if len(parts) > 1:
                    root_section = parts[1].split("###")[0].strip()
                    result["root_cause"] = root_section[:1000]
            
            # Aksiyonlar
            if "ÖNERİLEN AKSİYON" in text:
                parts = text.split("ÖNERİLEN AKSİYON")
                if len(parts) > 1:
                    actions_section = parts[1].split("###")[0]
                    # Madde işaretli satırları bul
                    lines = actions_section.split("\n")
                    for line in lines:
                        line = line.strip()
                        if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                            action = line.lstrip("-•* ").strip()
                            if action and len(action) > 5:
                                result["actions"].append(action)
        
        except Exception as e:
            logger.error(f"LLM yanıt parse hatası: {e}")
        
        return result
    
    def is_available(self) -> bool:
        """LLM servisinin kullanılabilir olup olmadığını kontrol et"""
        return self.model is not None


# Singleton instance
_analyzer: Optional[LLMAnalyzer] = None


def get_llm_analyzer() -> LLMAnalyzer:
    """Global LLM analyzer instance'ını getir veya oluştur"""
    global _analyzer
    if _analyzer is None:
        _analyzer = LLMAnalyzer()
    return _analyzer


def configure_llm_analyzer(api_key: str, model_name: str = "gemini-2.5-flash"):
    """LLM analyzer'ı yapılandır"""
    global _analyzer
    _analyzer = LLMAnalyzer(api_key=api_key, model_name=model_name)
    return _analyzer
