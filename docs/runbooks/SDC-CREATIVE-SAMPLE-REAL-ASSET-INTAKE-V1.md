# Creative Sample Real Asset Intake v1

This runbook defines the offline intake boundary for candidate media for `辞职信照旧`. It is a
contract and review guide, not permission to obtain media or execute a Provider. The only
admissible source is a local file set whose authority is exactly `USER_PROVIDED_LOCAL`, or media
generated in another separately approved task and locally delivered under
`SEPARATELY_APPROVED_LOCAL_GENERATION`. The second value does not approve generation in this task.
Discovery of a file on disk, a familiar filename or technical validity never implies consent,
provenance, rights or acceptance.

## Status and non-authority boundary

Real Asset Intake v1 prepares a *candidate* immutable media closure. A frozen pack is always
`FROZEN_UNREVIEWED`, `HUMAN_GATE` and `eligible_for_real_generation=false`. When all fourteen
members and both reviews per member close over the same bytes, the resulting revision may conclude
only `PASS_ASSET_INTAKE_ONLY`; it still remains `HUMAN_GATE`, `NOT_AUTHORIZED`,
`execution_authorized=false`, `posts_allowed=0` and `provider_requests=0`. Neither state is
Provider entitlement, live authorization, spend approval or permission to generate a sample.

The intake must remain offline and fail closed. It must not:

- search user directories, `output/`, `tmp/`, cloud drives, consoles or network locations for
  material; only the explicitly designated local intake root is in scope;
- accept a Synthetic fixture, placeholder, slate, colour block or test tone as real source media;
- read a Key, token, secret locator, cookie, account identifier or Provider environment setting;
- start Ark, a Worker, Temporal, PostgreSQL, a Provider adapter or any other service;
- create entitlement evidence, authorization, a positive-registry entry or a ledger claim;
- recharge, purchase, begin a trial, incur Provider spend or issue an HTTP request or `POST`; or
- commit private media, source documents, identities, signatures, account data, absolute local
  paths or secrets to Git.

Any missing input, uncertain source, technical failure, review gap, reviewer disagreement,
expiry or digest drift produces `STOP -> HUMAN_GATE`. No fallback asset, hidden conversion,
automatic approval or Provider call is permitted.

## Implemented offline interfaces and templates

`sdc.real_asset_media` performs bounded, pure-local PNG and WAV parsing. It has no subprocess or
network implementation. `sdc.real_asset_intake` owns the strict contracts and deterministic
template, submission, gap assessment, immutable freeze, verification, rights-manifest and
revision-qualification interfaces. Neither module imports a Provider, runtime, Worker, Temporal,
PostgreSQL, entitlement, authorization or ledger path.

The committed directory `examples/creative-sample-real-asset-intake-v1/` contains only two
non-private, zero-authority documents:

- `intake-template.json` binds the exact fourteen ordered requirements, the Pilot fixture
  denylist and `status=HUMAN_GATE`; and
- `gap-report.json` retains all fourteen rows as `MISSING`, with `missing_count=14`,
  `ready_for_rights_review=false`, `posts_allowed=0` and `provider_requests=0`.

An intake submission preserves the same fourteen rows in order. Each row is either `MISSING`, with
no source or byte claim, or `SUBMITTED`, with all four bindings: one of the two exact
`source_authority` values, SHA-256, positive byte length and provenance-record SHA-256. The
interface does not discover or infer these values. A partial submission can produce a gap report,
but cannot publish a candidate Asset Pack.

The public offline flow is deliberately narrow:

| Interface group | Responsibility |
|---|---|
| `build_real_asset_intake_template`, `build_real_asset_submission`, `build_real_asset_gap_report` | deterministic contracts with no file discovery |
| `load_real_asset_intake_template`, `load_real_asset_submission`, `load_real_asset_rights_manifest` | strict, canonical JSON loading for explicit paths |
| `assess_real_asset_submission` | local identity/technical assessment and fourteen-row gap output |
| `freeze_real_asset_candidate_pack`, `verify_real_asset_candidate_pack` | new-only publication and exact object/manifest re-verification |
| `build_real_asset_rights_manifest` | bind 28 caller-supplied reviews without granting authority |
| `qualify_real_asset_candidate_pack`, `verify_qualified_real_asset_revision` | derive or reproduce revision 2 after exact rights closure |
| `inspect_png`, `inspect_voice_wav`, `inspect_bgm_wav` | pure-local format and signal gates in `real_asset_media` |

## Exact fourteen-member closure

The candidate set is valid only when it contains one exact member for every row below and no
undeclared media member. The portable logical path is a role binding, not a discovery path. A
human explicitly maps a supplied local file to it; the intake never searches for a likely match.

| # | Portable logical path | Role | Frozen content binding |
|---:|---|---|---|
| 1 | `assets/characters/gu-yan/v1.png` | Gu Yan character reference board | one reviewed PNG |
| 2 | `assets/characters/su-qing/v1.png` | Su Qing character reference board | one reviewed PNG |
| 3 | `assets/scenes/office-night/v1.png` | architecture studio at night | one reviewed PNG |
| 4 | `assets/scenes/rooftop-dawn/v1.png` | rooftop at dawn | one reviewed PNG |
| 5 | `audio/voices/00.wav` | Su Qing, 6800–11600 ms | `辞职信在桌上。天亮前，我就走。` |
| 6 | `audio/voices/01.wav` | Gu Yan, 14000–15600 ms | `我不同意。` |
| 7 | `audio/voices/02.wav` | Su Qing, 20900–24800 ms | `项目都停了，你拿什么留我？` |
| 8 | `audio/voices/03.wav` | Gu Yan, 28900–32600 ms | `不是留你。跟我上天台。` |
| 9 | `audio/voices/04.wav` | Gu Yan, 36900–41800 ms | `三个月前，我把你的方案投进了城南改造终审。` |
| 10 | `audio/voices/05.wav` | Su Qing, 44100–46100 ms | `你没问过我。` |
| 11 | `audio/voices/06.wav` | Gu Yan, 50900–55600 ms | `所以今天不是替你决定，是请你自己选。` |
| 12 | `audio/voices/07.wav` | Gu Yan, 58900–62200 ms | `合伙人，或者自由建筑师。` |
| 13 | `audio/voices/08.wav` | Su Qing, 65700–70400 ms | `辞职信照旧。明天，我会以合伙人的身份回来。` |
| 14 | `audio/bgm/background.wav` | lyric-free 72-second score | one reviewed WAV |

The four images must depict only the fictional character or scene requirements frozen in the
Pilot Pack. They must not be photographs of an unconsenting private person. Each voice must bind
the declared fictional role and exact dialogue; changing the script is a new creative revision,
not an intake substitution. Music must contain no lyrics, samples or embedded third-party work
outside the reviewed rights basis.

## Immutable candidate Asset Pack

Intake treats the explicitly mapped source files as hostile until frozen and verified. For each
member it records, without embedding the private source record itself:

- the portable logical path and exact media role;
- lowercase SHA-256, positive byte length and declared media type;
- measured dimensions or measured audio duration, sample rate and channel count;
- a provenance-record SHA-256 and exact source authority—`USER_PROVIDED_LOCAL` or
  `SEPARATELY_APPROVED_LOCAL_GENERATION`; and
- a domain-separated technical-record SHA-256 over the media identity, technical profile and
  measured evidence.

The frozen manifest intentionally contains no approval. Its state is `FROZEN_UNREVIEWED`; the 28
review records live in a separately bound rights manifest with `status=REVIEW_CANDIDATE`.

Objects are addressed by their exact bytes. Publication is new-only and the manifest closes over
the exact object set; links, reparse points, non-regular files, path aliases and unexpected members
are rejected. A later verification re-reads each object and checks its digest, length and manifest
closure. Existing objects and manifests are never overwritten. A failed or interrupted staging
publication is cleaned up where possible and fails closed; it is not silently completed under the
same pack identity.

Each source is a stable, non-linked regular file with one hard-link count and a bounded opened-file
identity. PNG is capped at 16 MiB, each voice WAV at 4 MiB, BGM at 32 MiB and the complete pack at
256 MiB. All fourteen SHA-256 values must be distinct: one byte object cannot silently satisfy two
roles. The source root contains exactly the declared fourteen-file tree; the frozen pack contains
exactly `asset-pack.json` plus its fourteen content-addressed objects.

Source evidence, licenses, consent records and reviewer identities remain in the approved private
local evidence store. The candidate manifest may retain only portable pseudonymous references and
digests. It must not expose an absolute path, URL with credentials, email address, phone number,
government identifier, signature, account scope, secret locator or raw evidence document.

Freezing proves byte identity and mechanical technical admission only. It does not make a member
approved. A missing member has no object identity and stays `MISSING`; a present member can still
be technically rejected, review-pending or disputed. There is no partial-pack readiness state.

## Image technical and human gates

All four image roles use technical profile `strict-png-real-reference-v1`. Each source is at most
16 MiB. The technical report must bind the bytes before and after inspection and record all of
these checks:

- one decodable, non-interlaced 8-bit `RGB` or fully opaque `RGBA_OPAQUE` image with valid PNG
  signature, chunk lengths, CRCs, scanline filters and complete pixel closure;
- width and height each in the inclusive range 512–4096 pixels, with no more than 16,000,000
  total pixels; the measured values must match the manifest declaration;
- an exact `IHDR -> contiguous IDAT -> IEND` content profile, with no metadata, animation,
  attachment, external reference, trailing/polyglot data or embedded active content;
- fully opaque pixels, at least sixteen distinct decoded colours, no corrupt payload, decoder
  ambiguity or byte change during review; and
- a human privacy/creative inspection for real-person likeness, minors, biometric or personal
  data, documents, signatures, screens, logos, watermarks, readable text, third-party artwork and
  any material outside the declared character or scene role.

The mechanical record therefore fixes `active_content_absent=true` but deliberately retains
`semantic_privacy_reviewed=false`. Technical decoding cannot establish privacy, consent,
copyright or whether a face is fictional. Those findings require the two independent reviews
below. A technically valid image with an unresolved likeness or background element remains at
`HUMAN_GATE`.

## Audio technical and human gates

All ten audio roles use a canonical local RIFF/WAVE containing only an exact 16-byte `fmt ` chunk
followed by one `data` chunk. The admitted codec is little-endian signed PCM16 at exactly 48,000
Hz. Dialogue uses technical profile `pcm16-48khz-mono-dialogue-v1`, exactly one channel and at most
4 MiB. BGM uses `pcm16-48khz-stereo-score-72s-v1`, exactly two channels and at most 32 MiB. Block
alignment, byte rate, RIFF length, chunk order and padding must close over the exact file.

For each dialogue file, duration is at least 250 ms and no longer than its exact declared interval:
4800, 1600, 3900, 3700, 4900, 2000, 4700, 3300 and 4700 ms respectively for `00.wav` through
`08.wav`. The spoken words, speaker role and language must match the table above without
time-stretching or truncation. It must contain intelligible speech, useful head/tail room, no other
voice, watermark, prompt, music or private spoken information. Voice likeness, performer consent
and permitted synthetic-voice use are semantic rights/privacy questions and cannot be inferred
from waveform measurements.

The BGM frame count must cover exactly 72,000 ms. It must remain lyric-free and contain no
unreviewed sample. Any needed resampling, channel conversion, trimming, denoising or loudness
change creates new bytes, a new SHA-256 and a fresh technical and rights review rather than
modifying the frozen object.

The same mechanical envelope applies to every WAV: RMS from −40 to −6 dBFS inclusive, sample peak
from −30 to −0.1 dBFS inclusive, zero samples whose absolute value reaches 32767 and no more than
800,000 ppm (80%) samples in the `abs(sample) <= 327` silence band. The report stores these as
integer milli-dBFS and ppm. It fixes `semantic_content_reviewed=false`: mechanical thresholds do
not establish intelligible speech, exact words, speaker identity, lyric-free music or rights.
Both reviewers must separately approve the declared content role.

## Two independent rights and privacy reviews

Every one of the fourteen exact byte identities requires two review records. The reviewers must
be distinct people acting as `REVIEWER_A` and `REVIEWER_B`; neither role can be synthesized from a
single review, copied from the Pilot worksheet or inferred from a common approval reference.

Each record binds the candidate-pack ID, requirement and logical path, SHA-256, byte length,
provenance-record digest, technical-record digest, exact source authority, reviewer-reference
SHA-256, review-record SHA-256, review role and decision, plus all of these declarations:

- source authority and provenance are known and traceable in the private evidence store;
- copyright/license basis covers this exact media, territory, short-drama use, editing,
  compilation, internal evaluation and any proposed later generation/reference use;
- performer, voice, face and likeness consent is sufficient for the exact use, or the record
  affirmatively establishes that no real-person likeness is involved;
- privacy and personal-data review passes, including background details and spoken information;
- brands, logos, readable text, third-party works, music samples and other restrictions are
  disclosed and acceptable; and
- any start/end validity is explicit, unexpired for the proposed use and not broadened by this
  intake.

The rights manifest contains exactly 28 rows in canonical `REVIEWER_A`, `REVIEWER_B` pairs. Both
records must use `decision=APPROVED`, distinct reviewer-reference and review-record digests, and
agree on provenance, technical identity, source authority, copyright, likeness, privacy,
territory, use scope, content role and `valid_until`. `valid_until` is either `PERPETUAL` or an
exclusive UTC-second boundary; evaluation at or after it is expired. A future-dated review,
missing field, rejected review, disagreement, changed digest or unavailable retained record stays
at `HUMAN_GATE`. Review cannot be inherited by a replacement file, even when its role or filename
is unchanged.

The combined review is asset-use evidence only. It is not account entitlement, Ark evidence,
Provider authorization, ledger permission or approval to spend.

## New real-media specification and identities

The committed Pilot specification is fixture-only. Its
`SYNTHETIC_PLACEHOLDER_ONLY / TECHNICAL_COMPILATION_ONLY` envelope, placeholder asset versions,
sample identity, compilation identity, shot identities, pack identity, rehearsal results and
review placeholders are historical technical-fixture records and must remain unchanged.

Only after all fourteen exact members pass technical and double review may intake derive
real-asset revision 2. That derivation must:

1. create new immutable character and scene asset versions from the four reviewed PNG digests;
2. bind the nine exact WAV identities to their dialogue intervals and the reviewed BGM identity to
   the 72-second master clock;
3. emit an `IMPORTED_MEDIA` `CreativeSampleSpec` document binding the reviewed Asset Pack and
   rights manifest with `approval_scope=PASS_ASSET_INTAKE_ONLY`;
4. recompile NIR/PIR so the new asset-version bindings produce a new compilation ID and new shot
   IDs; and
5. retain explicit predecessor references only for audit, never as inherited approval or ID
   material.

The new specification, Pilot revision, compilation and every shot must be unequal to the fixture
identities. Equality, a reused placeholder digest, missing review closure or any failure to
recompute descendants is a hard error and enters `HUMAN_GATE`. Dialogue and creative direction may
remain textually unchanged, but that does not permit reuse of fixture asset, sample, compilation
or shot identities.

The qualified directory closes over exactly `creative-sample-spec.json`, `rights-manifest.json`
and `real-asset-revision.json`. Its decision is `PASS_ASSET_INTAKE_ONLY` and
`eligible_for_separate_provider_approval=true`; it does not change `NOT_AUTHORIZED`, leave
`HUMAN_GATE`, enable a Provider or turn any planned request ceiling into permission.

## Gap and replacement report

The offline gap report contains exactly fourteen rows and never omits an unresolved member. Its
row disposition is exactly one of `MISSING`, `IDENTITY_MISMATCH`, `TECHNICAL_REJECTED`,
`REVIEW_PENDING`, `DISPUTED`, `EXPIRED` or `APPROVED`, with bounded failures and replacement
guidance. `rejected_count` combines identity mismatch, technical rejection, dispute and expiry;
missing, pending and approved have separate counts. The report always remains `HUMAN_GATE`,
`ready_for_rights_review=false`, `posts_allowed=0` and `provider_requests=0`.

Permitted replacement guidance is role-specific and non-executing:

- a character or scene image may be replaced only by another explicitly supplied PNG satisfying
  the same frozen creative role;
- a voice may be replaced only by another explicitly supplied WAV for the same speaker, exact
  text and time interval;
- BGM may be replaced only by another explicitly supplied, lyric-free 72-second WAV; and
- any edit or conversion of an existing member is treated as a separately supplied replacement.

The report never downloads, generates or chooses a replacement. It never promotes `MISSING`,
`IDENTITY_MISMATCH`, `TECHNICAL_REJECTED`, `REVIEW_PENDING`, `DISPUTED` or `EXPIRED` to
`APPROVED`. Each replacement gets a new digest, provenance record, technical report, two review
records, pack identity and downstream identity derivation.

## Offline state transition

```text
explicit fourteen-row mapping: MISSING or SUBMITTED
  -> exact local technical inspection
  -> immutable fourteen-object freeze: FROZEN_UNREVIEWED / HUMAN_GATE
  -> immutable closure verification and technical-evidence reproduction
  -> 28-row rights manifest: REVIEW_CANDIDATE / HUMAN_GATE
  -> reviewer A + reviewer B both APPROVED on every object
  -> exact fourteen-member closure
  -> revision 2: PASS_ASSET_INTAKE_ONLY / HUMAN_GATE / NOT_AUTHORIZED
  -> new real-media spec/compilation/shot identities
  -> candidate handoff for a separately approved task

any gap, drift, failure, expiry or disagreement
  -> STOP -> HUMAN_GATE
```

There is no transition from intake to a Provider request. A later real sample task must separately
approve its exact Provider/model, account scope, entitlement evidence, authorization, cost and
request bounds, runtime release, Task Queue, ledger/deployment identities and task ownership. That
task must begin from the newly reviewed real-media identities and retain the permanent
`SUBMISSION_UNKNOWN -> HUMAN_GATE` no-repost rule.

## Completion conditions for this task

- The contract covers exactly four PNG and ten WAV roles; missing media remains visible and
  fail-closed.
- Source authority is exactly `USER_PROVIDED_LOCAL` or
  `SEPARATELY_APPROVED_LOCAL_GENERATION`; neither value is inferred.
- Every admitted object is immutable and bound by SHA-256, byte length, type, technical evidence,
  provenance-record digest and portable logical path.
- Image checks enforce 512–4096 RGB/opaque-RGBA PNG with at least 16 colours; audio checks enforce
  PCM16/48 kHz, mono dialogue, exact 72-second stereo BGM, RMS/peak, zero clipping and bounded
  silence.
- Every member requires two independent, byte-bound rights/privacy reviews; disagreement or
  expiry enters `HUMAN_GATE`.
- Complete real inputs derive revision 2, new spec, compilation and shot identities with only
  `PASS_ASSET_INTAKE_ONLY`; they inherit no fixture approval or digest.
- Git contains only contracts, validators, non-private templates, documentation and tests—not
  private source media or evidence.
- No Key, network, service, Ark/console access, entitlement, authorization, spend, Provider request
  or HTTP `POST` is part of Real Asset Intake v1.
