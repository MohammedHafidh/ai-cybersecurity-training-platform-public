# Attack Run Metadata Template — Draft v0

> Historical design record. Commands that require the original lab or private evidence are documented for context. See the public README for runnable checks.

Every controlled lab run should have a metadata record. This is what makes later labeling defensible.

## Required Fields

```yaml
run_id: ""
scenario: ""          # benign | brute_force | sql_injection | reconnaissance
expected_label: ""    # benign | malicious
start_time: ""
end_time: ""
source: ""
target: ""
tool_or_method: ""
log_sources: []
notes: ""
status: ""            # valid | excluded | needs_review
exclusion_reason: ""
```

## Example

```yaml
run_id: "auth-bf-001"
scenario: "brute_force"
expected_label: "malicious"
start_time: "2026-10-07T14:10:00+04:00"
end_time: "2026-10-07T14:12:00+04:00"
source: "local-lab-attacker"
target: "local-auth-target"
tool_or_method: "controlled repeated authentication attempts"
log_sources:
  - "auth.log"
notes: "Small bounded lab run."
status: "valid"
exclusion_reason: ""
```

## Rules
1. Record metadata when the run happens, not days later from memory.
2. Use a unique run_id.
3. Preserve exact start/end times.
4. Record benign runs too.
5. If evidence is ambiguous, mark it needs_review or excluded instead of guessing.
6. Labels come from known lab activity and timing, not from rule/ML predictions.
7. Do not include secrets or real production credentials.
