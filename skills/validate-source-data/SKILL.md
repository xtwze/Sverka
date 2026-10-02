---
name: validate-source-data
description: Проверяйте контракт и полноту данных HTTP-источника перед импортом или после изменения конфигурации 1С.
---

# Валидация данных источника

## Когда применять

- Перед первым или повторным импортом.
- После изменения реквизитов, HTTP-публикации, учётной записи чтения или фикстур.
- Когда источник недоступен либо импорт сообщает об ошибке контракта.

## Входные параметры

- `period` — месяц `YYYY-MM`; для демонстрации используйте `2026-08`.
- `mode` — `mock` или `real`. Для `real` должны быть заданы `ONEC_BASE_URL`,
  `ONEC_USER` и `ONEC_PASSWORD` в локальном `.env.agent`.
  Исключение: проверенная локальная учебная 1С в Linux/Docker не поддерживает пароли;
  для неё используются `APIReader` и пустой `ONEC_PASSWORD`, порт только localhost.
  Инструкция и границы этого режима: `onec/linux/README.md`.

## Команды

Локальный агент использует `.env.agent` из `agent.env.example`, без `DATABASE_URL`.
Общий `.env` импортёра агенту не передавайте. В Docker выполняйте команды
через `docker compose exec -T agent uv run --frozen --no-dev python -m source.cli.agent_tools ...`.

Для mock внутри Docker (учитывается `SOURCE_BASE_URL=http://source-mock:8000`):

```bash
docker compose exec -T agent uv run --frozen --no-dev python scripts/preflight.py
```

Для локального mock:

```bash
uv run --env-file .env.agent python scripts/preflight.py
uv run --env-file .env.agent python -m source.cli.agent_tools read_onec_charges --period 2026-08
```

Для опубликованной 1С:

```bash
uv run --env-file .env.agent python scripts/preflight.py --real
uv run --env-file .env.agent python -m source.cli.agent_tools read_onec_charges --period 2026-08
```

`read_onec_charges` получает полный снимок источника через `OneCClient`. Парсер
проверяет обязательные поля, уникальность ID, формат месяца, целые копейки и ссылки
начислений/платежей на существующие счета. Для режима `real` убедитесь, что
`ONEC_BASE_URL` указывает на настоящую публикацию, а не на mock.

## Проверяемый результат

- Preflight возвращает `PASS` и ненулевые количества `accounts`, `charges`,
  `payments`. При `BLOCKED` или ошибке команда не считается успешной.
- Для исходных фикстур за `2026-08` команда возвращает 3 начисления на
  `1140000` копеек; каждый элемент имеет `id`, `account_id`, `period`,
  `amount_kopecks`.
- В отчёте о применении навыка зафиксируйте режим, команды, количества и итог.
  Если использован mock, явно укажите это ограничение.
