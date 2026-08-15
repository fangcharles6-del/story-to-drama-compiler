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
to Ark. The Ark adapter remains in the codebase, but supported Worker startup with
`SDC_PROVIDER=volcengine_ark` still fails closed unconditionally. ADR-017 adds inert
evidence-bound contracts and validation, but does not connect them to the Worker or
`RuntimeActivities`. Worker startup rejects Ark before reading an API Key. Directly constructed Ark
runtime activities reject it before reserving an Attempt, consuming authorization or calling the
Provider. FakeProvider rehearsal remains available; do not put keys in `.env` or source control.

No real/live canary is authorized by BUILD-003. Before production, an operator must manually open
the Ark service, inject the secret through the deployment secret store, establish a cost cap, and
obtain separate approval for a monitored canary. The adapter never falls back to another model or
provider. See `docs/adr/SDC-ADR-010.md` for submission-unknown and two-Attempt semantics.

The Ark HTTP implementation is worker-only and is not imported into Temporal's deterministic
workflow sandbox. Result downloads use a separate credential-free HTTP client, are verified in a
temporary file, and are atomically published only after SHA-256, size, and ffprobe evidence pass.

## Zero-spend live readiness

SDC-ADR-011 historically added a second, fail-closed boundary in front of Ark submission using
versioned capability and pricing snapshots plus a separately approved, exact-request
`LiveAuthorization`. ADR-016 retires that supported live path, and ADR-017's inert contract does
not reopen it. The durable one-use design remains historical context, not a current execution
instruction.

The historical loose-snapshot `python -m sdc.canary` command is retired and fails closed. New
zero-network planning uses a Git-reviewed execution-day FRESH EvidenceBundle through
`python -m sdc.fresh_canary_plan`; its output is always `NOT_AUTHORIZED` with zero allowed POSTs.
See `docs/runbooks/ARK-CANARY-001.md`. No planner creates authorization or calls Ark.

SDC-ADR-012 adds the deterministic BUILD-005 operation path. A preparation command can compile a
one-beat, 4000 ms story and freeze one `CanaryExecution`: fixed `run_id`, deterministic single
`job_id`, exact request fingerprint, pinned Seedance 2.0 / 9:16 / 1080p parameters, text-only input,
and explicit `generate_audio=false`. The reviewed cost ceiling is capped at CNY 15. The historical
`python -m sdc.canary_authorize` command and Ark Worker startup path are now retired and fail closed
for all old and new authorization objects. FakeProvider rehearsal remains available. This build
performs no live call and grants no credentials or spend authority.

SDC-ADR-013 fixes the first Canary infrastructure to local Windows 10 Pro plus Docker Desktop WSL2.
PostgreSQL and Temporal bind to loopback only, while the Worker and client run through host `uv`.
Before any real Provider call, run the isolated FakeProvider rehearsal documented in
`docs/runbooks/SDC-CANARY-001-LOCAL-REHEARSAL.md`. It uses a dedicated Task Queue, Activity
concurrency one, one Run/Job/Attempt/candidate, 1080x1920 at 24 fps for four seconds, no audio, no
Ark adapter, no `LiveAuthorization`, and zero Provider HTTP POSTs. Failures enter `HUMAN_GATE`
without Attempt 2. Expired capability or price evidence can never be extended or reused.

## Immutable evidence bundles

SDC-ADR-014 and SDC-ADR-015 define immutable, content-addressed evidence bundles and a restricted
offline importer for the reviewed R2-R6 Canary archives. The canonical materialization deduplicates
unchanged historical evidence without modifying its source archive, capture time, or expiry. It
never restores live eligibility or reads R6-live, credentials, Provider requests, or generated
media. See `docs/runbooks/SDC-EVIDENCE-CAS-R2-R6.md` for the verify-first procedure and fixed
67-object closure.

SDC-ADR-016 adds a separate execution-day FRESH namespace and a zero-network evidence-bound
planner. The freezer produces only an untrusted candidate bundle; a distinct Git-reviewed positive
registry entry must bind its full ID, tree, contract hashes and expiry before planning. The new
`EvidenceBoundCanaryPlan` remains `NOT_AUTHORIZED` with zero POSTs. Historical authorization
generation and Ark Worker startup both fail closed rather than accepting it. See
`docs/runbooks/SDC-FRESH-EVIDENCE-PLANNING.md`; this build still does not access Ark, read a Key,
start services, create authorization, or permit paid generation.

SDC-ADR-017 adds an inert `EvidenceBoundLiveAuthorization` candidate and a module-private runtime
binding validator. A candidate rebinds the reviewed plan and execution, evidence
bundle/tree, cost and expiry, independent entitlement-anchor identifier, Task Queue, durable
ledger, runtime release, and domain-separated Ark wire policy. That wire policy fixes
`cn-beijing`, the official host and task-creation path, HTTP `POST`, the exact credential-free JSON
body, and one submit call. Candidate generation reports `mode=candidate-only-not-approved`; the
file and digest do not grant authority. Runtime validation first requires an exact entry in a
separate Git-reviewed positive authorization registry, before reading the plan, execution or
authorization artifacts. That registry is empty in this PR, and candidate generation never edits
it.

Migration `0007` only prepares append-only evidence-bound claim columns and constraints. It does
not implement the future atomic `POST_IN_FLIGHT` claim or connect any guard to Provider I/O. The
current FRESH profile contains capability and pricing only, not current account entitlement.
Future live enablement therefore still requires a positively trusted entitlement artifact,
independent approval of the exact authorization SHA, an approved runtime/ledger identity, atomic
claim and replay-to-`SUBMISSION_UNKNOWN` handling, and a dedicated one-concurrency Canary Worker.
Until a separate ADR and explicit approval deliver all of those gates, Ark remains disabled with
zero POSTs.

Proposed SDC-ADR-018 now fixes that future execution boundary at design level: a short-lived,
positively registered exact-account/Seedance/`cn-beijing` entitlement bundle; one database-UTC
transaction for Attempt 1 plus the immutable `POST_IN_FLIGHT` claim; replay to
`SUBMISSION_UNKNOWN` when no owned task ID exists; and a dedicated one-concurrency Worker that
loads the exact reviewed secret resource version only after every static and durable gate passes.
It remains non-operational and grants no authority. See
`docs/runbooks/SDC-EVIDENCE-BOUND-LIVE-CANARY.md` for the test and follow-up PR plan.
