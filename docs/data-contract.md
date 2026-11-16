# Normalized Event Data Contract — v1

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

This shared event contract is backed by the controlled authentication, web, and network evidence formats established during Days 4–6.

## Normalized Event

| Field | Meaning |
|---|---|
| event_id | Deterministic identifier derived from run, source file, line number, and raw record |
| run_id | Links the event to one controlled lab run |
| timestamp | Timezone-aware normalized event time |
| source_type | auth, web, or network |
| event_type | Short event category |
| source_ip | Source address when available |
| destination_ip | Destination address when available |
| username | Authentication username when relevant |
| outcome | success/failure/other when relevant |
| method | HTTP method when relevant |
| path | HTTP path when relevant |
| request_data | Relevant query/body or request-line evidence when appropriate |
| status_code | HTTP status when available |
| destination_port | Network destination port when relevant |
| protocol | Network protocol when available |
| raw_source_file | File from which the event came |
| attack_label | Ground truth joined from trusted run metadata |
| scenario | benign, brute_force, sql_injection, reconnaissance |

## Normalization rules

1. Raw files remain unchanged.
2. Only metadata with `status: valid` enters the processed dataset.
3. A raw source must be declared in `metadata.log_sources`.
4. Events outside the trusted run time window are excluded.
5. Embedded run IDs, when present, must match the metadata run ID.
6. Parsers extract observations only; `scenario` and `attack_label` always come from trusted run metadata.
7. Reprocessing the same input produces the same event IDs and JSON Lines records.

## Data Layers

### 1. Raw logs

Original security evidence captured from the lab.

Rule: raw logs remain unchanged after capture.

### 2. Normalized events

Consistent records produced by parsers, with source provenance and trusted labels attached.

Rule: normalization changes representation, not ground truth.

### 3. Features

Derived numeric observations aggregated once per trusted run for rule-based or ML detection.

The Day 8 feature contract contains:

- deterministic `feature_id` and source `run_id`
- event-window start and end
- source type and total event count
- authentication attempt, outcome, and unique-username counts
- web request, request-length, and SQL-token counts
- network connection and unique-destination-port counts
- unchanged trusted scenario and attack label

Rule: features describe observable evidence. They do not create or alter ground truth.

### 4. Labels

Ground truth derived from controlled attack-run metadata.

Rule: a parser or detector must never invent the ground-truth label.

## Folder Convention

- `data/raw/` — original lab evidence
- `data/processed/` — normalized/cleaned outputs
- `data/features/` — ML/rule feature tables
- `data/metadata/` — run manifests and provenance
- `data/reports/` — data-quality/evaluation summaries

Every processed artifact retains `run_id` and `raw_source_file` as a clear path back to its original lab run.

