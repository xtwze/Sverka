"""Отдельный HTTP-процесс агента, без подключения импортёра."""

from fastapi import FastAPI

from source.controllers.chat_controller import router as chat_router
from source.controllers.health_controller import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(title="Read-only reconciliation agent", version="1.0")
    application.include_router(health_router)
    application.include_router(chat_router)
    return application


app = create_app()
