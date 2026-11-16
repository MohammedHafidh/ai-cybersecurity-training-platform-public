from typing import Literal, NamedTuple


class CollectionRun(NamedTuple):
    source_type: Literal["auth", "web", "network"]
    expected_label: Literal["benign", "malicious"]
    scenario: Literal["benign", "brute_force", "sql_injection", "reconnaissance"]
    repetition: int

    @property
    def run_key(self) -> str:
        return f"{self.source_type}-{self.expected_label}-{self.repetition:02d}"

    @property
    def variant_group(self) -> str:
        """Pair the same bounded variant across every source/label stratum."""
        return f"variant-{self.repetition:02d}"


def day11_collection_plan(repetitions: int = 5) -> list[CollectionRun]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    attack_scenarios = {
        "auth": "brute_force",
        "web": "sql_injection",
        "network": "reconnaissance",
    }
    return [
        CollectionRun(
            source_type=source_type,
            expected_label=label,
            scenario="benign" if label == "benign" else attack_scenarios[source_type],
            repetition=repetition,
        )
        for source_type in ("auth", "web", "network")
        for label in ("benign", "malicious")
        for repetition in range(1, repetitions + 1)
    ]

