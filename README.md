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

## API

RESTful API сервера. Все пути начинаются с `/api`, тела запросов и
ответов в JSON. Все запросы, кроме health, регистрации и входа, должны
содержать заголовок `Authorization: Bearer <token>`. Токен выдают
регистрация и вход. Даты передаются строкой `YYYY-MM-DD` в часовом
поясе пользователя.

Полная спецификация в формате OpenAPI лежит в
[docs/openapi.yaml](docs/openapi.yaml), её можно посмотреть в
[Swagger UI](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/Anton-BDO/diet_tracker/main/docs/openapi.yaml).

### Эндпоинты

| Название действия | Локейшн (URL) | Тип запроса | Описание запроса и ответа |
| --- | --- | --- | --- |
| Проверить сервер | `/api/health` | GET | **Запрос:** без параметров и токена.<br>**Ответ:** `200` `{"status": "ok", "db": "ok"}`, если база недоступна `503` `{"status": "degraded", "db": "down"}` |
| Зарегистрироваться | `/api/auth/register` | POST | **Запрос:** `email`, `password` (от 8 символов), `name`, `sex` (`male`/`female`), `birth_date`, `height_cm` (от 100 до 250), `weight_kg` (от 30 до 300), `activity` (1.2, 1.375, 1.55, 1.725, 1.9), `goal` (`lose`/`keep`/`gain`).<br>**Ответ:** `201` `{"token": "...", "profile": {...}}`, профиль с вычисленной нормой. `409`, если email занят |
| Войти | `/api/auth/login` | POST | **Запрос:** `email`, `password`.<br>**Ответ:** `200` `{"token": "..."}`. `401` при неверном email или пароле |
| Выйти | `/api/auth/logout` | POST | **Запрос:** без тела, токен в заголовке.<br>**Ответ:** `204` без тела, сессия удалена |
| Получить профиль | `/api/profile` | GET | **Запрос:** без параметров.<br>**Ответ:** `200` `{"id", "email", "name", "sex", "birth_date", "height_cm", "weight_kg", "activity", "goal", "norm": {"kcal": 2437, "protein": 183, "fat": 81, "carbs": 244}}` |
| Изменить профиль | `/api/profile` | PATCH | **Запрос:** хотя бы одно из полей `height_cm`, `weight_kg`, `activity`, `goal`.<br>**Ответ:** `200` профиль в том же формате с пересчитанной нормой `norm` |
| Найти продукты | `/api/products?q=` | GET | **Запрос:** `q` часть названия, необязательный. Без `q` возвращается весь доступный справочник.<br>**Ответ:** `200` список `[{"id", "name", "kcal", "protein", "fat", "carbs", "owner_id"}]`, значения на 100 г. `owner_id` равен `null` у общего справочника |
| Добавить свой продукт | `/api/products` | POST | **Запрос:** `name`, `kcal`, `protein`, `fat`, `carbs` на 100 г, не меньше 0.<br>**Ответ:** `201` созданный продукт, `owner_id` равен id пользователя |
| Получить сводку дня | `/api/diary?date=` | GET | **Запрос:** `date` обязательный, `YYYY-MM-DD`.<br>**Ответ:** `200` `{"date", "entries": [...], "totals": {"kcal": 2423, ...}, "norm": {...}, "remaining": {"kcal": 14, ...}, "is_success": true}` |
| Добавить запись в дневник | `/api/diary` | POST | **Запрос:** `product_id`, `grams` (от 1 до 5000), `meal` (`breakfast`/`lunch`/`dinner`/`snack`), `date`.<br>**Ответ:** `201` `{"id", "product_id", "product_name", "date", "meal", "grams": 250, "kcal": 282.5, "protein": 59, "fat": 4.8, "carbs": 1}`. КБЖУ считает сервер. `404`, если продукта нет |
| Изменить запись | `/api/diary/{id}` | PATCH | **Запрос:** `id` записи в пути, в теле хотя бы одно из `grams`, `meal`.<br>**Ответ:** `200` запись с пересчитанным КБЖУ. `404`, если запись не найдена или чужая |
| Удалить запись | `/api/diary/{id}` | DELETE | **Запрос:** `id` записи в пути.<br>**Ответ:** `204` без тела. `404`, если запись не найдена или чужая |
| Получить историю веса | `/api/weight?from=&to=` | GET | **Запрос:** `from` и `to` необязательные, даты границ периода включительно.<br>**Ответ:** `200` `[{"id", "date": "2026-10-20", "weight_kg": 84.5}]` по возрастанию даты |
| Записать вес | `/api/weight` | POST | **Запрос:** `date`, `weight_kg` (от 30 до 300). Повторный запрос на ту же дату перезаписывает значение.<br>**Ответ:** `201` `{"id", "date", "weight_kg"}`. Вес в профиле меняется, только если замер не старее последнего |
| Получить серию дней | `/api/streak?today=` | GET | **Запрос:** `today` необязательный, текущая дата пользователя.<br>**Ответ:** `200` `{"current": 4, "record": 7}` |
| Получить статистику калорий | `/api/stats/calories?days=7&today=` | GET | **Запрос:** `days` от 1 до 90, по умолчанию 7, `today` необязательный.<br>**Ответ:** `200` `{"norm_kcal": 2437, "days": [{"date": "2026-10-20", "kcal": 2423, "is_success": true}]}` |

### Ошибки

Формат ошибки одинаковый для всех эндпоинтов:

```json
{"error": {"code": "validation_error", "message": "Рост должен быть от 100 до 250 см", "field": "height_cm"}}
```

| Код | Когда |
| --- | --- |
| 400 | неверные входные данные, в `field` указано поле |
| 401 | нет токена или сессия просрочена |
| 404 | запись не найдена или принадлежит другому пользователю |
| 409 | email уже занят |
| 500 | внутренняя ошибка сервера |

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
| Зайцев Кирилл | Frontend, макеты, экран входа, моки и API-клиент |
| Визгалёва Ярослава | Frontend, главный экран и статистика, документация |

Как работаем с ветками и PR, описано в [CONTRIBUTING.md](CONTRIBUTING.md).
