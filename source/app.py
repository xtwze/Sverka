"""HTTP API импорта и сверки."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from source.database import Database
from source.models import SourceContractError
from source.service import ReconciliationService
from source.settings import Settings
from source.source_client import SourceClient, SourceUnavailable

app = FastAPI(title="Reconciliation API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_service() -> ReconciliationService:
    settings = Settings.from_env()
    return ReconciliationService(SourceClient(settings), Database(settings.database_url))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/import")
def import_data():
    try:
        return get_service().import_data()
    except (SourceUnavailable, SourceContractError) as error:
        raise HTTPException(502, str(error)) from error


@app.get("/api/reconcile")
def reconcile(period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")):
    try:
        return get_service().reconcile(period)
    except (SourceUnavailable, SourceContractError) as error:
        raise HTTPException(502, str(error)) from error
