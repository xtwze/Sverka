"""HTTP-контроллер импорта."""

from fastapi import APIRouter, Depends, HTTPException

from source.clients.onec_client import SourceUnavailable
from source.config.dependencies import get_import_service
from source.dto.response_dto import ImportResponse
from source.dto.source_dto import SourceContractError
from source.services.import_service import ImportService

router = APIRouter(prefix="/api", tags=["import"])


@router.post("/import", response_model=ImportResponse)
def import_data(
    service: ImportService = Depends(get_import_service),
) -> ImportResponse:
    try:
        return service.import_data()
    except (SourceUnavailable, SourceContractError) as error:
        raise HTTPException(502, str(error)) from error
