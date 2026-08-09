import pytest

from sdc.qc import current_candidate_facts, segment_coverage_facts


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


def test_candidate_cannot_be_shared_by_jobs() -> None:
    assert not passed(["job_a", "job_b"], {"job_a": ["same"], "job_b": ["same"]})


@pytest.mark.parametrize(
    "actual_segments",
    [
        ["a.mp4"],
        ["a.mp4", "unexpected.mp4"],
        ["a.mp4", "a.mp4"],
    ],
    ids=["missing", "unexpected", "duplicate"],
)
def test_segment_coverage_rejects_non_exact_sets(actual_segments: list[str]) -> None:
    facts = segment_coverage_facts(
        ["job_a", "job_b"],
        {"job_a": ["a.mp4"], "job_b": ["b.mp4"]},
        actual_segments,
    )
    assert not all(fact[1] for fact in facts)


def test_segment_coverage_uses_candidate_metadata_not_order() -> None:
    facts = segment_coverage_facts(
        ["job_a", "job_b"],
        {"job_a": ["a.mp4"], "job_b": ["b.mp4"]},
        ["b.mp4", "a.mp4"],
    )
    assert all(fact[1] for fact in facts)
