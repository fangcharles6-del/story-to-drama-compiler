from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from sdc.persistence import ArtifactRecord, LiveAuthorizationUseRecord


def test_current_candidate_uses_postgresql_partial_unique_index() -> None:
    table = ArtifactRecord.__table__
    assert not any(
        {column.name for column in constraint.columns} == {"run_id", "job_id", "is_current"}
        for constraint in table.constraints
    )
    index = next(item for item in table.indexes if item.name == "uq_artifacts_one_current_per_job")
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert index.unique
    assert "UNIQUE INDEX" in ddl
    assert "WHERE is_current = true" in ddl
    assert "(run_id, job_id)" in ddl


def test_live_authorization_is_globally_one_use() -> None:
    table = LiveAuthorizationUseRecord.__table__
    assert table.primary_key.columns.keys() == ["authorization_id"]
    fingerprint = table.columns["request_fingerprint"]
    assert fingerprint.unique
