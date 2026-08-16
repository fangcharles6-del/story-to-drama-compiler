# Creative Sample Loop v1 (offline ImportedMedia only)

This runbook operationalizes proposed SDC-ADR-019 as a local review procedure. It contains no
generation or live-activation command. It may inspect media already supplied by a human; it must
not obtain media from Ark or any other network service.

## Hard boundary

Before inspecting a candidate, confirm all of the following:

- the session is offline and no network access is required;
- no API Key, secret locator, credential, `.env` value or Provider session is read;
- Ark, its console and every generation/inspection/download API remain untouched;
- Worker, Temporal and PostgreSQL are not started for this loop;
- entitlement and authorization registries remain unchanged and no ledger identity or claim is
  created;
- every input is an explicitly selected local regular file; and
- FakeProvider, color bars and other synthetic fixtures are labeled and excluded from creative
  scoring.

Stop immediately if any step would require a URL, remote mount, browser session, service startup,
authorization, purchase, recharge, trial or Provider request. Preserve local review state; do not
substitute a hidden network action or relabel a fixture.

Use an operator-controlled local directory whose parents will not be concurrently renamed,
relinked or replaced. The importer rejects links, hard links, reparse points, device names, remote
or unverified drives and protected evidence/Canary namespaces, but it is not a sandbox against a
same-privilege process mutating the local filesystem concurrently.

## 1. Declare the sample before scoring

Prepare a human-reviewed manifest or worksheet with this fixed sample shape:

- total edited timeline: 60–90 seconds;
- ordered shots: 8–12;
- recurring characters: 1–2;
- scenes: exactly 2; and
- at least three shots in each scene.

Give each sample, revision, scene, character and shot a stable identifier. For every recurring
character, declare at least three scored appearances spanning both scenes. Record a short frozen
narrative intent for every shot before reviewing its media.

The first-pass set is the exact ordered set admitted at this point. Do not drop a failed shot from
the denominator. Editorial repetition of the same bytes must be explicit; otherwise every shot
uses a distinct imported SHA-256.

## 2. Admit only ImportedMedia

For each shot, record at least:

| Field | Requirement |
|---|---|
| `shot_id` | Stable and unique within the sample revision |
| `ordinal` | One deterministic timeline position |
| `scene_id` | One of the two declared scenes |
| `character_ids` | Only declared recurring characters visible in the shot |
| `narrative_intent` | Frozen before scoring |
| `source_kind` | `IMPORTED_MEDIA`; fixtures use `SYNTHETIC_FIXTURE` instead |
| `logical_path` | Explicit local path, never a URL or remote path |
| `sha256` / `size_bytes` | Computed from the opened source bytes |
| `media_type` | Expected local media type |
| `measured_duration_ms` | Obtained by offline inspection, not copied from a filename |
| `approval_ref` | Portable reference to the bounded offline approval record |
| `provenance_record_sha256` | SHA-256 of a separately retained provenance record; no secret |
| `first_attempt_sha256` / `attempts` | Frozen first candidate and one-or-two Attempt history |
| two reviewer records | Distinct editor/independent refs and review-record SHA-256 values |

Open only the named file. Reject missing files, directories, devices, pipes, sockets, symlinks,
hard links, junctions, reparse points and paths that resolve outside the reviewed local roots. Do
not recursively scan for replacements. Recheck identity and metadata after reading so a source
change cannot be accepted under its earlier digest.

Treat source bytes as read-only. Any normalized clip, thumbnail, report or final sample is written
to a distinct output root. Existing output with different bytes is a conflict, not permission to
overwrite it.

`IMPORTED_MEDIA` does not prove where media came from. If independent origin evidence is absent,
say `origin not authenticated by SDC`. Never infer Ark, model, account, task or billing provenance
from appearance, filename or operator expectation.

## 3. Keep fixtures out of creative evidence

Synthetic clips may exercise deterministic compilation, assembly and report formatting. Keep them
in a visibly separate fixture set and mark `source_kind=SYNTHETIC_FIXTURE` in every derived record.

The following are forbidden:

- copying or transcoding a FakeProvider clip and marking it `IMPORTED_MEDIA`;
- using fixture shots to satisfy the 8–12 shot, two-scene or character-appearance requirements;
- counting fixture passes in continuity, intent, artifact or usable-shot ratios; and
- describing a fixture-only assembled video as a real creative sample.

If any scored shot resolves to fixture bytes, the decision is `STOP`; changing its label after
review does not repair provenance.

## 4. Perform offline technical inspection

Use local-only media inspection to record, without changing the source:

- decodability, stream types, dimensions, frame rate and measured duration;
- file SHA-256 and byte length;
- missing, duplicate or unexpected shot media; and
- the deterministic timeline sum and ordering.

All admitted shots must pass import integrity and technical usability. Choose one reviewed final
timeline format before assembly; conversion is a declared derivative, not a mutation of imported
evidence. A technically valid file is still subject to the creative and rights review below.

The implementation freezes declared bytes before media parsing. FFmpeg/ffprobe receive explicit
`mov`, `wav` or `srt` demuxers, a `file`-only protocol allowlist, closed stdin, a minimal child
environment, bounded runtime/output/diagnostics and fixed resource limits. MP4 external data
references are disabled. Input metadata and chapters are not copied into the final sample, and
persisted probe facts contain only allowlisted technical fields rather than local filenames or
source tags.

Treat the installed FFmpeg directory and process `PATH` as operator-controlled prerequisites. SDC
requires `ffmpeg` and `ffprobe` to resolve to ordinary local files in one directory, pins their
filesystem identities, records both binary SHA-256 values in the assembly receipt, and rejects
run-end drift. Do not run this procedure with an unreviewed writable tool directory earlier in
`PATH`.

For a v1 assembled sample, verify the final delivery profile is exactly:

- 1080x1920, 25 fps, H.264 with `yuv420p` pixel format;
- AAC audio resampled to 48 kHz; and
- an embedded `mov_text` subtitle stream covering the declared dialogue timeline.

Voice and optional BGM files are explicit local imports. Generated SRT or other subtitle
derivatives remain local outputs. Neither their presence nor the use of silence authorizes a voice,
music, image or avatar Provider.

Active character and scene image versions are frozen into one exact content-addressed Asset Pack.
Only the reviewed, decoded, metadata-free PNG profile is admitted; an extension or claimed digest
does not make arbitrary bytes an approved image.

## 5. Score creative continuity

Have the editor and an independent reviewer score the frozen first-pass set. Their portable
reviewer references must differ, and each declaration binds a separately retained review-record
SHA-256. A conservative flag from either reviewer is retained. SDC does not authenticate either
reviewer or record; the report states this limitation instead of presenting the score as automated
or independently proven QC.

| Metric | Calculation | Gate |
|---|---|---|
| Critical identity breaks | Declared role not reasonably recognizable as the same role | 0 |
| Character continuity | Passing character appearances / all declared appearances | >= 90% |
| Scene continuity | Passing adjacent in-scene shot boundaries / all reviewed boundaries | >= 90% |
| Shot intent | Shots communicating the frozen intent without replacement / all first-pass shots | >= 80% |
| Artifact-free | Shots without reviewer-blocking visual or temporal artifacts / all first-pass shots | >= 90% |
| First-pass usable | Shots accepted without replacement / all first-pass shots | >= 75% |
| Duplicate media | Undeclared repeated digests across different shot IDs | 0 |
| Human effort | Review plus edit minutes / final sample minute | Always report; pilot target <= 60 |

Also record qualitative notes for face/hair/body continuity, wardrobe and props, lighting and
spatial continuity, camera-direction discontinuity, motion deformation, flicker, unintended text
or watermark, and narrative comprehension. These notes are evidence for a decision, not a claim
that automated detection exists.

## 6. Decide or create a new offline revision

Use exactly one outcome:

- `PASS_SAMPLE`: every hard gate and metric threshold passes;
- `REVISE_OFFLINE`: provenance and safety gates pass, but one or more creative thresholds need a
  replacement or edit using locally supplied media; or
- `STOP`: provenance is unknown or false, a fixture entered the scored set, a critical identity
  break remains, required evidence is missing, or continuation would cross the offline boundary.

A revision receives a new identity and records the canonical predecessor-manifest SHA-256. The
operator must retain the earlier manifest, metrics and reviewer notes; this v1 verifier does not
load or authenticate that predecessor. Within one revision, Attempt 2 retains the first and current
digests and is never first-pass usable. Do not use the lineage commitment alone to claim a verified
cross-revision first-pass history.

`PASS_SAMPLE` is a bounded local creative result only. It does not approve a model, certify a
person's likeness or rights, authorize publication, prove economic viability, or unlock Ark.

## 7. Preserve bounded local outputs

Keep the following local artifacts together without treating them as an authorization
EvidenceBundle:

- immutable imported-media manifest for each sample revision;
- technical inspection facts and file digests;
- metric numerator, denominator and threshold results;
- reviewer decisions, disagreements and reconciliation notes;
- declared edits and replacement lineage; and
- the assembled local sample, if one is produced.

The implementation writes to a new sibling staging directory, keeps an `INCOMPLETE` marker during
work, freezes every input used by FFmpeg, and publishes the completion report last into a new
output root. A failed stage or partial publication is preserved for `HUMAN_GATE`; it is never
silently resumed or overwritten. The offline verifier accepts only the exact file closure and
recomputes the sample/revision, import manifest, Asset Pack, assembly receipt, release, technical
QC, metrics and decision bindings. Synthetic end-to-end fixtures must finish as `STOP` with
`SYNTHETIC_FIXTURE_NOT_SCORED`, even when their technical profile passes.

Do not store Keys, secret locators, cookies, headers, signed URLs, raw account identifiers or
Provider response bodies/task IDs in these artifacts. Do not add their hashes to entitlement or
authorization registries.

## Future live batch boundary

If offline results justify a live experiment, stop this runbook and propose a separate one-batch
delivery. The proposal must bind one exact finite batch, all input and shot identities, a maximum
submission count and spend, Provider/model/account/region, expiry, runtime release, ledger and
crash recovery. It must receive independent evidence and activation approval current for that
batch.

One batch approval cannot be reused, extended or interpreted as permission for a retry batch.
Ambiguous or incomplete execution enters its defined human gate. This runbook supplies no live
command, no Key step and no authorization path.
