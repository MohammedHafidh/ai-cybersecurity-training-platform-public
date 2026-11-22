from fastapi import APIRouter
from app.training.content import SCENARIOS, lesson
from app.training.contracts import ScenarioKey

router = APIRouter(prefix="/training", tags=["training"])

@router.get("/scenarios")
def scenarios():
    return [lesson(key) for key in SCENARIOS]

@router.get("/scenarios/{scenario}")
def guide(scenario: ScenarioKey):
    return lesson(scenario)
