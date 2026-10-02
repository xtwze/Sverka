"""Web chat endpoint backed by read-only reconciliation tools."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from source.agent.dependencies import get_agent_tools
from source.agent.routerai import ModelResponseError, ModelResponseTruncated, RouterAIAgent
from source.agent.tools import AgentTools
from source.clients.onec_client import SourceUnavailable
from source.dto.source_dto import SourceContractError

router = APIRouter(prefix="/api/agent", tags=["agent"])


def get_chat_tools() -> AgentTools:
    try:
        return get_agent_tools()
    except RuntimeError as error:
        raise HTTPException(503, "Доступ агента к данным не настроен на сервере.") from error


class ChatRequest(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, tools: AgentTools = Depends(get_chat_tools)) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(422, "Введите вопрос.")
    try:
        agent = RouterAIAgent.from_env(tools)
    except ValueError as error:
        raise HTTPException(503, "Модель не настроена на сервере.") from error
    try:
        return ChatResponse(answer=agent.ask_for_period(request.message, request.period))
    except (SourceUnavailable, SourceContractError) as error:
        raise HTTPException(502, "Источник данных недоступен. Повторите позже.") from error
    except ModelResponseTruncated as error:
        raise HTTPException(
            502, "Ответ модели превысил ограничение длины. Уточните вопрос или запросите меньше деталей."
        ) from error
    except (httpx.HTTPError, ModelResponseError) as error:
        raise HTTPException(502, "Не удалось получить ответ модели. Повторите позже.") from error
    finally:
        agent.close()
