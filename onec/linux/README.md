# 1С в Linux/Docker

**PASS, 02.10.2026:** 1С 8.3.27.1508, Apache 2.4.68, Linux x86_64.
Проверены восстановление из XML, две загрузки фикстур, read-only права, HTTP API,
повторный импорт в PostgreSQL и MATCH → MISMATCH → MATCH.
[Протокол](../../docs/evidence/real-1c-run.json).

## Сборка

Нужны Docker Desktop с поддержкой `linux/amd64` и официальный дистрибутив
[1С 8.3, учебная версия, Linux 64-bit](https://online.1c.ru/catalog/free/28766016/).
Архив остаётся локально, в Git и публичные образы не отправляется. Условия получения
на сайте принимает пользователь. macOS-сборка толстого клиента для Linux не подходит.

Проверенный файл: `setup-training-8.3.27.1508-x86_64.run`.
SHA256: `c3f0bbe662f2ac66cf329685b25fc3e73cc8ddcfa85ef47dd2319c9b8396b4d1`.
Dockerfile проверяет этот хеш перед запуском установщика. Для другого выпуска сначала
нужно проверить его происхождение, параметры и совместимость; не подменять хеш молча.

Из корня репозитория:

```bash
ONEC_DISTRIBUTION='/полный/путь/training_8_3_27_1508_LinuxRun'
docker build --platform linux/amd64 -f onec/linux/Dockerfile.base \
  -t fullstack-onec-linux-base:local onec/linux
docker build --platform linux/amd64 \
  --build-context "onecdist=$ONEC_DISTRIBUTION" \
  -f onec/linux/Dockerfile -t fullstack-onec-linux:8.3.27.1508 onec/linux
```

Устанавливаются `client_full`, `ws`, русский язык и проверенные через ldd библиотеки.
Xvfb обеспечивает запуск Конфигуратора/клиента без графического рабочего стола.

## Новая база — один раз

```bash
docker volume create fullstack-onec-linux-review-data
docker compose -f onec/linux/compose.yaml --profile setup run --rm init
```

`initialize.sh` создаёт `/var/lib/1c/review` из исходников и fixtures, дважды считывает
данные и сравнивает их с контрактом. Затем создаёт DemoAdmin/FullAccess и
APIReader/APIReadOnly, запускает тонкий клиент под APIReader и проверяет запрет записи
трёх существующих объектов. Транзакция каждой попытки записи всегда откатывается.
Логи и JSON лежат в том же volume в `/var/lib/1c/review-logs`.

Если каталог базы уже есть, инициализация **откажется** его перезаписывать.
Для уже созданной базы повторять init не нужно.
Для отдельного нового прогона задайте другое имя volume в копии Compose.
Используйте отдельную демобазу.

## Запуск HTTP-сервиса

```bash
docker compose -f onec/linux/compose.yaml up -d --wait onec
curl --fail http://127.0.0.1:18083/Sverka/hs/api/accounts
```

`publish.sh` требует успешный отчёт проверки прав и вызывает штатный `webinstt`.
Публикуется только ReconciliationAPI; веб-клиент, OData, аналитика и общие web-сервисы
отключены. Apache обрабатывает запросы последовательно из-за ограничения учебной
платформы на один сеанс. `reuseSessions="dontuse"` завершает сеанс после запроса.
Не открывайте эту базу клиентом одновременно с HTTP-проверкой.

**У учебной платформы нет паролей пользователей.** Публикация фиксирует APIReader
в строке подключения, порт проброшен только на `127.0.0.1`. Это локальная демосреда
с синтетическими данными; её нельзя публиковать в интернет как готовую защищённую
систему. Отсутствие пароля не отменяет проверенные ограничения роли на запись.

## Подключение приложения

В локальном `.env` основного Compose:

```dotenv
ONEC_BASE_URL=http://host.docker.internal:18083/Sverka/hs/api
ONEC_USER=APIReader
ONEC_PASSWORD=
```

Для локального CLI в `.env.agent` адрес другой:

```dotenv
ONEC_BASE_URL=http://127.0.0.1:18083/Sverka/hs/api
ONEC_USER=APIReader
ONEC_PASSWORD=
```

Не добавляйте `DATABASE_URL` в `.env.agent`. Агент использует только
`AGENT_DATABASE_URL` с ролью PostgreSQL `agent_reader`.

```bash
docker compose up -d --wait api agent
docker compose exec -T agent uv run --frozen --no-dev python scripts/preflight.py --real
docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools read_onec_charges --period 2026-08
```

После preflight можно импортировать данные кнопкой UI и выполнить сверку.
Для формального прогона применяются навыки валидации и сверки, оба независимых чтения
и отчёт. Тестовые расхождения вносить только в отдельную тестовую PostgreSQL.
Остановка: `docker compose -f onec/linux/compose.yaml stop onec` — volume сохраняется.
