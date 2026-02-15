"""ATLAS API Kesficisi modulu.

API arama, dokumantasyon ayristirma,
uyumluluk kontrolu, kimlik dogrulama gereksinimleri, fiyat analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CapabilityAPIDiscoverer:
    """API kesficisi.

    Yetenek edinimi icin API kaynaklarini kesfeder.

    Attributes:
        _apis: Kesfedilen API'ler.
        _evaluations: Degerlendirmeler.
    """

    def __init__(self) -> None:
        """API kesficisini baslatir."""
        self._apis: dict[
            str, dict[str, Any]
        ] = {}
        self._evaluations: list[
            dict[str, Any]
        ] = []
        self._registry: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "discovered": 0,
            "evaluated": 0,
        }

        logger.info(
            "CapabilityAPIDiscoverer "
            "baslatildi",
        )

    def register_api(
        self,
        api_name: str,
        capabilities: list[str],
        endpoint: str = "",
        auth_type: str = "api_key",
        pricing: str = "free",
        docs_url: str = "",
    ) -> dict[str, Any]:
        """API kaydeder.

        Args:
            api_name: API adi.
            capabilities: Sagladigi yetenekler.
            endpoint: Endpoint.
            auth_type: Kimlik dogrulama tipi.
            pricing: Fiyatlandirma.
            docs_url: Dokumantasyon URL.

        Returns:
            Kayit bilgisi.
        """
        self._apis[api_name] = {
            "name": api_name,
            "capabilities": capabilities,
            "endpoint": endpoint,
            "auth_type": auth_type,
            "pricing": pricing,
            "docs_url": docs_url,
            "registered_at": time.time(),
        }

        # Yetenek-API eslemesi
        for cap in capabilities:
            if cap not in self._registry:
                self._registry[cap] = []
            self._registry[cap].append({
                "api": api_name,
                "pricing": pricing,
            })

        self._stats["discovered"] += 1

        return {
            "api": api_name,
            "registered": True,
            "capabilities": len(capabilities),
        }

    def search_apis(
        self,
        capability: str,
    ) -> dict[str, Any]:
        """Yetenek icin API arar.

        Args:
            capability: Aranan yetenek.

        Returns:
            Arama sonucu.
        """
        matches = []

        # Dogrudan esleme
        if capability in self._registry:
            for entry in self._registry[
                capability
            ]:
                api = self._apis.get(
                    entry["api"],
                )
                if api:
                    matches.append(dict(api))

        # Kısmi esleme
        for api_name, api in (
            self._apis.items()
        ):
            if api not in matches:
                for cap in api["capabilities"]:
                    if (
                        capability.lower()
                        in cap.lower()
                        or cap.lower()
                        in capability.lower()
                    ):
                        if dict(api) not in matches:
                            matches.append(
                                dict(api),
                            )

        return {
            "capability": capability,
            "matches": matches,
            "count": len(matches),
        }

    def check_compatibility(
        self,
        api_name: str,
        requirements: dict[str, Any],
    ) -> dict[str, Any]:
        """Uyumluluk kontrolu yapar.

        Args:
            api_name: API adi.
            requirements: Gereksinimler.

        Returns:
            Uyumluluk bilgisi.
        """
        api = self._apis.get(api_name)
        if not api:
            return {"error": "api_not_found"}

        issues = []
        compatible = True

        # Auth uyumlulugu
        req_auth = requirements.get(
            "auth_type",
        )
        if (
            req_auth
            and api["auth_type"] != req_auth
        ):
            issues.append({
                "type": "auth_mismatch",
                "expected": req_auth,
                "actual": api["auth_type"],
            })

        # Fiyat uyumlulugu
        max_price = requirements.get(
            "max_price",
        )
        if (
            max_price
            and api["pricing"] != "free"
        ):
            issues.append({
                "type": "pricing_concern",
                "pricing": api["pricing"],
            })
            compatible = False

        # Yetenek uyumlulugu
        req_caps = requirements.get(
            "capabilities", [],
        )
        api_caps = set(api["capabilities"])
        missing = [
            c for c in req_caps
            if c not in api_caps
        ]
        if missing:
            issues.append({
                "type": "missing_capabilities",
                "missing": missing,
            })
            compatible = False

        result = {
            "api": api_name,
            "compatible": compatible,
            "issues": issues,
            "issue_count": len(issues),
        }

        self._evaluations.append(result)
        self._stats["evaluated"] += 1

        return result

    def analyze_pricing(
        self,
        api_name: str,
        expected_usage: int = 1000,
    ) -> dict[str, Any]:
        """Fiyat analizi yapar.

        Args:
            api_name: API adi.
            expected_usage: Beklenen kullanim.

        Returns:
            Fiyat bilgisi.
        """
        api = self._apis.get(api_name)
        if not api:
            return {"error": "api_not_found"}

        pricing = api["pricing"]

        if pricing == "free":
            monthly_cost = 0.0
            cost_per_call = 0.0
        elif pricing == "freemium":
            cost_per_call = 0.001
            free_calls = 1000
            paid = max(
                0,
                expected_usage - free_calls,
            )
            monthly_cost = paid * cost_per_call
        else:
            cost_per_call = 0.01
            monthly_cost = (
                expected_usage * cost_per_call
            )

        return {
            "api": api_name,
            "pricing_model": pricing,
            "expected_usage": expected_usage,
            "cost_per_call": round(
                cost_per_call, 4,
            ),
            "monthly_cost": round(
                monthly_cost, 2,
            ),
            "annual_cost": round(
                monthly_cost * 12, 2,
            ),
        }

    def get_auth_requirements(
        self,
        api_name: str,
    ) -> dict[str, Any]:
        """Kimlik dogrulama gereksinimlerini getirir.

        Args:
            api_name: API adi.

        Returns:
            Auth gereksinimleri.
        """
        api = self._apis.get(api_name)
        if not api:
            return {"error": "api_not_found"}

        auth_info = {
            "api_key": {
                "type": "api_key",
                "header": "Authorization",
                "setup_steps": [
                    "Register for API key",
                    "Set environment variable",
                ],
            },
            "oauth2": {
                "type": "oauth2",
                "flow": "client_credentials",
                "setup_steps": [
                    "Register application",
                    "Get client ID/secret",
                    "Implement token flow",
                ],
            },
            "none": {
                "type": "none",
                "setup_steps": [],
            },
        }

        return {
            "api": api_name,
            "auth": auth_info.get(
                api["auth_type"],
                auth_info["api_key"],
            ),
        }

    def get_api(
        self,
        api_name: str,
    ) -> dict[str, Any]:
        """API bilgisi getirir.

        Args:
            api_name: API adi.

        Returns:
            API bilgisi.
        """
        api = self._apis.get(api_name)
        if not api:
            return {"error": "api_not_found"}
        return dict(api)

    @property
    def api_count(self) -> int:
        """API sayisi."""
        return len(self._apis)

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return self._stats["evaluated"]
