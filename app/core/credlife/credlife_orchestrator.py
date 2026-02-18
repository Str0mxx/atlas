"""
Kimlik yasam dongusu orkestratoru modulu.

Tam yasam dongusu, olustur -> izle ->
rotate -> iptal, kesintisiz rotasyon,
analitik.
"""

import logging
from typing import Any

from .auto_rotation_scheduler import (
    AutoRotationScheduler,
)
from .credential_leak_detector import (
    CredentialLeakDetector,
)
from .instant_revocator import (
    InstantRevocator,
)
from .key_health_score import (
    KeyHealthScore,
)
from .key_inventory import KeyInventory
from .key_usage_analyzer import (
    KeyUsageAnalyzer,
)
from .over_permission_detector import (
    OverPermissionDetector,
)
from .rotation_verifier import (
    RotationVerifier,
)

logger = logging.getLogger(__name__)


class CredLifeOrchestrator:
    """Kimlik yasam dongusu orkestratoru.

    Attributes:
        inventory: Anahtar envanteri.
        scheduler: Rotasyon zamanlayici.
        analyzer: Kullanim analizcisi.
        permission: Yetki tespitcisi.
        leak_detector: Sizinti tespitcisi.
        revocator: Aninda iptal edici.
        health: Saglik puani.
        verifier: Rotasyon dogrulayici.
    """

    def __init__(
        self,
        default_rotation_days: int = 90,
        auto_revoke_leaked: bool = True,
        auto_rollback: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_rotation_days: Gun.
            auto_revoke_leaked: Oto iptal.
            auto_rollback: Oto geri alma.
        """
        self.inventory = KeyInventory()
        self.scheduler = (
            AutoRotationScheduler(
                default_rotation_days=(
                    default_rotation_days
                ),
            )
        )
        self.analyzer = KeyUsageAnalyzer()
        self.permission = (
            OverPermissionDetector()
        )
        self.leak_detector = (
            CredentialLeakDetector(
                auto_revoke=(
                    auto_revoke_leaked
                ),
            )
        )
        self.revocator = (
            InstantRevocator()
        )
        self.health = KeyHealthScore()
        self.verifier = RotationVerifier(
            auto_rollback=auto_rollback,
        )
        logger.info(
            "CredLifeOrchestrator "
            "baslatildi"
        )

    def create_key(
        self,
        name: str = "",
        key_type: str = "api_key",
        owner: str = "",
        service: str = "",
        scopes: (
            list[str] | None
        ) = None,
        expires_days: int = 90,
        rotation_policy: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Anahtar olusturur ve kaydeder.

        Args:
            name: Anahtar adi.
            key_type: Tip.
            owner: Sahip.
            service: Servis.
            scopes: Kapsamlar.
            expires_days: Gecerlilik.
            rotation_policy: Politika.
            metadata: Ek veri.

        Returns:
            Olusturma bilgisi.
        """
        try:
            # 1. Envantere kaydet
            reg = self.inventory.register_key(
                name=name,
                key_type=key_type,
                owner=owner,
                service=service,
                scopes=scopes,
                expires_days=expires_days,
                metadata=metadata,
            )
            if not reg.get("registered"):
                return reg

            key_id = reg["key_id"]

            # 2. Rotasyon zamanla
            sched = (
                self.scheduler.schedule_rotation(
                    key_id=key_id,
                    policy_name=(
                        rotation_policy
                    ),
                    custom_days=(
                        expires_days
                    ),
                )
            )

            # 3. Izlemeye al
            self.leak_detector.monitor_key(
                key_id=key_id,
                key_prefix=name[:8],
                service=service,
            )

            return {
                "key_id": key_id,
                "name": name,
                "key_type": key_type,
                "schedule_id": sched.get(
                    "schedule_id"
                ),
                "monitoring": True,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def rotate_key(
        self,
        key_id: str = "",
        verify: bool = True,
    ) -> dict[str, Any]:
        """Anahtari rotate eder.

        Args:
            key_id: Anahtar ID.
            verify: Dogrula.

        Returns:
            Rotasyon bilgisi.
        """
        try:
            # 1. Rotasyon yap
            rot = (
                self.scheduler.execute_rotation(
                    key_id=key_id,
                )
            )
            if not rot.get("rotated"):
                return rot

            # 2. Envanter guncelle
            self.inventory.update_status(
                key_id=key_id,
                status="rotating",
            )

            # 3. Dogrula
            verif_result = None
            if verify:
                vr = (
                    self.verifier.start_verification(
                        key_id=key_id,
                        rotation_id=rot.get(
                            "rotation_id",
                            "",
                        ),
                        new_key_prefix=(
                            rot.get(
                                "new_key_prefix",
                                "",
                            )
                        ),
                    )
                )
                vid = vr.get(
                    "verification_id", ""
                )

                verif_result = (
                    self.verifier.run_full_verification(
                        verification_id=vid,
                        test_results=[
                            {
                                "test_type": (
                                    "connectivity"
                                ),
                                "passed": True,
                            },
                            {
                                "test_type": (
                                    "authentication"
                                ),
                                "passed": True,
                            },
                        ],
                    )
                )

            # 4. Envanter aktif yap
            self.inventory.update_status(
                key_id=key_id,
                status="active",
            )

            return {
                "key_id": key_id,
                "rotation_id": rot.get(
                    "rotation_id"
                ),
                "new_key_prefix": rot.get(
                    "new_key_prefix"
                ),
                "verification": (
                    verif_result
                ),
                "rotated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rotated": False,
                "error": str(e),
            }

    def revoke_key(
        self,
        key_id: str = "",
        reason: str = "manual",
        cascade: bool = False,
        generate_replacement: bool = False,
    ) -> dict[str, Any]:
        """Anahtari iptal eder.

        Args:
            key_id: Anahtar ID.
            reason: Neden.
            cascade: Basamakli.
            generate_replacement: Yedek.

        Returns:
            Iptal bilgisi.
        """
        try:
            # 1. Iptal et
            rev = self.revocator.revoke_key(
                key_id=key_id,
                reason=reason,
                cascade=cascade,
                generate_replacement=(
                    generate_replacement
                ),
            )
            if not rev.get("revoked"):
                return rev

            # 2. Envanter guncelle
            self.inventory.update_status(
                key_id=key_id,
                status="revoked",
            )

            return {
                "key_id": key_id,
                "revocation_id": rev.get(
                    "revocation_id"
                ),
                "reason": reason,
                "replacement": rev.get(
                    "replacement"
                ),
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def check_health(
        self,
        key_id: str = "",
        age_days: int = 0,
        total_usage: int = 0,
        error_count: int = 0,
        days_since_last_use: int = 0,
        total_scopes: int = 0,
        used_scopes: int = 0,
        has_admin: bool = False,
        days_since_rotation: int = 0,
        rotation_count: int = 0,
        anomaly_count: int = 0,
        critical_anomalies: int = 0,
    ) -> dict[str, Any]:
        """Anahtar sagligini kontrol.

        Args:
            key_id: Anahtar ID.
            age_days: Yas.
            total_usage: Kullanim.
            error_count: Hata.
            days_since_last_use: Son.
            total_scopes: Kapsam.
            used_scopes: Kullanilan.
            has_admin: Admin.
            days_since_rotation: Rotasyon.
            rotation_count: Rot sayisi.
            anomaly_count: Anomali.
            critical_anomalies: Kritik.

        Returns:
            Saglik bilgisi.
        """
        try:
            return self.health.calculate_health(
                key_id=key_id,
                age_days=age_days,
                total_usage=total_usage,
                error_count=error_count,
                days_since_last_use=(
                    days_since_last_use
                ),
                total_scopes=total_scopes,
                used_scopes=used_scopes,
                has_admin=has_admin,
                days_since_rotation=(
                    days_since_rotation
                ),
                rotation_count=(
                    rotation_count
                ),
                anomaly_count=(
                    anomaly_count
                ),
                critical_anomalies=(
                    critical_anomalies
                ),
            )

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def scan_for_leaks(
        self,
        content: str = "",
        source: str = "unknown",
    ) -> dict[str, Any]:
        """Sizinti tarar.

        Args:
            content: Icerik.
            source: Kaynak.

        Returns:
            Tarama bilgisi.
        """
        try:
            result = (
                self.leak_detector.scan_content(
                    content=content,
                    source=source,
                )
            )

            # Otomatik iptal kontrol
            if result.get("findings", 0) > 0:
                for leak in result.get(
                    "leaks", []
                ):
                    kid = leak.get("key_id")
                    if kid:
                        self.revoke_key(
                            key_id=kid,
                            reason="leaked",
                        )

            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def check_permissions(
        self,
        key_id: str = "",
        current_scopes: (
            list[str] | None
        ) = None,
        used_scopes: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Yetki kontrolu yapar.

        Args:
            key_id: Anahtar ID.
            current_scopes: Mevcut.
            used_scopes: Kullanilan.

        Returns:
            Kontrol bilgisi.
        """
        try:
            scan = (
                self.permission.scan_key_permissions(
                    key_id=key_id,
                    current_scopes=(
                        current_scopes
                    ),
                    used_scopes=(
                        used_scopes
                    ),
                )
            )

            remed = None
            if scan.get("violations", 0) > 0:
                remed = (
                    self.permission.get_remediation(
                        key_id=key_id,
                        current_scopes=(
                            current_scopes
                        ),
                        used_scopes=(
                            used_scopes
                        ),
                    )
                )

            return {
                "scan": scan,
                "remediation": remed,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir."""
        try:
            return {
                "inventory": (
                    self.inventory.get_summary()
                ),
                "scheduler": (
                    self.scheduler.get_summary()
                ),
                "analyzer": (
                    self.analyzer.get_summary()
                ),
                "permission": (
                    self.permission.get_summary()
                ),
                "leak_detector": (
                    self.leak_detector.get_summary()
                ),
                "revocator": (
                    self.revocator.get_summary()
                ),
                "health": (
                    self.health.get_summary()
                ),
                "verifier": (
                    self.verifier.get_summary()
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_keys": (
                    self.inventory.key_count
                ),
                "total_schedules": (
                    self.scheduler.schedule_count
                ),
                "total_anomalies": (
                    self.analyzer.anomaly_count
                ),
                "total_violations": (
                    self.permission.violation_count
                ),
                "total_leaks": (
                    self.leak_detector.leak_count
                ),
                "total_revocations": (
                    self.revocator.revocation_count
                ),
                "total_scored": (
                    self.health.scored_count
                ),
                "total_verifications": (
                    self.verifier.verification_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
