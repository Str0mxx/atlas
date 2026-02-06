"""Sunucu guvenlik izleme agent modulu.

SSH uzerinden sunucu guvenlik durumunu tarar:
- auth.log / syslog analizi (basarisiz giris tespiti)
- Fail2ban entegrasyonu (IP engelleme)
- Acik port taramasi
- SSL sertifika kontrolu
- Supehli process tespiti

Sonuclari risk/aciliyet olarak siniflandirir ve karar matrisine iletir.
"""

import re
import logging
from collections import defaultdict
from typing import Any

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
from app.models.security import (
    BannedIPEntry,
    FailedLoginEntry,
    OpenPort,
    SecurityCheckType,
    SecurityScanConfig,
    SecurityScanResult,
    SSLCertInfo,
    SuspiciousProcess,
    ThreatLevel,
)
from app.models.server import ServerConfig
from app.tools.ssh_manager import SSHManager

logger = logging.getLogger("atlas.agent.security")


class SecurityAgent(BaseAgent):
    """Sunucu guvenlik izleme agent'i.

    SSH uzerinden sunucularin guvenlik durumunu tarar,
    tehditleri siniflandirir ve karar matrisine entegre eder.

    Attributes:
        servers: Taranacak sunucu yapilandirmalari.
        scan_config: Tarama yapilandirmasi.
    """

    def __init__(
        self,
        servers: list[ServerConfig] | None = None,
        scan_config: SecurityScanConfig | None = None,
    ) -> None:
        """SecurityAgent'i baslatir.

        Args:
            servers: Taranacak sunucu listesi.
                Bos ise config'den varsayilan sunucu eklenir.
            scan_config: Guvenlik taramasi yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="security")
        self.scan_config = scan_config or SecurityScanConfig()
        self.servers: list[ServerConfig] = list(servers) if servers else []

        # Config'den varsayilan sunucu ekle
        if not self.servers and settings.ssh_default_host:
            self.servers.append(
                ServerConfig(
                    host=settings.ssh_default_host,
                    user=settings.ssh_default_user or "root",
                    key_path=settings.ssh_default_key_path,
                )
            )

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Guvenlik taramasini calistirir.

        Args:
            task: Gorev detaylari. Opsiyonel anahtarlar:
                - servers: Ek sunucu listesi (dict listesi).
                - scan_config: Ozel tarama yapilandirmasi (dict).
                - checks: Calistirilacak kontrol tipleri (str listesi).

        Returns:
            Tum sunucularin guvenlik tarama sonuclarini iceren TaskResult.
        """
        # Task'tan ek sunucu ve yapilandirma al
        extra_servers = [
            ServerConfig(**s) for s in task.get("servers", [])
        ]
        if task.get("scan_config"):
            self.scan_config = SecurityScanConfig(**task["scan_config"])
        if task.get("checks"):
            self.scan_config.checks = [
                SecurityCheckType(c) for c in task["checks"]
            ]

        all_servers = self.servers + extra_servers
        if not all_servers:
            return TaskResult(
                success=False,
                message="Taranacak sunucu yapilandirilmamis.",
                errors=["Sunucu listesi bos."],
            )

        # Her sunucuyu tara
        self.logger.info("%d sunucu guvenlik taramasi baslatiliyor...", len(all_servers))
        all_results: dict[str, Any] = {}
        errors: list[str] = []

        for server in all_servers:
            try:
                scan_result = await self._scan_server(server)
                all_results[server.host] = scan_result.model_dump()
            except Exception as exc:
                self.logger.error("Guvenlik tarama hatasi [%s]: %s", server.host, exc)
                errors.append(f"{server.host}: {exc}")
                all_results[server.host] = SecurityScanResult(
                    threat_level=ThreatLevel.HIGH,
                    summary=f"Tarama basarisiz: {exc}",
                ).model_dump()

        # Analiz et
        analysis = await self.analyze({"scan_results": all_results})

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "scan_results": all_results,
                "analysis": analysis,
            },
            message=analysis.get("summary", "Guvenlik taramasi tamamlandi."),
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Guvenlik Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Tarama sonuclarini analiz eder ve risk/aciliyet belirler.

        Args:
            data: {"scan_results": {host: SecurityScanResult dict}}.

        Returns:
            Analiz sonuclari: risk, urgency, action, threat_level, summary, details.
        """
        scan_results = data.get("scan_results", {})
        worst_threat = ThreatLevel.NONE
        details: list[dict[str, Any]] = []
        total_failed_logins = 0
        total_unexpected_ports = 0
        total_suspicious_procs = 0
        has_ssl_issue = False
        has_fail2ban_down = False

        for host, result_dict in scan_results.items():
            result = SecurityScanResult(**result_dict) if isinstance(result_dict, dict) else result_dict

            host_issues: list[str] = []

            # Basarisiz giris analizi
            if result.total_failed_attempts > 0:
                total_failed_logins += result.total_failed_attempts
                top_ips = sorted(result.failed_logins, key=lambda x: x.count, reverse=True)[:5]
                for entry in top_ips:
                    host_issues.append(
                        f"Basarisiz giris: {entry.ip} ({entry.count}x, user={entry.username})"
                    )

            # Fail2ban durumu
            if not result.fail2ban_active:
                has_fail2ban_down = True
                host_issues.append("Fail2ban AKTIF DEGIL!")

            if result.banned_ips:
                host_issues.append(f"Engellenen IP sayisi: {len(result.banned_ips)}")

            # Beklenmeyen portlar
            if result.unexpected_ports:
                total_unexpected_ports += len(result.unexpected_ports)
                for port_info in result.unexpected_ports:
                    host_issues.append(
                        f"Beklenmeyen port: {port_info.port}/{port_info.protocol} "
                        f"({port_info.process or 'bilinmiyor'})"
                    )

            # SSL sorunlari
            for cert in result.ssl_certs:
                if not cert.is_valid:
                    has_ssl_issue = True
                    host_issues.append(f"SSL GECERSIZ: {cert.domain}")
                elif cert.days_remaining <= 30:
                    has_ssl_issue = True
                    host_issues.append(
                        f"SSL yakinda dolacak: {cert.domain} ({cert.days_remaining} gun)"
                    )

            # Supehli process'ler
            if result.suspicious_processes:
                total_suspicious_procs += len(result.suspicious_processes)
                for proc in result.suspicious_processes:
                    host_issues.append(
                        f"Supehli process: {proc.command} (PID={proc.pid}, "
                        f"user={proc.user}, neden={proc.reason})"
                    )

            # Host tehdit seviyesi
            worst_threat = self._worst_threat(worst_threat, result.threat_level)

            details.append({
                "host": host,
                "threat_level": result.threat_level.value,
                "issues": host_issues if host_issues else ["Guvenlik kontrolu temiz"],
            })

        # Risk ve aciliyet eslestirmesi
        risk, urgency = self._map_to_risk_urgency(
            worst_threat=worst_threat,
            total_failed_logins=total_failed_logins,
            total_unexpected_ports=total_unexpected_ports,
            total_suspicious_procs=total_suspicious_procs,
            has_ssl_issue=has_ssl_issue,
            has_fail2ban_down=has_fail2ban_down,
        )
        action = self._determine_action(risk, urgency)

        # Ozet olustur
        total_hosts = len(scan_results)
        threat_hosts = sum(
            1 for d in details if d["threat_level"] not in (ThreatLevel.NONE.value, ThreatLevel.LOW.value)
        )

        if worst_threat == ThreatLevel.NONE:
            summary = f"Tum sunucular guvenli ({total_hosts}/{total_hosts} temiz)."
        elif worst_threat == ThreatLevel.LOW:
            summary = f"Dusuk seviye bulgular mevcut ({total_hosts} sunucu taranadi)."
        elif worst_threat == ThreatLevel.MEDIUM:
            summary = f"{threat_hosts}/{total_hosts} sunucuda orta seviye tehdit tespit edildi."
        elif worst_threat == ThreatLevel.HIGH:
            summary = f"{threat_hosts}/{total_hosts} sunucuda yuksek tehdit tespit edildi!"
        else:
            summary = f"KRITIK: {threat_hosts}/{total_hosts} sunucuda kritik tehdit!"

        return {
            "threat_level": worst_threat.value,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": summary,
            "details": details,
            "stats": {
                "total_failed_logins": total_failed_logins,
                "total_unexpected_ports": total_unexpected_ports,
                "total_suspicious_procs": total_suspicious_procs,
                "has_ssl_issue": has_ssl_issue,
                "has_fail2ban_down": has_fail2ban_down,
            },
        }

    async def report(self, result: TaskResult) -> str:
        """Guvenlik tarama sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        details = analysis.get("details", [])
        stats = analysis.get("stats", {})

        lines = [
            "=== GUVENLIK TARAMA RAPORU ===",
            f"Tehdit Seviyesi: {analysis.get('threat_level', 'bilinmiyor').upper()}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
            "--- Istatistikler ---",
            f"  Toplam basarisiz giris: {stats.get('total_failed_logins', 0)}",
            f"  Beklenmeyen acik port: {stats.get('total_unexpected_ports', 0)}",
            f"  Supehli process: {stats.get('total_suspicious_procs', 0)}",
            f"  SSL sorunu: {'Evet' if stats.get('has_ssl_issue') else 'Hayir'}",
            f"  Fail2ban: {'KAPALI!' if stats.get('has_fail2ban_down') else 'Aktif'}",
            "",
        ]

        for detail in details:
            host = detail.get("host", "?")
            threat = detail.get("threat_level", "?").upper()
            issues = detail.get("issues", [])
            lines.append(f"--- {host} [{threat}] ---")
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Dahili metodlar ===

    async def _scan_server(self, server: ServerConfig) -> SecurityScanResult:
        """Tek bir sunucunun guvenlik taramasini yapar.

        Args:
            server: Sunucu yapilandirmasi.

        Returns:
            Guvenlik tarama sonucu.
        """
        host = server.host
        self.logger.info("Guvenlik taramasi baslatiliyor: %s", host)

        async with SSHManager(
            host=server.host,
            user=server.user,
            key_path=server.key_path,
            port=server.port,
        ) as ssh:
            scan_result = SecurityScanResult()
            checks = self.scan_config.checks

            # 1. Log analizi
            if SecurityCheckType.AUTH_LOG in checks:
                self.logger.info("[%s] Auth log analizi...", host)
                await self._analyze_auth_logs(ssh, scan_result)

            # 2. Fail2ban kontrolu
            if SecurityCheckType.FAIL2BAN in checks:
                self.logger.info("[%s] Fail2ban kontrolu...", host)
                await self._check_fail2ban(ssh, scan_result)

            # 3. Acik port taramasi
            if SecurityCheckType.OPEN_PORTS in checks:
                self.logger.info("[%s] Port taramasi...", host)
                await self._scan_open_ports(ssh, scan_result)

            # 4. SSL sertifika kontrolu
            if SecurityCheckType.SSL_CERT in checks:
                self.logger.info("[%s] SSL sertifika kontrolu...", host)
                await self._check_ssl_certs(ssh, scan_result)

            # 5. Supehli process tespiti
            if SecurityCheckType.SUSPICIOUS_PROCESS in checks:
                self.logger.info("[%s] Supehli process taramasi...", host)
                await self._detect_suspicious_processes(ssh, scan_result)

            # Genel tehdit seviyesini hesapla
            scan_result.threat_level = self._calculate_threat_level(scan_result)
            scan_result.summary = self._build_scan_summary(host, scan_result)

            self.logger.info(
                "[%s] Tarama tamamlandi: tehdit=%s",
                host,
                scan_result.threat_level.value,
            )
            return scan_result

    async def _analyze_auth_logs(
        self, ssh: SSHManager, result: SecurityScanResult
    ) -> None:
        """auth.log dosyasini analiz eder ve basarisiz girisleri tespit eder.

        Args:
            ssh: Aktif SSH baglantisi.
            result: Sonuclarin yazilacagi SecurityScanResult.
        """
        # Son 1000 satiri al (performans icin)
        log_path = self.scan_config.auth_log_path
        stdout, stderr, code = await ssh.execute_command(
            f"tail -n 1000 {log_path} 2>/dev/null || "
            f"tail -n 1000 /var/log/secure 2>/dev/null || echo ''"
        )

        if not stdout.strip():
            self.logger.warning("Auth log bos veya erisilemez: %s", log_path)
            return

        # Basarisiz SSH giris denemelerini say (IP bazli)
        # Ornek: "Failed password for root from 192.168.1.100 port 22 ssh2"
        # Ornek: "Failed password for invalid user admin from 10.0.0.1 port 22"
        failed_pattern = re.compile(
            r"Failed password for (?:invalid user )?(\S+) from (\S+)"
        )
        ip_attempts: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "usernames": set(), "last_line": ""}
        )

        for line in stdout.splitlines():
            match = failed_pattern.search(line)
            if match:
                username = match.group(1)
                ip = match.group(2)
                ip_attempts[ip]["count"] += 1
                ip_attempts[ip]["usernames"].add(username)
                ip_attempts[ip]["last_line"] = line.strip()

        # Sonuclari modele yaz
        total = 0
        for ip, info in sorted(ip_attempts.items(), key=lambda x: x[1]["count"], reverse=True):
            total += info["count"]
            result.failed_logins.append(
                FailedLoginEntry(
                    ip=ip,
                    username=", ".join(info["usernames"]),
                    count=info["count"],
                    last_attempt=info["last_line"][:200],
                    service="sshd",
                )
            )
        result.total_failed_attempts = total

    async def _check_fail2ban(
        self, ssh: SSHManager, result: SecurityScanResult
    ) -> None:
        """Fail2ban durumunu ve engellenen IP'leri kontrol eder.

        Args:
            ssh: Aktif SSH baglantisi.
            result: Sonuclarin yazilacagi SecurityScanResult.
        """
        # Fail2ban aktif mi?
        stdout, _, code = await ssh.execute_command(
            "systemctl is-active fail2ban 2>/dev/null"
        )
        result.fail2ban_active = stdout.strip() == "active" and code == 0

        if not result.fail2ban_active:
            self.logger.warning("Fail2ban aktif degil!")
            return

        # Engellenen IP'leri listele
        stdout, _, code = await ssh.execute_command(
            "fail2ban-client status sshd 2>/dev/null"
        )
        if code != 0:
            # sshd jail yoksa diger jail'leri dene
            stdout, _, code = await ssh.execute_command(
                "fail2ban-client status 2>/dev/null"
            )
            if code != 0:
                return

        # "Banned IP list:" satirindan IP'leri ayristir
        banned_pattern = re.compile(r"Banned IP list:\s*(.*)")
        for line in stdout.splitlines():
            match = banned_pattern.search(line)
            if match:
                ips = match.group(1).strip().split()
                for ip in ips:
                    ip = ip.strip()
                    if ip:
                        result.banned_ips.append(
                            BannedIPEntry(ip=ip, jail="sshd")
                        )

    async def _scan_open_ports(
        self, ssh: SSHManager, result: SecurityScanResult
    ) -> None:
        """Acik portlari tarar ve beklenmeyen portlari tespit eder.

        Args:
            ssh: Aktif SSH baglantisi.
            result: Sonuclarin yazilacagi SecurityScanResult.
        """
        # ss ile dinleyen portlari listele
        stdout, _, code = await ssh.execute_command(
            "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null"
        )
        if code != 0 or not stdout.strip():
            self.logger.warning("Port taramasi basarisiz (ss/netstat)")
            return

        allowed = set(self.scan_config.allowed_ports)

        # ss ciktisi ornegi:
        # LISTEN  0  128  0.0.0.0:22  0.0.0.0:*  users:(("sshd",pid=1234,fd=3))
        port_pattern = re.compile(
            r"(?:LISTEN\s+\S+\s+\S+\s+\S+:(\d+)\s+\S+\s*(.*))"
            r"|"
            r"(?:tcp\s+\S+\s+\S+\s+\S+:(\d+)\s+\S+\s*(.*))"
        )

        for line in stdout.splitlines():
            match = port_pattern.search(line)
            if not match:
                continue

            port_str = match.group(1) or match.group(3)
            extra = match.group(2) or match.group(4) or ""
            if not port_str:
                continue

            try:
                port_num = int(port_str)
            except ValueError:
                continue

            # Process bilgisini ayristir
            process_name = ""
            pid = 0
            proc_match = re.search(r'"(\w+)".*?pid=(\d+)', extra)
            if proc_match:
                process_name = proc_match.group(1)
                pid = int(proc_match.group(2))

            is_expected = port_num in allowed
            port_entry = OpenPort(
                port=port_num,
                protocol="tcp",
                process=process_name,
                pid=pid,
                is_expected=is_expected,
            )
            result.open_ports.append(port_entry)

            if not is_expected:
                result.unexpected_ports.append(port_entry)

    async def _check_ssl_certs(
        self, ssh: SSHManager, result: SecurityScanResult
    ) -> None:
        """SSL sertifika gecerliligini kontrol eder.

        Args:
            ssh: Aktif SSH baglantisi.
            result: Sonuclarin yazilacagi SecurityScanResult.
        """
        domains = self.scan_config.ssl_domains
        if not domains:
            self.logger.debug("SSL kontrolu icin domain tanimlanmamis")
            return

        for domain in domains:
            cert_info = SSLCertInfo(domain=domain)

            # openssl ile sertifika bilgisi al
            stdout, stderr, code = await ssh.execute_command(
                f"echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null "
                f"| openssl x509 -noout -dates -issuer 2>/dev/null"
            )

            if code != 0 or not stdout.strip():
                cert_info.is_valid = False
                cert_info.days_remaining = 0
                result.ssl_certs.append(cert_info)
                continue

            # Issuer ayristir
            issuer_match = re.search(r"issuer\s*=\s*(.+)", stdout)
            if issuer_match:
                cert_info.issuer = issuer_match.group(1).strip()

            # Son kullanma tarihi ayristir
            expiry_match = re.search(r"notAfter\s*=\s*(.+)", stdout)
            if expiry_match:
                cert_info.expiry_date = expiry_match.group(1).strip()

                # Kalan gun hesapla
                days_stdout, _, _ = await ssh.execute_command(
                    f'echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null '
                    f'| openssl x509 -noout -checkend 0 2>/dev/null; '
                    f'EXPIRY=$(echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null '
                    f'| openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2); '
                    f'echo $(( ($(date -d "$EXPIRY" +%s) - $(date +%s)) / 86400 ))'
                )
                try:
                    days = int(days_stdout.strip().splitlines()[-1])
                    cert_info.days_remaining = days
                    cert_info.is_valid = days > 0
                except (ValueError, IndexError):
                    self.logger.warning(
                        "SSL kalan gun hesaplanamadi [%s]: %s", domain, days_stdout
                    )

            result.ssl_certs.append(cert_info)

    async def _detect_suspicious_processes(
        self, ssh: SSHManager, result: SecurityScanResult
    ) -> None:
        """Supehli process'leri tespit eder.

        Args:
            ssh: Aktif SSH baglantisi.
            result: Sonuclarin yazilacagi SecurityScanResult.
        """
        # Tum process'leri listele
        stdout, _, code = await ssh.execute_command(
            "ps aux --no-headers 2>/dev/null"
        )
        if code != 0 or not stdout.strip():
            self.logger.warning("Process listesi alinamadi")
            return

        suspicious_cmds = set(self.scan_config.suspicious_commands)

        for line in stdout.splitlines():
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue

            user = parts[0]
            pid = int(parts[1]) if parts[1].isdigit() else 0
            cpu_pct = float(parts[2]) if self._is_float(parts[2]) else 0.0
            mem_pct = float(parts[3]) if self._is_float(parts[3]) else 0.0
            command = parts[10]
            cmd_base = command.split()[0].split("/")[-1] if command else ""

            reasons: list[str] = []

            # Bilinen supehli komut mu?
            if cmd_base in suspicious_cmds:
                reasons.append(f"bilinen supehli komut: {cmd_base}")

            # Asiri kaynak kullanan process (CPU > 90% veya MEM > 80%)
            if cpu_pct > 90.0:
                reasons.append(f"yuksek CPU: %{cpu_pct:.1f}")
            if mem_pct > 80.0:
                reasons.append(f"yuksek bellek: %{mem_pct:.1f}")

            if reasons:
                result.suspicious_processes.append(
                    SuspiciousProcess(
                        pid=pid,
                        user=user,
                        command=command[:200],
                        cpu_percent=cpu_pct,
                        mem_percent=mem_pct,
                        reason="; ".join(reasons),
                    )
                )

    def _calculate_threat_level(self, result: SecurityScanResult) -> ThreatLevel:
        """Tarama sonuclarina gore genel tehdit seviyesini hesaplar.

        Args:
            result: Guvenlik tarama sonucu.

        Returns:
            Genel tehdit seviyesi.
        """
        level = ThreatLevel.NONE
        threshold = self.scan_config.failed_login_threshold

        # Supehli process varsa -> en az MEDIUM
        if result.suspicious_processes:
            # Bilinen supehli komut varsa CRITICAL
            for proc in result.suspicious_processes:
                if "bilinen supehli komut" in proc.reason:
                    return ThreatLevel.CRITICAL
            level = self._worst_threat(level, ThreatLevel.MEDIUM)

        # Gecersiz SSL -> HIGH
        for cert in result.ssl_certs:
            if not cert.is_valid:
                level = self._worst_threat(level, ThreatLevel.HIGH)
            elif cert.days_remaining <= 7:
                level = self._worst_threat(level, ThreatLevel.HIGH)
            elif cert.days_remaining <= 30:
                level = self._worst_threat(level, ThreatLevel.MEDIUM)

        # Beklenmeyen acik port -> MEDIUM-HIGH
        if len(result.unexpected_ports) >= 3:
            level = self._worst_threat(level, ThreatLevel.HIGH)
        elif result.unexpected_ports:
            level = self._worst_threat(level, ThreatLevel.MEDIUM)

        # Fail2ban kapali -> MEDIUM
        if not result.fail2ban_active:
            level = self._worst_threat(level, ThreatLevel.MEDIUM)

        # Basarisiz giris sayisi
        if result.total_failed_attempts >= threshold * 10:
            level = self._worst_threat(level, ThreatLevel.HIGH)
        elif result.total_failed_attempts >= threshold:
            level = self._worst_threat(level, ThreatLevel.MEDIUM)
        elif result.total_failed_attempts > 0:
            level = self._worst_threat(level, ThreatLevel.LOW)

        return level

    def _build_scan_summary(self, host: str, result: SecurityScanResult) -> str:
        """Tek sunucu icin tarama ozeti olusturur.

        Args:
            host: Sunucu adresi.
            result: Tarama sonucu.

        Returns:
            Ozet metni.
        """
        parts = [f"{host}: tehdit={result.threat_level.value}"]
        if result.total_failed_attempts > 0:
            parts.append(f"basarisiz_giris={result.total_failed_attempts}")
        if result.unexpected_ports:
            parts.append(f"beklenmeyen_port={len(result.unexpected_ports)}")
        if result.suspicious_processes:
            parts.append(f"supehli_process={len(result.suspicious_processes)}")
        if not result.fail2ban_active:
            parts.append("fail2ban=KAPALI")
        return " | ".join(parts)

    @staticmethod
    def _worst_threat(a: ThreatLevel, b: ThreatLevel) -> ThreatLevel:
        """Iki tehdit seviyesi arasinda en kotu olani dondurur.

        Args:
            a: Birinci tehdit seviyesi.
            b: Ikinci tehdit seviyesi.

        Returns:
            En kotu tehdit seviyesi.
        """
        order = {
            ThreatLevel.NONE: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }
        return a if order[a] >= order[b] else b

    @staticmethod
    def _map_to_risk_urgency(
        worst_threat: ThreatLevel,
        total_failed_logins: int,
        total_unexpected_ports: int,
        total_suspicious_procs: int,
        has_ssl_issue: bool,
        has_fail2ban_down: bool,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Tehdit bulgularini RiskLevel ve UrgencyLevel'a esler.

        Karar matrisi entegrasyonu:
        - NONE/LOW  -> LOW risk, LOW urgency
        - MEDIUM    -> MEDIUM risk, MEDIUM urgency
        - HIGH + fail2ban kapali/supehli proc -> HIGH risk, HIGH urgency
        - HIGH + sadece port/ssl -> HIGH risk, MEDIUM urgency
        - CRITICAL  -> HIGH risk, HIGH urgency

        Args:
            worst_threat: En kotu tehdit seviyesi.
            total_failed_logins: Toplam basarisiz giris sayisi.
            total_unexpected_ports: Toplam beklenmeyen port sayisi.
            total_suspicious_procs: Toplam supehli process sayisi.
            has_ssl_issue: SSL sorunu var mi.
            has_fail2ban_down: Fail2ban kapali mi.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        if worst_threat in (ThreatLevel.NONE, ThreatLevel.LOW):
            return RiskLevel.LOW, UrgencyLevel.LOW

        if worst_threat == ThreatLevel.MEDIUM:
            # Fail2ban kapaliysa aciliyet yukselt
            if has_fail2ban_down and total_failed_logins > 0:
                return RiskLevel.MEDIUM, UrgencyLevel.HIGH
            return RiskLevel.MEDIUM, UrgencyLevel.MEDIUM

        if worst_threat == ThreatLevel.CRITICAL:
            return RiskLevel.HIGH, UrgencyLevel.HIGH

        # HIGH
        if total_suspicious_procs > 0 or has_fail2ban_down:
            return RiskLevel.HIGH, UrgencyLevel.HIGH
        return RiskLevel.HIGH, UrgencyLevel.MEDIUM

    @staticmethod
    def _determine_action(risk: RiskLevel, urgency: UrgencyLevel) -> ActionType:
        """Risk ve aciliyetten aksiyon tipini belirler.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.

        Returns:
            Uygun aksiyon tipi.
        """
        action, _ = DECISION_RULES.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )
        return action

    @staticmethod
    def _is_float(value: str) -> bool:
        """String'in float'a donusturulebilir olup olmadigini kontrol eder."""
        try:
            float(value)
            return True
        except ValueError:
            return False
