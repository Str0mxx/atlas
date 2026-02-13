"""ATLAS API Entegrasyon Motoru.

OpenAPI/Swagger spesifikasyonlarindan httpx tabanli asenkron API
istemci kodu uretir.
"""

import json
import logging
import re
import textwrap
from typing import Any, Optional

from app.models.selfcode import (
    APIAuthType,
    APIClientConfig,
    APIEndpointSpec,
    APISpec,
)

logger = logging.getLogger(__name__)

# Kimlik dogrulama sablonlari
_AUTH_TEMPLATES: dict[str, str] = {
    "none": "pass",
    "api_key": 'self._headers["X-API-Key"] = self._api_key',
    "bearer": 'self._headers["Authorization"] = f"Bearer {self._token}"',
    "oauth2": (
        "if self._token_expires_at <= time.time():\n"
        "    await self._refresh_oauth_token()\n"
        'self._headers["Authorization"] = f"Bearer {self._access_token}"'
    ),
    "basic": (
        "import base64\n"
        "credentials = base64.b64encode("
        'f"{self._username}:{self._password}".encode()).decode()\n'
        'self._headers["Authorization"] = f"Basic {credentials}"'
    ),
}

# Auth tipi -> __init__ parametre eki
_AUTH_INIT_PARAMS: dict[str, str] = {
    "none": "",
    "api_key": ', api_key: str = ""',
    "bearer": ', token: str = ""',
    "oauth2": ', client_id: str = "", client_secret: str = ""',
    "basic": ', username: str = "", password: str = ""',
}

# Auth tipi -> __init__ govde atamalari
_AUTH_INIT_BODY: dict[str, str] = {
    "api_key": "self._api_key = api_key",
    "bearer": "self._token = token",
    "oauth2": (
        "self._client_id = client_id\n"
        "self._client_secret = client_secret\n"
        'self._access_token = ""\nself._token_expires_at = 0.0'
    ),
    "basic": "self._username = username\nself._password = password",
}

# OpenAPI -> Python tip eslesmesi
_TYPE_MAP: dict[str, str] = {
    "string": "str", "integer": "int", "number": "float",
    "boolean": "bool", "array": "list", "object": "dict",
}


class APIIntegrator:
    """OpenAPI spesifikasyonlarindan API istemci kodu uretici.

    Attributes:
        default_timeout: Varsayilan istek zaman asimi (saniye).
        default_retry: Varsayilan yeniden deneme sayisi.
    """

    def __init__(self, default_timeout: float = 30.0, default_retry: int = 3) -> None:
        """Yeni APIIntegrator olusturur.

        Args:
            default_timeout: Varsayilan istek zaman asimi (saniye).
            default_retry: Varsayilan yeniden deneme sayisi.
        """
        self.default_timeout = default_timeout
        self.default_retry = default_retry
        logger.info("APIIntegrator baslatildi (timeout=%.1f, retry=%d)", default_timeout, default_retry)

    def parse_openapi(self, spec_dict: dict[str, Any]) -> APISpec:
        """OpenAPI/Swagger spec sozlugunu APISpec modeline ayristirir.

        Args:
            spec_dict: OpenAPI 3.0 spesifikasyon sozlugu.

        Returns:
            Ayristirilmis APISpec modeli.
        """
        info = spec_dict.get("info", {})
        servers = spec_dict.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""
        auth_type = self._detect_auth_type(spec_dict)

        endpoints: list[APIEndpointSpec] = []
        for path, methods in spec_dict.get("paths", {}).items():
            if not isinstance(methods, dict):
                continue
            for method, details in methods.items():
                m = method.upper()
                if m not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or not isinstance(details, dict):
                    continue
                params = {p.get("name", ""): p.get("schema", {}).get("type", "string")
                          for p in details.get("parameters", []) if p.get("name")}
                rb = details.get("requestBody", {}).get("content", {}).get("application/json", {})
                ok = details.get("responses", {}).get("200", details.get("responses", {}).get("201", {}))
                rs = ok.get("content", {}).get("application/json", {}).get("schema", {}) if ok else {}
                endpoints.append(APIEndpointSpec(
                    path=path, method=m, parameters=params,
                    request_body=rb.get("schema", {}),
                    response_model=rs.get("$ref", rs.get("type", "")),
                    description=details.get("summary", details.get("description", "")),
                ))

        spec = APISpec(
            title=info.get("title", "API"), base_url=base_url,
            version=info.get("version", "1.0.0"), auth_type=auth_type,
            endpoints=endpoints, headers={"Content-Type": "application/json"},
        )
        logger.info("OpenAPI ayristirildi: title=%s, endpoint=%d", spec.title, len(endpoints))
        return spec

    def generate_client(self, spec: APISpec, rate_limit: int = 0) -> APIClientConfig:
        """APISpec'ten eksiksiz Python istemci kodu uretir.

        Args:
            spec: API spesifikasyonu.
            rate_limit: Saniyedeki istek limiti (0 ise sinir yok).

        Returns:
            Uretilen istemci yapilandirmasi ve kodu.
        """
        logger.info("Istemci kodu uretiliyor: %s", spec.title)
        client_code = self._build_client_class(spec)
        if rate_limit > 0:
            client_code = self.add_rate_limiting(client_code, rate_limit)
        client_code = self.add_error_handling(client_code)
        config = APIClientConfig(
            spec_id=spec.id, client_code=client_code,
            auth_code=self.generate_auth_code(spec.auth_type),
            rate_limit=rate_limit, retry_count=self.default_retry, timeout=self.default_timeout,
        )
        logger.info("Istemci kodu uretildi: %d satir", client_code.count("\n") + 1)
        return config

    def generate_auth_code(self, auth_type: APIAuthType) -> str:
        """Kimlik dogrulama tipine gore yetkilendirme kodu uretir.

        Args:
            auth_type: API kimlik dogrulama tipi.

        Returns:
            Kimlik dogrulama islemi icin Python kod parcasi.
        """
        code = _AUTH_TEMPLATES.get(auth_type.value, "pass")
        logger.debug("Auth kodu uretildi: tip=%s", auth_type.value)
        return code

    def generate_endpoint_method(self, endpoint: APIEndpointSpec) -> str:
        """Tek bir API endpoint'i icin asenkron metot kodu uretir.

        Args:
            endpoint: API endpoint spesifikasyonu.

        Returns:
            Endpoint metodu icin Python kod parcasi.
        """
        name = self._endpoint_to_method_name(endpoint)
        sig = self._build_method_signature(endpoint)
        call = self._map_http_method(endpoint.method)
        ind = "        "
        desc = endpoint.description or f"{endpoint.method} {endpoint.path}"

        lines = [f"    async def {name}({sig}) -> dict:", f'        """{desc}"""']
        lines.append(f'{ind}url = f"{{self._base_url}}{endpoint.path}"')

        # Query parametreleri (yol disindakiler)
        qp = {k: v for k, v in endpoint.parameters.items() if f"{{{k}}}" not in endpoint.path}
        if qp:
            lines.append(f"{ind}params = {{{', '.join(f'\"{ k}\": {k}' for k in qp)}}}")
            lines.append(f"{ind}params = {{k: v for k, v in params.items() if v is not None}}")
        else:
            lines.append(f"{ind}params = None")

        body_arg = ", json=data" if endpoint.request_body else ""
        lines.append(f"{ind}response = await self._client.{call}(url{body_arg}, params=params, headers=self._headers)")
        lines.append(f"{ind}response.raise_for_status()")
        lines.append(f"{ind}return response.json()")
        logger.debug("Endpoint metodu uretildi: %s", name)
        return "\n".join(lines)

    def add_rate_limiting(self, client_code: str, rate_limit: int) -> str:
        """Uretilen istemci koduna hiz sinirlandirma mantigi ekler.

        Args:
            client_code: Mevcut istemci kodu.
            rate_limit: Saniyedeki maksimum istek sayisi.

        Returns:
            Hiz sinirlandirma eklenmis istemci kodu.
        """
        snippet = textwrap.indent(textwrap.dedent(f"""\
            # --- Hiz sinirlandirma ---
            _rate_semaphore = None
            _rate_limit = {rate_limit}

            async def _acquire_rate_limit(self) -> None:
                \"\"\"Hiz sinirlandirici kilidini bekler.\"\"\"
                if self._rate_semaphore is None:
                    import asyncio
                    self._rate_semaphore = asyncio.Semaphore(self._rate_limit)
                await self._rate_semaphore.acquire()

            async def _release_rate_limit(self) -> None:
                \"\"\"Hiz sinirlandirici kilidini serbest birakir.\"\"\"
                if self._rate_semaphore is not None:
                    self._rate_semaphore.release()
        """), "    ")
        logger.debug("Hiz sinirlandirma eklendi: limit=%d/s", rate_limit)
        return client_code.rstrip() + "\n" + snippet

    def add_error_handling(self, client_code: str) -> str:
        """Uretilen istemci koduna hata yonetimi/yeniden deneme mantigi ekler.

        Args:
            client_code: Mevcut istemci kodu.

        Returns:
            Hata yonetimi eklenmis istemci kodu.
        """
        snippet = textwrap.indent(textwrap.dedent("""\
            # --- Hata yonetimi ve yeniden deneme ---
            async def _request_with_retry(self, method: str, url: str, **kwargs) -> "httpx.Response":
                \"\"\"Yeniden deneme mantigi ile HTTP istegi gonderir.\"\"\"
                last_error = None
                for attempt in range(1, self._retry_count + 1):
                    try:
                        resp = await getattr(self._client, method)(url, **kwargs)
                        resp.raise_for_status()
                        return resp
                    except Exception as exc:
                        last_error = exc
                        if attempt < self._retry_count:
                            import asyncio
                            await asyncio.sleep(2 ** attempt)
                raise last_error  # type: ignore[misc]
        """), "    ")
        logger.debug("Hata yonetimi eklendi: retry=%d", self.default_retry)
        return client_code.rstrip() + "\n" + snippet

    def validate_spec(self, spec: APISpec) -> list[str]:
        """APISpec'i eksiksizlik icin dogrular.

        Args:
            spec: Dogrulanacak API spesifikasyonu.

        Returns:
            Dogrulama uyari/hata mesajlari listesi.
        """
        issues: list[str] = []
        if not spec.title:
            issues.append("API basligi (title) eksik")
        if not spec.base_url:
            issues.append("Temel URL (base_url) eksik")
        if not spec.endpoints:
            issues.append("Hic endpoint tanimlanmamis")
        for i, ep in enumerate(spec.endpoints):
            if not ep.path:
                issues.append(f"Endpoint[{i}]: yol (path) eksik")
            if ep.method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                issues.append(f"Endpoint[{i}]: gecersiz HTTP metodu '{ep.method}'")
            if ep.method in {"POST", "PUT", "PATCH"} and not ep.request_body:
                issues.append(f"Endpoint[{i}]: {ep.method} icin istek govdesi eksik")
        if issues:
            logger.warning("Spec dogrulama sorunlari: %d adet", len(issues))
        return issues

    # --- Dahili yardimci metotlar ---

    def _build_client_class(self, spec: APISpec) -> str:
        """APISpec'ten tam istemci sinif kodu olusturur."""
        cn = self._title_to_class_name(spec.title)
        i1, i2 = "    ", "        "
        lines = ["import httpx"]
        if spec.auth_type == APIAuthType.OAUTH2:
            lines.append("import time")
        lines += ["", "", f"class {cn}:", f'{i1}"""{spec.title} API istemcisi."""', ""]

        # __init__
        lines.append(f"{i1}def __init__(self{_AUTH_INIT_PARAMS.get(spec.auth_type.value, '')}) -> None:")
        lines.append(f'{i2}"""Yeni {cn} olusturur."""')
        lines.append(f'{i2}self._base_url = "{spec.base_url}"')
        lines.append(f"{i2}self._headers = {json.dumps(spec.headers)}")
        lines.append(f"{i2}self._retry_count = {self.default_retry}")
        lines.append(f"{i2}self._client = httpx.AsyncClient(timeout={self.default_timeout})")
        for al in _AUTH_INIT_BODY.get(spec.auth_type.value, "").split("\n"):
            if al:
                lines.append(f"{i2}{al}")
        lines += ["", f"{i1}async def close(self) -> None:",
                   f'{i2}"""Istemci baglantisini kapatir."""', f"{i2}await self._client.aclose()", ""]

        for ep in spec.endpoints:
            lines += [self.generate_endpoint_method(ep), ""]
        return "\n".join(lines)

    def _build_method_signature(self, endpoint: APIEndpointSpec) -> str:
        """Endpoint parametrelerinden metot imzasi olusturur."""
        parts: list[str] = ["self"]
        path_params = re.findall(r"\{(\w+)\}", endpoint.path)
        for pp in path_params:
            parts.append(f"{pp}: {_TYPE_MAP.get(endpoint.parameters.get(pp, 'string'), 'str')}")
        for name, ptype in endpoint.parameters.items():
            if name not in path_params:
                parts.append(f"{name}: Optional[{_TYPE_MAP.get(ptype, 'str')}] = None")
        if endpoint.request_body:
            parts.append("data: dict = None")
        return ", ".join(parts)

    def _map_http_method(self, method: str) -> str:
        """HTTP metot dizgesini httpx metot cagrisi adina esler."""
        return {"GET": "get", "POST": "post", "PUT": "put", "PATCH": "patch", "DELETE": "delete"}.get(method.upper(), "get")

    def _detect_auth_type(self, spec_dict: dict[str, Any]) -> APIAuthType:
        """OpenAPI spec'inden kimlik dogrulama tipini tespit eder."""
        for scheme in spec_dict.get("components", {}).get("securitySchemes", {}).values():
            st = scheme.get("type", "")
            if st == "oauth2":
                return APIAuthType.OAUTH2
            if st == "http":
                hs = scheme.get("scheme", "")
                return APIAuthType.BEARER if hs == "bearer" else (APIAuthType.BASIC if hs == "basic" else APIAuthType.NONE)
            if st == "apiKey":
                return APIAuthType.API_KEY
        return APIAuthType.NONE

    def _title_to_class_name(self, title: str) -> str:
        """API basligini PascalCase sinif adina donusturur."""
        cleaned = re.sub(r"[^a-zA-Z0-9]", " ", title)
        name = "".join(w.capitalize() for w in cleaned.split())
        return name if name.endswith("Client") else name + "Client"

    def _endpoint_to_method_name(self, endpoint: APIEndpointSpec) -> str:
        """Endpoint yolundan snake_case metot adi uretir."""
        path = re.sub(r"\{[^}]+\}", "", endpoint.path.strip("/"))
        parts = [p for p in re.split(r"[/\-_]", path) if p]
        return f"{endpoint.method.lower()}_{'_'.join(parts)}".lower() if parts else endpoint.method.lower()

    def _openapi_type_to_python(self, openapi_type: str) -> str:
        """OpenAPI tip adini Python tip adina esler."""
        return _TYPE_MAP.get(openapi_type, "str")
