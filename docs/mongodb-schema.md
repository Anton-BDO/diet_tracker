# Схема MongoDB

## Общая информация

База данных приложения состоит из коллекций:

- `users` — пользователи и их расчётные нормы питания;
- `products` — общий и пользовательский справочник продуктов;
- `food_entries` — записи дневника питания;
- `weight_logs` — история веса;
- `sessions` — сессии авторизации.

MongoDB не проверяет ссылки между коллекциями как внешние ключи
реляционной базы данных. Корректность ссылок должны проверять
репозитории и сервисы приложения.

В MongoDB идентификаторы документов хранятся в `_id` типа ObjectId.
В доменных моделях идентификаторы представлены строками.
Преобразование между строкой и ObjectId выполняется на уровне
репозиториев.

Временные метки `created_at` и `updated_at` хранятся как BSON Date,
а в Python представлены объектами `datetime`.

Даты дневника и журнала веса хранятся в формате `YYYY-MM-DD`.

## Коллекция users

Назначение: учётные данные, профиль и рассчитанные нормы питания.

Поля:

- `_id`: ObjectId;
- `email`: str, уникальный email в нижнем регистре;
- `password_hash`: str, хэш пароля;
- `name`: str;
- `gender`: `male` или `female`;
- `age`: int;
- `height_cm`: float;
- `weight_kg`: float;
- `activity`: `sedentary`, `light`, `moderate`, `high` или `extreme`;
- `goal`: `lose`, `maintain` или `gain`;
- `daily_calories`: int;
- `macros.protein`: float;
- `macros.fat`: float;
- `macros.carbs`: float;
- `created_at`: datetime;
- `updated_at`: datetime.

Индекс:

- уникальный `{email: 1}`.

Пароль хранится только в виде хэша, не в открытом виде.

## Коллекция products

Назначение: общий справочник продуктов и продукты пользователей.

Поля:

- `_id`: ObjectId;
- `name`: str;
- `name_lower`: str, нормализованное имя для поиска;
- `calories`: float, на 100 г;
- `protein`: float, на 100 г;
- `fat`: float, на 100 г;
- `carbs`: float, на 100 г;
- `is_custom`: bool;
- `owner_id`: ObjectId или null;
- `created_at`: datetime.

Для системного продукта `is_custom` равен false,
а `owner_id` равен null.

Для пользовательского продукта `is_custom` равен true,
а `owner_id` содержит идентификатор пользователя.

Индексы:

- `{name_lower: 1}`;
- `{owner_id: 1}`;
- `{owner_id: 1, name_lower: 1}`.

## Коллекция food_entries

Назначение: записи о съеденных продуктах.

Поля:

- `_id`: ObjectId;
- `user_id`: ObjectId, ссылка на `users._id`;
- `product_id`: ObjectId, ссылка на `products._id`;
- `product_name`: str, название продукта на момент добавления;
- `grams`: float, масса порции;
- `calories`: float, калории всей порции;
- `protein`: float, белки всей порции;
- `fat`: float, жиры всей порции;
- `carbs`: float, углеводы всей порции;
- `meal`: `breakfast`, `lunch`, `dinner` или `snack`;
- `date`: str в формате `YYYY-MM-DD`;
- `created_at`: datetime;
- `updated_at`: datetime.

Индекс:

- `{user_id: 1, date: 1}`.

Название продукта и нутриенты сохраняются в записи дневника,
чтобы изменение справочника не меняло историю питания задним числом.

## Коллекция weight_logs

Назначение: история измерений веса.

Поля:

- `_id`: ObjectId;
- `user_id`: ObjectId, ссылка на `users._id`;
- `weight_kg`: float;
- `date`: str в формате `YYYY-MM-DD`;
- `created_at`: datetime.

Индекс:

- уникальный `{user_id: 1, date: 1}`.

Для повторного ввода веса за тот же день репозиторий должен
обновлять существующий документ через update/upsert.

## Коллекция sessions

Назначение: сессии авторизации.

Поля:

- `_id`: ObjectId;
- `token`: str;
- `user_id`: ObjectId, ссылка на `users._id`;
- `created_at`: datetime;
- `expires_at`: datetime.

Индекс:

- уникальный `{token: 1}`.

## Связи между коллекциями

- `food_entries.user_id` -> `users._id`;
- `food_entries.product_id` -> `products._id`;
- `weight_logs.user_id` -> `users._id`;
- `products.owner_id` -> `users._id` для пользовательских продуктов;
- `sessions.user_id` -> `users._id`.

## Доменные модели

Доменные модели определены в `backend/domain/models.py`:

- `User`;
- `MacroTargets`;
- `Product`;
- `FoodEntry`;
- `WeightLog`;
- `Session`.

Они реализованы через Python dataclass и не зависят от PyMongo.
Проверка ссылок на существующие документы выполняется вне доменных
моделей — в репозиториях или сервисах.