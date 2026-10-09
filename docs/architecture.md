# Архитектура

Полный документ с диаграммой, моделью данных, бизнес-правилами и списком
эндпоинтов: https://claude.ai/code/artifact/ee9d79b5-e3f8-484b-97f1-7cc483575ff7

## Коротко

Трёхслойный монолит. Зависимости идут только сверху вниз:

```
Браузер (frontend/)  --HTTP, JSON-->  api/  -->  services/  -->  repositories/  -->  MongoDB
                                                    |
                                                    v
                                                 domain/  (чистые функции)
```

| Слой | Папка | Не должен |
| --- | --- | --- |
| HTTP | `backend/api/` | считать калории, ходить в MongoDB |
| Сервисы | `backend/services/` | знать про HTTP и pymongo |
| Расчёты | `backend/domain/` | делать ввод-вывод |
| Репозитории | `backend/repositories/` | содержать бизнес-правила |

Зависимости собираются в `backend/app.py`. В тестах вместо настоящего
клиента передаётся `mongomock.MongoClient()`.

## Коллекции MongoDB

`users`, `sessions`, `products`, `food_entries`, `weight_logs`.
Индексы создаёт `backend/db.py` при старте сервера.
