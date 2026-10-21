# Схема MongoDB

Схема соответствует `docs/architecture.md`. MongoDB хранит документы с `_id`
типа ObjectId; в доменных моделях идентификаторы представлены строками,
преобразование выполняется репозиториями. `created_at` и `updated_at` —
BSON Date / Python `datetime`. Даты дневника и рождения — строки `YYYY-MM-DD`.

## `users`

- `_id`: ObjectId;
- `email`: str, уникальный, нормализуется в нижний регистр;
- `password_hash`: str;
- `name`: str;
- `sex`: `male` или `female`;
- `birth_date`: дата рождения `YYYY-MM-DD`; возраст вычисляется, а не хранится;
- `height_cm`: число, диапазон 100–250;
- `weight_kg`: число, диапазон 30–300;
- `activity`: одно из чисел `1.2`, `1.375`, `1.55`, `1.725`, `1.9`;
- `goal`: `lose`, `keep` или `gain`;
- `created_at`, `updated_at`: datetime.

Индекс: уникальный `{email: 1}`.

Расчётные поля `daily_calories` и `macros` не хранятся. Суточная норма и
сводки питания вычисляются на лету на основе актуального профиля и дневника.

## `products`

- `_id`: ObjectId;
- `name`: str;
- `name_lower`: str, нормализованное имя для поиска;
- `kcal`, `protein`, `fat`, `carbs`: числа на 100 г;
- `owner_id`: ObjectId или `null`;
- `created_at`: datetime.

`owner_id: null` означает общий продукт; непустой `owner_id` означает продукт
пользователя. Отдельного поля `is_custom` нет.

Индексы:
- `{name_lower: 1}`;
- `{owner_id: 1}`.

Составной индекс `{owner_id: 1, name_lower: 1}` не создаётся.

## `food_entries`

- `_id`: ObjectId;
- `user_id`, `product_id`: ObjectId-ссылки;
- `product_name`: str, снимок названия продукта на момент добавления;
- `date`: дата в формате `YYYY-MM-DD`;
- `meal`: `breakfast`, `lunch`, `dinner` или `snack`;
- `grams`: число, диапазон 1–5000;
- `kcal`, `protein`, `fat`, `carbs`: числа для всей порции;
- `created_at`, `updated_at`: datetime.

Индекс: `{user_id: 1, date: 1}`.

Название и КБЖУ сохраняются в записи дневника как снимок, чтобы изменения
справочника продуктов не меняли историю питания.

## `weight_logs`

Поля:
- `_id`: ObjectId;
- `user_id`: ObjectId-ссылка;
- `weight_kg`: число, диапазон 30–300;
- `date`: дата в формате `YYYY-MM-DD`;
- `created_at`: datetime.

Уникальный индекс `{user_id: 1, date: 1}` обеспечивает не более одной записи
веса на пользователя за календарный день.

## `sessions`

Поля:
- `_id`: ObjectId;
- `token`: str;
- `user_id`: ObjectId-ссылка;
- `created_at`: datetime;
- `expires_at`: datetime.

`expires_at` сохраняется, чтобы API мог отклонять просроченные сессии.
Индекс `{token: 1}` уникальный.

## Связи

- `food_entries.user_id` → `users._id`;
- `food_entries.product_id` → `products._id`;
- `weight_logs.user_id` → `users._id`;
- `products.owner_id` → `users._id` для пользовательских продуктов;
- `sessions.user_id` → `users._id`.

MongoDB не обеспечивает внешние ключи. Ссылки и доступ к данным владельца
проверяются репозиториями и сервисами.

Доменная валидация выбрасывает `ValidationError(message, field)`.
HTTP-слой должен возвращать статус 400 и поле `error.field` для таких ошибок.
