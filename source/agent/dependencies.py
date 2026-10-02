"""Отдельное подключение агента к PostgreSQL только для чтения."""

import os

from psycopg.conninfo import conninfo_to_dict

from source.agent.tools import AgentTools
from source.clients.onec_client import OneCClient
from source.config.source_settings import SourceSettings
from source.repositories.account_repository import AccountRepository
from source.repositories.charge_repository import ChargeRepository
from source.repositories.database import Database
from source.services.reconciliation_service import ReconciliationService


def get_agent_tools() -> AgentTools:
    database_url = os.getenv("AGENT_DATABASE_URL")
    if not database_url:
        raise RuntimeError("AGENT_DATABASE_URL is required for agent tools")
    if os.getenv("DATABASE_URL"):
        raise RuntimeError("Remove DATABASE_URL from the agent environment; use .env.agent")
    if conninfo_to_dict(database_url).get("user") != "agent_reader":
        raise RuntimeError("Agent tools require the agent_reader database role")
    settings = SourceSettings.from_env()
    source = OneCClient(settings)
    database = Database(database_url)
    charges = ChargeRepository()
    service = ReconciliationService(
        source,
        database,
        AccountRepository(),
        charges,
    )
    return AgentTools(service, source, database, charges)
