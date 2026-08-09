import pytest

from sdc.qc import current_candidate_facts


def passed(expected: list[str], candidates: dict[str, list[str]]) -> bool:
    return all(fact[1] for fact in current_candidate_facts(expected, candidates))


def test_exactly_one_current_candidate_per_job_passes() -> None:
    assert passed(["job_a", "job_b"], {"job_a": ["a1"], "job_b": ["b1"]})


@pytest.mark.parametrize(
    "candidates",
    [
        {"job_a": []},
        {},
        {"job_a": ["a1", "a2"]},
        {"job_a": ["a1", "a1"]},
    ],
    ids=["zero", "missing", "two-different", "duplicate"],
)
def test_invalid_current_candidate_cardinality_fails(candidates: dict[str, list[str]]) -> None:
    assert not passed(["job_a"], candidates)


def test_unexpected_job_candidate_fails() -> None:
    assert not passed(["job_a"], {"job_a": ["a1"], "job_b": ["b1"]})
