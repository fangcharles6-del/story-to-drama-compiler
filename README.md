# Story-to-Drama Compiler (SDC)

SDC is a deterministic compiler whose versioned NIR is the sole story source of truth. This
BUILD-001 slice compiles `StoryInput → NIR → PIR → AudioMasterClock → JobGraph → AssemblyPlan`,
generates deterministic local clips, assembles a release, and records evidence-first QC. It never
calls a real generation platform.

## Quick start / 快速开始

Requirements / 依赖: Python 3.12, [uv](https://docs.astral.sh/uv/), FFmpeg/ffprobe, GNU Make.

```bash
make bootstrap       # install the exact locked environment / 安装锁定依赖
make lint typecheck test
make integration      # PostgreSQL 16 + local Temporal, migrations and runtime tests
make demo            # offline end-to-end run / 离线端到端运行
make verify-demo     # independently re-check output / 再次验证产物
```

The output is under `.artifacts/demo/`: all five compiler IR files, append-only-style run events,
segments, `final.mp4`, raw ffprobe evidence in `qc_report.json`, and the checksummed
`release_manifest.json`. Run `make schemas` after editing contracts; tests reject schema drift.

## Structure / 结构

- `src/sdc/contracts.py`, `compiler.py`: immutable contracts and pure compiler.
- `provider.py`, `media.py`, `qc.py`: replaceable gateway, FFmpeg media engine, QC.
- `workflow.py`, `persistence.py`: Temporal orchestration and SQLAlchemy production adapters.
- `schemas/`: committed JSON Schema; `migrations/`: Alembic history.
- `examples/`, `tests/`, `docs/adr/`: runnable input, verification, accepted decisions.

For production-adapter development, `docker compose up -d` starts PostgreSQL and Temporal. The
offline demo and unit suite do not require Docker. Temporal owns workflow state; PostgreSQL keeps
queryable run state, immutable events, and uniquely keyed generation artifacts. Creative jobs have
one current candidate and exactly two possible automatic attempts; exhaustion transitions to
`STOP-2`, requiring a human gate rather than a hidden third try.

## Durable worker

Apply migrations with `uv run alembic upgrade head`, then start the replaceable runtime worker
with `uv run python -m sdc.worker`. `SDC_DATABASE_URL`, `SDC_TEMPORAL_ADDRESS`, `SDC_TASK_QUEUE`,
and `SDC_OUTPUT_ROOT` configure its boundaries. Provider attempts are reserved transactionally
before generation, so activity redelivery or a worker restart cannot create an automatic third
attempt. The worker defaults to the offline `FakeProvider`. Its durable production path reserves an
Attempt, submits exactly once, then inspects and downloads only the persisted remote task ID.
Inspect/download technical retries never reserve another creative Attempt.

Submit a real execution with `uv run python -m sdc.client examples/minimal_story.json`. Every
submission creates a unique `run_id`, uses it verbatim as the Temporal workflow ID, and passes it
beside the deterministic `JobGraph`; repeated compilation therefore preserves content IDs without
colliding durable runtime state. Both the submitting client and worker use Temporal's Pydantic v2
payload converter. See `docs/adr/SDC-ADR-009.md` for the accepted identity and retry decisions.

## Seedance provider (offline integration only)

`SDC_PROVIDER=fake` is the safe default and CI never needs a provider credential or network access
to Ark. The accepted optional adapter is selected with `SDC_PROVIDER=volcengine_ark`; it requires
`SDC_ARK_API_KEY` at worker startup and otherwise fails fast. Optional settings are
`SDC_ARK_MODEL` (default `doubao-seedance-2-0-260128`), `SDC_ARK_BASE_URL` (official HTTPS URL by
default; override for local tests), `SDC_ARK_MAX_IN_FLIGHT` (default 2),
`SDC_ARK_POLL_INTERVAL_SECONDS`, and `SDC_ARK_TASK_TIMEOUT_SECONDS`. Do not put keys in `.env` or
source control.

No real/live canary is authorized by BUILD-003. Before production, an operator must manually open
the Ark service, inject the secret through the deployment secret store, establish a cost cap, and
obtain separate approval for a monitored canary. The adapter never falls back to another model or
provider. See `docs/adr/SDC-ADR-010.md` for submission-unknown and two-Attempt semantics.

The Ark HTTP implementation is worker-only and is not imported into Temporal's deterministic
workflow sandbox. Result downloads use a separate credential-free HTTP client, are verified in a
temporary file, and are atomically published only after SHA-256, size, and ffprobe evidence pass.

## Zero-spend live readiness

SDC-ADR-011 adds a second, fail-closed boundary in front of Ark submission. A live worker requires
versioned capability and pricing snapshots plus a separately approved, exact-request
`LiveAuthorization`. Consumption is persisted before POST and is globally one-use, so worker
restart cannot replay a paid authorization. Missing, stale, mismatched, reused, or over-budget
evidence enters `HUMAN_GATE` without a provider request.

`uv run python -m sdc.canary` creates a zero-network plan and frozen request. Its output is always
`NOT_AUTHORIZED` with zero allowed POSTs; it cannot create a live authorization or call Ark. See
`docs/runbooks/ARK-CANARY-001.md`. BUILD-004 still authorizes no credentials, service activation,
purchase, recharge, paid generation, or live canary; that requires a separate SDC-CANARY approval.

SDC-ADR-012 adds the deterministic BUILD-005 operation path. A preparation command can compile a
one-beat, 4000 ms story and freeze one `CanaryExecution`: fixed `run_id`, deterministic single
`job_id`, exact request fingerprint, pinned Seedance 2.0 / 9:16 / 1080p parameters, text-only input,
and explicit `generate_audio=false`. The reviewed cost ceiling is capped at CNY 15. Authorization
artifact creation uses the separate `python -m sdc.canary_authorize` command, and execution uses
`python -m sdc.client --canary-execution ...`; neither preparation command executes a Workflow or
touches Ark. The canary Workflow permits Attempt 1 and at most one POST, then fails closed to
`HUMAN_GATE` without Attempt 2. BUILD-005 still performs no live call and grants no credentials or
spend authority; `SDC-CANARY-001` remains a separate approval based on execution-day official
evidence.
