import logging
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, status

from .schemas import HealthResponse, ModelInfoResponse, FarmRequest, PredictionResponse
from .services import (
    ALLOWED_REGIONS,
    MODEL_NAME,
    MODEL_TYPE,
    MODEL_VERSION,
    get_recommendation,
    get_risk_level,
    make_prediction,
)
from .storage import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MODEL_READY = True

app = FastAPI(
    title="Agro Scoring API",
    description="REST API для оценки риска сельскохозяйственных предприятий.",
    version="1.0.0",
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(round(time.perf_counter() - start_time, 6))
    return response


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка состояния API",
    description="Используется для проверки того, что REST API запущен и отвечает.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Информация о модели",
    description="Возвращает название, версию, тип и текущее состояние модели.",
)
def model_info() -> ModelInfoResponse:
    return ModelInfoResponse(
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        model_type=MODEL_TYPE,
        status="ready" if MODEL_READY else "unavailable",
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Оценить риск хозяйства",
    description="Принимает характеристики хозяйства, выполняет валидацию, инференс и возвращает оценку риска.",
)
def predict(request: FarmRequest) -> PredictionResponse:
    if not MODEL_READY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model is temporarily unavailable")

    if request.region not in ALLOWED_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown region: {request.region}. Allowed regions: {sorted(ALLOWED_REGIONS)}",
        )

    logger.info("Prediction request received | farm_id=%s", request.farm_id)
    score, level, recommendation = make_prediction(request)
    request_id = str(uuid.uuid4())

    result = PredictionResponse(
        request_id=request_id,
        farm_id=request.farm_id,
        risk_score=score,
        risk_level=level,
        recommendation=recommendation,
        model_version=MODEL_VERSION,
    )
    storage.save(result)
    logger.info(
        "Prediction completed | request_id=%s | farm_id=%s | risk_score=%s | risk_level=%s",
        request_id,
        request.farm_id,
        score,
        level,
    )
    return result


@app.get(
    "/predictions",
    response_model=list[PredictionResponse],
    summary="Получить список прогнозов",
    description="Возвращает список выполненных прогнозов с ограничением и фильтрацией по уровню риска.",
)
def get_predictions(
    limit: int = Query(default=10, ge=1, le=100, description="Максимальное количество результатов"),
    risk_level: Optional[str] = Query(default=None, description="Фильтр: low, medium или high"),
) -> list[PredictionResponse]:
    if risk_level is not None and risk_level not in {"low", "medium", "high"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="risk_level must be 'low', 'medium' or 'high'")

    values = storage.list()
    if risk_level is not None:
        values = [item for item in values if item.risk_level == risk_level]
    return values[:limit]


@app.get(
    "/predictions/{request_id}",
    response_model=PredictionResponse,
    summary="Получить прогноз по request_id",
    description="Возвращает сохраненный прогноз по его уникальному идентификатору.",
)
def get_prediction(request_id: str) -> PredictionResponse:
    prediction = storage.get(request_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return prediction


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agro_api.main:app", host="127.0.0.1", port=8000, reload=True)
