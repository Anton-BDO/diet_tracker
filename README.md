# Трекер диеты

Учебный проект: веб-приложение для учёта питания. Профиль с дневной нормой
калорий, дневник еды, сводка за день, серии успешных дней, журнал веса и графики.

Стек без фреймворков: сервер на стандартном `http.server`, фронт на чистом
HTML, CSS и JS, данные в MongoDB.

## Запуск через Docker

```bash
docker compose up --build
```

Приложение откроется на http://localhost:8000, проверка сервера на
http://localhost:8000/api/health.

## Запуск без Docker

Нужны Python 3.12+ и запущенная MongoDB на `localhost:27017`.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m backend.app
```

Настройки берутся из переменных окружения, пример в `.env.example`.

## Тесты и проверка стиля

```bash
flake8 backend tests scripts     # PEP8
pytest                           # тесты и покрытие, порог 80%
```

То же самое запускает CI на каждый PR. Красный CI блокирует мерж.

## Структура

```
backend/
  app.py            точка входа, сборка зависимостей
  config.py         настройки из окружения
  db.py             клиент MongoDB и индексы
  api/              сервер, роутер, обработчики, CORS
  services/         сценарии приложения
  domain/           модели и расчёты, чистые функции
  repositories/     работа с коллекциями MongoDB
frontend/           index.html, css, js (api, store, views, charts)
tests/              unit, repositories (mongomock), integration (urllib)
scripts/            служебные скрипты, загрузка продуктов
docs/               openapi.yaml, архитектура, Postman
```

Подробная архитектура в `docs/architecture.md`.

## Библиотеки

Используются только согласованные с преподавателем: `pymongo`, а для
разработки `pytest`, `pytest-cov`, `mongomock`, `flake8`.

## Команда

| Участник | Роль |
| --- | --- |
| Фроленко Антон | Team Lead, архитектор, DevOps |
| Андриенко Юлия | Project Manager, системный аналитик |
| Сторожев Владимир | QA, автотесты |
| Егоров Алексей | Backend, бизнес-логика и БД |
| Быков Иван | Backend, HTTP API |
| Зайцев Кирилл | Frontend, интерфейс |
| Визгалёва Ярослава | Frontend, состояние и API-клиент, документация |

Как работаем с ветками и PR, описано в [CONTRIBUTING.md](CONTRIBUTING.md).
