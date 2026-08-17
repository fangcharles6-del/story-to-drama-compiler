"use strict";

(() => {
  const context = window.SDC_HUMAN_REVIEW_CONTEXT;
  const contextSha256 = window.SDC_HUMAN_REVIEW_CONTEXT_SHA256;
  const SHA256_PATTERN = /^[0-9a-f]{64}$/;
  const UTC_SECONDS_PATTERN = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/;
  const hashGenerations = new WeakMap();
  let evidenceDraftExported = false;
  let evidenceDraftDirtySinceExport = false;
  let evidenceHashPending = false;
  let evidenceHashGeneration = 0;
  const approvalNames = [
    "provenance_approved",
    "copyright_approved",
    "likeness_approved",
    "privacy_approved",
    "territory_approved",
    "use_scope_approved",
  ];
  const exceptionGates = [
    ["PROVENANCE", "来源记录"],
    ["COPYRIGHT", "著作权"],
    ["LIKENESS", "形象/声音"],
    ["PRIVACY", "隐私"],
    ["TERRITORY", "地域"],
    ["USE_SCOPE", "使用范围"],
    ["CONTENT_ROLE", "内容角色"],
  ];
  const gateApprovalFields = {
    PROVENANCE: "provenance_approved",
    COPYRIGHT: "copyright_approved",
    LIKENESS: "likeness_approved",
    PRIVACY: "privacy_approved",
    TERRITORY: "territory_approved",
    USE_SCOPE: "use_scope_approved",
  };

  function failClosed(message) {
    document.body.replaceChildren();
    const main = document.createElement("main");
    main.className = "panel warning-panel";
    const heading = document.createElement("h1");
    heading.textContent = "本地上下文不可用";
    const detail = document.createElement("p");
    detail.textContent = message;
    main.append(heading, detail);
    document.body.append(main);
  }

  if (
    !context ||
    !SHA256_PATTERN.test(contextSha256 || "") ||
    context.console_state !== "DRAFT_ONLY" ||
    context.current_gate !== "HUMAN_GATE" ||
    context.provider_state !== "NOT_AUTHORIZED" ||
    context.execution_authorized !== false ||
    context.posts_allowed !== 0 ||
    context.provider_requests !== 0 ||
    !["EVIDENCE", "REVIEWER_A", "REVIEWER_B"].includes(context.workspace_kind) ||
    (
      context.workspace_kind === "EVIDENCE"
        ? context.reviewer_role !== null
        : context.reviewer_role !== context.workspace_kind
    ) ||
    !Array.isArray(context.assets) ||
    context.assets.length !== 14 ||
    (
      context.workspace_kind === "EVIDENCE"
        ? context.evidence_bundle !== null
        : (
          !context.evidence_bundle ||
          typeof context.evidence_bundle !== "object" ||
          !SHA256_PATTERN.test(context.evidence_bundle.bundle_sha256 || "") ||
          !SHA256_PATTERN.test(context.evidence_bundle.evidence_record_sha256 || "") ||
          context.evidence_bundle.read_only !== true ||
          !context.evidence_bundle.bundle_id ||
          !context.evidence_bundle.copyright_basis ||
          !context.evidence_bundle.likeness_basis ||
          !context.evidence_bundle.privacy_basis ||
          !context.evidence_bundle.territory ||
          !context.evidence_bundle.use_scope ||
          !context.evidence_bundle.valid_until
        )
    )
  ) {
    failClosed("上下文未保持精确的14项冻结绑定和零权限状态。请停止操作并重新运行本地准备器。");
    return;
  }

  function byId(id) {
    const node = document.getElementById(id);
    if (!node) {
      throw new Error(`missing local UI element: ${id}`);
    }
    return node;
  }

  function setText(selector, value) {
    const node = document.querySelector(selector);
    if (node) {
      node.textContent = String(value);
    }
  }

  function textOrNull(id) {
    const value = byId(id).value.trim();
    return value === "" ? null : value;
  }

  function radioOrNull(name) {
    const selected = document.querySelector(`input[name="${name}"]:checked`);
    if (!selected) {
      return null;
    }
    if (selected.value === "true") {
      return true;
    }
    if (selected.value === "false") {
      return false;
    }
    return selected.value;
  }

  function sortedValue(value) {
    if (Array.isArray(value)) {
      return value.map(sortedValue);
    }
    if (value !== null && typeof value === "object") {
      const result = {};
      Object.keys(value).sort().forEach((key) => {
        result[key] = sortedValue(value[key]);
      });
      return result;
    }
    return value;
  }

  function canonicalDocument(value) {
    return `${JSON.stringify(sortedValue(value), null, 2)}\n`;
  }

  function safeFilePart(value) {
    return String(value).replace(/[^A-Za-z0-9._-]/g, "-");
  }

  function encodeRelativeFilePath(value) {
    return String(value).split("/").map((part) => {
      if (part === "." || part === "..") {
        return part;
      }
      return encodeURIComponent(part);
    }).join("/");
  }

  function downloadDraft(value, name) {
    const bytes = canonicalDocument(value);
    const blob = new Blob([bytes], {type: "application/json;charset=utf-8"});
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = safeFilePart(name);
    link.rel = "noreferrer";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }

  function hexDigest(buffer) {
    return Array.from(new Uint8Array(buffer), (value) => value.toString(16).padStart(2, "0")).join("");
  }

  function invalidatePendingHash(targetInput) {
    hashGenerations.set(targetInput, (hashGenerations.get(targetInput) || 0) + 1);
  }

  function takeOverHashWithManualInput(fileInput, targetInput, statusNode) {
    const hashStatusActive =
      statusNode.textContent.startsWith("正在本机内存中计算") ||
      statusNode.textContent.startsWith("已在本机内存中计算") ||
      statusNode.textContent.startsWith("当前本地浏览器不能计算摘要");
    invalidatePendingHash(targetInput);
    fileInput.value = "";
    if (hashStatusActive) {
      statusNode.textContent = "已清除文件选择；使用当前手工输入的摘要。";
      statusNode.className = "status";
    }
  }

  async function hashSelectedFile(fileInput, targetInput, statusNode) {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      statusNode.textContent = "未选择文件；可手工输入摘要。";
      statusNode.className = "status";
      return false;
    }
    const generation = (hashGenerations.get(targetInput) || 0) + 1;
    hashGenerations.set(targetInput, generation);
    targetInput.value = "";
    statusNode.textContent = `正在本机内存中计算 ${file.name} 的 SHA-256…`;
    statusNode.className = "status";
    try {
      const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
      if (
        hashGenerations.get(targetInput) !== generation ||
        !fileInput.files ||
        fileInput.files[0] !== file
      ) {
        return false;
      }
      targetInput.value = hexDigest(digest);
      statusNode.textContent = `已在本机内存中计算 ${file.name} 的 SHA-256；文件未被复制。`;
      statusNode.className = "status is-complete";
      return true;
    } catch (_error) {
      if (
        hashGenerations.get(targetInput) !== generation ||
        !fileInput.files ||
        fileInput.files[0] !== file
      ) {
        return false;
      }
      targetInput.value = "";
      statusNode.textContent = "当前本地浏览器不能计算摘要；请使用离线工具计算后手工粘贴。";
      statusNode.className = "status has-warnings";
      return false;
    }
  }

  function evidenceAssetBindings() {
    return context.assets.map((asset) => ({
      ordinal: asset.ordinal,
      requirement_id: asset.requirement_id,
      kind: asset.kind,
      subject_id: asset.subject_id,
      logical_path: asset.logical_path,
      object_path: asset.object_path,
      media_type: asset.media_type,
      media_sha256: asset.media_sha256,
      media_size_bytes: asset.media_size_bytes,
      duration_ms: asset.duration_ms,
      source_authority: asset.source_authority,
      provenance_record_sha256: asset.provenance_record_sha256,
      technical_profile: asset.technical_profile,
      technical_record_sha256: asset.technical_record_sha256,
    }));
  }

  function buildEvidenceDraft() {
    return {
      schema_version: "2.0.0",
      document_type: "sdc.creative-sample-real-asset-rights-evidence-bundle-v2-draft",
      profile: "creative-sample-real-asset-human-review-v2",
      review_context_sha256: contextSha256,
      pack_id: context.pack_id,
      pack_manifest_sha256: context.pack_manifest_sha256,
      evidence_record_sha256: textOrNull("evidence-record-sha"),
      asset_bindings: evidenceAssetBindings(),
      copyright_basis: textOrNull("copyright-basis"),
      likeness_basis: textOrNull("likeness-basis"),
      privacy_basis: textOrNull("privacy-basis"),
      territory: textOrNull("territory"),
      use_scope: textOrNull("use-scope"),
      valid_until: textOrNull("valid-until"),
      status: "DRAFT",
      current_gate: "HUMAN_GATE",
      provider_state: "NOT_AUTHORIZED",
      execution_authorized: false,
      posts_allowed: 0,
      provider_requests: 0,
    };
  }

  function isPortableEvidenceText(value, maximum) {
    return (
      typeof value === "string" &&
      value.length > 0 &&
      Array.from(value).length <= maximum &&
      value === value.normalize("NFC") &&
      !/[\u0000-\u001f\u007f]/u.test(value)
    );
  }

  function isCanonicalUtcSeconds(value) {
    if (typeof value !== "string" || !UTC_SECONDS_PATTERN.test(value)) {
      return false;
    }
    const year = Number(value.slice(0, 4));
    const month = Number(value.slice(5, 7));
    const day = Number(value.slice(8, 10));
    const hour = Number(value.slice(11, 13));
    const minute = Number(value.slice(14, 16));
    const second = Number(value.slice(17, 19));
    const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    return (
      year >= 1 &&
      month >= 1 &&
      month <= 12 &&
      day >= 1 &&
      day <= daysInMonth[month - 1] &&
      hour <= 23 &&
      minute <= 59 &&
      second <= 59
    );
  }

  function evidenceFieldChecks(draft) {
    return [
      {
        controlId: "evidence-record-sha",
        valid: SHA256_PATTERN.test(draft.evidence_record_sha256 || ""),
        warning: "证据记录摘要须为 64 位小写 SHA-256",
      },
      {
        controlId: "copyright-basis",
        valid: isPortableEvidenceText(draft.copyright_basis, 1000),
        warning: "著作权依据须为 1–1000 个规范单行字符；粘贴异常时请离线转为 Unicode NFC",
      },
      {
        controlId: "likeness-basis",
        valid: isPortableEvidenceText(draft.likeness_basis, 1000),
        warning: "形象或声音依据须为 1–1000 个规范单行字符；粘贴异常时请离线转为 Unicode NFC",
      },
      {
        controlId: "privacy-basis",
        valid: isPortableEvidenceText(draft.privacy_basis, 1000),
        warning: "隐私依据须为 1–1000 个规范单行字符；粘贴异常时请离线转为 Unicode NFC",
      },
      {
        controlId: "territory",
        valid: isPortableEvidenceText(draft.territory, 256),
        warning: "地域范围须为 1–256 个规范字符；粘贴异常时请离线转为 Unicode NFC",
      },
      {
        controlId: "use-scope",
        valid: isPortableEvidenceText(draft.use_scope, 1000),
        warning: "用途范围须为 1–1000 个规范单行字符；粘贴异常时请离线转为 Unicode NFC",
      },
      {
        controlId: "valid-until",
        valid: draft.valid_until === "PERPETUAL" || isCanonicalUtcSeconds(draft.valid_until),
        warning: "有效期须为 PERPETUAL 或真实有效的 UTC 秒时间",
      },
    ];
  }

  function evidenceWarnings(draft) {
    const warnings = evidenceFieldChecks(draft)
      .filter((check) => !check.valid)
      .map((check) => check.warning);
    if (evidenceHashPending) {
      warnings.unshift("证据记录摘要仍在本机计算中");
    }
    return warnings;
  }

  function markEvidenceDraftChanged() {
    if (evidenceDraftExported) {
      evidenceDraftExported = false;
      evidenceDraftDirtySinceExport = true;
    }
    if (!evidenceDraftDirtySinceExport) {
      return;
    }
    const status = byId("evidence-status");
    const message = "字段已更改；先前下载的草稿不再对应当前表单，请重新导出。";
    if (status.textContent !== message) {
      status.textContent = message;
      status.className = "status has-warnings";
    }
  }

  function handleEvidenceInput(event) {
    if (event.currentTarget === byId("evidence-record-sha")) {
      takeOverHashWithManualInput(
        byId("evidence-record-file"),
        event.currentTarget,
        byId("evidence-status"),
      );
      if (evidenceHashPending) {
        evidenceHashPending = false;
        evidenceHashGeneration += 1;
      }
    }
    markEvidenceDraftChanged();
    renderEvidenceReadiness();
  }

  function renderEvidenceReadiness() {
    const readiness = byId("evidence-readiness");
    const status = byId("evidence-readiness-status");
    const missing = byId("evidence-readiness-missing");
    const download = byId("download-evidence");
    const draft = buildEvidenceDraft();
    const checks = evidenceFieldChecks(draft);
    const warnings = evidenceWarnings(draft);
    checks.forEach((check) => {
      byId(check.controlId).setAttribute("aria-invalid", String(!check.valid));
    });
    missing.replaceChildren();
    if (warnings.length === 0) {
      download.disabled = false;
      readiness.dataset.state = "FORM_COMPLETE_DRAFT_ONLY";
      if (status.textContent !== "字段形式完整，可导出未受信草稿") {
        status.textContent = "字段形式完整，可导出未受信草稿";
      }
      readiness.className = "readiness-card is-form-complete";
      missing.append(
        createText(
          "li",
          "",
          "仅通过本页机械格式检查；请真人另行确认记录当前可用、期限未过期，并由本地 finalizer 严格验证。",
        ),
      );
      return;
    }
    download.disabled = true;
    readiness.dataset.state = "NEEDS_EVIDENCE";
    if (status.textContent !== "缺少依据，停止") {
      status.textContent = "缺少依据，停止";
    }
    readiness.className = "readiness-card is-stop";
    warnings.forEach((warning) => missing.append(createText("li", "", warning)));
  }

  function createText(tag, className, value) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    node.textContent = value;
    return node;
  }

  function metaCell(label, value, code) {
    const cell = document.createElement("div");
    cell.append(createText("strong", "", label));
    cell.append(createText(code ? "code" : "span", "", String(value)));
    return cell;
  }

  function buildAssetCard(asset) {
    const article = document.createElement("article");
    article.className = "asset-card";
    article.dataset.ordinal = String(asset.ordinal);

    const head = document.createElement("div");
    head.className = "asset-card-head";
    const titleWrap = document.createElement("div");
    titleWrap.append(
      createText("p", "label", `Asset ${String(asset.ordinal).padStart(2, "0")}`),
      createText("h3", "", asset.logical_path),
    );
    head.append(titleWrap, createText("span", "kind-badge", asset.kind));

    const meta = document.createElement("div");
    meta.className = "asset-meta";
    meta.append(
      metaCell("角色", asset.subject_id, false),
      metaCell("大小", `${asset.media_size_bytes} bytes`, false),
      metaCell("媒体 SHA-256", asset.media_sha256, true),
      metaCell("技术记录 SHA-256", asset.technical_record_sha256, true),
      metaCell("来源记录 SHA-256", asset.provenance_record_sha256, true),
      metaCell("本地只读相对路径", asset.media_relative_path, true),
    );

    const preview = document.createElement("div");
    preview.className = "preview-wrap";
    const media = document.createElement(asset.kind === "IMAGE" ? "img" : "audio");
    if (asset.kind === "IMAGE") {
      media.alt = `${asset.subject_id} 冻结图片预览`;
    } else {
      media.controls = true;
      media.preload = "none";
    }
    preview.append(media);

    const actions = document.createElement("div");
    actions.className = "asset-actions";
    const previewButton = createText("button", "", "打开本地预览");
    previewButton.type = "button";
    previewButton.addEventListener("click", () => {
      if (!preview.classList.contains("is-open")) {
        media.src = new URL(
          encodeRelativeFilePath(asset.media_relative_path),
          window.location.href,
        ).href;
        preview.classList.add("is-open");
        previewButton.textContent = "关闭预览";
      } else {
        if (media.pause) {
          media.pause();
        }
        media.removeAttribute("src");
        if (media.load) {
          media.load();
        }
        preview.classList.remove("is-open");
        previewButton.textContent = "打开本地预览";
      }
    });
    const inspectionLabel = document.createElement("label");
    const inspection = document.createElement("input");
    inspection.type = "checkbox";
    inspection.className = "inspection-confirmed";
    inspection.addEventListener("change", updateInspectionProgress);
    inspectionLabel.append(inspection, document.createTextNode("我已查看并核对上述精确冻结媒体"));
    actions.append(previewButton, inspectionLabel);

    const review = document.createElement("div");
    review.className = "asset-review";
    const contentRole = document.createElement("fieldset");
    contentRole.className = "content-role";
    contentRole.append(createText("legend", "", "content_role_approved（真人选择）"));
    [
      ["true", "通过"],
      ["false", "不通过"],
    ].forEach(([value, label]) => {
      const choice = document.createElement("label");
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `content_role_${asset.ordinal}`;
      radio.value = value;
      choice.append(radio, document.createTextNode(label));
      contentRole.append(choice);
    });
    const exceptionLabel = document.createElement("label");
    exceptionLabel.className = "exception-field";
    exceptionLabel.append(createText("span", "", "异常说明（无异常时留空）"));
    const exception = document.createElement("textarea");
    exception.className = "exception-finding";
    exception.maxLength = 1000;
    exception.placeholder = "仅记录真人实际发现的素材级异常";
    exceptionLabel.append(exception);
    const exceptionBlock = document.createElement("div");
    exceptionBlock.className = "exception-block";
    const failedGates = document.createElement("fieldset");
    failedGates.className = "exception-gates";
    failedGates.append(createText("legend", "", "异常涉及的门禁（仅有异常时选择）"));
    exceptionGates.forEach(([value, label]) => {
      const choice = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "exception-gate";
      checkbox.value = value;
      choice.append(checkbox, document.createTextNode(label));
      failedGates.append(choice);
    });
    exceptionBlock.append(failedGates, exceptionLabel);
    review.append(contentRole, exceptionBlock);

    const technical = document.createElement("details");
    technical.className = "technical";
    technical.append(createText("summary", "", "查看只读技术摘要"));
    technical.append(createText("pre", "", JSON.stringify(sortedValue(asset.technical_summary), null, 2)));

    article.append(head, meta, preview, actions, review, technical);
    return article;
  }

  function updateInspectionProgress() {
    const complete = document.querySelectorAll(".inspection-confirmed:checked").length;
    byId("inspection-progress").textContent = String(complete);
  }

  function assetFindings() {
    return context.assets.map((asset) => {
      const card = document.querySelector(`.asset-card[data-ordinal="${asset.ordinal}"]`);
      if (!card) {
        throw new Error("asset review card is missing");
      }
      const inspection = card.querySelector(".inspection-confirmed");
      const exception = card.querySelector(".exception-finding");
      const failedGates = Array.from(card.querySelectorAll(".exception-gate:checked"))
        .map((input) => input.value);
      return {
        ordinal: asset.ordinal,
        requirement_id: asset.requirement_id,
        logical_path: asset.logical_path,
        media_sha256: asset.media_sha256,
        media_size_bytes: asset.media_size_bytes,
        inspection_confirmed: inspection.checked ? true : null,
        content_role_approved: radioOrNull(`content_role_${asset.ordinal}`),
        failed_gates: failedGates,
        exception_finding: exception.value.trim() === "" ? null : exception.value.trim(),
      };
    });
  }

  function buildReviewDraft() {
    const findings = assetFindings();
    return {
      schema_version: "2.0.0",
      document_type: "sdc.creative-sample-real-asset-human-pack-review-v2-draft",
      profile: "creative-sample-real-asset-human-review-v2",
      review_context_sha256: contextSha256,
      pack_id: context.pack_id,
      pack_manifest_sha256: context.pack_manifest_sha256,
      evidence_bundle_id: context.evidence_bundle.bundle_id,
      evidence_bundle_sha256: context.evidence_bundle.bundle_sha256,
      reviewer_role: context.reviewer_role,
      reviewer_ref_sha256: textOrNull("reviewer-ref-sha"),
      asset_findings: findings,
      provenance_approved: radioOrNull("provenance_approved"),
      copyright_approved: radioOrNull("copyright_approved"),
      likeness_approved: radioOrNull("likeness_approved"),
      privacy_approved: radioOrNull("privacy_approved"),
      territory_approved: radioOrNull("territory_approved"),
      use_scope_approved: radioOrNull("use_scope_approved"),
      rejection_reason: textOrNull("rejection-reason"),
      decision: radioOrNull("decision"),
      status: "DRAFT",
      current_gate: "HUMAN_GATE",
      provider_state: "NOT_AUTHORIZED",
      execution_authorized: false,
      posts_allowed: 0,
      provider_requests: 0,
    };
  }

  function reviewWarnings(draft) {
    const warnings = [];
    if (!draft.evidence_bundle_id) {
      warnings.push("evidence_bundle_id 尚未填写");
    }
    if (!SHA256_PATTERN.test(draft.reviewer_ref_sha256 || "")) {
      warnings.push("Reviewer 证明摘要尚未填写为64位小写 SHA-256");
    }
    approvalNames.forEach((name) => {
      if (draft[name] === null) {
        warnings.push(`${name} 尚未由真人选择`);
      }
    });
    draft.asset_findings.forEach((finding) => {
      if (finding.inspection_confirmed !== true) {
        warnings.push(`Asset ${finding.ordinal} 尚未确认查看`);
      }
      if (finding.content_role_approved === null) {
        warnings.push(`Asset ${finding.ordinal} 的 content_role_approved 尚未选择`);
      }
      if (
        finding.content_role_approved === false &&
        (finding.exception_finding === null || !finding.failed_gates.includes("CONTENT_ROLE"))
      ) {
        warnings.push(`Asset ${finding.ordinal} 的内容角色不通过必须明确选择 CONTENT_ROLE 并填写异常说明`);
      }
      if (finding.failed_gates.length > 0 && finding.exception_finding === null) {
        warnings.push(`Asset ${finding.ordinal} 已选择异常门禁但尚缺异常说明`);
      }
      if (finding.failed_gates.length === 0 && finding.exception_finding !== null) {
        warnings.push(`Asset ${finding.ordinal} 已填写异常说明但尚未选择异常门禁`);
      }
      finding.failed_gates.forEach((gate) => {
        if (gate === "CONTENT_ROLE" && finding.content_role_approved === true) {
          warnings.push(`Asset ${finding.ordinal} 的内容角色异常与通过选择冲突`);
        }
        const approvalField = gateApprovalFields[gate];
        if (approvalField && draft[approvalField] === true) {
          warnings.push(`Asset ${finding.ordinal} 的 ${gate} 异常与 Pack 级通过选择冲突`);
        }
      });
    });
    if (draft.decision === null) {
      warnings.push("decision 尚未由真人选择");
    }
    const allPackApproved = approvalNames.every((name) => draft[name] === true);
    const allContentApproved = draft.asset_findings.every((finding) => finding.content_role_approved === true);
    const hasException = draft.asset_findings.some(
      (finding) => finding.exception_finding !== null || finding.failed_gates.length > 0,
    );
    if (draft.decision === "APPROVED" && (!allPackApproved || !allContentApproved || hasException)) {
      warnings.push("APPROVED 与当前人工布尔值或异常项不一致");
    }
    if (draft.decision === "REJECTED" && !draft.rejection_reason) {
      warnings.push("REJECTED 尚缺真人填写的 rejection_reason");
    }
    return warnings;
  }

  function showDownloadStatus(node, warnings) {
    if (warnings.length === 0) {
      node.textContent = "草稿字段已完整导出；仍需后续本地 finalizer 严格验证。";
      node.className = "status is-complete";
    } else {
      node.textContent = `已导出可继续编辑的草稿；当前有 ${warnings.length} 项未闭合或不一致。`;
      node.className = "status has-warnings";
    }
  }

  setText("[data-pack-id]", context.pack_id);
  setText("[data-pack-sha]", context.pack_manifest_sha256);
  setText("[data-asset-count]", context.assets.length);

  const evidenceSection = byId("evidence-section");
  const evidenceBindingSection = byId("evidence-binding-section");
  const reviewSection = byId("review-section");
  if (context.workspace_kind === "EVIDENCE") {
    reviewSection.hidden = true;
    [
      "evidence-record-sha",
      "copyright-basis",
      "likeness-basis",
      "privacy-basis",
      "territory",
      "use-scope",
      "valid-until",
    ].forEach((id) => byId(id).addEventListener("input", handleEvidenceInput));
    renderEvidenceReadiness();
  } else {
    evidenceSection.hidden = true;
    evidenceBindingSection.hidden = false;
    byId("evidence-bundle-id").value = context.evidence_bundle.bundle_id;
    byId("reviewer-role").value = context.reviewer_role;
    setText("[data-evidence-bundle-id]", context.evidence_bundle.bundle_id);
    setText("[data-evidence-bundle-sha]", context.evidence_bundle.bundle_sha256);
    setText("[data-evidence-record-sha]", context.evidence_bundle.evidence_record_sha256);
    setText("[data-copyright-basis]", context.evidence_bundle.copyright_basis);
    setText("[data-likeness-basis]", context.evidence_bundle.likeness_basis);
    setText("[data-privacy-basis]", context.evidence_bundle.privacy_basis);
    setText("[data-territory]", context.evidence_bundle.territory);
    setText("[data-use-scope]", context.evidence_bundle.use_scope);
    setText("[data-valid-until]", context.evidence_bundle.valid_until);
    const assetList = byId("asset-list");
    context.assets.forEach((asset) => assetList.append(buildAssetCard(asset)));
  }

  byId("evidence-record-file").addEventListener("change", () => {
    markEvidenceDraftChanged();
    const generation = evidenceHashGeneration + 1;
    evidenceHashGeneration = generation;
    evidenceHashPending = Boolean(
      byId("evidence-record-file").files && byId("evidence-record-file").files[0],
    );
    const hashing = hashSelectedFile(
      byId("evidence-record-file"),
      byId("evidence-record-sha"),
      byId("evidence-status"),
    );
    renderEvidenceReadiness();
    void hashing.then(() => {
      if (generation !== evidenceHashGeneration) {
        return;
      }
      evidenceHashPending = false;
      markEvidenceDraftChanged();
      renderEvidenceReadiness();
    });
  });
  byId("reviewer-ref-sha").addEventListener("input", (event) => {
    takeOverHashWithManualInput(
      byId("reviewer-ref-file"),
      event.currentTarget,
      byId("review-status"),
    );
  });
  byId("reviewer-ref-file").addEventListener("change", () => {
    void hashSelectedFile(byId("reviewer-ref-file"), byId("reviewer-ref-sha"), byId("review-status"));
  });

  byId("download-evidence").addEventListener("click", () => {
    const draft = buildEvidenceDraft();
    const warnings = evidenceWarnings(draft);
    renderEvidenceReadiness();
    if (warnings.length !== 0) {
      const status = byId("evidence-status");
      status.textContent = `缺少依据，未导出草稿；请先闭合 ${warnings.length} 项。`;
      status.className = "status has-warnings";
      return;
    }
    downloadDraft(draft, `rights-evidence-bundle-v2-draft-${context.pack_id}.json`);
    evidenceDraftExported = true;
    evidenceDraftDirtySinceExport = false;
    showDownloadStatus(byId("evidence-status"), warnings);
  });

  byId("download-review").addEventListener("click", () => {
    const draft = buildReviewDraft();
    const warnings = reviewWarnings(draft);
    downloadDraft(
      draft,
      `human-pack-review-v2-draft-${context.pack_id}-${context.reviewer_role.toLowerCase()}.json`,
    );
    showDownloadStatus(byId("review-status"), warnings);
  });
})();
