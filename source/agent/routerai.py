"""Адаптер RouterAI для сверки через разрешённые инструменты."""

import json
import os
from typing import Any

import httpx

from source.agent.tools import AgentTools, ReconcileChargesInput, ToolInputError, UnknownToolError

MODEL = "qwen/qwen3.5-flash-02-23"
API_URL = "https://routerai.ru/api/v1/chat/completions"
SYSTEM_MESSAGE = (
    "Ты помогаешь сверять начисления 1С и PostgreSQL. "
    "Для фактов о данных вызывай только предоставленный инструмент. "
    "Не придумывай суммы, записи или причины расхождений. "
    "Если период не указан, попроси месяц в формате YYYY-MM. "
    "После вызова инструмента кратко объясни его результат по-русски."
)
WEB_SYSTEM_MESSAGE = (
    "Ты объясняешь результаты сверки 1С и PostgreSQL. "
    "Отвечай только по данным инструментов в сообщении пользователя. "
    "Суммы указаны в копейках. Не придумывай факты, причины или действия. "
    "Если данных для ответа нет, прямо скажи об этом. Отвечай по-русски."
)
TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "reconcile_charges",
        "description": "Сверить начисления 1С и PostgreSQL за месяц",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "pattern": r"^\d{4}-(0[1-9]|1[0-2])$",
                    "description": "Месяц в формате YYYY-MM",
                }
            },
            "required": ["period"],
            "additionalProperties": False,
        },
    },
}


class ModelResponseError(RuntimeError):
    """Провайдер вернул неполный или неожиданный ответ."""


class RouterAIAgent:
    def __init__(self, tools: AgentTools, api_key: str, client: httpx.Client | None = None):
        if not api_key:
            raise ValueError("LLM_API is required")
        self.tools = tools
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30)

    @classmethod
    def from_env(cls, tools: AgentTools) -> "RouterAIAgent":
        return cls(tools, os.getenv("LLM_API", ""))

    def _complete(self, messages: list[dict[str, Any]], include_tools: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 600,
        }
        if include_tools:
            body["tools"] = [TOOL_SPEC]
            body["tool_choice"] = "auto"
        response = self.client.post(
            API_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
        )
        response.raise_for_status()
        try:
            return response.json()["choices"][0]["message"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ModelResponseError("RouterAI returned an invalid response") from error

    def ask(self, question: str) -> str:
        if not question.strip():
            raise ValueError("Question must not be empty")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": question},
        ]
        first = self._complete(messages, include_tools=True)
        calls = first.get("tool_calls") or []
        if not calls:
            # Без результата инструмента разрешено лишь уточнить отсутствующий период.
            return "Укажите месяц сверки в формате YYYY-MM."
        if len(calls) != 1:
            raise ModelResponseError("Expected exactly one tool call")
        call = calls[0]
        try:
            name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"])
            call_id = call["id"]
            result = self.tools.invoke(name, arguments)
        except (KeyError, TypeError, ValueError, ToolInputError, UnknownToolError) as error:
            raise ModelResponseError("Invalid tool call from model") from error
        messages.append(
            {
                "role": "assistant",
                "content": first.get("content"),
                "tool_calls": calls,
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
        final = self._complete(messages, include_tools=False)
        answer = final.get("content")
        if not isinstance(answer, str) or not answer.strip():
            raise ModelResponseError("RouterAI returned an empty answer")
        return answer.strip()

    def ask_for_period(self, question: str, period: str) -> str:
        """Read approved data for the selected month, then explain the results."""
        ReconcileChargesInput.model_validate({"period": period})
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty")
        facts = {
            "charges_reconciliation": self.tools.invoke("reconcile_charges", {"period": period}),
            "payments_summary": self.tools.invoke("summarize_payments", {"period": period}),
        }
        return self._answer_from_facts(question, period, facts)

    def _answer_from_facts(self, question: str, period: str, facts: dict[str, Any]) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": WEB_SYSTEM_MESSAGE},
            {"role": "user", "content": f"Период: {period}. Вопрос: {question.strip()}\n"
             f"Данные инструментов: {json.dumps(facts, ensure_ascii=False)}"},
        ]
        final = self._complete(messages, include_tools=False)
        answer = final.get("content")
        if not isinstance(answer, str) or not answer.strip():
            raise ModelResponseError("RouterAI returned an empty answer")
        return answer.strip()
