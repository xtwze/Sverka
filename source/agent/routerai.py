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
    "Суммы указаны в копейках. Пиши копейки и переводи в рубли в скобках. Не придумывай факты, причины или действия. "
    "Если данных для ответа нет, прямо скажи об этом. Отвечай по-русски. "
    "Начинай с прямого ответа на вопрос, без вводных фраз о предоставленных данных. "
    "На простой вопрос отвечай одним-двумя предложениями без списка. "
    "Отвечай только о том, что спросили: вопрос о количестве платежей не требует "
    "сумм, начислений или статуса их сверки. Если количества в источниках различаются, "
    "назови оба; не объединяй их. Суммы добавляй только по запросу. "
    "Не показывай внутренние имена полей, инструментов и разделов JSON "
    "(payments_summary, charges_reconciliation, count, total_kopecks). "
    "Называй источники 1С и PostgreSQL, а период — по-русски. "
    "Статусы MATCH/MISMATCH и список расхождений относятся только к начислениям. "
    "Для платежей доступны лишь количество и общая сумма: даже их совпадение "
    "не доказывает совпадения отдельных платежей. Если просят сверить платежи, "
    "объясни это ограничение. Не вычисляй новые суммы или разницы самостоятельно."
)
class ModelResponseError(RuntimeError):
    """Провайдер вернул неполный или неожиданный ответ."""


class ModelResponseTruncated(ModelResponseError):
    """Ответ остановлен из-за ограничения длины."""


class RouterAIAgent:
    def __init__(self, tools: AgentTools, api_key: str, client: httpx.Client | None = None):
        if not api_key:
            raise ValueError("LLM_API is required")
        self.trace: list[dict[str, Any]] = []
        self.tools = tools
        self.api_key = api_key
        self._owns_client = client is None
        self.client = client if client is not None else httpx.Client(timeout=30)

    def close(self) -> None:
        """Закрыть собственный клиент; переданным клиентом управляет вызывающий код."""
        if self._owns_client:
            self.client.close()

    @classmethod
    def from_env(cls, tools: AgentTools) -> "RouterAIAgent":
        return cls(tools, os.getenv("LLM_API", ""))

    def _complete(self, messages: list[dict[str, Any]], include_tools: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4096,
        }
        if include_tools:
            body["tools"] = [self.tools.model_spec("reconcile_charges")]
            body["tool_choice"] = "auto"
        response = self.client.post(
            API_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
        )
        response.raise_for_status()
        try:
            choice = response.json()["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ModelResponseTruncated("Model response exceeded the token limit")
            return choice["message"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ModelResponseError("RouterAI returned an invalid response") from error

    def ask(self, question: str) -> str:
        self.trace = []
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
        self.trace.append({"name": name, "arguments": arguments, "output": result})
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
