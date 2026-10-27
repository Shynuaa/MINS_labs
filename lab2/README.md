# Практическая работа №1 — Agro Scoring API

Расширение исходного FastAPI-сервиса агроскоринга: сквозной `request_id`, асинхронная SQLite, одиночный и пакетный инференс, очередь с dynamic batching и backpressure, пагинация, обработка ошибок и интеграция с Vireonix LLM.

## 1. Установка и запуск (Windows PowerShell)

```powershell
cd MINS_labs-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn agro_api.main:app --reload
```

Откройте Swagger UI: <http://127.0.0.1:8000/docs>

При первом запуске приложение создаёт `agro_api/agro_scoring.db`. База данных находится рядом с модулем сервиса.

## 2. Основные endpoints

| Метод | Endpoint | Назначение |
|---|---|---|
| GET | `/health` | Проверка доступности |
| GET | `/model-info` | Информация о модели |
| POST | `/predict` | Одиночный прогноз с сохранением в SQLite |
| POST | `/batch-predict` | Явный пакет до 8 хозяйств |
| POST | `/predict-queued` | Очередь и dynamic batching |
| GET | `/queue-status` | Размер и параметры очереди |
| GET | `/predictions` | История прогнозов из SQLite |
| GET | `/predictions/{request_id}` | Один прогноз; 409 для batch request ID |
| GET | `/requests/{request_id}/predictions` | Все результаты одного HTTP-запроса |
| GET | `/predictions/by-weekday` | Пагинация по дню недели |
| POST | `/llm/chat` | Запрос к Vireonix LLM |
| POST | `/predict-with-llm` | Прогноз и отдельное текстовое объяснение LLM |
| POST | `/demo/seed-weekdays` | Демоданные для проверки пагинации |

Каждый ответ содержит заголовки `X-Request-ID` и `X-Process-Time`. Клиент может передать свой `X-Request-ID`; иначе сервис создаёт UUID. Ошибки содержат `request_id` в JSON-ответе.

## 3. Пример запроса

```json
{
  "farm_id": "FARM-001",
  "region": "Krasnodar",
  "crop_type": "wheat",
  "area_ha": 2500,
  "temperature_avg": 24.3,
  "precipitation_mm": 320,
  "payment_delay_days": 45,
  "previous_defaults": 1,
  "debt": 6500000
}
```

## 4. Примеры для Swagger

- `POST /predict` — используйте JSON выше.
- `POST /batch-predict` — передайте `{"items": [<объект хозяйства>, <объект хозяйства>]}`.
- `POST /predict-queued` — отправьте один объект хозяйства.
- `GET /predictions/by-weekday?weekday=monday&page=1&per_page=5`.
- `POST /llm/chat` — `{"prompt":"Объясни, что такое агроскоринг","model":"auto","temperature":0.3,"max_tokens":300}`.

Передавайте в LLM только учебные, несекретные данные. `predict-with-llm` рассчитывает и сохраняет скор независимо от ответа LLM: LLM формирует только объяснение.

## 5. Тесты

```powershell
python -m pytest -v
```

Для интеграционных тестов необходимы зависимости из `requirements.txt`. Тесты, требующие реального Vireonix API, не должны выполняться против внешнего сервиса без необходимости; LLM-вызовы в тестах следует подменять mock-объектом.

## Структура проекта

- `agro_api/main.py` — расширенный FastAPI-сервис и маршруты.
- `agro_api/model.py`, `services.py`, `schemas.py`, `storage.py` — модули исходной реализации; расширенная версия сервиса содержит собственные схемы и асинхронный SQLite storage в `main.py`.
- `tests/test_api.py` — базовые тесты исходного API.
- `files/` — материалы предыдущей лабораторной работы.
