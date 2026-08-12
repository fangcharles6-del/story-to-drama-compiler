# SDC-CANARY-001 local FakeProvider rehearsal

This runbook is the mandatory local rehearsal before the first real Canary. It permits local
PostgreSQL/Temporal image pulls and loopback traffic only. It does not authorize Ark access,
`LiveAuthorization` creation, credentials, recharge, purchase, or paid generation.

## Fixed boundary

- Host: Windows 10 Pro; Docker Desktop WSL2 Linux containers.
- Containers: PostgreSQL 16 and Temporal 1.27, bound only to `127.0.0.1`.
- Host processes: Worker and Canary Client through `uv`.
- Task Queue: `sdc-canary-001-v01-rehearsal`.
- Provider: `FakeProvider`; Ark adapter not loaded; Provider HTTP POST count zero.
- Cardinality: one Run, one Job, Attempt 1, one current candidate; Activity concurrency one.
- Media: text-only, 9:16, 1080x1920, 24 fps, 4000 ms, no generated audio.
- Failure: `HUMAN_GATE`; no Attempt 2 after restart or Activity failure.

Do not put `SDC_ARK_API_KEY`, evidence paths, or authorization paths in a `.env` file. The rehearsal
script removes those names from its child environment without reading or displaying their values.

## PowerShell commands

From the repository root in Windows PowerShell:

```powershell
git rev-parse HEAD
docker version
docker context show
uv sync --frozen
docker compose config --quiet
docker compose up -d --wait
docker compose ps
docker compose images
docker compose exec -T postgres pg_isready -U sdc -d sdc
docker compose exec -T temporal tctl --address temporal:7233 cluster health
uv run alembic upgrade head
uv run alembic check
```

For the first rehearsal on a disposable local database, include the migration round trip:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-SdcCanaryRehearsal.ps1 `
  -RunId sdc-canary-001-v01-rehearsal-run `
  -MigrationRoundTrip
```

For a later repeat against an already migrated local stack, omit `-MigrationRoundTrip` and choose a
new fixed Run ID before starting:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-SdcCanaryRehearsal.ps1 `
  -RunId sdc-canary-001-v01-rehearsal-run-02
```

The command must finish with a JSON report containing all of the following:

```text
"state": "SUCCEEDED"
"task_queue": "sdc-canary-001-v01-rehearsal"
"attempts": 1
"maximum_attempt": 1
"current_candidates": 1
"provider_http_posts": 0
"live_authorizations": 0
"activity_max_concurrency": 1
"width": 1080
"height": 1920
"fps": 24
"duration_ms": 4000
"generate_audio": false
```

The report is written under `.artifacts/canary-rehearsal/` and is not a live Canary evidence pack.
Do not add it to source control.

## Stop conditions

Stop immediately on any Docker, migration, Temporal, port conflict, network, or authentication
error. Preserve the original output. Do not bypass a failure by skipping checks, widening a port
binding, selecting the Ark provider, adding retries, or producing Attempt 2.

Before a separately approved real execution, recapture and freeze official capability and pricing
evidence. Never extend or reuse expired evidence. Do not run the first real Canary in GitHub Actions
or on a production VPS.
