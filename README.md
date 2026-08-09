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
