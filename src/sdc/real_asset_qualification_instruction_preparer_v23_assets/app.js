(() => {
  "use strict";

  const CONTEXT_GLOBAL = "SDC_QUALIFICATION_INSTRUCTION_CONTEXT";
  const CONTEXT_SCHEMA_VERSION = "2.3.0";
  const CONTEXT_DOCUMENT_TYPE = "sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3";
  const DRAFT_DOCUMENT_TYPE = "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3";
  const PROFILE = "creative-sample-real-asset-qualification-instruction-preparation-v2.3";
  const POLICY_ID = "creative-sample-real-asset-qualification-policy";
  const POLICY_VERSION = "2.0.0";
  const POLICY_DOCUMENT_SHA256 = "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031";
  const DRAFT_FILENAME = "qualification-instruction-draft-v23.json";
  const EXPLICIT_EMPTY = "__EXPLICIT_EMPTY__";
  const SHA256_PATTERN = /^[0-9a-f]{64}$/;
  const REQUEST_ID_PATTERN = /^real_asset_qualification_request_v2_[0-9a-f]{20}$/;
  const CONTEXT_ID_PATTERN = /^real_asset_qualification_instruction_context_v23_[0-9a-f]{20}$/;
  const UTC_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$/;
  const ISSUE_ORDER = Object.freeze([
    "EVIDENCE_SCOPE_UNCLEAR",
    "POLICY_REQUIREMENT_NOT_MET",
    "QUALIFIER_REJECTED_ASSET_INTAKE",
    "OTHER_BLOCKING_ISSUE",
  ]);
  const DECISIONS = Object.freeze([
    "PASS_ASSET_INTAKE_ONLY",
    "REJECTED",
    "NEEDS_HUMAN_REVIEW",
  ]);
  const CONTEXT_KEYS = Object.freeze([
    "context_id",
    "current_gate",
    "document_type",
    "draft_document_type",
    "eligible_for_real_generation",
    "eligible_for_separate_manifest_design_review",
    "execution_authorized",
    "policy_document_sha256",
    "policy_id",
    "policy_version",
    "posts_allowed",
    "prepared_at",
    "profile",
    "provider_requests",
    "provider_state",
    "qualification_scope",
    "qualifier_ref_sha256",
    "qualifier_role",
    "request_id",
    "request_sha256",
    "request_valid_until",
    "requested_at",
    "rights_manifest_created",
    "rights_qualification_performed",
    "schema_version",
    "status",
  ]);
  const HUMAN_INPUT_KEYS = Object.freeze([
    "decision",
    "decision_at",
    "qualification_basis",
    "qualification_issue_codes",
  ]);
  const DRAFT_KEYS = Object.freeze([
    "context_id",
    "context_sha256",
    "decision",
    "decision_at",
    "document_type",
    "profile",
    "qualification_basis",
    "qualification_issue_codes",
    "qualifier_ref_sha256",
    "request_id",
    "request_sha256",
    "schema_version",
    "status",
  ]);
  const SHA256_CONSTANTS = Object.freeze([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function hasExactKeys(value, expected) {
    if (!isRecord(value)) {
      return false;
    }
    const actual = Object.keys(value).sort();
    return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
  }

  function sortJson(value) {
    if (Array.isArray(value)) {
      return value.map(sortJson);
    }
    if (isRecord(value)) {
      const result = {};
      Object.keys(value).sort().forEach((key) => {
        result[key] = sortJson(value[key]);
      });
      return result;
    }
    return value;
  }

  function canonicalDocument(value) {
    return `${JSON.stringify(sortJson(value), null, 2)}\n`;
  }

  function stableId(kind, value) {
    const digest = sha256Ascii(JSON.stringify(sortJson(value)));
    return digest ? `${kind}_${digest.slice(0, 20)}` : "";
  }

  function rotateRight(value, amount) {
    return (value >>> amount) | (value << (32 - amount));
  }

  function sha256Ascii(value) {
    const bytes = [];
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code > 0x7f) {
        return "";
      }
      bytes.push(code);
    }
    const bitLength = bytes.length * 8;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) {
      bytes.push(0);
    }
    const high = Math.floor(bitLength / 0x100000000);
    const low = bitLength >>> 0;
    for (let shift = 24; shift >= 0; shift -= 8) {
      bytes.push((high >>> shift) & 0xff);
    }
    for (let shift = 24; shift >= 0; shift -= 8) {
      bytes.push((low >>> shift) & 0xff);
    }

    const hash = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    const words = new Array(64).fill(0);
    for (let offset = 0; offset < bytes.length; offset += 64) {
      for (let index = 0; index < 16; index += 1) {
        const start = offset + index * 4;
        words[index] = (
          (bytes[start] << 24)
          | (bytes[start + 1] << 16)
          | (bytes[start + 2] << 8)
          | bytes[start + 3]
        ) >>> 0;
      }
      for (let index = 16; index < 64; index += 1) {
        const s0 = (
          rotateRight(words[index - 15], 7)
          ^ rotateRight(words[index - 15], 18)
          ^ (words[index - 15] >>> 3)
        ) >>> 0;
        const s1 = (
          rotateRight(words[index - 2], 17)
          ^ rotateRight(words[index - 2], 19)
          ^ (words[index - 2] >>> 10)
        ) >>> 0;
        words[index] = (words[index - 16] + s0 + words[index - 7] + s1) >>> 0;
      }

      let [a, b, c, d, e, f, g, h] = hash;
      for (let index = 0; index < 64; index += 1) {
        const sum1 = (rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)) >>> 0;
        const choose = ((e & f) ^ ((~e) & g)) >>> 0;
        const first = (h + sum1 + choose + SHA256_CONSTANTS[index] + words[index]) >>> 0;
        const sum0 = (rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)) >>> 0;
        const majority = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
        const second = (sum0 + majority) >>> 0;
        h = g;
        g = f;
        f = e;
        e = (d + first) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (first + second) >>> 0;
      }
      const state = [a, b, c, d, e, f, g, h];
      for (let index = 0; index < hash.length; index += 1) {
        hash[index] = (hash[index] + state[index]) >>> 0;
      }
    }
    return hash.map((word) => word.toString(16).padStart(8, "0")).join("");
  }

  function isCanonicalUtcSeconds(value) {
    if (typeof value !== "string") {
      return false;
    }
    const match = UTC_PATTERN.exec(value);
    if (!match) {
      return false;
    }
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const hour = Number(match[4]);
    const minute = Number(match[5]);
    const second = Number(match[6]);
    if (year < 1 || month < 1 || month > 12 || hour > 23 || minute > 59 || second > 59) {
      return false;
    }
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    return day >= 1 && day <= days[month - 1];
  }

  function hasUnpairedSurrogate(value) {
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        const following = value.charCodeAt(index + 1);
        if (!(following >= 0xdc00 && following <= 0xdfff)) {
          return true;
        }
        index += 1;
      } else if (code >= 0xdc00 && code <= 0xdfff) {
        return true;
      }
    }
    return false;
  }

  function isPythonStripCharacter(value) {
    return /[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/u.test(value);
  }

  function hasPythonStripBoundary(value) {
    const points = Array.from(value);
    return points.length > 0
      && (isPythonStripCharacter(points[0]) || isPythonStripCharacter(points[points.length - 1]));
  }

  function validateContextEnvelope(envelope) {
    if (!hasExactKeys(envelope, ["context", "context_sha256"])) {
      return false;
    }
    const context = envelope.context;
    if (
      !SHA256_PATTERN.test(envelope.context_sha256)
      || !hasExactKeys(context, CONTEXT_KEYS)
      || context.schema_version !== CONTEXT_SCHEMA_VERSION
      || context.document_type !== CONTEXT_DOCUMENT_TYPE
      || context.profile !== PROFILE
      || !CONTEXT_ID_PATTERN.test(context.context_id)
      || !REQUEST_ID_PATTERN.test(context.request_id)
      || !SHA256_PATTERN.test(context.request_sha256)
      || !isCanonicalUtcSeconds(context.requested_at)
      || !isCanonicalUtcSeconds(context.prepared_at)
      || !isCanonicalUtcSeconds(context.request_valid_until)
      || context.requested_at > context.prepared_at
      || context.prepared_at >= context.request_valid_until
      || context.policy_id !== POLICY_ID
      || context.policy_version !== POLICY_VERSION
      || context.policy_document_sha256 !== POLICY_DOCUMENT_SHA256
      || context.qualification_scope !== "ASSET_INTAKE_ONLY"
      || context.qualifier_role !== "INDEPENDENT_QUALIFIER"
      || !SHA256_PATTERN.test(context.qualifier_ref_sha256)
      || context.draft_document_type !== DRAFT_DOCUMENT_TYPE
      || context.status !== "AWAITING_EXPLICIT_QUALIFIER_INPUT"
      || context.rights_manifest_created !== false
      || context.rights_qualification_performed !== false
      || context.eligible_for_separate_manifest_design_review !== false
      || context.current_gate !== "HUMAN_GATE"
      || context.provider_state !== "NOT_AUTHORIZED"
      || context.eligible_for_real_generation !== false
      || context.execution_authorized !== false
      || context.posts_allowed !== 0
      || context.provider_requests !== 0
    ) {
      return false;
    }
    const identityPayload = {...context};
    delete identityPayload.context_id;
    const expectedContextId = stableId(
      "real_asset_qualification_instruction_context_v23",
      identityPayload,
    );
    const canonical = canonicalDocument(context);
    return context.context_id === expectedContextId
      && sha256Ascii(canonical) === envelope.context_sha256;
  }

  function validateHumanInput(values, context) {
    const errors = [];
    if (!hasExactKeys(values, HUMAN_INPUT_KEYS)) {
      return {valid: false, errors: ["shape"], normalized: null};
    }
    if (
      !isCanonicalUtcSeconds(values.decision_at)
      || values.decision_at < context.prepared_at
      || values.decision_at >= context.request_valid_until
    ) {
      errors.push("decision_at");
    }
    if (!DECISIONS.includes(values.decision)) {
      errors.push("decision");
    }
    if (!Array.isArray(values.qualification_issue_codes)) {
      errors.push("qualification_issue_codes");
    }
    const rawIssues = Array.isArray(values.qualification_issue_codes)
      ? values.qualification_issue_codes
      : [];
    const explicitEmpty = rawIssues.includes(EXPLICIT_EMPTY);
    const issues = rawIssues.filter((value) => value !== EXPLICIT_EMPTY);
    const canonicalIssues = ISSUE_ORDER.filter((value) => issues.includes(value));
    if (
      rawIssues.length === 0
      || rawIssues.length !== new Set(rawIssues).size
      || issues.some((value) => !ISSUE_ORDER.includes(value))
      || canonicalIssues.length !== issues.length
      || canonicalIssues.some((value, index) => value !== issues[index])
      || (explicitEmpty && issues.length > 0)
    ) {
      errors.push("qualification_issue_codes");
    }
    if (values.decision === "PASS_ASSET_INTAKE_ONLY" && !(explicitEmpty && issues.length === 0)) {
      errors.push("decision_issue_combination");
    }
    if (
      values.decision === "REJECTED"
      && (explicitEmpty || !issues.includes("QUALIFIER_REJECTED_ASSET_INTAKE"))
    ) {
      errors.push("decision_issue_combination");
    }
    if (
      values.decision === "NEEDS_HUMAN_REVIEW"
      && (explicitEmpty || issues.length === 0 || issues.includes("QUALIFIER_REJECTED_ASSET_INTAKE"))
    ) {
      errors.push("decision_issue_combination");
    }
    const basis = values.qualification_basis;
    if (
      typeof basis !== "string"
      || basis.length === 0
      || Array.from(basis).length > 1000
      || hasPythonStripBoundary(basis)
      || basis !== basis.normalize("NFC")
      || /[\u0000-\u001f\u007f]/.test(basis)
      || hasUnpairedSurrogate(basis)
    ) {
      errors.push("qualification_basis");
    }
    return {
      valid: errors.length === 0,
      errors,
      normalized: errors.length === 0
        ? {
            decision_at: values.decision_at,
            decision: values.decision,
            qualification_issue_codes: issues,
            qualification_basis: basis,
          }
        : null,
    };
  }

  function buildDraft(envelope, values) {
    if (!validateContextEnvelope(envelope)) {
      throw new Error("context rejected");
    }
    const result = validateHumanInput(values, envelope.context);
    if (!result.valid || !result.normalized) {
      throw new Error("human input rejected");
    }
    const input = result.normalized;
    const draft = {
      schema_version: CONTEXT_SCHEMA_VERSION,
      document_type: envelope.context.draft_document_type,
      profile: envelope.context.profile,
      context_id: envelope.context.context_id,
      context_sha256: envelope.context_sha256,
      request_id: envelope.context.request_id,
      request_sha256: envelope.context.request_sha256,
      qualifier_ref_sha256: envelope.context.qualifier_ref_sha256,
      decision_at: input.decision_at,
      decision: input.decision,
      qualification_issue_codes: input.qualification_issue_codes,
      qualification_basis: input.qualification_basis,
      status: "UNTRUSTED_DRAFT",
    };
    if (!hasExactKeys(draft, DRAFT_KEYS)) {
      throw new Error("draft shape rejected");
    }
    return draft;
  }

  const documentRoot = globalThis.document;
  if (!documentRoot || typeof documentRoot.getElementById !== "function") {
    return;
  }

  const contextStatus = documentRoot.getElementById("context-status");
  const bindings = documentRoot.getElementById("context-bindings");
  const form = documentRoot.getElementById("instruction-draft-form");
  const downloadButton = documentRoot.getElementById("download-draft");
  const formStatus = documentRoot.getElementById("form-status");
  let envelope;
  try {
    const providedEnvelope = globalThis[CONTEXT_GLOBAL];
    if (!validateContextEnvelope(providedEnvelope)) {
      throw new Error("context rejected");
    }
    envelope = JSON.parse(JSON.stringify(providedEnvelope));
    if (!validateContextEnvelope(envelope)) {
      throw new Error("context clone rejected");
    }
  } catch {
    contextStatus.textContent = "本地上下文未通过严格绑定检查；停止，不得填写或导出。";
    contextStatus.classList.add("is-error");
    return;
  }
  Object.freeze(envelope.context);
  Object.freeze(envelope);
  const context = envelope.context;

  documentRoot.querySelectorAll("[data-context-field]").forEach((node) => {
    node.textContent = String(context[node.dataset.contextField]);
  });
  documentRoot.querySelector("[data-context-sha256]").textContent = envelope.context_sha256;
  bindings.hidden = false;
  form.hidden = false;
  contextStatus.textContent = "上下文绑定已在本页内重新计算；仍只允许生成未受信草稿。";
  contextStatus.classList.add("is-ready");

  const decisionAt = documentRoot.getElementById("decision-at");
  const basis = documentRoot.getElementById("qualification-basis");
  const decisionFieldset = documentRoot.getElementById("decision-fieldset");
  const issuesFieldset = documentRoot.getElementById("issues-fieldset");
  const explicitEmpty = documentRoot.getElementById("issues-explicit-empty");
  const issueInputs = Array.from(
    documentRoot.querySelectorAll('input[name="qualification_issue_codes"]'),
  );
  let draftDownloaded = false;
  let downloadedDraftStale = false;

  function selectedDecision() {
    const selected = documentRoot.querySelector('input[name="decision"]:checked');
    return selected ? selected.value : "";
  }

  function humanValues() {
    return {
      decision_at: decisionAt.value,
      decision: selectedDecision(),
      qualification_issue_codes: issueInputs.filter((node) => node.checked).map((node) => node.value),
      qualification_basis: basis.value,
    };
  }

  function updateFormState() {
    const values = humanValues();
    const result = validateHumanInput(values, context);
    const invalid = new Set(result.errors);
    decisionAt.setAttribute("aria-invalid", String(invalid.has("decision_at")));
    basis.setAttribute("aria-invalid", String(invalid.has("qualification_basis")));
    decisionFieldset.setAttribute(
      "aria-invalid",
      String(invalid.has("decision") || invalid.has("decision_issue_combination")),
    );
    issuesFieldset.setAttribute(
      "aria-invalid",
      String(invalid.has("qualification_issue_codes") || invalid.has("decision_issue_combination")),
    );
    downloadButton.disabled = !result.valid;
    formStatus.textContent = result.valid
      ? downloadedDraftStale
        ? "已下载草稿已过时；请重新下载当前完整的未受信草稿。"
        : "四个人工字段形式完整；可下载未受信草稿。"
      : downloadedDraftStale
        ? "已下载草稿已过时；请修正当前四个字段后重新下载。"
        : "等待真人完整填写四个字段并满足机械组合规则。";
    formStatus.classList.toggle("is-ready", result.valid);
  }

  function markFormChanged() {
    if (draftDownloaded) {
      downloadedDraftStale = true;
    }
    updateFormState();
  }

  issueInputs.forEach((input) => {
    input.addEventListener("change", () => {
      if (input === explicitEmpty && input.checked) {
        issueInputs.filter((item) => item !== explicitEmpty).forEach((item) => {
          item.checked = false;
        });
      } else if (input !== explicitEmpty && input.checked) {
        explicitEmpty.checked = false;
      }
    });
  });
  form.addEventListener("input", markFormChanged);
  form.addEventListener("change", markFormChanged);
  form.addEventListener("submit", (event) => event.preventDefault());

  function downloadDraft(draft) {
    const bytes = canonicalDocument(draft);
    const blob = new Blob([bytes], {type: "application/json;charset=utf-8"});
    const objectUrl = URL.createObjectURL(blob);
    const link = documentRoot.createElement("a");
    link.href = objectUrl;
    link.download = DRAFT_FILENAME;
    link.rel = "noopener";
    documentRoot.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }

  downloadButton.addEventListener("click", () => {
    const values = humanValues();
    const result = validateHumanInput(values, context);
    if (!result.valid) {
      updateFormState();
      return;
    }
    const draft = buildDraft(envelope, values);
    downloadDraft(draft);
    draftDownloaded = true;
    downloadedDraftStale = false;
    formStatus.textContent = "已下载未受信草稿；它仍不是 Instruction 或资格决定。";
    formStatus.classList.add("is-ready");
  });

  updateFormState();
})();
