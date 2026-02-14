"""ATLAS Guvenlik Orkestratoru modulu.

Tam guvenlik pipeline'i, tehdit yaniti,
olay yonetimi, guvenlik politikalari
ve surekli izleme.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.models.security_hardening import (
    AccessAction,
    AuditEventType,
    FirewallAction,
    SecuritySnapshot,
    ThreatLevel,
    ThreatType,
)

from app.core.security.access_controller import AccessController
from app.core.security.audit_logger import AuditLogger
from app.core.security.encryption_manager import EncryptionManager
from app.core.security.firewall import Firewall
from app.core.security.input_validator import InputValidator
from app.core.security.secret_manager import SecretManager
from app.core.security.session_guardian import SessionGuardian
from app.core.security.threat_detector import ThreatDetector

logger = logging.getLogger(__name__)


class SecurityOrchestrator:
    """Guvenlik orkestratoru.

    Tum guvenlik bilesenlerini koordine
    eder ve birlesik guvenlik saglar.

    Attributes:
        threat_detector: Tehdit tespiti.
        access_controller: Erisim kontrolu.
        encryption: Sifreleme.
        validator: Girdi dogrulama.
        secrets: Gizli veri yonetimi.
        sessions: Oturum yonetimi.
        firewall: Guvenlik duvari.
        audit: Denetim gunlugu.
    """

    def __init__(
        self,
        session_timeout: int = 30,
        max_login_attempts: int = 5,
        audit_retention_days: int = 90,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            session_timeout: Oturum zamanlama (dk).
            max_login_attempts: Maks giris denemesi.
            audit_retention_days: Denetim saklama suresi.
        """
        self.threat_detector = ThreatDetector(
            max_login_attempts=max_login_attempts,
        )
        self.access_controller = AccessController()
        self.encryption = EncryptionManager()
        self.validator = InputValidator()
        self.secrets = SecretManager()
        self.sessions = SessionGuardian(
            session_timeout=session_timeout,
        )
        self.firewall = Firewall()
        self.audit = AuditLogger(
            retention_days=audit_retention_days,
        )

        self._incidents: list[dict[str, Any]] = []
        self._policies: dict[str, dict[str, Any]] = {}
        self._start_time = time.time()

        logger.info("SecurityOrchestrator baslatildi")

    def process_request(
        self,
        ip: str,
        path: str,
        payload: str = "",
        country: str = "",
        user: str = "",
        token: str = "",
    ) -> dict[str, Any]:
        """Istegi tam guvenlik pipeline'indan gecirir.

        Args:
            ip: Kaynak IP.
            path: Istek yolu.
            payload: Veri yuku.
            country: Ulke kodu.
            user: Kullanici.
            token: Oturum tokeni.

        Returns:
            Pipeline sonucu.
        """
        result: dict[str, Any] = {
            "allowed": False,
            "checks": [],
        }

        # 1. Firewall kontrolu
        fw_result = self.firewall.check_request(
            ip, path, country,
        )
        result["checks"].append({
            "step": "firewall",
            "result": fw_result["action"],
        })
        if fw_result["action"] == FirewallAction.BLOCK.value:
            self.audit.log_event(
                event_type=AuditEventType.ACCESS,
                actor=ip,
                action="firewall_block",
                resource=path,
                severity=ThreatLevel.MEDIUM,
            )
            result["reason"] = f"firewall:{fw_result['reason']}"
            return result

        if fw_result["action"] == FirewallAction.RATE_LIMIT.value:
            result["reason"] = "rate_limited"
            return result

        # 2. Girdi dogrulama
        if payload:
            validation = self.validator.validate(payload)
            result["checks"].append({
                "step": "input_validation",
                "result": "safe" if validation["safe"] else "unsafe",
            })
            if not validation["safe"]:
                self.audit.log_event(
                    event_type=AuditEventType.THREAT,
                    actor=ip,
                    action="input_violation",
                    resource=path,
                    details={"violations": validation["violations"]},
                    severity=ThreatLevel.HIGH,
                )
                result["reason"] = "input_validation_failed"
                return result

        # 3. Tehdit tespiti
        threat = self.threat_detector.detect_intrusion(
            ip, path, payload,
        )
        result["checks"].append({
            "step": "threat_detection",
            "result": "clean" if not threat else "threat",
        })
        if threat:
            self._create_incident(threat.threat_id, ip, path)
            result["reason"] = "threat_detected"
            return result

        # 4. Oturum dogrulama
        if token:
            token_result = self.sessions.validate_token(
                token, ip,
            )
            result["checks"].append({
                "step": "session_validation",
                "result": "valid" if token_result["valid"] else "invalid",
            })
            if not token_result["valid"]:
                result["reason"] = (
                    f"session:{token_result.get('reason', 'invalid')}"
                )
                return result

        # 5. Tum kontrollerden gecti
        result["allowed"] = True
        result["reason"] = "all_checks_passed"
        return result

    def authenticate_user(
        self,
        user: str,
        password: str,
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Kullanici dogrulama yapar.

        Args:
            user: Kullanici.
            password: Parola.
            ip_address: IP adresi.

        Returns:
            Dogrulama sonucu.
        """
        verified = self.secrets.verify_password(user, password)

        # Brute force kontrolu
        threat = self.threat_detector.detect_brute_force(
            user, success=verified,
        )

        # Denetim kaydi
        self.audit.log_login(user, verified, ip_address)

        if threat:
            self.firewall.add_to_blacklist(ip_address)
            return {
                "authenticated": False,
                "reason": "brute_force_detected",
            }

        if not verified:
            return {
                "authenticated": False,
                "reason": "invalid_credentials",
            }

        # Oturum olustur
        session = self.sessions.create_session(
            user, ip_address,
        )
        return {
            "authenticated": True,
            "session_id": session["session_id"],
            "token": session["token"],
        }

    def check_authorization(
        self,
        user: str,
        resource: str,
        action: AccessAction,
    ) -> bool:
        """Yetkilendirme kontrolu.

        Args:
            user: Kullanici.
            resource: Kaynak.
            action: Aksiyon.

        Returns:
            Yetkili ise True.
        """
        granted = self.access_controller.check_access(
            user, resource, action,
        )
        self.audit.log_access(
            user, resource, action.value, granted,
        )
        return granted

    def add_security_policy(
        self,
        name: str,
        rules: dict[str, Any],
    ) -> dict[str, Any]:
        """Guvenlik politikasi ekler.

        Args:
            name: Politika adi.
            rules: Kurallar.

        Returns:
            Politika bilgisi.
        """
        policy = {
            "name": name,
            "rules": rules,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._policies[name] = policy

        self.audit.log_event(
            event_type=AuditEventType.POLICY,
            actor="system",
            action="policy_added",
            resource=name,
        )
        return policy

    def respond_to_threat(
        self,
        threat_type: ThreatType,
        source: str,
        severity: ThreatLevel,
    ) -> dict[str, Any]:
        """Tehdide yanit verir.

        Args:
            threat_type: Tehdit turu.
            source: Tehdit kaynagi.
            severity: Onem derecesi.

        Returns:
            Yanit bilgisi.
        """
        actions_taken: list[str] = []

        # Yuksek/kritik: IP engelle
        if severity in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            self.firewall.add_to_blacklist(source)
            actions_taken.append("ip_blacklisted")

        # Brute force: giris denemelerini sifirla
        if threat_type == ThreatType.BRUTE_FORCE:
            self.threat_detector.reset_login_attempts(source)
            actions_taken.append("attempts_reset")

        # Denetim kaydi
        self.audit.log_threat(
            source=source,
            threat_type=threat_type.value,
            severity=severity,
        )
        actions_taken.append("audit_logged")

        # Olay olustur
        incident_id = self._create_incident(
            f"threat_{threat_type.value}",
            source,
            threat_type.value,
        )

        return {
            "incident_id": incident_id,
            "threat_type": threat_type.value,
            "severity": severity.value,
            "actions_taken": actions_taken,
        }

    def get_security_snapshot(self) -> SecuritySnapshot:
        """Guvenlik goruntusunu getirir.

        Returns:
            Guvenlik goruntusu.
        """
        return SecuritySnapshot(
            total_threats=self.threat_detector.threat_count,
            blocked_threats=self.threat_detector.blocked_count,
            active_sessions=self.sessions.active_count,
            access_denials=self.access_controller.denial_count,
            audit_entries=self.audit.entry_count,
            firewall_blocks=self.firewall.blocked_count,
            encryption_operations=self.encryption.operation_count,
            secrets_managed=self.secrets.secret_count,
            uptime_seconds=time.time() - self._start_time,
        )

    def _create_incident(
        self,
        incident_type: str,
        source: str,
        target: str,
    ) -> str:
        """Olay olusturur.

        Args:
            incident_type: Olay turu.
            source: Kaynak.
            target: Hedef.

        Returns:
            Olay ID.
        """
        incident_id = f"INC-{len(self._incidents) + 1:04d}"
        incident = {
            "id": incident_id,
            "type": incident_type,
            "source": source,
            "target": target,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._incidents.append(incident)
        return incident_id

    @property
    def incident_count(self) -> int:
        """Olay sayisi."""
        return len(self._incidents)

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)
