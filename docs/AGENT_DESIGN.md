# Read-only агент сверки

Пользователь → CLI или веб-чат → проверка аргументов → AgentTools →
ReconciliationService → HTTP-источник + PostgreSQL → структурированный отчёт.
Модель объясняет результат; суммы и расхождения вычисляет код.

## Изоляция

Compose запускает `api` и `agent` отдельными процессами. Только `api` получает
`DATABASE_URL` импортёра; только `agent` получает `LLM_API` и `AGENT_DATABASE_URL`.
Для 1С используется пользователь только с чтением. Frontend обращается через
Nginx: `/api/agent/` направляется в `agent`, прочие `/api/` в `api`.
Маршрута импорта в приложении агента нет.

`get_agent_tools` отклоняет окружение с `DATABASE_URL`, требует роль
`agent_reader` и создаёт `SourceSettings`, в которой нет подключения импортёра.
PostgreSQL запрещает агенту INSERT/UPDATE/DELETE; установлен режим read-only.
Запрет поддерживается правами БД и списком инструментов, а не только промптом.

Локальные команды используют `.env.agent` из `agent.env.example`. Общий `.env`
используется Compose и импортёром, но не CLI-агентом. Ключи не печатаются в логах.

## Инструменты

Операции объявлены `@tool` из `langchain-core`. Аргументы строго ограничены полем
`period` формата `YYYY-MM`, неизвестные поля и имена отклоняются.

- `read_onec_charges` — записи, количество и сумма источника за месяц;
- `read_postgres_charges` — те же поля из PostgreSQL под `agent_reader`;
- `reconcile_charges` — общий структурированный отчёт;
- `summarize_payments` — сводка платежей, без заявления о построчной сверке платежей.

Первые три доступны через `source.cli.agent_tools`. В модельном CLI открыт только
`reconcile_charges`; веб-чат сам вызывает сверку и сводку платежей, затем передаёт
готовые факты модели. Произвольного SQL, импорта или удаления в списке нет.

```bash
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_onec_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_postgres_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools reconcile_charges --period 2026-08
```

Локально:

```bash
uv run --env-file .env.agent python -m source.agent.cli 'Сверь начисления за 2026-08'
```

Без ключа модели чат возвращает 503. Недоступность источника не превращается в
`MATCH`. Сравнивать точность ответа модели нужно с JSON инструмента, а не с другим
ответом модели. Проверены отдельные сценарии с HTTP mock и с настоящей 1С в Linux/Docker;
результаты real-прогона сохранены в `docs/evidence/real-1c-run.json`.
