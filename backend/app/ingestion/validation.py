from app.models.runs import RunMetadata


def validate_run_metadata(metadata: RunMetadata) -> list[str]:
    """Return human-readable problems without changing the supplied metadata."""
    errors: list[str] = []
    aware = all(value.tzinfo is not None and value.utcoffset() is not None for value in (metadata.start_time, metadata.end_time))
    if not aware:
        errors.append("timestamps must be timezone-aware")
    if aware and metadata.end_time < metadata.start_time:
        errors.append("end_time must be on or after start_time")
    for name in ("run_id", "source", "target", "tool_or_method"):
        if not getattr(metadata, name).strip():
            errors.append(f"{name} must not be empty")
    if len(metadata.log_sources) != len(set(metadata.log_sources)):
        errors.append("duplicate log sources")
    for name in metadata.log_sources:
        if not name.strip() or name.startswith(("/", "\\")) or ":" in name or ".." in name.replace("\\", "/").split("/"):
            errors.append("log sources must be safe relative paths")
    if not metadata.log_sources:
        errors.append("at least one log source is required")
    if metadata.status in ("excluded", "needs_review") and not metadata.exclusion_reason.strip():
        errors.append("excluded runs require an exclusion_reason")
    if metadata.scenario == "benign" and metadata.expected_label != "benign":
        errors.append("benign scenario requires expected_label='benign'")
    if metadata.scenario != "benign" and metadata.expected_label != "malicious":
        errors.append(
            f"{metadata.scenario} scenario requires expected_label='malicious'"
        )
    return errors
