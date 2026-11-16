from datetime import datetime
from typing import Literal

from pydantic import BaseModel


Scenario = Literal["benign", "brute_force", "sql_injection", "reconnaissance"]
ExpectedLabel = Literal["benign", "malicious"]
RunStatus = Literal["valid", "excluded", "needs_review"]


class RunMetadata(BaseModel):
    """Ground-truth metadata recorded when a controlled lab run happens."""

    run_id: str
    scenario: Scenario
    expected_label: ExpectedLabel
    start_time: datetime
    end_time: datetime
    source: str
    target: str
    tool_or_method: str
    log_sources: list[str]
    notes: str = ""
    status: RunStatus = "valid"
    exclusion_reason: str = ""
