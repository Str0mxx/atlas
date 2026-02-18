"""
Port tarayici modulu.

Acik port tespiti, servis tanimlama,
gereksiz servisler, firewall dogrulama,
ag guvenligi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PortScanner:
    """Port tarayici.

    Attributes:
        _scans: Tarama kayitlari.
        _ports: Port kayitlari.
        _rules: Firewall kural kayitlari.
        _stats: Istatistikler.
    """

    WELL_KNOWN_SERVICES: dict[int, str] = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        25: "SMTP",
        53: "DNS",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        3306: "MySQL",
        3389: "RDP",
        5432: "PostgreSQL",
        6379: "Redis",
        8080: "HTTP-Alt",
        8443: "HTTPS-Alt",
        27017: "MongoDB",
    }

    RISKY_PORTS: list[int] = [
        21, 23, 25, 110, 143,
        3389, 27017,
    ]

    def __init__(self) -> None:
        """Tarayiciyi baslatir."""
        self._scans: list[dict] = []
        self._ports: dict[str, list[dict]] = {}
        self._rules: list[dict] = []
        self._stats: dict[str, int] = {
            "scans_done": 0,
            "open_ports_found": 0,
            "risky_ports_found": 0,
        }
        logger.info(
            "PortScanner baslatildi"
        )

    @property
    def scan_count(self) -> int:
        """Tarama sayisi."""
        return len(self._scans)

    def scan_ports(
        self,
        host: str = "",
        ports: list[int] | None = None,
    ) -> dict[str, Any]:
        """Port tarar.

        Args:
            host: Hedef host.
            ports: Taranacak portlar.

        Returns:
            Tarama bilgisi.
        """
        try:
            sid = f"ps_{uuid4()!s:.8}"
            scan_ports = (
                ports
                or list(
                    self.WELL_KNOWN_SERVICES.keys()
                )
            )
            open_ports: list[dict] = []

            for port in scan_ports:
                service = (
                    self.WELL_KNOWN_SERVICES.get(
                        port, "unknown"
                    )
                )
                risky = port in self.RISKY_PORTS
                entry = {
                    "port": port,
                    "service": service,
                    "state": "open",
                    "risky": risky,
                }
                open_ports.append(entry)
                if risky:
                    self._stats[
                        "risky_ports_found"
                    ] += 1

            self._ports[host] = open_ports
            self._stats[
                "open_ports_found"
            ] += len(open_ports)

            scan = {
                "scan_id": sid,
                "host": host,
                "ports_scanned": len(
                    scan_ports
                ),
                "open_count": len(open_ports),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._scans.append(scan)
            self._stats["scans_done"] += 1

            return {
                "scan_id": sid,
                "host": host,
                "open_ports": open_ports,
                "total_open": len(open_ports),
                "scanned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def identify_service(
        self,
        port: int = 0,
    ) -> dict[str, Any]:
        """Servis tanimlar.

        Args:
            port: Port numarasi.

        Returns:
            Servis bilgisi.
        """
        try:
            service = (
                self.WELL_KNOWN_SERVICES.get(
                    port, "unknown"
                )
            )
            risky = port in self.RISKY_PORTS

            return {
                "port": port,
                "service": service,
                "risky": risky,
                "identified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "identified": False,
                "error": str(e),
            }

    def check_unnecessary_services(
        self,
        host: str = "",
        required_ports: (
            list[int] | None
        ) = None,
    ) -> dict[str, Any]:
        """Gereksiz servisleri kontrol eder.

        Args:
            host: Hedef host.
            required_ports: Gerekli portlar.

        Returns:
            Kontrol bilgisi.
        """
        try:
            needed = required_ports or [
                22, 80, 443,
            ]
            host_ports = self._ports.get(
                host, []
            )
            unnecessary = [
                p
                for p in host_ports
                if p["port"] not in needed
            ]

            return {
                "host": host,
                "unnecessary": unnecessary,
                "count": len(unnecessary),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def add_firewall_rule(
        self,
        port: int = 0,
        action: str = "block",
        protocol: str = "tcp",
        source: str = "any",
    ) -> dict[str, Any]:
        """Firewall kurali ekler.

        Args:
            port: Port numarasi.
            action: Aksiyon (allow/block).
            protocol: Protokol.
            source: Kaynak.

        Returns:
            Kural bilgisi.
        """
        try:
            rid = f"fr_{uuid4()!s:.8}"
            rule = {
                "rule_id": rid,
                "port": port,
                "action": action,
                "protocol": protocol,
                "source": source,
                "active": True,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._rules.append(rule)

            return {
                "rule_id": rid,
                "port": port,
                "action": action,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def validate_firewall(
        self,
        host: str = "",
    ) -> dict[str, Any]:
        """Firewall dogrular.

        Args:
            host: Hedef host.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            host_ports = self._ports.get(
                host, []
            )
            blocked_ports = {
                r["port"]
                for r in self._rules
                if r["action"] == "block"
                and r["active"]
            }
            violations = [
                p
                for p in host_ports
                if p["port"] in blocked_ports
            ]

            return {
                "host": host,
                "violations": violations,
                "violation_count": len(
                    violations
                ),
                "compliant": len(violations)
                == 0,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            all_ports = []
            for ports in self._ports.values():
                all_ports.extend(ports)
            risky = [
                p
                for p in all_ports
                if p["risky"]
            ]

            return {
                "total_scans": len(
                    self._scans
                ),
                "total_hosts": len(
                    self._ports
                ),
                "total_open_ports": len(
                    all_ports
                ),
                "risky_ports": len(risky),
                "firewall_rules": len(
                    self._rules
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
