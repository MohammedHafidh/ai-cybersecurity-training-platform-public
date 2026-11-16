"""SQLi observations; suspicious tokens do not establish ground truth."""
import re
from collections import defaultdict

from app.processing.features import SUSPICIOUS_SQL_TOKENS


def build_web_features(events):
    grouped = defaultdict(list)
    for event in events:
        if event.source_type == "web":
            grouped[event.run_id].append(event)
    output = []
    for run_id, members in sorted(grouped.items()):
        values = [e.request_data for e in members if e.request_data is not None]
        output.append(dict(run_id=run_id, request_count=len(members),
            missing_input_count=sum(e.request_data is None for e in members),
            empty_input_count=sum(e.request_data == "" for e in members),
            max_request_length=max(map(len, values), default=0),
            suspicious_token_count=sum(len(SUSPICIOUS_SQL_TOKENS.findall(v)) for v in values),
            residual_encoded_count=sum(bool(re.search(r"%[0-9a-fA-F]{2}", v)) for v in values),
            error_response_count=sum(e.status_code is not None and e.status_code >= 400 for e in members),
            event_ids=sorted(e.event_id for e in members)))
    return output
