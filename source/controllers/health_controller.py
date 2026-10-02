"""HTTP-контроллер проверки доступности."""

from fastapi import APIRouter

from source.config.source_settings import SourceSettings
from source.dto.response_dto import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/source-info")
def source_info() -> dict[str, str]:
    """Режим подключения из конфигурации; не подтверждает доступность 1С."""
    return {"mode": SourceSettings.from_env().source_mode}
