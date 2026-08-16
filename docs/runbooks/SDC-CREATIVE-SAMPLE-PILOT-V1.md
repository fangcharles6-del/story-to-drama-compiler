# Creative Sample Pilot Pack v1 (design only)

This runbook freezes the content plan for the first evaluable short-drama sample. It is a design
and offline-rehearsal artifact, not an instruction to generate media. The story is titled
`辞职信照旧` (`The Resignation Still Stands`) and uses only fictional adult characters.

## Status and hard boundary

The pack is `DESIGN_ONLY`. Its committed `CreativeSampleSpec` binds synthetic placeholder PNGs so
that deterministic compilation and FFmpeg mechanics can be rehearsed. Those placeholder digests,
asset-version IDs, derived shot IDs and pack ID must never be relabeled as real creative evidence.

The machine file `creative-sample-spec.json` is not a bare legacy spec. It is a strict
`sdc.creative-sample-pilot-spec` envelope whose `source_mode=SYNTHETIC_PLACEHOLDER_ONLY`,
`fixture_admission_scope=TECHNICAL_COMPILATION_ONLY` and
`eligible_for_real_generation=false`. The embedded legacy asset provenance means only that the
fixture bytes are admitted to the existing compiler shape; it does not assert real-media rights,
content approval or Provider eligibility. A consumer that ignores the envelope must fail parsing
rather than treating the placeholder spec as a normal imported-media spec.

When separately reviewed real assets become available, create and review a new specification and
Asset Pack from their exact bytes. Recompute every content digest and derived ID, compile a new
sample identity and retain the placeholder pack only as fixture history. Do not overwrite a
placeholder file, substitute bytes under an existing digest or inherit its approval reference.

This task provides no permission to:

- read a Key, secret locator, account identifier, cookie or Provider session;
- start a Worker, Temporal, PostgreSQL, Ark adapter or other service;
- access Ark, its console or any external generation service;
- create entitlement or authorization evidence, edit a positive registry or consume a ledger
  claim;
- recharge, buy, start a trial or incur spend; or
- issue a Provider request or HTTP `POST`.

Stop at `HUMAN_GATE` if any requested action crosses that boundary. No command in this runbook
starts a live or remote action.

## Frozen sample shape

| Property | Frozen value |
|---|---|
| Title | `辞职信照旧` |
| Seed | `20260816` |
| Duration | exactly `72000 ms` |
| Delivery | 9:16, 1080x1920, 25 fps, H.264/yuv420p, AAC 48 kHz |
| Characters | exactly 2 recurring fictional adults |
| Scenes | exactly 2 contiguous scene blocks |
| Shots | exactly 10, contiguous from zero with no gap or overlap |
| Dialogue | 9 non-overlapping lines, each bound to exactly one shot |

The first 36 seconds take place in the architecture studio. The final 36 seconds take place on
the roof of the same building. The narrative moves from resignation, through confrontation and
revelation, to a choice: Su Qing resigns as an employee but returns as a partner.

### Character bibles

The names and descriptions below are canonical inputs to `CharacterBible.derive_id`. At
serialization time, character bibles and every multi-character shot reference are sorted by the
actual derived `character_id`, not by the aliases in this document.

| Alias | Name | Canonical visual description | Wardrobe token |
|---|---|---|---|
| `C_SU` | 苏晴 | 28岁成年中国女性，椭圆脸，深棕色眼睛，黑色低马尾，身形匀称，神态克制；全片固定穿象牙白无标识衬衫、炭灰色直筒裤和黑色平底鞋，不佩戴首饰；自然妆容，无纹身、品牌标志或可读文字。 | `ivory-blouse-charcoal-trousers-black-flats-low-ponytail` |
| `C_GU` | 顾言 | 32岁成年中国男性，短黑发，深棕色眼睛，轮廓清晰，身形修长，表达冷静；全片固定穿海军蓝无标识工作夹克、浅灰色衬衫和炭灰色长裤，不打领带；无胡须、首饰、品牌标志或可读文字。 | `navy-work-jacket-light-gray-shirt-charcoal-trousers` |

Each character has one active version-1 PNG. The reference board should show front and
three-quarter facial views plus half- and full-body proportions under neutral lighting. It must
not be made from a real private person's photograph.

### Scene bibles

| Alias / ordinal | Name | Canonical visual description |
|---|---|---|
| `S_OFFICE` / 0 | 建筑工作室深夜 | 当代小型建筑工作室深夜，深灰水泥地面、浅木工作桌、玻璃门和落地窗，窗外为雨后虚化城市灯光；4300K冷白顶灯为主光，画面右后方有一盏2700K暖色台灯；空间整洁，无品牌、标识、屏幕内容或可读文字。 |
| `S_ROOFTOP` / 1 | 同楼屋顶清晨 | 同一建筑屋顶的清晨蓝调时刻，浅灰混凝土地面、腰高深灰女儿墙、远处无品牌城市天际线，暖色地平线位于画面右后方；无广告牌、车辆、其他人物或可读文字。 |

The fixed screen direction in both scenes places Su Qing on camera left and Gu Yan on camera
right. Do not cross the 180-degree line. On the roof, both characters remain at least 1.5 metres
inside the parapet; the story must not imply climbing, falling or self-harm.

### Props and state continuity

Only two canonical prop tokens are used. Tuples containing both use this sorted order:
`("blue-partner-folder", "cream-envelope")`.

- The cream, unmarked envelope is placed on the desk by Su Qing's right hand in Shot 0, remains
  there through Shot 3, and returns to her right hand in Shot 4 through the end.
- The cobalt-blue, unmarked folder enters in Gu Yan's left hand in Shot 2. He places it on the
  roof platform in Shot 7, pushes it to a neutral midpoint and fully withdraws in Shot 8, and Su
  Qing picks it up with her left hand in Shot 9.
- No page, envelope, screen or environmental surface may contain readable generated text, a logo
  or a watermark.

## Frozen dialogue timeline

`line_id` values are derived with the existing `DialogueLine.derive_id`. Dialogue ordinals are
contiguous and each interval lies wholly inside the one shot that references it.

| Alias / ordinal | Shot | Character | Start | End | Exact subtitle text |
|---|---:|---|---:|---:|---|
| `D00` / 0 | 1 | 苏晴 | 6800 | 11600 | 辞职信在桌上。天亮前，我就走。 |
| `D01` / 1 | 2 | 顾言 | 14000 | 15600 | 我不同意。 |
| `D02` / 2 | 3 | 苏晴 | 20900 | 24800 | 项目都停了，你拿什么留我？ |
| `D03` / 3 | 4 | 顾言 | 28900 | 32600 | 不是留你。跟我上天台。 |
| `D04` / 4 | 5 | 顾言 | 36900 | 41800 | 三个月前，我把你的方案投进了城南改造终审。 |
| `D05` / 5 | 6 | 苏晴 | 44100 | 46100 | 你没问过我。 |
| `D06` / 6 | 7 | 顾言 | 50900 | 55600 | 所以今天不是替你决定，是请你自己选。 |
| `D07` / 7 | 8 | 顾言 | 58900 | 62200 | 合伙人，或者自由建筑师。 |
| `D08` / 8 | 9 | 苏晴 | 65700 | 70400 | 辞职信照旧。明天，我会以合伙人的身份回来。 |

Voice imports are individual local WAV files, one per dialogue line. Use an adult, natural,
restrained delivery. The exact text above becomes the subtitle track; do not add speaker labels,
paraphrases or generated on-screen titles.

## Shot plan and acceptance criteria

Every shot binds the active scene asset and exactly the active assets for its declared characters.
The scene asset and each named character asset are required even when a character appears only as
an over-shoulder foreground anchor. `dialogue_line_ids` retain dialogue ordinal order.

### Shot 0 — resignation hook

- **Clock:** `start_ms=0`, `duration_ms=6000`; `S_OFFICE`; `C_SU`; no dialogue.
- **Narrative / visual direction:** the resignation envelope lands on the desk before its reason is
  explained. From a high static close-up, Su Qing's right hand places the cream envelope on the
  left-front portion of the light wood desk, long edge parallel to the desk edge; her recognizable
  face remains in shallow-focus background.
- **Creative fields:** emotion `克制、疲惫，但决定已经做出，不哭泣`; action `右手放下信封，停顿半秒后收回`;
  `CLOSE_UP / HIGH_ANGLE / STATIC`; fixed wardrobe; props `("cream-envelope",)`.
- **Audio / post:** no voice; restrained room tone and one piano note; hard cut at 6000 ms.
- **Reject:** a solid/static card, late hook, malformed hand or envelope, readable text, extra
  person, logo or watermark.
- **First-pass usable:** the action completes in the first two seconds; identity, hand anatomy and
  final prop location pass. This first scene shot uses `scene_continuity_pass=null`.

### Shot 1 — the decision

- **Clock:** `start_ms=6000`, `duration_ms=7000`; `S_OFFICE`; `C_SU`; `D00`.
- **Narrative / visual direction:** eye-level static medium close-up, Su Qing on camera left with
  the envelope in foreground. She looks from the envelope to the door, says the line, then closes
  her mouth.
- **Creative fields:** emotion `平静外表下的失望，尾句坚定`; action `看信封后抬眼望向右侧门口并说完对白`;
  `MEDIUM_CLOSE_UP / EYE_LEVEL / STATIC`; fixed wardrobe; `("cream-envelope",)`.
- **Audio / post:** restrained adult female voice; exact D00 subtitle; BGM remains minimal.
- **Reject:** face, hair, wardrobe or eye flicker; lip mismatch; moving envelope; an off-camera
  speaker rendered on screen.
- **First-pass usable:** Su Qing remains recognizable, the sentence is complete and intelligible,
  and the prop and screen direction match Shot 0.

### Shot 2 — Gu Yan enters

- **Clock:** `start_ms=13000`, `duration_ms=7000`; `S_OFFICE`; `C_GU`, `C_SU`; `D01`.
- **Narrative / visual direction:** an eye-level medium shot slowly dollies as Gu Yan enters one
  step through the right-rear glass door and stops. He holds the blue folder at his left side;
  Su Qing is a left-foreground back/shoulder anchor.
- **Creative fields:** Gu Yan `错愕后压住焦急`, Su Qing `戒备，不回头`; action `顾言入门、停步并说话，苏晴保持静止`;
  `MEDIUM / EYE_LEVEL / DOLLY`; fixed wardrobes; both props.
- **Audio / post:** calm, low adult male voice; exact D01 subtitle; introduce a quiet low pulse.
- **Reject:** an extra person, door or folder teleportation, folder changing hands, Su Qing moving
  her mouth, or a line-axis reversal.
- **First-pass usable:** both identities are stable, Gu Yan is the only speaker and the folder is
  consistently cobalt blue in his left hand.

### Shot 3 — challenge

- **Clock:** `start_ms=20000`, `duration_ms=8000`; `S_OFFICE`; `C_GU`, `C_SU`; `D02`.
- **Narrative / visual direction:** static eye-level medium close-up over Gu Yan's shoulder. Su
  Qing turns about 45 degrees, questions him, and holds eye contact; Gu Yan listens without
  speaking.
- **Creative fields:** Su Qing `压抑的愤怒与失望`, Gu Yan `克制倾听，不辩解`; action `苏晴转身、质问并停住，顾言闭口`;
  `MEDIUM_CLOSE_UP / EYE_LEVEL / STATIC`; fixed wardrobes; both props.
- **Audio / post:** female voice slightly quicker but articulated; exact D02 subtitle; pulse rises
  slightly.
- **Reject:** both mouths moving, bad eyeline, line crossing, identity drift or a foreground
  shoulder turning into a third person.
- **First-pass usable:** the confrontation is legible, only Su Qing speaks, and face, space and
  prop continuity pass.

### Shot 4 — invitation upstairs

- **Clock:** `start_ms=28000`, `duration_ms=8000`; `S_OFFICE`; `C_GU`, `C_SU`; `D03`.
- **Narrative / visual direction:** eye-level medium two-shot with a restrained dolly. Gu Yan speaks
  from camera right. After he finishes, Su Qing retrieves the envelope with her right hand while
  Gu Yan, still holding the folder in his left, turns toward the door.
- **Creative fields:** Gu Yan `坦诚、急切但不施压`, Su Qing `不信任中出现轻微动摇`; action `顾言说话后转身，苏晴右手取信封`;
  `MEDIUM / EYE_LEVEL / DOLLY`; fixed wardrobes; both props.
- **Audio / post:** steady male voice; exact D03 subtitle; leave action room after the line; hard
  cut to the roof at 36000 ms.
- **Reject:** hand intersection, premature prop pickup, either prop changing hands, character
  position reversal or Su Qing lip motion during Gu Yan's line.
- **First-pass usable:** dialogue, envelope pickup and turn are three distinct beats and establish
  the exact cross-scene prop state.

### Shot 5 — rooftop reveal

- **Clock:** `start_ms=36000`, `duration_ms=7000`; `S_ROOFTOP`; `C_GU`, `C_SU`; `D04`.
- **Narrative / visual direction:** eye-level wide establishing shot with a slow dolly. Gu Yan is
  on camera right with folder in left hand; Su Qing is on the left with envelope in right hand.
  Both stay at least 1.5 metres inside the parapet while Gu Yan reveals the submission.
- **Creative fields:** Gu Yan `谨慎揭示事实并准备承担后果`, Su Qing `警惕观察`; action `两人停下，顾言面对苏晴说话`;
  `WIDE / EYE_LEVEL / DOLLY`; fixed wardrobes; both props.
- **Audio / post:** clearly paced male voice; exact D04 subtitle; music opens into a warm pad.
- **Reject:** unsafe edge behaviour, extra people, lost wardrobe/props, wrong weather, readable
  skyline signage or scene substitution.
- **First-pass usable:** the roof reads immediately and all identities, wardrobe and prop states
  survive the scene cut. This first rooftop shot uses `scene_continuity_pass=null`.

### Shot 6 — objection

- **Clock:** `start_ms=43000`, `duration_ms=7000`; `S_ROOFTOP`; `C_SU`; `D05`.
- **Narrative / visual direction:** static eye-level close-up. Su Qing looks briefly toward the
  off-screen-right folder, then at Gu Yan and objects without melodrama.
- **Creative fields:** emotion `意外、被冒犯，同时产生好奇`; action `轻吸气、说短句，右手信封保持不动`;
  `CLOSE_UP / EYE_LEVEL / STATIC`; fixed wardrobe; both props remain declared for state continuity.
- **Audio / post:** short questioning female line; exact D05 subtitle; lower the music under speech.
- **Reject:** exaggerated crying, identity drift, reversed background light, the envelope changing
  hands or the off-screen folder appearing in her possession.
- **First-pass usable:** the reaction is natural and recognizable, voice is clear and the roof
  boundary remains continuous.

### Shot 7 — choice returned

- **Clock:** `start_ms=50000`, `duration_ms=8000`; `S_ROOFTOP`; `C_GU`, `C_SU`; `D06`.
- **Narrative / visual direction:** static eye-level medium close-up over Su Qing's shoulder. Gu
  Yan places the folder on the inside platform, holds its left edge with his left hand and opens
  it with his right. Pages remain unmarked and unreadable.
- **Creative fields:** Gu Yan `坦诚、带歉意、愿意承担后果`, Su Qing `逐渐理解但仍克制`; action `顾言放下并打开文件夹后说话，苏晴不触碰`;
  `MEDIUM_CLOSE_UP / EYE_LEVEL / STATIC`; fixed wardrobes; both props.
- **Audio / post:** slower, non-coercive male delivery; exact D06 subtitle; retain only a soft pad.
- **Reject:** generated document text, malformed pages/hands, folder colour drift, Su Qing grabbing
  the folder or threatening posture.
- **First-pass usable:** the folder transfer to the platform is complete, Gu Yan is the only
  speaker and the apology/choice intent is clear.

### Shot 8 — two options

- **Clock:** `start_ms=58000`, `duration_ms=7000`; `S_ROOFTOP`; `C_GU`, `C_SU`; `D07`.
- **Narrative / visual direction:** static eye-level medium-wide two-shot. Gu Yan closes the folder,
  slides it to the neutral midpoint and fully withdraws his hand. Su Qing does not touch it yet.
- **Creative fields:** Gu Yan `释然，把选择权交出`, Su Qing `犹豫开始转为坚定`; action `顾言说完选项、推文件夹并撤手，苏晴只看文件夹`;
  `MEDIUM_WIDE / EYE_LEVEL / STATIC`; fixed wardrobes; both props.
- **Audio / post:** calm male line with a natural pause between options; exact D07 subtitle; music
  begins its resolution.
- **Reject:** simultaneous handoff, hand fusion, folder teleportation, failure to withdraw,
  line-axis reversal or unsafe edge placement.
- **First-pass usable:** both choices are intelligible and the folder ends stationary between the
  characters with neither person touching it.

### Shot 9 — new identity

- **Clock:** `start_ms=65000`, `duration_ms=7000`; `S_ROOFTOP`; `C_GU`, `C_SU`; `D08`.
- **Narrative / visual direction:** eye-level medium close-up with a slow dolly. Su Qing picks up the
  folder with her left hand while keeping the envelope in her right, delivers the final line and
  looks toward the dawn with only a slight smile. Gu Yan's right-side shoulder anchors the frame.
- **Creative fields:** Su Qing `坚定、释然，笑意极轻`, Gu Yan `松一口气但不抢戏`; action `苏晴左手拿文件夹后说话，顾言闭口静听`;
  `MEDIUM_CLOSE_UP / EYE_LEVEL / DOLLY`; fixed wardrobes; both props.
- **Audio / post:** female delivery moves from restraint to confidence; exact D08 subtitle; resolve
  the chord after 70400 ms and hold a stable final image until exactly 72000 ms.
- **Reject:** a missing or switched prop, both people speaking, exaggerated smile, identity/hair
  drift, hand fusion or generated title text.
- **First-pass usable:** dialogue and pickup occur in order, both props have their final hands,
  character identity remains stable and the final hold is clean.

## Audio and assembly plan

- Import one local 48 kHz PCM WAV for each dialogue line. The measured voice duration must fit its
  declared interval; silence outside the line is not a reason to move the master-clock cue.
- Su Qing uses a natural adult female mid-low register without an exaggerated crying voice. Gu
  Yan uses a calm adult male mid-low register without a commanding or romanticized delivery.
- Import at most one separately reviewed 72-second WAV for music: lyric-free sparse piano from
  0–13 seconds, a quiet low pulse through 36 seconds, a warm pad through 58 seconds and a restrained
  harmonic resolution at the end. Record its rights evidence separately.
- Generate subtitles only from the exact dialogue table. Assembly uses hard cuts, the fixed 48 kHz
  master and embedded `mov_text`; it adds no generative title, interpolation or remote effect.

## Asset Pack and rights worksheet

The planning worksheet has exactly four intended active image members. It is not yet an admitted
real Asset Pack.

| Intended logical path | Kind | Submission | Rights | Privacy | Real generation eligible |
|---|---|---|---|---|---|
| `assets/characters/su-qing/v1.png` | character | `NOT_SUBMITTED` | `PENDING_REVIEW` | `PENDING_REVIEW` | `false` |
| `assets/characters/gu-yan/v1.png` | character | `NOT_SUBMITTED` | `PENDING_REVIEW` | `PENDING_REVIEW` | `false` |
| `assets/scenes/office-night/v1.png` | scene | `NOT_SUBMITTED` | `PENDING_REVIEW` | `PENDING_REVIEW` | `false` |
| `assets/scenes/rooftop-dawn/v1.png` | scene | `NOT_SUBMITTED` | `PENDING_REVIEW` | `PENDING_REVIEW` | `false` |

The machine rights template contains 14 unfilled rows: these four intended images, nine dialogue
WAV files and one BGM WAV file. Every row can later bind an exact SHA-256, byte length, provenance
record, source category, rights basis, territory, scope, privacy basis and two distinct review
records with distinct digests. In this committed pack all such values are absent, every decision is `PENDING_REVIEW`
and every real-generation eligibility flag is `false`.

For each future file, the rights worksheet must record, outside committed private data:

- a portable asset reference, exact local SHA-256 and byte length;
- non-empty canonical `source_category`, rights basis, territory, media/use scope and likeness/privacy
  basis; optional expiry is an exact calendar date or UTC-second timestamp;
- likeness/privacy basis and confirmation that the depicted characters are fictional adults;
- prohibited brands, logos, third-party works and readable personal data;
- reviewer A and reviewer B decisions as separately hashed local review records; and
- final `APPROVED` or `REJECTED`, never inferred from a filename or appearance.

Until every field is reviewed, retain the states in the table. Do not commit a URL, raw identity,
signature, account field, private image, secret locator or license document. A rights worksheet is
not Provider entitlement or live authorization.

## Two-reviewer worksheet

The real-media worksheet begins `UNFILLED`; the design pack contains no review outcome. It must
eventually contain exactly two distinct rows per shot: `EDITOR` and `INDEPENDENT`. Each row binds
the frozen shot digest and a separately retained review-record digest.

| Field | Required rule before scoring |
|---|---|
| `shot_id`, `media_sha256` | Exact compiled shot and admitted bytes |
| `review_role` | `EDITOR` or `INDEPENDENT`; exactly one of each |
| `reviewer_ref`, `review_record_sha256` | Distinct portable refs; both currently `UNFILLED` |
| `first_pass_usable` | `true` only for accepted Attempt 1 bytes |
| `shot_intent_pass`, `artifact_free` | Explicit boolean from each reviewer |
| `character_continuity` | Exact key closure for characters declared in that shot |
| `scene_continuity_pass` | `null` only for Shots 0 and 5; boolean for every other shot |
| `critical_identity_break` | Conservative OR across reviewers; any `true` stops the sample |
| `failure_codes`, `notes` | Canonical codes plus bounded non-sensitive observations |
| `human_review_ms`, `human_edit_ms` | Measured milliseconds; presentation may convert to minutes |

For `first_pass_usable=true`, both reviewers must also pass shot intent, artifact freedom, every
declared character appearance and the applicable scene boundary, with no identity break. A
replacement is `attempts=2` and cannot be reported as first-pass usable. Reviewer disagreement is
recorded and enters `HUMAN_GATE`; it is not silently resolved by the editor.

## Metrics worksheet

All real-sample values below remain `UNFILLED` until exact `IMPORTED_MEDIA` bytes and two review
records per shot exist. The committed synthetic rehearsal cannot populate them.

| Metric | Frozen denominator / calculation | Pass gate | Initial value |
|---|---|---:|---|
| First-pass usable | accepted Attempt-1 shots / 10 | >= 8/10 | `UNFILLED` |
| Character continuity | passing appearances / 17 (Su Qing 10, Gu Yan 7) | >= 16/17 | `UNFILLED` |
| Scene continuity | passing in-scene boundaries / 8 | 8/8 | `UNFILLED` |
| Shot intent | passing shots / 10 | >= 8/10 | `UNFILLED` |
| Artifact-free | passing shots / 10 | >= 9/10 | `UNFILLED` |
| Critical identity breaks | conservative reviewer OR | 0 | `UNFILLED` |
| Duplicate media | repeated final shot digests not explicitly allowed | 0 | `UNFILLED` |
| Average attempts | sum of attempts / 10, range 1–2 | report | `UNFILLED` |
| Total elapsed | first admitted work to final local report | report | `UNFILLED` |
| Human review/edit | separately measured minutes | report | `UNFILLED` |
| Cost | sum of admitted per-shot costs in CNY | report | `UNFILLED` |
| Failures | counts by the taxonomy below | report | `UNFILLED` |

The scene-boundary denominator is eight: Shots 1–4 and 6–9. Shots 0 and 5 begin scenes and have no
prior in-scene boundary.

The pack also carries ten fillable shot-work rows. A completed row binds its `source_mode`, Attempt
count, first and final media digests, Provider-request count, Provider cost in CNY microunits,
measured human edit milliseconds and canonical failure codes. `IMPORTED_MEDIA` rows require zero
Provider requests and zero Provider cost; `PROVIDER_GENERATED` rows require one request per Attempt.
The committed rows are all `UNFILLED`; they are record templates, not estimates or authority. The
frozen delivery profile is part of the pack identity:
1080x1920 (9:16), 25 fps, H.264/yuv420p, AAC stereo at 48 kHz, embedded `mov_text`, MP4.

## Failure taxonomy

Use only canonical lower-case codes. More than one code may bind a failed shot.

| Code | Meaning | Required disposition |
|---|---|---|
| `content.identity_break` | A declared person is no longer recognizably the same character | `STOP` and `HUMAN_GATE` |
| `content.character_drift` | Face, hair, age, body or declared role drifts without a critical break | fail continuity |
| `content.scene_drift` | Location, lighting direction or spatial axis changes incorrectly | fail scene continuity |
| `content.wardrobe_drift` | Fixed wardrobe changes, gains a logo or changes colour | fail continuity |
| `content.prop_drift` | Envelope/folder state, colour, position or hand is wrong | fail intent/continuity |
| `content.dialogue_lipsync` | Wrong speaker, extra mouth motion or blocking sync failure | fail intent |
| `content.shot_intent` | Frozen narrative/action/camera intent is not communicated | fail intent |
| `artifact.face` | Face deformation, flicker or temporal instability | fail artifact-free |
| `artifact.hand` | Hand deformation, fusion or impossible prop interaction | fail artifact-free |
| `artifact.text_or_watermark` | Unintended readable text, logo or watermark | reject media |
| `artifact.extra_person` | Undeclared person or person-like foreground appears | reject media |
| `artifact.static_or_placeholder` | Static/solid fixture or slate is presented as content | `STOP` |
| `artifact.duplicate_media` | Two shot IDs use undeclared identical final bytes | `STOP` |
| `audio.voice_quality` | Unintelligible, wrong adult role or materially artificial delivery | fail usable |
| `audio.subtitle_timing` | Text or timing differs from the frozen dialogue | fail technical QC |
| `audio.bgm_rights` | Music rights are absent, unclear or expired | `STOP` and `HUMAN_GATE` |
| `technical.duration` | Media or assembled master misses its exact clock | fail technical QC |
| `technical.frame` | Wrong aspect, dimensions, fps, pixel format or decodability | fail technical QC |
| `review.disagreement` | Reviewers differ on any scored declaration | record and `HUMAN_GATE` |
| `rights.unverified` | Content or likeness rights are incomplete | `STOP` and `HUMAN_GATE` |
| `provenance.unverified` | Source cannot be bound to a retained local provenance record | `STOP` |

No failure code authorizes a hidden retry. Attempt history, replacement bytes and reviewer records
remain explicit.

## Synthetic technical rehearsal

One repeatable local rehearsal may exercise the 72-second clock, ten-shot assembly, nine voice
cues, subtitles, 48 kHz master, FFmpeg delivery profile, report closure and independent verifier.
It must satisfy all of the following:

- every asset, shot, voice and BGM import is `SYNTHETIC_FIXTURE`;
- moving test-grid/timecode/slate material is visibly synthetic and is not ten solid-colour clips;
- it is never described, screened or scored as the content sample above;
- `provider_requests=0`, `posts_allowed=0` and no network-capable implementation is constructed;
- the final decision is `STOP` with human-facing status `NOT_SCORED` and machine metric status
  `NOT_SCORED_FIXTURE`; and
- any technically passing result proves assembly mechanics only, not character continuity,
  creative quality, rights, cost or Provider readiness.

Fixture-only reviewer fields, if required to exercise serialization, are test declarations and
must remain distinguishable from the `UNFILLED` real-review worksheet. They cannot be copied into
a future imported-media manifest.

## Proposed finite Provider batch — NOT_AUTHORIZED

The following numbers are a planning ceiling for a later, separately approved task. They grant no
authority and are intentionally fail-closed now.

| Boundary | Proposed value now |
|---|---|
| Mode | `NOT_AUTHORIZED` |
| Exact shots | 10 |
| Maximum Attempts per shot | 2 |
| Planned maximum requests | 20 |
| Proposed aggregate cost ceiling | CNY 450 |
| Current `posts_allowed` | 0 |
| Current gate | full `HUMAN_GATE` |

A future proposal would need to bind a newly frozen real spec and Asset Pack, exact Provider/model,
account scope, region, operation, request fingerprints, current entitlement evidence, reviewed
authorization, database-UTC expiry, runtime release, Task Queue, ledger identity, deployment
identity and task-ID ownership. It must also define whether fewer than 20 requests are authorized;
the planning maximum is not permission to consume them.

Even after separate approval, stop without another `POST` when any of the following occurs:

- request count reaches 20, cost reaches CNY 450 or any shot reaches Attempt 2;
- authorization/evidence expires, a digest or runtime binding changes, or rights become unclear;
- a critical identity break, privacy/compliance issue or unresolved reviewer disagreement occurs;
- a submit result is unknown, a `POST_IN_FLIGHT` claim lacks a safely persisted owned task ID, or
  any ownership/ledger row is partial or conflicting; or
- technical import, immutable closure or final verification fails.

Submission-unknown follows the existing permanent `SUBMISSION_UNKNOWN -> HUMAN_GATE` rule and is
never repaired with a replacement POST. This Pilot Pack neither creates that future authorization
nor changes the empty positive registries or Ark runtime hard block.

## Completion checklist for this design task

- The 72-second story, ten-shot clock and two contiguous scene blocks are frozen.
- Every shot declares narrative, visual, emotion, action, camera, wardrobe, props, continuity,
  asset needs, sound/post direction, rejection conditions and first-pass criteria.
- Asset/rights and double-review worksheets remain pending and unfilled.
- Real creative metrics remain unfilled; a fixture rehearsal is forced to `STOP / NOT_SCORED`.
- The proposed 20-request/CNY-450 Provider batch remains `NOT_AUTHORIZED` with zero POSTs.
- No Key, service, Ark access, live authorization, spend or Provider request is part of this task.
