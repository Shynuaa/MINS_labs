from .schemas import FarmRequest
from .model import calculate_risk

MODEL_NAME = "agro-risk-model"
MODEL_VERSION = "1.0"
MODEL_TYPE = "risk-scoring"
ALLOWED_REGIONS = {"Krasnodar", "Rostov", "Stavropol"}


def get_risk_level(score: float) -> str:
    if score < 0.3:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def get_recommendation(level: str) -> str:
    if level == "low":
        return "Стандартное рассмотрение"
    if level == "medium":
        return "Требуется дополнительная проверка"
    return "Высокий риск. Требуется ручное рассмотрение"


def make_prediction(request: FarmRequest) -> tuple[float, str, str]:
    score = calculate_risk(request)
    level = get_risk_level(score)
    recommendation = get_recommendation(level)
    return score, level, recommendation
