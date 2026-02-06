"""Sunucu izleme agent modulu.

SSH uzerinden sunucu saglik metriklerini toplar, analiz eder,
risk/aciliyet seviyelerini belirler ve gerektiginde bildirim gonderir.
"""

import asyncio
import platform
import logging
from typing import Any

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import RiskLevel, UrgencyLevel, ActionType
from app.models.server import (
    CpuMetrics,
    DiskMetrics,
    MetricStatus,
    MetricThresholds,
    RamMetrics,
    ServerConfig,
    ServerMetrics,
    ServiceStatus,
)
from app.tools.ssh_manager import SSHManager

logger = logging.getLogger("atlas.agent.server_monitor")


class ServerMonitorAgent(BaseAgent):
    """Sunucu saglik izleme agent'i.

    SSH uzerinden sunucularin CPU, RAM, disk ve servis metriklerini toplar,
    esik degerlerine gore siniflandirir ve raporlar.

    Attributes:
        servers: Izlenecek sunucu yapilandirmalari.
        thresholds: Metrik esik degerleri.
    """

    def __init__(
        self,
        servers: list[ServerConfig] | None = None,
        thresholds: MetricThresholds | None = None,
    ) -> None:
        """ServerMonitorAgent'i baslatir.

        Args:
            servers: Izlenecek sunucu listesi.
                Bos ise config'den varsayilan sunucu eklenir.
            thresholds: Metrik esik degerleri.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="server_monitor")
        self.thresholds = thresholds or MetricThresholds()
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
        """Sunuculari kontrol eder ve metriklerini toplar.

        Args:
            task: Gorev detaylari. Opsiyonel anahtarlar:
                - servers: Ek sunucu listesi (dict listesi).
                - thresholds: Ozel esik degerleri (dict).

        Returns:
            Tum sunucularin metriklerini iceren TaskResult.
        """
        # Task'tan ek sunucu ve esik degerleri al
        extra_servers = [
            ServerConfig(**s) for s in task.get("servers", [])
        ]
        if task.get("thresholds"):
            self.thresholds = MetricThresholds(**task["thresholds"])

        all_servers = self.servers + extra_servers
        if not all_servers:
            return TaskResult(
                success=False,
                message="Izlenecek sunucu yapilandirilmamis.",
                errors=["Sunucu listesi bos."],
            )

        # Paralel sunucu kontrolu
        self.logger.info("%d sunucu kontrol ediliyor...", len(all_servers))
        results = await asyncio.gather(
            *[self._check_server(server) for server in all_servers],
            return_exceptions=True,
        )

        # Sonuclari topla
        metrics_list: list[ServerMetrics] = []
        errors: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                host = all_servers[i].host
                self.logger.error("Sunucu kontrol hatasi [%s]: %s", host, result)
                errors.append(f"{host}: {result}")
                metrics_list.append(
                    ServerMetrics(host=host, reachable=False, overall_status=MetricStatus.CRITICAL)
                )
            else:
                metrics_list.append(result)

        # Analiz et
        analysis = await self.analyze(
            {"metrics": [m.model_dump() for m in metrics_list]}
        )

        # Rapor olustur
        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "metrics": [m.model_dump() for m in metrics_list],
                "analysis": analysis,
            },
            message=analysis.get("summary", "Sunucu kontrolu tamamlandi."),
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Rapor:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Metrikleri esik degerlerine gore siniflandirir.

        Args:
            data: {"metrics": [ServerMetrics dict listesi]}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary, details.
        """
        metrics_list = data.get("metrics", [])
        worst_status = MetricStatus.NORMAL
        details: list[dict[str, Any]] = []
        has_unreachable = False
        has_service_down = False

        for m_dict in metrics_list:
            metrics = ServerMetrics(**m_dict) if isinstance(m_dict, dict) else m_dict
            host = metrics.host

            if not metrics.reachable:
                has_unreachable = True
                worst_status = MetricStatus.CRITICAL
                details.append({
                    "host": host,
                    "status": MetricStatus.CRITICAL.value,
                    "issues": ["Sunucu erisilemez"],
                })
                continue

            # Her metrik icin durum belirle
            host_issues: list[str] = []
            host_worst = MetricStatus.NORMAL

            # CPU
            cpu_status = self._classify_metric(
                metrics.cpu.usage_percent,
                self.thresholds.cpu_warning,
                self.thresholds.cpu_critical,
            )
            if cpu_status != MetricStatus.NORMAL:
                host_issues.append(f"CPU: %{metrics.cpu.usage_percent:.1f} ({cpu_status.value})")
                host_worst = self._worst_of(host_worst, cpu_status)

            # RAM
            ram_status = self._classify_metric(
                metrics.ram.usage_percent,
                self.thresholds.ram_warning,
                self.thresholds.ram_critical,
            )
            if ram_status != MetricStatus.NORMAL:
                host_issues.append(f"RAM: %{metrics.ram.usage_percent:.1f} ({ram_status.value})")
                host_worst = self._worst_of(host_worst, ram_status)

            # Diskler
            for disk in metrics.disks:
                disk_status = self._classify_metric(
                    disk.usage_percent,
                    self.thresholds.disk_warning,
                    self.thresholds.disk_critical,
                )
                if disk_status != MetricStatus.NORMAL:
                    host_issues.append(
                        f"Disk {disk.mount_point}: %{disk.usage_percent:.1f} ({disk_status.value})"
                    )
                    host_worst = self._worst_of(host_worst, disk_status)

            # Servisler
            for svc in metrics.services:
                if not svc.is_active:
                    has_service_down = True
                    host_issues.append(f"Servis durmus: {svc.name}")
                    host_worst = self._worst_of(host_worst, MetricStatus.CRITICAL)

            worst_status = self._worst_of(worst_status, host_worst)
            details.append({
                "host": host,
                "status": host_worst.value,
                "issues": host_issues if host_issues else ["Tum metrikler normal"],
            })

        # Risk ve aciliyet eslestirmesi
        risk, urgency = self._map_to_risk_urgency(
            worst_status, has_unreachable, has_service_down,
        )
        action = self._determine_action(risk, urgency)

        # Ozet olustur
        total = len(metrics_list)
        critical_count = sum(1 for d in details if d["status"] == MetricStatus.CRITICAL.value)
        warning_count = sum(1 for d in details if d["status"] == MetricStatus.WARNING.value)

        if worst_status == MetricStatus.NORMAL:
            summary = f"Tum sunucular sagliki ({total}/{total} normal)."
        elif worst_status == MetricStatus.WARNING:
            summary = f"{warning_count}/{total} sunucuda uyari tespit edildi."
        else:
            summary = f"{critical_count}/{total} sunucuda kritik durum tespit edildi!"

        return {
            "overall_status": worst_status.value,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": summary,
            "details": details,
        }

    async def report(self, result: TaskResult) -> str:
        """Analiz sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        details = analysis.get("details", [])

        lines = [
            "=== SUNUCU SAGLIK RAPORU ===",
            f"Durum: {analysis.get('overall_status', 'bilinmiyor').upper()}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
        ]

        for detail in details:
            host = detail.get("host", "?")
            status = detail.get("status", "?").upper()
            issues = detail.get("issues", [])
            lines.append(f"--- {host} [{status}] ---")
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Dahili metodlar ===

    async def _check_server(self, server: ServerConfig) -> ServerMetrics:
        """Tek bir sunucuyu kontrol eder.

        Args:
            server: Sunucu yapilandirmasi.

        Returns:
            Sunucu metrikleri.
        """
        host = server.host
        self.logger.info("Sunucu kontrol ediliyor: %s", host)

        # Ping kontrolu
        reachable = await self._check_ping(host)
        if not reachable:
            self.logger.warning("Sunucu erisilemez: %s", host)
            return ServerMetrics(
                host=host,
                reachable=False,
                overall_status=MetricStatus.CRITICAL,
            )

        # SSH ile metrik toplama
        try:
            async with SSHManager(
                host=server.host,
                user=server.user,
                key_path=server.key_path,
                port=server.port,
            ) as ssh:
                cpu = await self._collect_cpu(ssh)
                ram = await self._collect_ram(ssh)
                disks = await self._collect_disks(ssh)
                services = await self._check_services(ssh, server.services)

                return ServerMetrics(
                    host=host,
                    reachable=True,
                    cpu=cpu,
                    ram=ram,
                    disks=disks,
                    services=services,
                )
        except Exception as exc:
            self.logger.error("SSH metrik toplama hatasi [%s]: %s", host, exc)
            return ServerMetrics(
                host=host,
                reachable=True,
                overall_status=MetricStatus.WARNING,
            )

    async def _check_ping(self, host: str) -> bool:
        """Sunucuya ping atar (platform-aware).

        Args:
            host: Hedef sunucu adresi.

        Returns:
            Sunucu erisilebilir mi.
        """
        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "3000", host]
            else:
                cmd = ["ping", "-c", "1", "-W", "3", host]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            returncode = await asyncio.wait_for(proc.wait(), timeout=5)
            return returncode == 0
        except (asyncio.TimeoutError, OSError) as exc:
            self.logger.debug("Ping hatasi [%s]: %s", host, exc)
            return False

    async def _collect_cpu(self, ssh: SSHManager) -> CpuMetrics:
        """SSH uzerinden CPU metriklerini toplar.

        Args:
            ssh: Aktif SSH baglantisi.

        Returns:
            CPU metrikleri.
        """
        # CPU kullanim yuzdesi
        stdout, _, _ = await ssh.execute_command(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2+$4}'"
        )
        usage = 0.0
        try:
            usage = float(stdout.strip())
        except (ValueError, IndexError):
            self.logger.warning("CPU yuzdesi ayristirilamadi: %s", stdout)

        # Load average
        stdout2, _, _ = await ssh.execute_command("cat /proc/loadavg")
        load_1m = load_5m = load_15m = 0.0
        try:
            parts = stdout2.strip().split()
            load_1m = float(parts[0])
            load_5m = float(parts[1])
            load_15m = float(parts[2])
        except (ValueError, IndexError):
            self.logger.warning("Load average ayristirilamadi: %s", stdout2)

        return CpuMetrics(
            usage_percent=usage,
            load_1m=load_1m,
            load_5m=load_5m,
            load_15m=load_15m,
        )

    async def _collect_ram(self, ssh: SSHManager) -> RamMetrics:
        """SSH uzerinden RAM metriklerini toplar.

        Args:
            ssh: Aktif SSH baglantisi.

        Returns:
            RAM metrikleri.
        """
        stdout, _, _ = await ssh.execute_command("free -m | grep Mem")
        total = used = available = 0
        usage_pct = 0.0
        try:
            # Ornek cikti: "Mem:           7976       3421       1234        ..."
            parts = stdout.split()
            total = int(parts[1])
            used = int(parts[2])
            available = int(parts[6]) if len(parts) > 6 else total - used
            usage_pct = (used / total * 100) if total > 0 else 0.0
        except (ValueError, IndexError):
            self.logger.warning("RAM metrikleri ayristirilamadi: %s", stdout)

        return RamMetrics(
            total_mb=total,
            used_mb=used,
            available_mb=available,
            usage_percent=round(usage_pct, 1),
        )

    async def _collect_disks(self, ssh: SSHManager) -> list[DiskMetrics]:
        """SSH uzerinden disk metriklerini toplar.

        Args:
            ssh: Aktif SSH baglantisi.

        Returns:
            Disk metrikleri listesi.
        """
        stdout, _, _ = await ssh.execute_command(
            "df -BG --output=target,size,used,avail,pcent | tail -n +2"
        )
        disks: list[DiskMetrics] = []
        for line in stdout.strip().splitlines():
            try:
                parts = line.split()
                if len(parts) < 5:
                    continue
                mount = parts[0]
                total_gb = float(parts[1].rstrip("G"))
                used_gb = float(parts[2].rstrip("G"))
                avail_gb = float(parts[3].rstrip("G"))
                pct = float(parts[4].rstrip("%"))
                disks.append(DiskMetrics(
                    mount_point=mount,
                    total_gb=total_gb,
                    used_gb=used_gb,
                    available_gb=avail_gb,
                    usage_percent=pct,
                ))
            except (ValueError, IndexError):
                self.logger.warning("Disk satiri ayristirilamadi: %s", line)
        return disks

    async def _check_services(
        self, ssh: SSHManager, services: list[str]
    ) -> list[ServiceStatus]:
        """SSH uzerinden systemd servis durumlarini kontrol eder.

        Args:
            ssh: Aktif SSH baglantisi.
            services: Kontrol edilecek servis adlari.

        Returns:
            Servis durumlari listesi.
        """
        statuses: list[ServiceStatus] = []
        for svc_name in services:
            stdout, _, exit_code = await ssh.execute_command(
                f"systemctl is-active {svc_name}"
            )
            is_active = stdout.strip() == "active" and exit_code == 0
            statuses.append(ServiceStatus(
                name=svc_name,
                is_active=is_active,
                status=MetricStatus.NORMAL if is_active else MetricStatus.CRITICAL,
            ))
        return statuses

    @staticmethod
    def _classify_metric(
        value: float, warning_threshold: float, critical_threshold: float
    ) -> MetricStatus:
        """Metrik degerini esik degerlerine gore siniflandirir.

        Args:
            value: Mevcut metrik degeri.
            warning_threshold: Uyari esigi.
            critical_threshold: Kritik esigi.

        Returns:
            Metrik durumu.
        """
        if value >= critical_threshold:
            return MetricStatus.CRITICAL
        if value >= warning_threshold:
            return MetricStatus.WARNING
        return MetricStatus.NORMAL

    @staticmethod
    def _worst_of(a: MetricStatus, b: MetricStatus) -> MetricStatus:
        """Iki durum arasinda en kotu olani dondurur.

        Args:
            a: Birinci durum.
            b: Ikinci durum.

        Returns:
            En kotu durum.
        """
        order = {MetricStatus.NORMAL: 0, MetricStatus.WARNING: 1, MetricStatus.CRITICAL: 2}
        return a if order[a] >= order[b] else b

    @staticmethod
    def _map_to_risk_urgency(
        status: MetricStatus,
        has_unreachable: bool,
        has_service_down: bool,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """MetricStatus'u RiskLevel ve UrgencyLevel'a esler.

        Karar matrisi entegrasyonu:
        - NORMAL  -> LOW risk, LOW urgency
        - WARNING -> MEDIUM risk, MEDIUM urgency
        - CRITICAL + erisilemez/servis durmus -> HIGH risk, HIGH urgency
        - CRITICAL + sadece yuksek kaynak -> HIGH risk, MEDIUM urgency

        Args:
            status: Genel metrik durumu.
            has_unreachable: Erisilemez sunucu var mi.
            has_service_down: Durmus servis var mi.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        if status == MetricStatus.NORMAL:
            return RiskLevel.LOW, UrgencyLevel.LOW
        if status == MetricStatus.WARNING:
            return RiskLevel.MEDIUM, UrgencyLevel.MEDIUM
        # CRITICAL
        if has_unreachable or has_service_down:
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
        from app.core.decision_matrix import DECISION_RULES
        action, _ = DECISION_RULES.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )
        return action
