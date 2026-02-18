"""
IDS/IPS orkestrator modulu.

Tam sizma tespit ve onleme,
Detect -> Block -> Record -> Respond,
gercek zamanli koruma, analitik.
"""

import logging
from typing import Any

from app.core.idsips.auto_blocker import (
    AutoBlocker,
)
from app.core.idsips.brute_force_detector import (
    BruteForceDetector,
)
from app.core.idsips.incident_recorder import (
    IDSIncidentRecorder,
)
from app.core.idsips.injection_guard import (
    InjectionGuard,
)
from app.core.idsips.network_analyzer import (
    NetworkAnalyzer,
)
from app.core.idsips.session_hijack_detector import (
    SessionHijackDetector,
)
from app.core.idsips.threat_intel_feed import (
    ThreatIntelFeed,
)
from app.core.idsips.xss_protector import (
    XSSProtector,
)

logger = logging.getLogger(__name__)


class IDSIPSOrchestrator:
    """IDS/IPS orkestrator.

    Attributes:
        network: Ag analizcisi.
        brute_force: Kaba kuvvet tespitcisi.
        injection: Enjeksiyon koruyucu.
        xss: XSS koruyucu.
        session: Oturum kacirma tespitcisi.
        blocker: Otomatik engelleyici.
        threat_intel: Tehdit istihbarati.
        recorder: Olay kaydedici.
    """

    def __init__(self) -> None:
        """Orkestratoru baslatir."""
        self.network = NetworkAnalyzer()
        self.brute_force = (
            BruteForceDetector()
        )
        self.injection = InjectionGuard()
        self.xss = XSSProtector()
        self.session = (
            SessionHijackDetector()
        )
        self.blocker = AutoBlocker()
        self.threat_intel = ThreatIntelFeed()
        self.recorder = IDSIncidentRecorder()
        logger.info(
            "IDSIPSOrchestrator baslatildi"
        )

    def analyze_request(
        self,
        source_ip: str = "",
        input_data: str = "",
        session_id: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        """Tam istek analizi yapar.

        Args:
            source_ip: Kaynak IP.
            input_data: Girdi verisi.
            session_id: Oturum ID.
            user_id: Kullanici ID.

        Returns:
            Analiz bilgisi.
        """
        try:
            threats: list[dict] = []
            blocked = False

            # IP engelli mi?
            if self.blocker.is_blocked(
                source_ip
            ):
                blocked = True
                threats.append({
                    "type": "blocked_ip",
                    "severity": "critical",
                })

            # Tehdit istihbarati kontrolu
            ioc_check = (
                self.threat_intel.check_ioc(
                    value=source_ip
                )
            )
            if ioc_check.get("matched"):
                threats.append({
                    "type": "threat_intel",
                    "severity": "critical",
                    "matches": ioc_check.get(
                        "match_count", 0
                    ),
                })

            # Injection kontrolu
            inj_check = (
                self.injection.check_all(
                    input_str=input_data,
                    source=source_ip,
                )
            )
            if inj_check.get(
                "total_detections", 0
            ) > 0:
                threats.append({
                    "type": "injection",
                    "severity": "critical",
                    "detections": inj_check[
                        "total_detections"
                    ],
                })

            # XSS kontrolu
            xss_check = self.xss.detect_xss(
                input_str=input_data,
                source=source_ip,
            )
            if xss_check.get("detected"):
                threats.append({
                    "type": "xss",
                    "severity": "high",
                    "patterns": xss_check.get(
                        "pattern_count", 0
                    ),
                })

            # Tehdit varsa kaydet
            if threats and not blocked:
                max_sev = "medium"
                for t in threats:
                    if (
                        t["severity"]
                        == "critical"
                    ):
                        max_sev = "critical"
                        break
                    if t["severity"] == "high":
                        max_sev = "high"

                self.recorder.record_incident(
                    incident_type=(
                        "request_threat"
                    ),
                    source_ip=source_ip,
                    severity=max_sev,
                    description=(
                        f"{len(threats)} "
                        f"threats detected"
                    ),
                )

            return {
                "source_ip": source_ip,
                "blocked": blocked,
                "threats": threats,
                "threat_count": len(threats),
                "safe": len(threats) == 0
                and not blocked,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def monitor_login(
        self,
        ip: str = "",
        username: str = "",
        success: bool = False,
        service: str = "",
    ) -> dict[str, Any]:
        """Giris denemesi izler.

        Args:
            ip: IP adresi.
            username: Kullanici adi.
            success: Basarili mi.
            service: Servis adi.

        Returns:
            Izleme bilgisi.
        """
        try:
            result = (
                self.brute_force.record_attempt(
                    ip=ip,
                    username=username,
                    success=success,
                    service=service,
                )
            )

            alert_generated = result.get(
                "alert_generated", False
            )
            if alert_generated:
                self.blocker.block_ip(
                    ip=ip,
                    reason="brute_force",
                    duration_minutes=60,
                )
                self.recorder.record_incident(
                    incident_type="brute_force",
                    source_ip=ip,
                    severity="high",
                    description=(
                        f"Brute force on "
                        f"{username}"
                    ),
                )

            return {
                "ip": ip,
                "username": username,
                "success": success,
                "alert": alert_generated,
                "blocked": alert_generated,
                "monitored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "monitored": False,
                "error": str(e),
            }

    def validate_session(
        self,
        session_id: str = "",
        current_ip: str = "",
        current_fingerprint: str = "",
    ) -> dict[str, Any]:
        """Oturum dogrular.

        Args:
            session_id: Oturum ID.
            current_ip: Mevcut IP.
            current_fingerprint: Mevcut izi.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            issues: list[str] = []

            ip_check = (
                self.session.check_ip_change(
                    session_id=session_id,
                    current_ip=current_ip,
                )
            )
            if ip_check.get("ip_changed"):
                issues.append("ip_changed")

            if current_fingerprint:
                fp_check = (
                    self.session.check_fingerprint(
                        session_id=session_id,
                        current_fingerprint=(
                            current_fingerprint
                        ),
                    )
                )
                if fp_check.get(
                    "fingerprint_changed"
                ):
                    issues.append(
                        "fingerprint_changed"
                    )

            if issues:
                self.recorder.record_incident(
                    incident_type=(
                        "session_hijack"
                    ),
                    source_ip=current_ip,
                    severity="critical",
                    description=(
                        f"Session {session_id}"
                        f": {', '.join(issues)}"
                    ),
                )

            return {
                "session_id": session_id,
                "issues": issues,
                "valid": len(issues) == 0,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def protect_input(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Girdiyi korur.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Koruma bilgisi.
        """
        try:
            # Injection kontrolu
            inj = self.injection.check_all(
                input_str=input_str,
                source=source,
            )
            # XSS kontrolu
            xss = self.xss.detect_xss(
                input_str=input_str,
                source=source,
            )

            threats_found = (
                inj.get(
                    "total_detections", 0
                )
                > 0
                or xss.get("detected", False)
            )

            sanitized = input_str
            if threats_found:
                san = (
                    self.injection.sanitize(
                        input_str=input_str
                    )
                )
                sanitized = san.get(
                    "sanitized", input_str
                )
                xss_san = (
                    self.xss.sanitize_html(
                        html=sanitized
                    )
                )
                sanitized = xss_san.get(
                    "sanitized", sanitized
                )

            return {
                "original": input_str,
                "sanitized": sanitized,
                "threats_found": (
                    threats_found
                ),
                "injection_check": inj,
                "xss_check": xss,
                "protected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "protected": False,
                "error": str(e),
            }

    def security_status(
        self,
    ) -> dict[str, Any]:
        """Guvenlik durumunu getirir.

        Returns:
            Durum bilgisi.
        """
        try:
            network_sum = (
                self.network.get_summary()
            )
            brute_sum = (
                self.brute_force.get_summary()
            )
            injection_sum = (
                self.injection.get_summary()
            )
            xss_sum = (
                self.xss.get_summary()
            )
            session_sum = (
                self.session.get_summary()
            )
            blocker_sum = (
                self.blocker.get_summary()
            )
            threat_sum = (
                self.threat_intel.get_summary()
            )
            incident_sum = (
                self.recorder.get_summary()
            )

            return {
                "network": network_sum,
                "brute_force": brute_sum,
                "injection": injection_sum,
                "xss": xss_sum,
                "session": session_sum,
                "blocker": blocker_sum,
                "threat_intel": threat_sum,
                "incidents": incident_sum,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir.

        Returns:
            Analitik bilgisi.
        """
        try:
            return {
                "network_anomalies": (
                    self.network.anomaly_count
                ),
                "brute_force_alerts": (
                    self.brute_force.alert_count
                ),
                "injection_detections": (
                    self.injection.detection_count
                ),
                "xss_detections": (
                    self.xss.detection_count
                ),
                "active_sessions": (
                    self.session.session_count
                ),
                "blocked_ips": (
                    self.blocker.blocked_count
                ),
                "iocs_tracked": (
                    self.threat_intel.ioc_count
                ),
                "total_incidents": (
                    self.recorder.incident_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
