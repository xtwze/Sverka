FROM ghcr.io/astral-sh/uv:0.11.6@sha256:b1e699368d24c57cda93c338a57a8c5a119009ba809305cc8e86986d4a006754 AS uv
FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS runtime
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --python /usr/local/bin/python
FROM runtime AS agent
COPY source/__init__.py ./source/
COPY source/agent ./source/agent
COPY source/clients ./source/clients
COPY source/domain ./source/domain
COPY source/dto ./source/dto
COPY source/config/__init__.py source/config/source_settings.py ./source/config/
COPY source/controllers/__init__.py source/controllers/health_controller.py source/controllers/chat_controller.py ./source/controllers/
COPY source/services/__init__.py source/services/reconciliation_service.py ./source/services/
COPY source/repositories/__init__.py source/repositories/database.py source/repositories/account_repository.py source/repositories/charge_repository.py source/repositories/common.py ./source/repositories/
COPY source/cli/__init__.py source/cli/agent_tools.py source/cli/commands.py ./source/cli/
COPY scripts/preflight.py ./scripts/
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "source.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS application
COPY source ./source
COPY fixtures/data.json ./fixtures/data.json
COPY scripts/preflight.py scripts/discrepancy.py ./scripts/
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "source.main:app", "--host", "0.0.0.0", "--port", "8000"]
