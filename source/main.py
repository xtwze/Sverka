"""Точка входа HTTP API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from source.controllers.chat_controller import router as chat_router
from source.controllers.health_controller import router as health_router
from source.controllers.import_controller import router as import_router
from source.controllers.reconciliation_controller import router as reconciliation_router


def create_app() -> FastAPI:
    application = FastAPI(title="Reconciliation API", version="1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(import_router)
    application.include_router(reconciliation_router)
    application.include_router(chat_router)
    return application


app = create_app()
