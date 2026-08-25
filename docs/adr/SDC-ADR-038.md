# SDC-ADR-038: Production Adapter Foundation v1

- Status: Proposed
- Date: 2026-08-25
- Source assessment: `harry0703/MoneyPrinterTurbo@6cd36b5a2c56b49b24621463038e4db3963f0a43`
- License observed at source revision: MIT
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Network/spend boundary: zero new network calls, zero credentials, zero Provider requests

## Context

MoneyPrinterTurbo is a production-oriented short-video application. Its service layer contains
useful implementation patterns around centralized Provider metadata, allowlisted material source
records, optional semantic video analysis, pluggable speech synthesis, and cross-platform media
assembly. Its task orchestration and keyword-to-stock-footage content model do not match SDC's
deterministic compiler and durable runtime.

SDC already owns the stronger core boundary: versioned NIR/PIR, AudioMasterClock, JobGraph,
AssemblyPlan, Temporal/PostgreSQL durability, persisted remote task IDs, technical retry separation,
creative Attempt limits, `SUBMISSION_UNKNOWN -> HUMAN_GATE`, evidence-first QC, and fail-closed Ark
execution. This ADR must not replace or weaken those decisions.

This slice uses design ideas only. It does not vendor MoneyPrinterTurbo source code, import that
package, add it as a dependency, or copy its orchestration implementation.

## Component mapping and disposition

| MoneyPrinterTurbo component | Useful idea | SDC destination | Disposition |
| --- | --- | --- | --- |
| `app/services/material.py` | Persist an allowlist of provider/asset/source/creator/rendition metadata while stripping download secrets and local paths | `src/sdc/material_provenance.py` | Integrate as pure sanitization and immutable dataclasses; no search/download adapter yet |
| `app/services/task.py` | Stage-specific diagnostics and resumable external work | Existing `workflow.py`, `persistence.py`, Runtime Activities and Provider Attempt ledger | Do not copy task/thread orchestration; Temporal/PostgreSQL remain authoritative |
| `app/services/llm.py` and Provider registry | Separate stable Provider metadata from adapter invocation | `src/sdc/provider_catalog.py` | Integrate static metadata registry only; no LLM call is added to Compiler Core |
| `app/services/video.py` | Treat FFmpeg path construction as a portability/security boundary | `src/sdc/media.py` | Integrate deterministic ffconcat header, LF encoding and path quoting; keep current codecs and AssemblyPlan |
| `app/services/voice.py` | Common request/artifact protocol across speech providers | `src/sdc/speech.py` | Integrate a 48 kHz WAV protocol and fail-closed default; no concrete TTS or voice cloning |
| `app/services/twelvelabs.py` | Optional semantic analysis with a safe no-op when unconfigured | `src/sdc/semantic_qc.py` | Integrate provider-neutral advisory observations; no remote adapter and no automatic quality decision |

## Decision

### 1. Static Provider catalog

Add immutable `ProviderSpec` metadata with exact IDs, capability names, execution boundaries,
network/secret/cost properties and current availability. The registry initially describes only
existing SDC paths:

- `fake`: offline video generation, available offline;
- `imported_media`: human-supplied local media, available offline; and
- `volcengine_ark`: worker-only paid network adapter, explicitly `DISABLED_FAIL_CLOSED`.

The catalog performs no dynamic import or discovery. A catalog entry is never an authorization,
entitlement, credential, capability snapshot, pricing snapshot or runtime gate. Every spec reports
`grants_execution_authority=false`.

### 2. Material provenance allowlist

Add a pure builder for `MaterialSourceRecord`. It persists only:

- canonical provider ID;
- local basename, never an absolute path;
- duration;
- optional search term and provider asset ID;
- public source page with query, fragment and credentials removed;
- optional allowlisted creator ID/name/profile page; and
- optional rendition ID and dimensions.

Unknown provider response fields, API keys, download URLs, signed query parameters, local working
directories, emails and raw payloads are ignored. The module performs no filesystem or network I/O.

### 3. Advisory semantic QC boundary

Add a `SemanticVideoAnalyzer` protocol, an exact request derived from `StoryboardShotV2`, an
immutable observation and a null analyzer. Observations bind the compiled shot intent to one
candidate SHA-256.

Semantic output is advisory evidence only:

- it cannot set `QCReport.passed`;
- it cannot reserve another Attempt;
- it cannot trigger Retry, `STOP-2`, publication or Provider execution;
- a negative recommendation remains a detail value rather than a failed technical QC fact; and
- `qc.verify` is unchanged.

A future remote analyzer requires a separately reviewed worker-only adapter, retention/privacy
policy, capability and pricing evidence, credentials and cost authorization.

### 4. Speech adapter boundary

Add a provider-neutral speech request/artifact protocol pinned to 48 kHz WAV so future TTS output
can close over `AudioMasterClock`. The default provider raises before touching the output path. No
TTS SDK, API key, voice cloning, remote processing or paid request is introduced.

### 5. FFmpeg concat manifest hardening

Keep the existing deterministic FFmpeg assembly profile and add:

- the canonical `ffconcat version 1.0` header;
- explicit UTF-8 and LF output;
- resolved POSIX-style path rendering;
- concat-format apostrophe escaping;
- rejection of NUL/CR/LF path values; and
- an output-specific concat-manifest filename.

This does not add random material selection, MoviePy, hardware codec fallback, transition effects,
mutable render presets or an alternate media clock.

## Frozen compatibility boundary

This slice must not change:

- StoryInput, NIR, PIR, AudioMasterClock, JobGraph or AssemblyPlan contracts;
- Temporal workflow ownership or PostgreSQL durable state;
- Provider submit/inspect/download/cancel semantics;
- persisted remote task IDs or `SUBMISSION_UNKNOWN -> HUMAN_GATE`;
- one-current-candidate, two-Creative-Attempt or `STOP-2` policy;
- Ark model/region/endpoint pinning, authorization registries, entitlement evidence or ledgers;
- any Worker startup gate, API-key handling or network policy;
- `qc.verify` technical pass/fail behavior;
- any released Pydantic contract or committed Schema byte; or
- `sdc.schemas.MODELS`, which remains exactly 68.

## Rejected imports

The following MoneyPrinterTurbo patterns are intentionally not integrated:

- keyword search terms as SDC's story source of truth;
- random stock-footage concatenation;
- in-process thread pools or Redis state as a replacement for Temporal;
- mutable runtime Provider defaults inside compiled artifacts;
- API-key presence as execution authority;
- automatic POST retry after an ambiguous submission;
- semantic-model output as an automatic PASS/RETRY decision;
- cross-platform publishing inside Compiler Core; and
- concrete TTS, LLM, stock-video or semantic-analysis network adapters in this slice.

## Validation

The implementation must pass the existing offline `make check` and integration suite. New tests
cover:

- canonical registry order, filtering and zero-authority behavior;
- fail-closed Ark metadata;
- source URL/query/credential stripping and local path minimization;
- dropping unknown or malformed external metadata;
- null semantic analysis and explicit advisory-only conversion;
- proof that a negative semantic recommendation is not a QC failure or authority;
- 48 kHz/WAV speech invariants and fail-before-output default behavior; and
- deterministic ffconcat rendering, apostrophe escaping and empty-input rejection.

No test may contact MoneyPrinterTurbo, TwelveLabs, a stock library, a TTS provider, Ark or any other
remote service.

## Follow-up boundaries

Concrete stock-media, TTS or semantic-QC adapters require separate ADR/BUILD slices. Each must
specify its exact worker boundary, credentials, data retention/privacy, rights provenance, pricing,
cost ceiling, retry semantics, persistence schema and human gate before implementation.
