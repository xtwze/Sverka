---
name: verify-reconciliation-report
description: Проверяйте отчёт сверки начислений по отдельному чтению 1С и PostgreSQL, включая ID и точные суммы.
---

# Проверка отчёта сверки

## Когда применять

- После импорта при запуске сверки за месяц.
- При статусе `MISMATCH` перед объяснением причины пользователю.
- После исправления данных в тестовой PostgreSQL для подтверждения восстановления.

## Входные параметры

- `period` — месяц `YYYY-MM`.
- Доступ к read-only HTTP-источнику и `AGENT_DATABASE_URL` с ролью только для чтения.
- Для демонстрационного сценария источник остаётся неизменным; расхождения
  вносятся только в тестовую PostgreSQL.

## Команды

```bash
uv run --env-file .env python -m source.cli.agent_tools read_onec_charges --period 2026-08
uv run --env-file .env python -m source.cli.agent_tools read_postgres_charges --period 2026-08
uv run --env-file .env python -m source.cli.agent_tools reconcile_charges --period 2026-08
```

Для воспроизводимого тестового расхождения примените
`uv run --env-file .env python scripts/discrepancy.py introduce`, повторите три
команды, затем обязательно выполните
`uv run --env-file .env python scripts/discrepancy.py restore`.
Запись в PostgreSQL выполняет только отдельный тестовый скрипт с правами импортёра;
агенту эта команда не предоставляется как инструмент.

## Проверяемый результат

- Сопоставьте `period`, `count`, `total_kopecks` и наборы `rows[].id` из двух
  чтений с полями `source`, `postgres` и `differences` отчёта.
- При `MATCH` списки расхождений пусты и итоги совпадают. Для исходного августа:
  3 начисления и `1140000` копеек с каждой стороны.
- При `MISMATCH` назовите тип, ID и значения с каждой стороны для каждой строки;
  не выводите причину, которой нет в данных.
- После `introduce` ожидаются одновременно `amount_mismatch` для `charge-2`
  (`24950`/`25050`) и `missing_in_postgres` для `charge-3` (`990000`/`null`).
- Если источник или PostgreSQL недоступны, зафиксируйте ошибку. Не сообщайте
  статус `MATCH` без завершённого чтения обоих источников.
- Сохраните в отчёте о применении навыка команды, статус, ID расхождений и
  пометку `mock` либо `real` для источника.
