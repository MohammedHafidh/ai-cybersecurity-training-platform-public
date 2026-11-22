from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ScenarioKey = Literal["brute-force", "sql-injection", "reconnaissance"]
Mode = Literal["live", "sample"]
STAGES = ("preparing", "starting", "activity", "capturing", "normalizing", "rules", "ml", "saving", "ready")


class StartExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: ScenarioKey
    mode: Mode = "live"


class QuizSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[int] = Field(min_length=4, max_length=4)


class AskQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=300)
