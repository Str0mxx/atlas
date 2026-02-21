"""OpenClaw beceri guvenlik tarayicisi.

Prompt injection, kimlik bilgisi hirsizligi,
kotu amacli kod ve kalite sorunlarini tespit eder.
"""

import logging
import re
import time
from typing import Any

from app.models.openclaw_models import (
    OpenClawSkillRaw,
    ScanFinding,
    SecurityScanResult,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 5000
_MAX_HISTORY = 5000

# ---- Prompt Injection Kaliplari ----
_PROMPT_INJECTION_PATTERNS: list[
    tuple[str, int, str]
] = [
    (
        r"ignore\s+(all\s+)?previous\s+"
        r"instructions",
        30, "Onceki talimatlari yok say",
    ),
    (
        r"override\s+system\s+prompt",
        25, "Sistem promptunu gecersiz kil",
    ),
    (
        r"forget\s+(all\s+)?your\s+rules",
        25, "Kurallarini unut",
    ),
    (
        r"you\s+are\s+now\s+(?:DAN|jailbr)",
        30, "Jailbreak denemesi",
    ),
    (
        r"disregard\s+(?:all|any|your)\s+"
        r"(?:previous|prior|above)",
        25, "Onceki talimatlari yok say",
    ),
    (
        r"new\s+instructions?\s*:",
        15, "Yeni talimat enjeksiyonu",
    ),
    (
        r"act\s+as\s+if\s+you\s+have\s+no\s+"
        r"(?:rules|restrictions)",
        25, "Kural kisitlamasi kaldirma",
    ),
    (
        r"pretend\s+(?:you\s+are|to\s+be)\s+"
        r"(?:an?\s+)?(?:unrestricted|evil)",
        20, "Kisitlamasiz davranma",
    ),
    (
        r"do\s+not\s+follow\s+(?:any|your)\s+"
        r"(?:safety|content)\s+(?:rules|policies)",
        25, "Guvenlik kurallari atlama",
    ),
    (
        r"system\s*:\s*you\s+are",
        20, "Sistem prompt taklidi",
    ),
]

# ---- Kimlik Bilgisi Hirsizligi ----
_CREDENTIAL_PATTERNS: list[
    tuple[str, int, str]
] = [
    (
        r"exfiltrate",
        30, "Veri cikartma",
    ),
    (
        r"webhook\.site",
        25, "Webhook.site veri sizdirma",
    ),
    (
        r"send\s+(?:data\s+)?to\s+https?://",
        20, "Disari veri gonderme",
    ),
    (
        r"ngrok\.io",
        25, "Ngrok tunel veri sizdirma",
    ),
    (
        r"requestbin",
        25, "RequestBin veri sizdirma",
    ),
    (
        r"steal\s+(?:api|secret|token|key|"
        r"credential|password)",
        30, "Kimlik bilgisi calma",
    ),
    (
        r"forward\s+(?:all\s+)?(?:secrets?"
        r"|keys?|tokens?|credentials?)",
        25, "Gizli bilgi yonlendirme",
    ),
    (
        r"base64\s+encode\s+(?:and\s+)?send",
        20, "Base64 kodlama ile sizdirma",
    ),
    (
        r"curl\s+.*\s+-d\s+.*(?:api.key|"
        r"secret|token|password)",
        25, "Curl ile kimlik sizdirma",
    ),
    (
        r"(?:env|environment)\s*\[.*"
        r"(?:KEY|SECRET|TOKEN|PASSWORD)",
        20, "Ortam degiskeni erisimi",
    ),
]

# ---- Kotu Amacli Kod ----
_MALICIOUS_CODE_PATTERNS: list[
    tuple[str, int, str]
] = [
    (
        r"eval\s*\(",
        20, "eval() kullanimi",
    ),
    (
        r"exec\s*\(",
        20, "exec() kullanimi",
    ),
    (
        r"rm\s+-rf\s+/",
        30, "Kok dizin silme",
    ),
    (
        r"sudo\s+",
        15, "Sudo kullanimi",
    ),
    (
        r"os\.system\s*\(",
        20, "os.system() kullanimi",
    ),
    (
        r"subprocess\.\w+\s*\(",
        15, "subprocess kullanimi",
    ),
    (
        r"__import__\s*\(",
        20, "__import__() kullanimi",
    ),
    (
        r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",
        30, "Fork bombasi",
    ),
    (
        r"shutil\.rmtree\s*\(",
        20, "Dizin agaci silme",
    ),
    (
        r"(?:chmod|chown)\s+.*777",
        15, "Asiri izin verme",
    ),
    (
        r"mkfifo|nc\s+-[el]|ncat\s+-[el]",
        25, "Ters kabuk",
    ),
    (
        r"(?:import|require)\s+(?:child_process"
        r"|spawn|execFile)",
        15, "Alt islem calistirma",
    ),
]

# ---- Kalite Kaliplari ----
_MIN_BODY_LENGTH = 50
_MIN_DESCRIPTION_LENGTH = 5


class OpenClawSecurityScanner:
    """OpenClaw beceri guvenlik tarayicisi.

    Prompt icerigini analiz ederek
    guvenlik risklerini tespit eder.

    Attributes:
        _records: Tarama sonuclari.
    """

    def __init__(self) -> None:
        """OpenClawSecurityScanner baslatir."""
        self._records: dict[
            str, SecurityScanResult
        ] = {}
        self._record_order: list[str] = []
        self._total_ops: int = 0
        self._total_passed: int = 0
        self._total_failed: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

    # ---- Tarama ----

    def scan_skill(
        self,
        raw: OpenClawSkillRaw,
        min_score: int = 70,
    ) -> SecurityScanResult:
        """Beceriyi guvenlik acisisindan tarar.

        Args:
            raw: Ham beceri verisi.
            min_score: Minimum gecme puani.

        Returns:
            Tarama sonucu.
        """
        self._total_ops += 1
        start = time.time()

        findings: list[ScanFinding] = []
        full_text = (
            raw.body + "\n"
            + raw.frontmatter.description
        )

        # Tum kategori taramalari
        self._scan_prompt_injection(
            full_text, findings,
        )
        self._scan_credential_stealing(
            full_text, findings,
        )
        self._scan_malicious_code(
            full_text, findings,
        )
        self._scan_quality(
            raw, findings,
        )

        score = self._compute_score(findings)
        risk_level = self._score_to_risk(score)
        passed = score >= min_score

        elapsed = time.time() - start

        result = SecurityScanResult(
            skill_path=raw.file_path,
            skill_name=(
                raw.frontmatter.name
                or raw.file_path
            ),
            score=score,
            risk_level=risk_level,
            findings=findings,
            passed=passed,
            scan_time=elapsed,
        )

        if passed:
            self._total_passed += 1
        else:
            self._total_failed += 1

        key = raw.file_path
        self._records[key] = result
        self._record_order.append(key)
        if len(self._records) > _MAX_RECORDS:
            self._rotate()

        self._record_history(
            "scan",
            key,
            f"score={score} risk={risk_level}",
        )
        return result

    def scan_text(
        self,
        text: str,
        name: str = "",
        min_score: int = 70,
    ) -> SecurityScanResult:
        """Ham metni guvenlik acisisindan tarar.

        Args:
            text: Taranacak metin.
            name: Beceri adi.
            min_score: Minimum gecme puani.

        Returns:
            Tarama sonucu.
        """
        from app.models.openclaw_models import (
            OpenClawFrontmatter,
        )
        raw = OpenClawSkillRaw(
            file_path=name or "inline",
            frontmatter=OpenClawFrontmatter(
                name=name,
            ),
            body=text,
        )
        return self.scan_skill(raw, min_score)

    # ---- Kategori Taramalari ----

    def _scan_prompt_injection(
        self,
        text: str,
        findings: list[ScanFinding],
    ) -> None:
        """Prompt injection kaliplarini tarar.

        Args:
            text: Taranacak metin.
            findings: Bulgu listesi.
        """
        text_lower = text.lower()
        for pattern, deduction, desc in (
            _PROMPT_INJECTION_PATTERNS
        ):
            matches = re.finditer(
                pattern, text_lower,
                re.IGNORECASE,
            )
            for m in matches:
                line_num = text_lower[
                    :m.start()
                ].count("\n") + 1
                context = m.group(0)[:80]
                findings.append(ScanFinding(
                    category="prompt_injection",
                    pattern=pattern[:60],
                    description=desc,
                    severity=(
                        "critical"
                        if deduction >= 25
                        else "high"
                    ),
                    deduction=deduction,
                    line_number=line_num,
                    context=context,
                ))

    def _scan_credential_stealing(
        self,
        text: str,
        findings: list[ScanFinding],
    ) -> None:
        """Kimlik bilgisi hirsizligini tarar.

        Args:
            text: Taranacak metin.
            findings: Bulgu listesi.
        """
        text_lower = text.lower()
        for pattern, deduction, desc in (
            _CREDENTIAL_PATTERNS
        ):
            matches = re.finditer(
                pattern, text_lower,
                re.IGNORECASE,
            )
            for m in matches:
                line_num = text_lower[
                    :m.start()
                ].count("\n") + 1
                context = m.group(0)[:80]
                findings.append(ScanFinding(
                    category=(
                        "credential_stealing"
                    ),
                    pattern=pattern[:60],
                    description=desc,
                    severity=(
                        "critical"
                        if deduction >= 25
                        else "high"
                    ),
                    deduction=deduction,
                    line_number=line_num,
                    context=context,
                ))

    def _scan_malicious_code(
        self,
        text: str,
        findings: list[ScanFinding],
    ) -> None:
        """Kotu amacli kod kaliplarini tarar.

        Args:
            text: Taranacak metin.
            findings: Bulgu listesi.
        """
        for pattern, deduction, desc in (
            _MALICIOUS_CODE_PATTERNS
        ):
            matches = re.finditer(
                pattern, text,
                re.IGNORECASE,
            )
            for m in matches:
                line_num = text[
                    :m.start()
                ].count("\n") + 1
                context = m.group(0)[:80]
                findings.append(ScanFinding(
                    category="malicious_code",
                    pattern=pattern[:60],
                    description=desc,
                    severity=(
                        "critical"
                        if deduction >= 25
                        else "high"
                        if deduction >= 15
                        else "medium"
                    ),
                    deduction=deduction,
                    line_number=line_num,
                    context=context,
                ))

    def _scan_quality(
        self,
        raw: OpenClawSkillRaw,
        findings: list[ScanFinding],
    ) -> None:
        """Kalite sorunlarini kontrol eder.

        Args:
            raw: Ham beceri verisi.
            findings: Bulgu listesi.
        """
        fm = raw.frontmatter

        # Govde cok kisa
        if len(raw.body.strip()) < _MIN_BODY_LENGTH:
            findings.append(ScanFinding(
                category="quality",
                description=(
                    "Govde cok kisa "
                    f"({len(raw.body.strip())} "
                    f"karakter)"
                ),
                severity="medium",
                deduction=10,
            ))

        # Aciklama yok veya cok kisa
        if len(fm.description.strip()) < (
            _MIN_DESCRIPTION_LENGTH
        ):
            findings.append(ScanFinding(
                category="quality",
                description=(
                    "Aciklama yok veya cok kisa"
                ),
                severity="low",
                deduction=5,
            ))

        # Isim yok
        if not fm.name.strip():
            findings.append(ScanFinding(
                category="quality",
                description="Beceri adi yok",
                severity="medium",
                deduction=15,
            ))

        # YAML ayristirma hatalari
        if raw.parse_errors:
            findings.append(ScanFinding(
                category="quality",
                description=(
                    f"{len(raw.parse_errors)} "
                    f"YAML hatasi"
                ),
                severity="low",
                deduction=5,
            ))

    # ---- Puan Hesaplama ----

    def _compute_score(
        self,
        findings: list[ScanFinding],
    ) -> int:
        """Guvenlik puanini hesaplar.

        Args:
            findings: Bulgu listesi.

        Returns:
            0-100 arasi guvenlik puani.
        """
        score = 100
        for f in findings:
            score -= f.deduction
        return max(0, min(100, score))

    def _score_to_risk(
        self,
        score: int,
    ) -> str:
        """Puani risk seviyesine cevirir.

        Args:
            score: Guvenlik puani.

        Returns:
            Risk seviyesi.
        """
        if score >= 90:
            return "low"
        if score >= 70:
            return "medium"
        if score >= 50:
            return "high"
        return "critical"

    # ---- Sorgulama ----

    def get_result(
        self,
        file_path: str,
    ) -> SecurityScanResult | None:
        """Tarama sonucunu dondurur.

        Args:
            file_path: Dosya yolu.

        Returns:
            Sonuc veya None.
        """
        return self._records.get(file_path)

    def list_results(
        self,
        passed_only: bool = False,
        limit: int = 100,
    ) -> list[SecurityScanResult]:
        """Tarama sonuclarini listeler.

        Args:
            passed_only: Sadece gecenler.
            limit: Maks sayi.

        Returns:
            Sonuc listesi.
        """
        keys = list(
            reversed(self._record_order),
        )
        result: list[SecurityScanResult] = []
        for k in keys:
            r = self._records.get(k)
            if not r:
                continue
            if passed_only and not r.passed:
                continue
            result.append(r)
            if len(result) >= limit:
                break
        return result

    # ---- Dahili ----

    def _rotate(self) -> int:
        """Eski kayitlari temizler."""
        keep = _MAX_RECORDS // 2
        if len(self._record_order) <= keep:
            return 0
        to_remove = self._record_order[:-keep]
        for k in to_remove:
            self._records.pop(k, None)
        self._record_order = (
            self._record_order[-keep:]
        )
        return len(to_remove)

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-2500:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "total_scanned": self._total_ops,
            "total_passed": self._total_passed,
            "total_failed": self._total_failed,
            "total_records": len(self._records),
        }
