from .schemas import PredictionResponse


class PredictionStorage:

    def __init__(self) -> None:
        self._predictions: dict[str, PredictionResponse] = {}

    def save(self, prediction: PredictionResponse) -> None:
        self._predictions[prediction.request_id] = prediction

    def get(self, request_id: str) -> PredictionResponse | None:
        return self._predictions.get(request_id)

    def list(self) -> list[PredictionResponse]:
        return list(self._predictions.values())


storage = PredictionStorage()
