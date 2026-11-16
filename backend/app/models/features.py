from datetime import datetime

from pydantic import BaseModel, Field

from app.models.events import Label, Scenario, SourceType


class RunFeatures(BaseModel):
    """One deterministic numeric feature row for one controlled lab run."""

    feature_id: str
    run_id: str
    window_start: datetime
    window_end: datetime
    source_type: SourceType
    event_count: int = Field(ge=1)
    auth_attempt_count: int = Field(ge=0)
    failed_login_count: int = Field(ge=0)
    successful_login_count: int = Field(ge=0)
    unique_username_count: int = Field(ge=0)
    web_request_count: int = Field(ge=0)
    max_request_length: int = Field(ge=0)
    suspicious_token_count: int = Field(ge=0)
    connection_count: int = Field(ge=0)
    unique_destination_port_count: int = Field(ge=0)
    attack_label: Label
    scenario: Scenario

