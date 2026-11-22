import pytest
from pydantic import ValidationError
from app.training.content import SCENARIOS, lesson
from app.training.contracts import StartExercise


def test_three_lessons_have_required_teaching_and_twelve_curated_questions():
    assert len(SCENARIOS) == 3
    for key in SCENARIOS:
        public = lesson(key)
        assert all(
            public[name]
            for name in (
                "definition",
                "importance",
                "objectives",
                "safety",
                "activity",
                "observe",
                "logs",
                "features",
                "rule",
                "ml",
                "limitations",
                "mitigation",
                "references",
            )
        )
        assert len(public["questions"]) == 4
        assert all("correct" not in q and "explanation" not in q for q in public["questions"])
        assert all(
            0 <= q["correct"] < len(q["options"]) for q in lesson(key, answers=True)["questions"]
        )


@pytest.mark.parametrize(
    "extra",
    [
        {"target": "example.com"},
        {"command": "anything"},
        {"port": 22},
        {"variant": 99},
        {"script": "x"},
        {"payload": "x"},
    ],
)
def test_student_cannot_supply_execution_parameters(extra):
    with pytest.raises(ValidationError):
        StartExercise(scenario="brute-force", **extra)
