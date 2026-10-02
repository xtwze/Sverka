# Сверка начислений 1С → PostgreSQL

React + TypeScript, FastAPI и PostgreSQL. Приложение импортирует счета, начисления
и платежи через read-only HTTP JSON, затем сверяет начисления за выбранный месяц.
Суммы хранятся в целых копейках. UI, CLI и агент используют один
`ReconciliationService`; арифметику выполняет Python, не модель.

**Статус:** проверены HTTP mock и **настоящая 1С 8.3.27.1508 в Linux/Docker**.
Восстановление базы, повторный импорт, read-only права и цикл MATCH → MISMATCH → MATCH
прошли. [Протокол](docs/VALIDATION.md), [запуск настоящей 1С](onec/linux/README.md).
Обычный Compose без настройки `ONEC_BASE_URL` запускает mock; это отдельный режим.

## Запуск

Нужны Docker Engine/Desktop и Compose v2. Из корня:

```bash
cp .env.example .env
COMPOSE_BAKE=false DOCKER_BUILDKIT=0 docker compose up -d --build --wait
```

Если `.env` уже существует, сохраните его; не заменяйте ключи и настройки шаблоном.
Классическая сборка используется для совместимости с кириллицей в пути.

- UI: <http://localhost:5173>;
- API/OpenAPI: <http://localhost:8080/docs>;
- изолированный агент/OpenAPI: <http://localhost:8081/docs>;
- HTTP mock: <http://localhost:8093>;
- PostgreSQL: `localhost:5543/reporting`.

Nginx направляет `/api/agent/` отдельному сервису `agent`, остальные `/api/` —
в `api`. Браузер использует тот же origin, поэтому изменение `FRONTEND_PORT`
не требует пересборки адреса API. Режим источника виден в шапке и отчёте.

Для чата задайте `LLM_API` в локальном `.env`, затем:

```bash
docker compose up -d --wait agent
```

Без ключа импорт и сверка работают, а чат сообщает, что модель не настроена.
Результаты инструментов отправляются внешнему провайдеру только при вопросе в чат.
API-ключ доступен серверному процессу агента, в браузер не передаётся.

## Сценарий проверки (mock)

Перед импортом примените [навык валидации](skills/validate-source-data/SKILL.md):

```bash
uv sync --frozen
uv run python scripts/preflight.py
curl -fsS -X POST http://localhost:5173/api/import
curl -fsS 'http://localhost:5173/api/reconcile?period=2026-08'
curl -fsS -X POST http://localhost:5173/api/import
```

Оба импорта возвращают 2 счёта, 4 начисления и 1 платёж. Август: 3 начисления,
`1140000` копеек с каждой стороны и `MATCH`. Сентябрьская запись исключается.

Только в локальной **тестовой** PostgreSQL:

```bash
uv run --env-file .env python scripts/discrepancy.py introduce
curl -fsS 'http://localhost:5173/api/reconcile?period=2026-08'
uv run --env-file .env python scripts/discrepancy.py restore
curl -fsS 'http://localhost:5173/api/reconcile?period=2026-08'
```

Ожидаются `amount_mismatch` у `charge-2` (`24950`/`25050`) и
`missing_in_postgres` у `charge-3` (`990000`/`null`), затем снова `MATCH`.
Исходник mock/1С скрипт не меняет. После `introduce` всегда выполняйте `restore`.
Скрипт отказывается вносить расхождения, если исходные две записи уже изменены.

## CLI и граница прав агента

Предпочтительный вариант — уже настроенный отдельный контейнер:

```bash
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_onec_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_postgres_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools reconcile_charges --period 2026-08
docker compose exec -T agent uv run --frozen --no-dev python -m source.agent.cli 'Сверь начисления за 2026-08'
```

Для CLI на хосте скопируйте `agent.env.example` в **отдельный** `.env.agent`:

```bash
cp agent.env.example .env.agent
uv run --env-file .env.agent python -m source.cli.agent_tools reconcile_charges --period 2026-08
uv run --env-file .env.agent python -m source.cli.commands --period 2026-08
```

Не передавайте агенту общий `.env` и не экспортируйте `DATABASE_URL` в его shell.
При наличии этой переменной или иной роли вместо `agent_reader` инструменты
отказываются работать. `source.cli.commands` возвращает код 0 для `MATCH`, 1 для
`MISMATCH`; команды `agent_tools` выводят JSON (статус находится в отчёте).
Подключение импортёра существует только в API/тестовых скриптах.
Роль `agent_reader` имеет SELECT без INSERT/UPDATE/DELETE и read-only транзакции.
`agent` не содержит HTTP-маршрута импорта. Skills:
[валидация](skills/validate-source-data/SKILL.md) и
[сверка](skills/verify-reconciliation-report/SKILL.md).

## Проверки кода

```bash
uv sync --frozen
uv run ruff check source tests scripts
uv run pytest -q
cd frontend
npm ci
npm test
npm run build
```

Два PostgreSQL-теста пропускаются без `TEST_DATABASE_URL`. Задайте его на
**отдельную тестовую базу**, где тестовая роль может создавать схемы. Каждый тест
создаёт свою схему и удаляет её в `finally`. Проверяются повторный импорт с точным
сравнением строк и полный цикл внесения/восстановления расхождений. Не используйте
рабочую базу. [Результаты проверок](docs/VALIDATION.md).

Ручная UI smoke-проверка: открыть страницу, убедиться в отметке mock, выбрать
`2026-08`, запустить сверку, проверить статус, обе суммы, количество и ID запуска.
Сменить месяц: старый отчёт должен исчезнуть. Ошибка API должна отображаться
сообщением, а не успешным пустым отчётом.

## Как добавить правило

В `source/domain/source_validation.py` определите функцию
`rule(snapshot) -> None`, выбрасывающую `SourceContractError` при нарушении,
и зарегистрируйте её в `DEFAULT_SOURCE_RULES`. Парсер и `ImportService` менять
не требуется. [Пример расширения](docs/RULES.md): `unique_account_numbers`
проверяет ограничение UNIQUE ещё до открытия транзакции.

## Состав

- `source/controllers`, `services`, `repositories`, `domain` — маршруты,
  сценарии, SQL и правила; `dto` — входные/выходные контракты;
- `source/agent` — отдельное приложение и read-only инструменты;
- `frontend` — одна веб-страница и Nginx;
- `onec/configuration` — XML/BSL минимальной конфигурации;
- `scripts/onec_demo.py` — создание новой демобазы и двукратная загрузка фикстур;
- `fixtures/data.json` — фиксированный источник тестовых данных;
- `postgres/init.sql` — роль `agent_reader`;
- `docs/evidence` — результаты команд без ключей и локальных баз.

Поле `source_mode: real` означает выбранное подключение `ONEC_BASE_URL`,
а не самостоятельное доказательство успешной интеграции. Для реального прогона
нужны опубликованная 1С, успешный preflight, импорт, сверка и проверка прав.

## Документация

- [Архитектура](docs/ARCHITECTURE.md) и [read-only агент](docs/AGENT_DESIGN.md).
- [Конфигурация 1С](onec/README.md) и [запуск Linux/Docker](onec/linux/README.md).
- [Результаты проверок](docs/VALIDATION.md) и [использование AI](AI_USAGE.md).

Секреты, файлы баз, лицензии и установщики не включаются в Git.
Образ платформы 1С собирается локально из официального дистрибутива.
