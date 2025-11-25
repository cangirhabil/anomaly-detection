"""
E-posta Bildirim Servisi
Anomali raporlarını e-posta ile gönderir

Kullanım:
    service = EmailService(smtp_config)
    await service.send_anomaly_report(report, recipients)
"""

import os
import smtplib
import ssl
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class SMTPConfig:
    """SMTP Konfigürasyonu"""
    host: str = "smtp.zoho.com"
    port: int = 587
    username: str = ""
    password: str = ""
    sender_email: str = ""
    sender_name: str = "Anomali Tespit Sistemi"
    use_tls: bool = True
    use_ssl: bool = False
    
    @classmethod
    def from_env(cls) -> 'SMTPConfig':
        """Environment variable'lardan oku"""
        return cls(
            host=os.getenv("SMTP_HOST", "smtp.zoho.com"),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            sender_email=os.getenv("SMTP_SENDER_EMAIL", ""),
            sender_name=os.getenv("SMTP_SENDER_NAME", "Anomali Tespit Sistemi"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'e dönüştür (şifre hariç)"""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "use_tls": self.use_tls,
            "use_ssl": self.use_ssl,
            "configured": bool(self.username and self.password)
        }


@dataclass
class EmailRecipient:
    """E-posta alıcısı"""
    email: str
    name: str = ""
    notify_on_critical: bool = True
    notify_on_high: bool = True
    notify_on_medium: bool = False
    notify_on_low: bool = False
    
    def should_notify(self, risk_level: str) -> bool:
        """Bu risk seviyesi için bildirim gönderilmeli mi?"""
        level_map = {
            "CRITICAL": self.notify_on_critical,
            "HIGH": self.notify_on_high,
            "MEDIUM": self.notify_on_medium,
            "LOW": self.notify_on_low
        }
        return level_map.get(risk_level.upper(), False)


class EmailService:
    """
    E-posta gönderim servisi
    """
    
    # Risk seviyesi renkleri
    RISK_COLORS = {
        "CRITICAL": "#dc2626",  # Kırmızı
        "HIGH": "#ea580c",      # Turuncu
        "MEDIUM": "#ca8a04",    # Sarı
        "LOW": "#16a34a"        # Yeşil
    }
    
    # Risk seviyesi Türkçe karşılıkları
    RISK_LABELS = {
        "CRITICAL": "KRİTİK",
        "HIGH": "YÜKSEK",
        "MEDIUM": "ORTA",
        "LOW": "DÜŞÜK"
    }
    
    def __init__(self, config: Optional[SMTPConfig] = None):
        """
        Email Service başlat
        
        Args:
            config: SMTP konfigürasyonu (None ise env'den alınır)
        """
        self.config = config or SMTPConfig.from_env()
        self.recipients: List[EmailRecipient] = []
        
        # Varsayılan alıcıları env'den yükle
        default_recipients = os.getenv("EMAIL_RECIPIENTS", "")
        if default_recipients:
            for email in default_recipients.split(","):
                email = email.strip()
                if email:
                    self.recipients.append(EmailRecipient(email=email))
    
    def add_recipient(self, recipient: EmailRecipient):
        """Alıcı ekle"""
        # Aynı e-posta varsa güncelle
        for i, r in enumerate(self.recipients):
            if r.email == recipient.email:
                self.recipients[i] = recipient
                return
        self.recipients.append(recipient)
    
    def remove_recipient(self, email: str):
        """Alıcı kaldır"""
        self.recipients = [r for r in self.recipients if r.email != email]
    
    def get_recipients(self) -> List[Dict[str, Any]]:
        """Alıcı listesini getir"""
        return [
            {
                "email": r.email,
                "name": r.name,
                "notify_on_critical": r.notify_on_critical,
                "notify_on_high": r.notify_on_high,
                "notify_on_medium": r.notify_on_medium,
                "notify_on_low": r.notify_on_low
            }
            for r in self.recipients
        ]
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """
        Anomali raporu için HTML e-posta içeriği oluştur
        
        Args:
            report: AnomalyReport.to_dict() çıktısı
        
        Returns:
            HTML formatında e-posta içeriği
        """
        risk_level = report.get("risk_level", "MEDIUM")
        risk_color = self.RISK_COLORS.get(risk_level, "#ca8a04")
        risk_label = self.RISK_LABELS.get(risk_level, risk_level)
        
        # Anomali tablosu HTML'i
        anomaly_rows = ""
        for anomaly in report.get("anomalies", [])[:20]:  # İlk 20 anomali
            severity = anomaly.get("severity", "Medium")
            severity_color = "#ca8a04"
            if severity == "High":
                severity_color = "#dc2626"
            elif severity == "Low":
                severity_color = "#16a34a"
            
            anomaly_rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{anomaly.get("timestamp", "")[:19]}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{anomaly.get("sensor_type", "")}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{anomaly.get("current_value", 0):.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{anomaly.get("z_score", 0):.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                    <span style="background-color: {severity_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">
                        {severity}
                    </span>
                </td>
            </tr>
            """
        
        # Önerilen aksiyonlar HTML'i
        actions_html = ""
        for action in report.get("recommended_actions", []):
            actions_html += f'<li style="margin-bottom: 8px;">{action}</li>'
        
        # Ana HTML şablonu
        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anomali Raporu - {report.get("report_id", "")}</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f3f4f6;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; padding: 30px; border-radius: 12px 12px 0 0;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h1 style="margin: 0; font-size: 24px;">🏭 Anomali Tespit Raporu</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Rapor ID: {report.get("report_id", "")}</p>
                </div>
                <div style="text-align: right;">
                    <div style="background-color: {risk_color}; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 18px;">
                        {risk_label} RİSK
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Özet Kartı -->
        <div style="background-color: white; padding: 25px; border-left: 4px solid {risk_color};">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 18px;">📋 Yönetici Özeti</h2>
            <p style="color: #475569; line-height: 1.6;">
                {report.get("summary", "Özet bilgisi mevcut değil.")}
            </p>
            
            <div style="display: flex; gap: 20px; margin-top: 20px; flex-wrap: wrap;">
                <div style="background-color: #f8fafc; padding: 15px 20px; border-radius: 8px; flex: 1; min-width: 150px;">
                    <div style="color: #64748b; font-size: 12px; text-transform: uppercase;">Toplam Anomali</div>
                    <div style="color: #1e293b; font-size: 28px; font-weight: bold;">{report.get("total_anomalies", 0)}</div>
                </div>
                <div style="background-color: #f8fafc; padding: 15px 20px; border-radius: 8px; flex: 1; min-width: 150px;">
                    <div style="color: #64748b; font-size: 12px; text-transform: uppercase;">Etkilenen Sensör</div>
                    <div style="color: #1e293b; font-size: 28px; font-weight: bold;">{len(report.get("affected_sensors", []))}</div>
                </div>
                <div style="background-color: #f8fafc; padding: 15px 20px; border-radius: 8px; flex: 1; min-width: 150px;">
                    <div style="color: #64748b; font-size: 12px; text-transform: uppercase;">Analiz Tarihi</div>
                    <div style="color: #1e293b; font-size: 16px; font-weight: bold;">{report.get("generated_at", "")[:10]}</div>
                </div>
            </div>
        </div>
        
        <!-- LLM Analizi -->
        <div style="background-color: white; padding: 25px; margin-top: 2px;">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 18px;">🤖 AI Analizi</h2>
            <div style="color: #475569; line-height: 1.8; white-space: pre-wrap; background-color: #f8fafc; padding: 20px; border-radius: 8px; font-size: 14px;">
{report.get("llm_analysis", "LLM analizi mevcut değil.")[:3000]}
            </div>
        </div>
        
        <!-- Kök Neden Analizi -->
        {f'''
        <div style="background-color: white; padding: 25px; margin-top: 2px;">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 18px;">🔍 Kök Neden Analizi</h2>
            <p style="color: #475569; line-height: 1.6;">
                {report.get("root_cause_analysis", "")}
            </p>
        </div>
        ''' if report.get("root_cause_analysis") else ""}
        
        <!-- Önerilen Aksiyonlar -->
        {f'''
        <div style="background-color: white; padding: 25px; margin-top: 2px;">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 18px;">⚡ Önerilen Aksiyonlar</h2>
            <ul style="color: #475569; line-height: 1.8; padding-left: 20px;">
                {actions_html}
            </ul>
        </div>
        ''' if actions_html else ""}
        
        <!-- Anomali Tablosu -->
        <div style="background-color: white; padding: 25px; margin-top: 2px;">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 18px;">📊 Anomali Detayları</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #f8fafc;">
                            <th style="padding: 12px 10px; text-align: left; color: #64748b; font-weight: 600;">Zaman</th>
                            <th style="padding: 12px 10px; text-align: left; color: #64748b; font-weight: 600;">Sensör</th>
                            <th style="padding: 12px 10px; text-align: left; color: #64748b; font-weight: 600;">Değer</th>
                            <th style="padding: 12px 10px; text-align: left; color: #64748b; font-weight: 600;">Z-Score</th>
                            <th style="padding: 12px 10px; text-align: left; color: #64748b; font-weight: 600;">Şiddet</th>
                        </tr>
                    </thead>
                    <tbody>
                        {anomaly_rows if anomaly_rows else '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #64748b;">Anomali verisi bulunamadı</td></tr>'}
                    </tbody>
                </table>
            </div>
            {f'<p style="color: #64748b; font-size: 12px; margin-top: 10px;">* Toplam {report.get("total_anomalies", 0)} anomaliden ilk 20 tanesi gösterilmektedir.</p>' if report.get("total_anomalies", 0) > 20 else ""}
        </div>
        
        <!-- Footer -->
        <div style="background-color: #1e293b; color: white; padding: 20px; border-radius: 0 0 12px 12px; text-align: center;">
            <p style="margin: 0; font-size: 12px; opacity: 0.8;">
                Bu rapor Anomali Tespit Sistemi tarafından otomatik olarak oluşturulmuştur.
            </p>
            <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.6;">
                Rapor Tarihi: {report.get("generated_at", "")} | Dönem: {report.get("period_start", "")[:10]} - {report.get("period_end", "")[:10]}
            </p>
        </div>
        
    </div>
</body>
</html>
"""
        return html
    
    def _generate_plain_text_report(self, report: Dict[str, Any]) -> str:
        """
        Anomali raporu için düz metin e-posta içeriği oluştur
        
        Args:
            report: AnomalyReport.to_dict() çıktısı
        
        Returns:
            Düz metin formatında e-posta içeriği
        """
        risk_label = self.RISK_LABELS.get(report.get("risk_level", "MEDIUM"), "ORTA")
        
        text = f"""
================================================================================
🏭 ANOMALİ TESPİT RAPORU
================================================================================

Rapor ID: {report.get("report_id", "")}
Risk Seviyesi: {risk_label}
Oluşturulma: {report.get("generated_at", "")}
Analiz Dönemi: {report.get("period_start", "")[:10]} - {report.get("period_end", "")[:10]}

--------------------------------------------------------------------------------
📋 YÖNETİCİ ÖZETİ
--------------------------------------------------------------------------------
{report.get("summary", "Özet bilgisi mevcut değil.")}

Toplam Anomali: {report.get("total_anomalies", 0)}
Etkilenen Sensörler: {", ".join(report.get("affected_sensors", []))}

--------------------------------------------------------------------------------
🤖 AI ANALİZİ
--------------------------------------------------------------------------------
{report.get("llm_analysis", "LLM analizi mevcut değil.")}

"""
        
        if report.get("root_cause_analysis"):
            text += f"""
--------------------------------------------------------------------------------
🔍 KÖK NEDEN ANALİZİ
--------------------------------------------------------------------------------
{report.get("root_cause_analysis")}

"""
        
        if report.get("recommended_actions"):
            text += """
--------------------------------------------------------------------------------
⚡ ÖNERİLEN AKSİYONLAR
--------------------------------------------------------------------------------
"""
            for i, action in enumerate(report.get("recommended_actions", []), 1):
                text += f"{i}. {action}\n"
        
        text += """
--------------------------------------------------------------------------------
📊 ANOMALİ DETAYLARI
--------------------------------------------------------------------------------
"""
        for anomaly in report.get("anomalies", [])[:20]:
            text += f"""
Zaman: {anomaly.get("timestamp", "")[:19]}
Sensör: {anomaly.get("sensor_type", "")}
Değer: {anomaly.get("current_value", 0):.2f}
Z-Score: {anomaly.get("z_score", 0):.2f}
Şiddet: {anomaly.get("severity", "")}
---
"""
        
        text += """
================================================================================
Bu rapor Anomali Tespit Sistemi tarafından otomatik olarak oluşturulmuştur.
================================================================================
"""
        return text
    
    async def send_report(
        self, 
        report: Dict[str, Any], 
        recipients: Optional[List[str]] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Anomali raporunu e-posta ile gönder
        
        Args:
            report: AnomalyReport.to_dict() çıktısı
            recipients: Alıcı e-posta adresleri (None ise kayıtlı alıcılar kullanılır)
            subject: E-posta konusu (None ise otomatik oluşturulur)
        
        Returns:
            Gönderim sonucu
        """
        # Alıcıları belirle
        if recipients:
            to_addresses = recipients
        else:
            risk_level = report.get("risk_level", "MEDIUM")
            to_addresses = [
                r.email for r in self.recipients 
                if r.should_notify(risk_level)
            ]
        
        if not to_addresses:
            logger.warning("E-posta gönderilecek alıcı bulunamadı")
            return {
                "success": False,
                "error": "Alıcı listesi boş",
                "recipients": []
            }
        
        # Konfigürasyon kontrolü
        if not self.config.username or not self.config.password:
            logger.error("SMTP kimlik bilgileri yapılandırılmamış")
            return {
                "success": False,
                "error": "SMTP kimlik bilgileri yapılandırılmamış",
                "recipients": to_addresses
            }
        
        # E-posta konusu
        risk_label = self.RISK_LABELS.get(report.get("risk_level", "MEDIUM"), "ORTA")
        if not subject:
            subject = f"🚨 [{risk_label}] Anomali Raporu - {report.get('report_id', '')}"
        
        # E-posta oluştur
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.sender_name} <{self.config.sender_email or self.config.username}>"
        msg["To"] = ", ".join(to_addresses)
        
        # Düz metin ve HTML içerik
        text_content = self._generate_plain_text_report(report)
        html_content = self._generate_html_report(report)
        
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        # JSON raporu ek olarak ekle
        json_attachment = MIMEBase("application", "json")
        json_attachment.set_payload(json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"))
        encoders.encode_base64(json_attachment)
        json_attachment.add_header(
            "Content-Disposition",
            f"attachment; filename=anomaly_report_{report.get('report_id', 'unknown')}.json"
        )
        msg.attach(json_attachment)
        
        # E-posta gönder
        try:
            result = await asyncio.to_thread(
                self._send_email_sync,
                msg,
                to_addresses
            )
            return result
        except Exception as e:
            logger.error(f"E-posta gönderim hatası: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": to_addresses
            }
    
    def _send_email_sync(self, msg: MIMEMultipart, to_addresses: List[str]) -> Dict[str, Any]:
        """Senkron e-posta gönderimi"""
        try:
            if self.config.use_ssl:
                # SSL bağlantısı
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config.host, self.config.port, context=context) as server:
                    server.login(self.config.username, self.config.password)
                    server.sendmail(
                        self.config.sender_email or self.config.username,
                        to_addresses,
                        msg.as_string()
                    )
            else:
                # TLS bağlantısı
                with smtplib.SMTP(self.config.host, self.config.port) as server:
                    if self.config.use_tls:
                        server.starttls()
                    server.login(self.config.username, self.config.password)
                    server.sendmail(
                        self.config.sender_email or self.config.username,
                        to_addresses,
                        msg.as_string()
                    )
            
            logger.info(f"E-posta başarıyla gönderildi: {to_addresses}")
            return {
                "success": True,
                "recipients": to_addresses,
                "sent_at": datetime.now().isoformat()
            }
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP kimlik doğrulama hatası")
            return {
                "success": False,
                "error": "SMTP kimlik doğrulama hatası. Kullanıcı adı veya şifre yanlış.",
                "recipients": to_addresses
            }
        except smtplib.SMTPException as e:
            logger.error(f"SMTP hatası: {e}")
            return {
                "success": False,
                "error": f"SMTP hatası: {str(e)}",
                "recipients": to_addresses
            }
    
    async def send_test_email(self, recipient: str) -> Dict[str, Any]:
        """
        Test e-postası gönder
        
        Args:
            recipient: Test e-postası alıcısı
        
        Returns:
            Gönderim sonucu
        """
        test_report = {
            "report_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "period_start": datetime.now().isoformat(),
            "period_end": datetime.now().isoformat(),
            "total_anomalies": 3,
            "risk_level": "MEDIUM",
            "summary": "Bu bir test e-postasıdır. E-posta yapılandırmanız doğru çalışıyor.",
            "affected_sensors": ["test_sensor_1", "test_sensor_2"],
            "llm_analysis": "Test analizi: E-posta sistemi başarıyla yapılandırılmış.",
            "root_cause_analysis": "Test kök neden analizi.",
            "recommended_actions": [
                "Bu bir test aksiyonudur.",
                "E-posta ayarlarınızı kontrol edin."
            ],
            "anomalies": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "sensor_type": "test_sensor",
                    "current_value": 100.0,
                    "z_score": 3.5,
                    "severity": "High"
                }
            ]
        }
        
        return await self.send_report(
            report=test_report,
            recipients=[recipient],
            subject="🧪 Test E-postası - Anomali Tespit Sistemi"
        )
    
    def is_configured(self) -> bool:
        """E-posta servisinin yapılandırılıp yapılandırılmadığını kontrol et"""
        return bool(self.config.username and self.config.password)
    
    def update_config(self, **kwargs):
        """SMTP konfigürasyonunu güncelle"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Global email service instance'ını getir veya oluştur"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def configure_email_service(config: SMTPConfig) -> EmailService:
    """Email service'i yapılandır"""
    global _email_service
    _email_service = EmailService(config=config)
    return _email_service
