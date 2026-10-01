"""HTTP-контроллер проверки доступности."""

from fastapi import APIRouter

from source.dto.response_dto import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
