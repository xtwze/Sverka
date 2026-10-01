"""HTTP-контроллер сверки."""

from fastapi import APIRouter, Depends, HTTPException, Query

from source.clients.onec_client import SourceUnavailable
from source.config.dependencies import get_reconciliation_service
from source.dto.response_dto import ReconciliationResponse
from source.dto.source_dto import SourceContractError
from source.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api", tags=["reconciliation"])


@router.get("/reconcile", response_model=ReconciliationResponse)
def reconcile(
    period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationResponse:
    try:
        return service.reconcile(period)
    except (SourceUnavailable, SourceContractError) as error:
        raise HTTPException(502, str(error)) from error
