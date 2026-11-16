"""Official Day 24 observable-only 60-second authentication baseline."""
import hashlib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


RULE_VERSION="auth-failed-burst-v1"
FAILURE_THRESHOLD=3


class AuthWindowInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    row_id: str=Field(min_length=1)
    run_id: str=Field(min_length=1)
    source_ip: str=Field(min_length=1)
    target: str=Field(min_length=1)
    window_start: datetime
    window_end: datetime
    attempt_count: int=Field(ge=1,strict=True)
    failed_login_count: int=Field(ge=0,strict=True)
    successful_login_count: int=Field(ge=0,strict=True)
    event_ids: list[str]=Field(min_length=1)

    @model_validator(mode="after")
    def consistent(self):
        if any(value.tzinfo is None or value.utcoffset() is None for value in (self.window_start,self.window_end)):
            raise ValueError("aware window timestamps required")
        if (self.window_end-self.window_start).total_seconds()!=60 or self.window_start.timestamp()%60:
            raise ValueError("fixed epoch-aligned 60-second window required")
        if self.failed_login_count+self.successful_login_count!=self.attempt_count:
            raise ValueError("authentication counts disagree")
        if len(self.event_ids)!=self.attempt_count or len(set(self.event_ids))!=len(self.event_ids):
            raise ValueError("event provenance/count mismatch")
        return self


def detect_auth_window(observation: AuthWindowInput):
    triggered=observation.failed_login_count>=FAILURE_THRESHOLD
    return dict(detection_id="auth-det-"+hashlib.sha256((RULE_VERSION+"\0"+observation.model_dump_json()).encode()).hexdigest()[:24],
        run_id=observation.run_id,row_id=observation.row_id,detector_type="rule_based",
        rule_version=RULE_VERSION,predicted_label="malicious" if triggered else "benign",
        predicted_scenario="brute_force" if triggered else "benign",triggered=triggered,
        evidence=dict(feature="failed_login_count",observed=observation.failed_login_count,
            operator=">=",threshold=FAILURE_THRESHOLD,window_seconds=60,
            source_ip=observation.source_ip,target=observation.target,
            window_start=observation.window_start.isoformat(),window_end=observation.window_end.isoformat(),
            event_ids=observation.event_ids))


def detect_auth_windows(observations):
    rows=set()
    events=set()
    groups=set()
    results=[]
    for observation in sorted(observations,key=lambda row:(row.run_id,row.row_id)):
        group=(observation.run_id,observation.source_ip,observation.target,observation.window_start)
        if observation.row_id in rows or events.intersection(observation.event_ids) or group in groups:
            raise ValueError("duplicate window/event evidence")
        groups.add(group)
        rows.add(observation.row_id)
        events.update(observation.event_ids)
        results.append(detect_auth_window(observation))
    return results


def binary_metrics(truth,predictions):
    if not truth or len(truth)!=len(predictions) or not set(truth+predictions)<= {"benign","malicious"}:
        raise ValueError("valid aligned labels required")
    tn=sum(t==p=="benign" for t,p in zip(truth,predictions))
    tp=sum(t==p=="malicious" for t,p in zip(truth,predictions))
    fp=sum(t=="benign" and p=="malicious" for t,p in zip(truth,predictions))
    fn=sum(t=="malicious" and p=="benign" for t,p in zip(truth,predictions))
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    return dict(sample_count=len(truth),accuracy=(tp+tn)/len(truth),precision=precision,
        recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
        false_positive_rate=fp/(fp+tn) if fp+tn else 0.0,
        confusion_matrix=[[tn,fp],[fn,tp]],label_order=["benign","malicious"])
