"""Plugin sistemi API endpoint'leri."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.models.plugin import PluginInfo, PluginListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


def _get_plugin_manager(request: Request) -> Any:
    """Request'ten PluginManager alir.

    Args:
        request: FastAPI request nesnesi.

    Returns:
        PluginManager ornegi.

    Raises:
        HTTPException: PluginManager mevcut degilse.
    """
    pm = getattr(request.app.state, "plugin_manager", None)
    if pm is None:
        raise HTTPException(
            status_code=503,
            detail="Plugin sistemi kullanilabilir degil",
        )
    return pm


@router.get("", response_model=PluginListResponse)
async def list_plugins(request: Request) -> PluginListResponse:
    """Tum plugin'leri listeler.

    Returns:
        Plugin listesi ve toplam sayisi.
    """
    pm = _get_plugin_manager(request)
    plugins = pm.registry.list_all()
    return PluginListResponse(total=len(plugins), plugins=plugins)


@router.get("/{name}")
async def get_plugin(request: Request, name: str) -> PluginInfo:
    """Plugin detayini dondurur.

    Args:
        name: Plugin adi.

    Returns:
        Plugin bilgisi.
    """
    pm = _get_plugin_manager(request)
    info = pm.registry.get(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin bulunamadi: {name}")
    return info


@router.post("/{name}/enable")
async def enable_plugin(request: Request, name: str) -> dict[str, Any]:
    """Plugin'i etkinlestirir.

    Args:
        name: Plugin adi.

    Returns:
        Islem sonucu.
    """
    pm = _get_plugin_manager(request)
    try:
        info = await pm.enable_plugin(name)
        return {"status": "enabled", "plugin": name, "state": info.state.value}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{name}/disable")
async def disable_plugin(request: Request, name: str) -> dict[str, Any]:
    """Plugin'i devre disi birakir.

    Args:
        name: Plugin adi.

    Returns:
        Islem sonucu.
    """
    pm = _get_plugin_manager(request)
    try:
        info = await pm.disable_plugin(name)
        return {"status": "disabled", "plugin": name, "state": info.state.value}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/reload")
async def reload_all_plugins(request: Request) -> dict[str, Any]:
    """Tum plugin'leri yeniden yukler.

    Returns:
        Yukleme sonuclari.
    """
    pm = _get_plugin_manager(request)
    try:
        await pm.shutdown()
        count = await pm.initialize()
        results = await pm.load_all()
        enabled = sum(1 for i in results.values() if i.state.value == "enabled")
        return {
            "status": "reloaded",
            "discovered": count,
            "enabled": enabled,
        }
    except Exception as exc:
        logger.error("Plugin reload hatasi: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
