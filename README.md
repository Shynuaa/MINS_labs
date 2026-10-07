# Практическая работа №1 — REST API для AI-сервиса на FastAPI

## Архитектура

### Потребители
- CRM банка
- Web-портал
- мобильное приложение
- внутренние банковские системы
- BI-система

### Протокол
HTTP/REST + JSON.

### Инференс
Синхронный запрос POST /predict.

### Хранение
In-memory storage для лабораторного прототипа.

### Логирование и наблюдаемость
- logging;
- request_id;
- X-Process-Time;
- HTTP-коды;
- OpenAPI/Swagger.

## Структура

```text
agro_api/
├── __init__.py
├── main.py       # FastAPI и endpoints
├── schemas.py    # Pydantic-модели
├── model.py      # расчёт risk score
├── services.py   # postprocessing и бизнес-логика
└── storage.py    # временное in-memory хранилище
```

## Запуск

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn agro_api.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Endpoints

- `GET /health`
- `GET /model-info`
- `POST /predict`
- `GET /predictions/{request_id}`
- `GET /predictions?limit=10&risk_level=high`

## Тесты

```bash
pytest -q
```

## Компонентная схема

Исходник диаграммы также находится в [`architecture.mmd`](architecture.mmd), а HTML-версия — в [`architecture.html`](architecture.html).

```mermaid
flowchart LR
    clients["CRM банка / веб-портал / мобильное приложение / внутренние сервисы / BI"]

    subgraph api["Agro Scoring API — FastAPI"]
      main["agro_api/main.py<br/>HTTP-маршруты, проверка региона и готовности модели"]
      schemas["agro_api/schemas.py<br/>Pydantic-схемы запроса и ответа"]
      services["agro_api/services.py<br/>Вызов модели, категория риска, рекомендация"]
      model["agro_api/model.py<br/>Учебный расчёт risk_score"]
      storage["agro_api/storage.py<br/>Словарь прогнозов в памяти процесса"]
    end

    docs["Swagger UI и OpenAPI<br/>/docs, /openapi.json"]
    logging["Логи прогнозов<br/>X-Process-Time"]

    clients -- "HTTP/JSON: GET и POST" --> main
    main -- "валидация FarmRequest" --> schemas
    schemas -- "валидные данные" --> main
    main -- "POST /predict" --> services
    services -- "calculate_risk" --> model
    model -- "risk_score" --> services
    services -- "score, level, recommendation" --> main
    main -- "save / get / list" --> storage
    storage -- "PredictionResponse или список" --> main
    main -- "JSON и HTTP-код" --> clients
    main -. "автоматический контракт" .-> docs
    main -. "наблюдаемость" .-> logging

    classDef client fill:#e7f0ff,stroke:#5a84c4,color:#17212b
    classDef component fill:#edf8f0,stroke:#5b9b6b,color:#17212b
    classDef support fill:#fff4df,stroke:#bd9448,color:#17212b
    class clients client
    class main,schemas,services,model,storage component
    class docs,logging support
```
