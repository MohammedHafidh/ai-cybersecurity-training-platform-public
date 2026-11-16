from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["auth", "web", "network"]
Scenario = Literal["benign", "brute_force", "sql_injection", "reconnaissance"]
Label = Literal["benign", "malicious"]


class NormalizedEvent(BaseModel):
    """Common event shape produced by all future log parsers."""

    event_id: str
    run_id: str
    timestamp: datetime
    source_type: SourceType
    event_type: str
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = None
    outcome: str | None = None
    method: str | None = None
    path: str | None = None
    request_data: str | None = None
    status_code: int | None = None
    destination_port: int | None = Field(default=None, ge=1, le=65535)
    protocol: str | None = None
    raw_source_file: str
    attack_label: Label
    scenario: Scenario
