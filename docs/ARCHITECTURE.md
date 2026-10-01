# Архитектура по ТЗ

Основание: fullstack.pdf v2.2, README.md, ONEC_SETUP.md, CONTRACT.md.
Исходный репозиторий: https://github.com/RadioCpp/interview
Проверенный SHA: 84845ebe0bdfce5cd014a9cfb5864b452b4767eb.
В корень перенесено содержимое fullstack; .gitignore объединён с настройками фронтенда.
Исходная копия доступна в игнорируемой папке starter-upstream/fullstack.

## Обязательные границы

- 1С содержит источник: счета, начисления, платежи. Доступ приложения через read-only HTTP/OData.
- PostgreSQL хранит отчётную копию. Импорт сохраняет ID, связи и целые копейки; повтор не создаёт дубли.
- Python backend выполняет импорт и детерминированную сверку начислений за месяц.
- React вызывает backend, показывает готовый отчёт и ошибки.
- CLI-агент вызывает ту же логику сверки и инструменты чтения. Пароль импортёра ему недоступен.
- Приложение и отчётная PostgreSQL запускаются через Compose. 1С допускается локально, в VM или Docker.

ТЗ не предписывает названия Python-модулей, ORM, микросервисы или конкретное дерево каталогов.

## Структура backend

```text
source/
  main.py                         сборка FastAPI и подключение маршрутов
  config/settings.py             конфигурация из окружения
  config/dependencies.py         сборка зависимостей сервисов
  controllers/                   HTTP-входы приложения
  dto/source_dto.py              проверка контракта источника
  dto/response_dto.py            модели HTTP-ответов
  services/import_service.py     транзакционный импорт снимка
  services/reconciliation_service.py сценарий сверки
  repositories/                  изолированные запросы PostgreSQL
  clients/onec_client.py         read-only HTTP-клиент 1С
  domain/models.py               доменные сущности
  domain/reconciliation.py       чистые правила сравнения
  cli/commands.py                консольный вход в сервис сверки
frontend/                        React-интерфейс
onec/                            исходники конфигурации 1С
fixtures/data.json               фиксированный тестовый источник
postgres/                        роли PostgreSQL
scripts/                         preflight и контролируемое расхождение
tests/                           проверки контракта, API и сверки
compose.yaml                     полный локальный запуск
```

Контроллеры не содержат SQL или правил сравнения. Сервисы координируют сценарии,
репозитории работают с хранилищем, а доменный модуль не зависит от FastAPI и PostgreSQL.

## История Git

README организатора требует первым коммитом неизменённый starter kit, затем изменения.
Первый коммит содержит неизменённый starter kit; последующие коммиты содержат
реализацию приложения. Копия starter-upstream не предназначена для публикации.
