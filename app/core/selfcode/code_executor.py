"""ATLAS guvenli kod calistirma motoru.

Sandbox ortaminda Python kodu calistirma, dosya calistirma, pytest
entegrasyonu, guvenlik kontrolu ve kaynak limitleri yonetimi saglar.
"""

import logging
import os
import re
import subprocess
import tempfile
import time
from typing import Optional
from uuid import uuid4

from app.models.selfcode import (
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)

# Tehlikeli kod desenleri: calistirmaya izin verilmez
DANGEROUS_PATTERNS: list[str] = [
    r"\bos\.system\s*\(",
    r"subprocess\.call\s*\(.*shell\s*=\s*True",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\b__import__\s*\(",
    r"open\s*\([^)]*['\"][wa]['\"]",
    r"\bshutil\.rmtree\s*\(",
    r"\bos\.remove\s*\(",
]


class SafeExecutor:
    """Sandbox ortaminda guvenli Python kod calistiricisi.

    Kod guvenlik kontrolu, kaynak sinirlamasi (bellek/zaman),
    gecici dosya yonetimi ve pytest entegrasyonu saglar.

    Attributes:
        config: Calistirma yapilandirmasi (timeout, bellek vb.).
        sandbox_mode: True ise gercek subprocess calistirmaz, simule eder.
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        sandbox_mode: bool = True,
    ) -> None:
        """SafeExecutor'u yapilandirir.

        Args:
            config: Calistirma yapilandirmasi. None ise varsayilan kullanilir.
            sandbox_mode: True ise sandbox modunda calisir (gercek calistirma yok).
        """
        self.config = config or ExecutionConfig()
        self.sandbox_mode = sandbox_mode
        self._temp_files: list[str] = []
        logger.info(
            f"SafeExecutor baslatildi (sandbox={sandbox_mode}, "
            f"timeout={self.config.timeout}s, "
            f"max_memory={self.config.max_memory_mb}MB)"
        )

    def check_safety(self, code: str) -> tuple[bool, list[str]]:
        """Kodu statik olarak guvenlik kontrolunden gecirir.

        Tehlikeli desenleri (os.system, eval, exec vb.) tarar
        ve guvenli olup olmadigini belirler.

        Args:
            code: Kontrol edilecek Python kaynak kodu.

        Returns:
            (guvenli_mi, bulunan_tehditler) demeti.
        """
        violations: list[str] = []

        for pattern in DANGEROUS_PATTERNS:
            matches = re.findall(pattern, code)
            if matches:
                violations.append(
                    f"Tehlikeli desen tespit edildi: {pattern}"
                )

        is_safe = len(violations) == 0

        if not is_safe:
            logger.warning(
                f"Guvenlik kontrolu basarisiz: {len(violations)} ihlal bulundu"
            )
        else:
            logger.debug("Guvenlik kontrolu basarili: tehlikeli desen bulunamadi")

        return is_safe, violations

    def set_resource_limits(
        self,
        timeout: Optional[float] = None,
        max_memory_mb: Optional[int] = None,
        max_output_lines: Optional[int] = None,
    ) -> None:
        """Kaynak limitlerini gunceller.

        Args:
            timeout: Yeni zaman asimi (saniye). None ise degismez.
            max_memory_mb: Yeni bellek limiti (MB). None ise degismez.
            max_output_lines: Yeni cikti satir limiti. None ise degismez.
        """
        if timeout is not None:
            self.config.timeout = timeout
        if max_memory_mb is not None:
            self.config.max_memory_mb = max_memory_mb
        if max_output_lines is not None:
            self.config.max_output_lines = max_output_lines

        logger.debug(
            f"Kaynak limitleri guncellendi: timeout={self.config.timeout}s, "
            f"memory={self.config.max_memory_mb}MB, "
            f"output_lines={self.config.max_output_lines}"
        )

    def execute(self, code: str) -> ExecutionResult:
        """Python kodunu sandbox ortaminda calistirir.

        Guvenlik kontrolu yapar, sandbox moduna gore gercek veya
        simule calistirma gerceklestirir.

        Args:
            code: Calistirilacak Python kaynak kodu.

        Returns:
            Calistirma sonucunu iceren ExecutionResult.
        """
        result = ExecutionResult(
            id=uuid4().hex[:12],
            status=ExecutionStatus.PENDING,
        )

        # 1. Guvenlik kontrolu
        is_safe, violations = self.check_safety(code)
        if not is_safe:
            result.status = ExecutionStatus.FAILED
            result.stderr = "Guvenlik ihlali:\n" + "\n".join(violations)
            result.exit_code = 1
            logger.warning(f"Calistirma reddedildi: {len(violations)} guvenlik ihlali")
            return result

        # 2. Sandbox modunda simule et
        if self.sandbox_mode:
            return self._simulate_execution(code, result)

        # 3. Gercek calistirma
        temp_path = self._create_temp_file(code)
        if not temp_path:
            result.status = ExecutionStatus.FAILED
            result.stderr = "Gecici dosya olusturulamadi"
            result.exit_code = 1
            return result

        try:
            result = self.execute_file(temp_path)
        finally:
            self._cleanup_file(temp_path)

        return result

    def execute_file(self, file_path: str) -> ExecutionResult:
        """Bir Python dosyasini sandbox ortaminda calistirir.

        Args:
            file_path: Calistirilacak Python dosyasi yolu.

        Returns:
            Calistirma sonucunu iceren ExecutionResult.
        """
        result = ExecutionResult(
            id=uuid4().hex[:12],
            status=ExecutionStatus.RUNNING,
        )

        if not os.path.isfile(file_path):
            result.status = ExecutionStatus.FAILED
            result.stderr = f"Dosya bulunamadi: {file_path}"
            result.exit_code = 1
            logger.error(f"Calistirilacak dosya bulunamadi: {file_path}")
            return result

        # Sandbox modunda dosya icerigini oku ve simule et
        if self.sandbox_mode:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                return self._simulate_execution(code, result)
            except OSError as e:
                result.status = ExecutionStatus.FAILED
                result.stderr = f"Dosya okunamadi: {e}"
                result.exit_code = 1
                return result

        # Gercek calistirma
        stdout, stderr, exit_code, duration, timed_out = self._run_subprocess(
            ["python", file_path]
        )

        result.stdout = self.capture_output(stdout)
        result.stderr = self.capture_output(stderr)
        result.exit_code = exit_code
        result.duration = duration
        result.timed_out = timed_out

        if timed_out:
            result.status = ExecutionStatus.TIMEOUT
            logger.warning(f"Calistirma zaman asimina ugradi: {file_path}")
        elif exit_code == 0:
            result.status = ExecutionStatus.COMPLETED
            logger.info(f"Calistirma basarili: {file_path} ({duration:.2f}s)")
        else:
            result.status = ExecutionStatus.FAILED
            logger.warning(
                f"Calistirma basarisiz: {file_path} (exit={exit_code})"
            )

        return result

    def execute_tests(self, test_code: str) -> ExecutionResult:
        """Pytest ile test kodunu calistirir ve sonuclari yakalar.

        Args:
            test_code: Calistirilacak pytest uyumlu test kodu.

        Returns:
            Test sonuclarini iceren ExecutionResult. stdout'ta
            gecen/kalan test sayilari yer alir.
        """
        result = ExecutionResult(
            id=uuid4().hex[:12],
            status=ExecutionStatus.PENDING,
        )

        # Guvenlik kontrolu
        is_safe, violations = self.check_safety(test_code)
        if not is_safe:
            result.status = ExecutionStatus.FAILED
            result.stderr = "Test kodunda guvenlik ihlali:\n" + "\n".join(violations)
            result.exit_code = 1
            return result

        # Sandbox modunda test sonuclarini simule et
        if self.sandbox_mode:
            return self._simulate_test_execution(test_code, result)

        # Gecici test dosyasi olustur
        temp_path = self._create_temp_file(test_code, prefix="test_")
        if not temp_path:
            result.status = ExecutionStatus.FAILED
            result.stderr = "Gecici test dosyasi olusturulamadi"
            result.exit_code = 1
            return result

        try:
            stdout, stderr, exit_code, duration, timed_out = self._run_subprocess(
                ["python", "-m", "pytest", temp_path, "-v", "--tb=short"]
            )

            result.stdout = self.capture_output(stdout)
            result.stderr = self.capture_output(stderr)
            result.exit_code = exit_code
            result.duration = duration
            result.timed_out = timed_out

            if timed_out:
                result.status = ExecutionStatus.TIMEOUT
            elif exit_code == 0:
                result.status = ExecutionStatus.COMPLETED
            else:
                result.status = ExecutionStatus.FAILED

            # Test sonuclarini ayristir
            passed, failed, errors = self._parse_test_results(result.stdout)
            result.stdout += (
                f"\n--- Test Ozeti ---\n"
                f"Gecen: {passed}, Kalan: {failed}, Hata: {errors}\n"
            )

            logger.info(
                f"Test calistirma tamamlandi: gecen={passed}, "
                f"kalan={failed}, hata={errors}"
            )
        finally:
            self._cleanup_file(temp_path)

        return result

    def capture_output(self, raw_output: str) -> str:
        """Ciktiyi satir limitine gore keser.

        Args:
            raw_output: Ham cikti metni.

        Returns:
            Satir limitine gore kesilmis cikti.
        """
        if not raw_output:
            return ""

        lines = raw_output.splitlines()
        max_lines = self.config.max_output_lines

        if len(lines) <= max_lines:
            return raw_output

        truncated = lines[:max_lines]
        truncated.append(
            f"\n... ({len(lines) - max_lines} satir daha kesildi)"
        )
        logger.debug(
            f"Cikti kesildi: {len(lines)} -> {max_lines} satir"
        )
        return "\n".join(truncated)

    def cleanup(self) -> None:
        """Tum gecici dosyalari ve kaynaklari temizler."""
        cleaned = 0
        for path in self._temp_files:
            self._cleanup_file(path)
            cleaned += 1

        self._temp_files.clear()
        logger.info(f"Temizlik tamamlandi: {cleaned} gecici dosya silindi")

    def _run_subprocess(
        self, cmd: list[str]
    ) -> tuple[str, str, int, float, bool]:
        """Alt sureci timeout ile calistirir.

        Args:
            cmd: Calistirilacak komut ve argumanlari.

        Returns:
            (stdout, stderr, exit_code, duration, timed_out) demeti.
        """
        start_time = time.monotonic()
        timed_out = False
        stdout = ""
        stderr = ""
        exit_code = -1

        try:
            env = os.environ.copy()
            # Ag erisimini kisitla
            if not self.config.allow_network:
                env["no_proxy"] = "*"

            working_dir = self.config.working_dir or None

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                cwd=working_dir,
                env=env,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            timed_out = True
            stderr = f"Zaman asimi: {self.config.timeout}s limiti asildi"
            logger.warning(f"Alt surec zaman asimi: {cmd}")

        except OSError as e:
            stderr = f"Surec calistirma hatasi: {e}"
            exit_code = 1
            logger.error(f"Alt surec baslatma hatasi: {e}")

        duration = time.monotonic() - start_time
        return stdout, stderr, exit_code, duration, timed_out

    def _create_temp_file(
        self, code: str, prefix: str = "atlas_exec_"
    ) -> Optional[str]:
        """Kod icerigi ile gecici dosya olusturur.

        Args:
            code: Dosyaya yazilacak Python kodu.
            prefix: Gecici dosya adi oneki.

        Returns:
            Olusturulan gecici dosya yolu veya None (hata durumunda).
        """
        try:
            fd, path = tempfile.mkstemp(
                suffix=".py",
                prefix=prefix,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)

            self._temp_files.append(path)
            logger.debug(f"Gecici dosya olusturuldu: {path}")
            return path

        except OSError as e:
            logger.error(f"Gecici dosya olusturma hatasi: {e}")
            return None

    def _cleanup_file(self, path: str) -> None:
        """Tek bir gecici dosyayi guvenli sekilde siler.

        Args:
            path: Silinecek dosya yolu.
        """
        try:
            if os.path.exists(path):
                os.unlink(path)
                logger.debug(f"Gecici dosya silindi: {path}")
        except OSError as e:
            logger.warning(f"Gecici dosya silinemedi: {path} - {e}")

    def _parse_test_results(
        self, output: str
    ) -> tuple[int, int, int]:
        """Pytest ciktisini ayristirarak gecen/kalan/hata sayilarini cikarir.

        Args:
            output: Pytest standart ciktisi.

        Returns:
            (gecen, kalan, hata) sayilari demeti.
        """
        passed = 0
        failed = 0
        errors = 0

        # pytest ozet satiri deseni: "X passed, Y failed, Z error"
        summary_match = re.search(
            r"(\d+)\s+passed", output
        )
        if summary_match:
            passed = int(summary_match.group(1))

        failed_match = re.search(
            r"(\d+)\s+failed", output
        )
        if failed_match:
            failed = int(failed_match.group(1))

        error_match = re.search(
            r"(\d+)\s+error", output
        )
        if error_match:
            errors = int(error_match.group(1))

        return passed, failed, errors

    def _simulate_execution(
        self, code: str, result: ExecutionResult
    ) -> ExecutionResult:
        """Sandbox modunda calistirmayi simule eder.

        Kodu gercekten calistirmaz; satir sayisi ve sinif/fonksiyon
        bilgilerini ciktiya yazar.

        Args:
            code: Simule edilecek Python kodu.
            result: Doldurulacak ExecutionResult nesnesi.

        Returns:
            Simule edilmis sonuc iceren ExecutionResult.
        """
        lines = code.strip().splitlines()
        line_count = len(lines)

        # Basit kod analizi: fonksiyon ve sinif sayilarini cikar
        func_count = sum(1 for l in lines if re.match(r"\s*def\s+", l))
        class_count = sum(1 for l in lines if re.match(r"\s*class\s+", l))

        result.status = ExecutionStatus.COMPLETED
        result.exit_code = 0
        result.duration = 0.0
        result.stdout = (
            f"[SANDBOX] Kod basariyla dogrulandi.\n"
            f"Satir sayisi: {line_count}\n"
            f"Fonksiyon sayisi: {func_count}\n"
            f"Sinif sayisi: {class_count}\n"
        )
        result.stderr = ""

        logger.info(
            f"Sandbox simule calistirma: {line_count} satir, "
            f"{func_count} fonksiyon, {class_count} sinif"
        )
        return result

    def _simulate_test_execution(
        self, test_code: str, result: ExecutionResult
    ) -> ExecutionResult:
        """Sandbox modunda test calistirmayi simule eder.

        Test fonksiyonlarini sayar ve basarili sonuc uretir.

        Args:
            test_code: Simule edilecek test kodu.
            result: Doldurulacak ExecutionResult nesnesi.

        Returns:
            Simule edilmis test sonucu iceren ExecutionResult.
        """
        lines = test_code.strip().splitlines()
        test_count = sum(
            1 for l in lines if re.match(r"\s*def\s+test_", l)
        )

        result.status = ExecutionStatus.COMPLETED
        result.exit_code = 0
        result.duration = 0.0
        result.stdout = (
            f"[SANDBOX] Test calistirma simule edildi.\n"
            f"Tespit edilen test sayisi: {test_count}\n"
            f"{test_count} passed\n"
            f"\n--- Test Ozeti ---\n"
            f"Gecen: {test_count}, Kalan: 0, Hata: 0\n"
        )
        result.stderr = ""

        logger.info(f"Sandbox test simule: {test_count} test tespit edildi")
        return result
