"""Official Day 25 rules: transparent heuristics on observable features only."""
from datetime import datetime
import hashlib

from pydantic import BaseModel,ConfigDict,Field,model_validator

from app.detection.auth_baseline import AuthWindowInput,detect_auth_window


SQL_TOKEN_THRESHOLD=1
PORT_THRESHOLD=2


class EvidenceInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    row_id:str=Field(min_length=1)
    run_id:str=Field(min_length=1)
    event_ids:list[str]=Field(min_length=1)

    @model_validator(mode="after")
    def unique_events(self):
        if len(set(self.event_ids))!=len(self.event_ids) or any(not value for value in self.event_ids):
            raise ValueError("unique nonempty event IDs required")
        return self


class WebRunInput(EvidenceInput):
    request_count:int=Field(ge=1,strict=True)
    suspicious_token_count:int=Field(ge=0,strict=True)

    @model_validator(mode="after")
    def request_provenance(self):
        if self.request_count!=len(self.event_ids):
            raise ValueError("request/evidence count mismatch")
        return self


class NetworkWindowInput(EvidenceInput):
    source_ip:str=Field(min_length=1)
    target:str=Field(min_length=1)
    window_start:datetime
    window_end:datetime
    connection_count:int=Field(ge=1,strict=True)
    unique_destination_port_count:int=Field(ge=1,le=65535,strict=True)

    @model_validator(mode="after")
    def consistent_window(self):
        if any(value.tzinfo is None or value.utcoffset() is None for value in (self.window_start,self.window_end)):
            raise ValueError("aware timestamps required")
        if (self.window_end-self.window_start).total_seconds()!=60 or self.window_start.timestamp()%60:
            raise ValueError("fixed epoch-aligned 60-second window required")
        if self.connection_count!=len(self.event_ids) or self.unique_destination_port_count>self.connection_count:
            raise ValueError("connection/port/evidence counts disagree")
        return self


def _result(observation,version,scenario,feature,threshold):
    observed=getattr(observation,feature)
    triggered=observed>=threshold
    evidence=dict(feature=feature,observed=observed,operator=">=",threshold=threshold,
        event_ids=sorted(observation.event_ids))
    if isinstance(observation,NetworkWindowInput):
        evidence.update(source_ip=observation.source_ip,target=observation.target,window_seconds=60,
            window_start=observation.window_start.isoformat(),window_end=observation.window_end.isoformat())
    else:
        evidence["aggregation_unit"]="web run"
    fingerprint=observation.model_dump(mode="json")
    fingerprint["event_ids"]=sorted(observation.event_ids)
    import json
    identity=json.dumps(fingerprint,sort_keys=True,separators=(",",":"))
    return dict(detection_id="rule-det-"+hashlib.sha256((version+"\0"+identity).encode()).hexdigest()[:24],
        run_id=observation.run_id,row_id=observation.row_id,detector_type="rule_based",rule_version=version,
        predicted_label="malicious" if triggered else "benign",
        predicted_scenario=scenario if triggered else "benign",triggered=triggered,evidence=evidence)


def detect_web_run(observation:WebRunInput):
    return _result(observation,"web-sql-token-v1","sql_injection","suspicious_token_count",SQL_TOKEN_THRESHOLD)


def detect_network_window(observation:NetworkWindowInput):
    return _result(observation,"network-multiport-v1","reconnaissance","unique_destination_port_count",PORT_THRESHOLD)


INPUT_MODELS={"auth":AuthWindowInput,"web":WebRunInput,"network":NetworkWindowInput}
DETECTORS={"auth":detect_auth_window,"web":detect_web_run,"network":detect_network_window}


def detect_scenario_rows(source,observations):
    if source not in INPUT_MODELS:
        raise ValueError("unsupported source")
    model=INPUT_MODELS[source]
    seen_rows,seen_events,seen_groups=set(),set(),set()
    results=[]
    for observation in sorted(observations,key=lambda row:(row.run_id,row.row_id)):
        if not isinstance(observation,model):
            raise ValueError("source/input model mismatch")
        group=(observation.run_id,) if source=="web" else (observation.run_id,observation.source_ip,observation.target,observation.window_start)
        if observation.row_id in seen_rows or seen_events.intersection(observation.event_ids) or group in seen_groups:
            raise ValueError("duplicate evidence/window")
        seen_rows.add(observation.row_id)
        seen_events.update(observation.event_ids)
        seen_groups.add(group)
        results.append(DETECTORS[source](observation))
    return results
