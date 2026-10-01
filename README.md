# Сверка начислений 1С → PostgreSQL

Приложение импортирует лицевые счета, начисления и платежи из read-only HTTP API 1С
в PostgreSQL и сверяет начисления за выбранный месяц. Суммы передаются и хранятся
целым числом копеек.

## Состав

- `onec/configuration` — исходники минимальной конфигурации 1С;
- `source` — FastAPI, импорт, сверка и CLI;
- `frontend` — React + TypeScript;
- `postgres` — создание отдельной read-only роли агента;
- `fixtures` — фиксированный набор данных стартового контракта;
- `scripts` — preflight и контролируемое внесение расхождения.

HTTP API и CLI используют `ReconciliationService`, поэтому правила сравнения не
дублируются. Импорт сначала получает и проверяет весь снимок источника, затем
сохраняет его одной транзакцией с upsert. Повторный запуск идемпотентен.

## Запуск

Требуется Docker Engine/Desktop с Compose v2+.

```bash
cp .env.example .env
COMPOSE_BAKE=false DOCKER_BUILDKIT=0 docker compose up -d --build --wait
```

Классический режим сборки указан для каталогов, в пути которых есть кириллица.

- интерфейс: <http://localhost:5173>;
- backend и OpenAPI: <http://localhost:8080/docs>;
- mock-источник: <http://localhost:8093>;
- PostgreSQL: `localhost:5543/reporting`.

## Проверка сценария

```bash
curl -X POST http://localhost:8080/api/import
curl 'http://localhost:8080/api/reconcile?period=2026-08'

# Повторный импорт возвращает те же количества и не создаёт дубликаты.
curl -X POST http://localhost:8080/api/import

# Внести отличие в 100 копеек и увидеть MISMATCH.
uv run python scripts/discrepancy.py introduce
curl 'http://localhost:8080/api/reconcile?period=2026-08'

# Восстановить значение или повторить импорт.
uv run python scripts/discrepancy.py restore
```

Ожидаемые итоги августа 2026: 3 начисления и `1 140 000` копеек.

CLI с отдельным пользователем PostgreSQL только для чтения:

```bash
docker compose run --rm \
  -e DATABASE_URL=postgresql://agent_reader:demo-reader-local@postgres:5432/reporting \
  api uv run --frozen --no-dev python -m source.cli --period 2026-08
```

CLI завершает работу с кодом `0` для `MATCH` и `1` для `MISMATCH`.

## Проверки

```bash
uv sync --frozen
uv run ruff check source tests scripts
uv run pytest

cd frontend
npm ci
npm test -- --run
npm run build
```

## Настоящая 1С

Конфигурация создана в учебной платформе 1С 8.3.27.1606 и содержит:

- справочники `ЛицевыеСчета`, `Начисления`, `Платежи`;
- HTTP-сервис `ReconciliationAPI` с GET `/accounts`, `/charges`, `/payments`;
- роль `APIReadOnly` с чтением и просмотром трёх справочников;
- роль `FullAccess` для отдельного администратора.

Исходники конфигурации находятся в `onec/configuration`. Локальная файловая база,
выгрузка `.dt`, лицензии и учётные данные исключены из Git.

Текущая учебная установка macOS не содержит модуля расширения веб-сервера, поэтому
реальная HTTP-публикация и `scripts/preflight.py --real` пока имеют статус `BLOCKED`.
Это не подменяется успешным прогоном через mock. Для финального интеграционного прогона
конфигурацию нужно загрузить в официальную платформу с компонентом веб-публикации на
Windows/Linux либо в полноценную macOS-установку с поддерживаемым веб-сервером.

После публикации заполните `ONEC_BASE_URL`, `ONEC_USER`, `ONEC_PASSWORD` в локальном
`.env` и выполните:

```bash
uv run --env-file .env python scripts/preflight.py --real
```

Подробнее о mapping и восстановлении: [onec/README.md](onec/README.md) и
[ONEC_SETUP.md](ONEC_SETUP.md).
