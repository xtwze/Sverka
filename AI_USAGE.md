# Использование AI

## Вклад и время

Самостоятельно определил веб-архитектуру приложения, описал контракты данных,
настроил исходную базу и HTTP-контракты в 1С.

Coding agent участвовал в реализации backend и frontend, тестах, документации,
настройке Docker и проверке интеграции. Для проверки и доработки решения использован
Codex; точная модель агента исходного этапа не зафиксирована.

Приблизительное активное время исходной разработки:

- подготовка 1С — 1–1,5 часа;
- приложение с coding agent — 3–4 часа.

Последующая проверка и подготовка окружения в эти оценки не входят;
отдельный точный хронометраж не вёлся.

## Модель в приложении

`qwen/qwen3.5-flash-02-23` через RouterAI: `temperature=0`, `max_tokens=600`,
HTTP timeout 30 секунд. Ключ задаётся в локальном окружении сервиса агента.
Модель объясняет результаты инструментов, а суммы и расхождения вычисляет Python/SQL.

## Пример применения: валидация источника

[Навык валидации](skills/validate-source-data/SKILL.md) проверяет контракт,
типы полей, уникальность ID и номеров счетов, периоды и ссылки между записями.

```bash
docker compose exec -T agent uv run --frozen --no-dev python scripts/preflight.py --real
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_onec_charges --period 2026-08
```

В реальном источнике проверены 2 счёта, 4 начисления и 1 платёж. За август:
`charge-1`, `charge-2`, `charge-3`; 3 записи и `1140000` копеек.

## Пример применения: проверка сверки

[Навык сверки](skills/verify-reconciliation-report/SKILL.md) сопоставляет отдельные
чтения 1С и PostgreSQL с отчётом общего сервиса:

```bash
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_onec_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_postgres_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools reconcile_charges --period 2026-08
```

В отдельной тестовой PostgreSQL проверен цикл MATCH → MISMATCH → MATCH.
При расхождении обнаружены `charge-2` (`24950`/`25050`) и отсутствие `charge-3`
(`990000`/`null`). После восстановления результаты совпали. Значения взяты из
вывода инструментов, а не из арифметики модели. Mock и настоящая 1С проверены
отдельными прогонами.

## Контроль результата агента

Код проверен тестами и реальными вызовами. В частности:

- независимые проверки счёта и суммы позволяют сообщить оба расхождения одной записи;
- отдельный процесс агента не получает реквизиты импортёра;
- состав Docker-образа ограничен исходниками и зависимостями;
- права чтения проверены попытками записи в 1С и PostgreSQL;
- ответ чата сопоставлен с JSON инструментов.

[Результаты проверок](docs/VALIDATION.md) · [Пример ответа чата](docs/evidence/agent-chat-real.json).
