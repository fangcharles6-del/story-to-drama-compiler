# SDC-ADR-019: Offline Creative Sample Loop v1

- **Status:** Proposed
- **Date:** 2026-08-16
- **Version:** V01

## Context

SDC's deterministic compiler, durable runtime and evidence-bound Canary work establish strong
control-plane boundaries. They do not yet prove that a sequence of generated shots tells a coherent
story, preserves a recurring character, or can be edited into a useful short-drama sample. A real
Ark call is neither necessary nor authorized to define and rehearse that creative review loop.

This ADR introduces a deliberately separate offline sample boundary. It evaluates media that a
human has already placed on local storage. It does not acquire media, infer Provider provenance,
create authority, or reopen any live execution path.

## Decision

Creative Sample Loop v1 accepts only explicitly selected local `ImportedMedia` and produces an
offline, reviewable sample definition and scorecard. One sample has all of the following fixed
shape:

- a final timeline of 60–90 seconds (60,000–90,000 ms, inclusive);
- 8–12 ordered shots, with one imported video candidate per shot;
- exactly two narratively distinct scenes;
- one or two named recurring characters; and
- deterministic shot, scene, character and sample identities derived from canonical non-secret
  inputs rather than wall-clock time.

The loop may validate, hash, inspect, assemble and review local inputs. It has no Key or network
access and must not contact Ark or another generation service, start a Worker, Temporal or
PostgreSQL, create an entitlement or authorization, populate a positive registry, consume a
ledger claim, recharge, purchase, claim a trial, or submit a Provider task.

`ImportedMedia` means media that already exists before SDC begins the loop. Import is not
generation. A source may have been filmed or generated in a separately governed process, but SDC
does not authenticate that origin merely because an operator supplies a filename or description.
The sample records only the bounded provenance that can be reviewed locally.

The implementation invokes only locally resolved `ffmpeg` and `ffprobe` processes. Their child
environment is reduced to locale and required Windows runtime variables, stdin is closed, runtime
and diagnostic sizes are bounded, input demuxers are explicit, and the FFmpeg protocol allowlist
contains only `file`. MP4 data references and absolute references are disabled. Output metadata
and chapters are stripped. These controls are defense in depth for the offline operating boundary;
they do not make arbitrary untrusted media parsing a general-purpose sandbox.

The installed FFmpeg directory is part of the operator-controlled local trusted computing base.
At run start SDC resolves both tools to ordinary non-link files in one directory, records their
SHA-256 values, pins their filesystem identities, and re-reads both binaries before completing the
sample. The hashes, never the absolute installation paths, are bound into the assembly receipt.

## Imported-media provenance and immutability

Every candidate must be named explicitly; the importer must not discover inputs by recursively
scanning a directory. Admission binds at least the local logical path, byte length, SHA-256,
media type, measured duration, shot identity, scene identity, recurring-character appearances,
bounded approval/review-record references and a provenance-record SHA-256. Original input bytes
are read-only. Every admitted file is copied into a new immutable staging closure before FFmpeg
consumes it. Derived clips, reports and assembled samples use a separate output location and never
replace a source file.

Network URLs, network shares, pipes, devices, links, junctions, reparse points and non-regular files
are outside this boundary. A provenance statement must not contain credentials, signed URLs,
cookies, headers, Provider task IDs, raw account identifiers or other secret/private operational
metadata.

FakeProvider output, color bars, synthetic fixtures and placeholder media remain useful for unit
and assembly tests. They must be labeled `SYNTHETIC_FIXTURE` and excluded from every creative
quality numerator, denominator and pass decision. Renaming, transcoding or copying a fixture does
not turn it into real imported media. A creative sample claiming actual-shot evidence requires
`IMPORTED_MEDIA` bytes and must not claim that SDC or Ark generated them unless independent
provenance outside this ADR supports that statement.

The initially admitted ordered candidate set is frozen before creative scoring. The revision ID
binds the deterministic compilation and canonical import manifest. Attempt 2 retains the Attempt 1
digest, is never counted as first-pass usable, and a later revision binds the predecessor manifest
digest. That predecessor digest is an operator-retained lineage commitment: v1 does not load or
authenticate the older manifest, so a pass cannot prove a cross-revision history. Automatic
cross-revision comparison belongs to a later predecessor-bundle verifier.

## Character and scene coverage

A recurring character is an explicit sample identity, not a name repeated in prompts. Each
recurring character must appear in at least three scored shots and in both scenes so that continuity
has a meaningful cross-scene observation. Each shot declares zero or more on-screen recurring
characters, and each scene contains at least three shots. Extras do not count toward the one-to-two
recurring-character limit unless they are deliberately promoted into the frozen character set.

The review compares only declared identities and observable continuity. It does not claim face
recognition, biometric identification or proof that a depicted person is a particular real person.
Real-person likenesses require a separate rights and consent review outside this ADR.

If the loop assembles a final sample, its reviewed v1 delivery profile is 1080x1920 at 25 fps,
H.264/yuv420p video, AAC audio at 48 kHz and an embedded `mov_text` subtitle stream. Voice, BGM and
subtitle inputs are local-only assets subject to the same provenance and no-overwrite boundary.

Character and scene Asset Packs contain only the active, exact-version closure required by the
sample. v1 assets use a bounded, decoded, metadata-free RGB/RGBA PNG profile. The pack is
content-addressed, no-replace and manifest-last; arbitrary bytes cannot be relabeled as an image.

## Metrics and decision rule

The v1 scorecard separates hard admission gates from creative measurements. All ratios use the
frozen first-pass set; removing a failed shot cannot improve a score. The editor and an independent
reviewer supply distinct review-record references. SDC conservatively retains a failure from either
declaration and explicitly reports that reviewer identity and record authenticity are not proven by
SDC.

| Metric | Definition | v1 pass gate |
|---|---|---|
| Shape compliance | Duration, shot, scene and recurring-character cardinalities above | 100% |
| Import integrity | Explicit regular local files whose observed digest and metadata match the manifest | 100% |
| Technical usability | Decodable shot with complete measured duration and no missing/duplicate media | 100% |
| Critical identity breaks | A reviewer cannot reasonably identify a declared recurring character as the same role | 0 |
| Character continuity | Passing appearances / all declared appearances | at least 90% |
| Scene continuity | Passing adjacent in-scene boundaries / all reviewed boundaries | at least 90% |
| Shot-intent pass rate | Shots that communicate their frozen narrative purpose without replacement | at least 80% |
| Artifact-free rate | Shots without a reviewer-blocking visual or temporal artifact | at least 90% |
| First-pass usable-shot rate | Frozen shots accepted into the sample without replacement | at least 75% |
| Duplicate media | Undeclared reuse of one digest for different shots | 0 |
| Human review effort | Review and edit minutes / finished sample minute | report; pilot target at most 60 |

A `PASS_SAMPLE` decision requires every hard gate and threshold. `REVISE_OFFLINE` permits a new
immutable revision using other already available or newly supplied `ImportedMedia`, still with no
Provider access. Unknown provenance, a synthetic fixture presented as real, a critical identity
break, missing review evidence or any attempt to cross the offline boundary is `STOP` rather than a
waiver.

Passing this scorecard means only that the reviewed local sample met the v1 criteria. It is not an
Ark entitlement, LiveAuthorization, production-readiness certification, billing result, model
benchmark or permission to publish.

## Quality and compliance boundary

Mechanical inspection and human review are complementary. Existing ffprobe/checksum checks may
support import integrity, but they do not prove story fidelity, character continuity, aesthetics,
likeness rights, copyright, music rights, privacy, age suitability or platform policy compliance.
The scorecard records those exclusions rather than treating a technically valid MP4 as an approved
creative asset.

Any voice, music, subtitle, image or reference asset included by an implementation remains local
imported media under the same provenance and no-overwrite rules. This ADR does not select a
TTS, image, avatar, music or moderation Provider and does not authorize one.

## Future live work is one separately approved batch

No sample manifest, metric result or `PASS_SAMPLE` decision can be converted into live authority.
A future live proposal must be a separate delivery and approval for one exact, finite batch. That
batch must independently bind its batch ID, immutable inputs, exact shot IDs, Provider/model,
account/region, maximum submission count, maximum spend, expiry, runtime release and recovery
semantics. It must use the evidence-bound live chain current at execution time.

Approval for one batch is not standing authority. It cannot roll over to another batch, add shots,
replace expired evidence, authorize an automatic retry batch or be inferred from imported results.
Incomplete or ambiguous execution stops at its defined human gate. This ADR intentionally provides
no live command, Key-loading step, registry entry or activation procedure.

## Consequences

Creative quality can now be discussed against a bounded sample shape and explicit measurements
without weakening the Canary safety boundary. The first loop may establish a useful baseline for
character continuity, usable-shot yield and human effort, but it cannot establish Provider yield or
economics unless a later independently approved batch records all submitted candidates rather than
only selected results.

This delivery keeps legacy NIR/PIR/schema bytes stable and introduces new versioned contracts. It
adds only a separate pure compiler entry point, local Asset Packs, local provider protocols, media
assembly, technical QC and an offline report-last output verifier. It does not change the existing
runtime, Worker, Temporal, PostgreSQL, Provider adapters, evidence registries, authorization or
live network behavior.
