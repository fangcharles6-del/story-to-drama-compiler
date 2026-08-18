from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ASSET_ROOT = (
    Path(__file__).parents[1]
    / "src"
    / "sdc"
    / "real_asset_qualification_instruction_preparer_v23_assets"
)


class _TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.tags.append((tag, dict(attrs)))


def _asset(name: str) -> str:
    return (ASSET_ROOT / name).read_text(encoding="utf-8")


def test_v23_ui_asset_surface_is_exact_static_and_file_local() -> None:
    assert {path.name for path in ASSET_ROOT.iterdir()} == {
        "app.js",
        "index.html",
        "style.css",
    }
    assert all(path.is_file() and not path.is_symlink() for path in ASSET_ROOT.iterdir())

    html = _asset("index.html")
    parser = _TagCollector()
    parser.feed(html)
    scripts = [attrs for tag, attrs in parser.tags if tag == "script"]
    links = [attrs for tag, attrs in parser.tags if tag == "link"]
    assert [item.get("src") for item in scripts] == ["instruction-context.js", "app.js"]
    assert all(item.get("defer") is None for item in scripts)
    assert links == [{"rel": "stylesheet", "href": "style.css"}]
    empty_external_scripts = re.findall(
        r"<script(?:\s[^>]*)?>\s*</script>",
        html,
        re.IGNORECASE,
    )
    assert len(empty_external_scripts) == 2
    assert "<style" not in html.casefold()
    assert not re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE)
    assert "http://" not in html.casefold()
    assert "https://" not in html.casefold()

    csp = next(
        attrs["content"]
        for tag, attrs in parser.tags
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"
    )
    assert csp == (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'none'; "
        "media-src 'none'; connect-src 'none'; font-src 'none'; object-src 'none'; "
        "frame-src 'none'; base-uri 'none'; form-action 'none'; manifest-src 'none'; "
        "worker-src 'none'"
    )
    style = _asset("style.css").casefold()
    assert "@import" not in style
    assert "url(" not in style
    assert "http://" not in style
    assert "https://" not in style


def test_v23_ui_exposes_only_four_blank_human_fields_with_accessible_controls() -> None:
    html = _asset("index.html")
    parser = _TagCollector()
    parser.feed(html)
    controls = [
        attrs
        for tag, attrs in parser.tags
        if tag in {"input", "textarea", "select"}
    ]
    assert {attrs["name"] for attrs in controls if attrs.get("name")} == {
        "decision_at",
        "decision",
        "qualification_issue_codes",
        "qualification_basis",
    }
    assert not any(attrs.get("type") == "file" for attrs in controls)
    assert not any("checked" in attrs or "selected" in attrs for attrs in controls)
    assert next(attrs for attrs in controls if attrs.get("name") == "decision_at").get(
        "value"
    ) is None
    assert re.search(
        r'<textarea[^>]*name="qualification_basis"[^>]*>\s*</textarea>',
        html,
        re.DOTALL,
    )
    basis_control = next(
        attrs for attrs in controls if attrs.get("name") == "qualification_basis"
    )
    assert basis_control.get("maxlength") is None
    assert html.count("<fieldset") >= 2
    assert html.count("<legend") >= 2
    assert '<label for="decision-at">' in html
    assert '<label for="qualification-basis">' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'class="skip-link" href="#human-input"' in html
    download = re.search(r'<button id="download-draft"(?P<attrs>[^>]*)>', html)
    assert download is not None and "disabled" in download.group("attrs")
    assert "没有预选项" in html
    assert "不会起草、补全或建议" in html
    assert "所选代码按固定显示顺序导出，不会自动补全" in html
    assert "只能交给可信 Python" in html
    assert "finalize-instruction" in html
    assert "不得作为 canonical Instruction 输入 v2.2 Decision Finalizer" in html


def test_v23_ui_has_no_network_storage_clock_environment_or_execution_surface() -> None:
    html = _asset("index.html")
    script = _asset("app.js")
    combined = f"{html}\n{script}"
    forbidden = (
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "eventsource",
        "sendbeacon",
        "localstorage",
        "sessionstorage",
        "indexeddb",
        "document.cookie",
        "settimeout",
        "setinterval",
        "requestanimationframe",
        "new date",
        "date.now",
        "performance.now",
        "navigator.",
        "process.",
        "import(",
        "worker(",
        "console.",
    )
    lowered = combined.casefold()
    for marker in forbidden:
        assert marker not in lowered, marker
    for forbidden_field in (
        "instruction_id",
        "qualifier_record_sha256",
        "eligible_for_real_generation: true",
        "execution_authorized: true",
        "rights_manifest_created: true",
        "provider_requests: 1",
    ):
        assert forbidden_field not in lowered
    assert "HUMAN_GATE" in html
    assert "NOT_AUTHORIZED" in html
    assert "rights_qualification_performed=false" in html
    assert "rights_manifest_created=false" in html
    assert "eligible_for_separate_manifest_design_review=false" in html
    assert "eligible_for_real_generation=false" in html
    assert "execution_authorized=false" in html
    assert "posts_allowed=0" in html
    assert "provider_requests=0" in html


def test_v23_ui_readonly_context_projection_and_untrusted_export_are_bounded() -> None:
    html = _asset("index.html")
    script = _asset("app.js")
    projected = set(re.findall(r'data-context-field="([a-z0-9_]+)"', html))
    assert projected == {
        "context_id",
        "draft_document_type",
        "policy_document_sha256",
        "policy_id",
        "policy_version",
        "prepared_at",
        "qualification_scope",
        "qualifier_ref_sha256",
        "qualifier_role",
        "request_id",
        "request_sha256",
        "request_valid_until",
        "requested_at",
    }
    assert "data-context-sha256" in html
    assert ".textContent =" in script
    assert ".innerHTML" not in script
    assert 'const DRAFT_FILENAME = "qualification-instruction-draft-v23.json"' in script
    draft_literal = re.search(
        r"    const draft = \{\n(?P<body>.*?)^    \};",
        script,
        re.DOTALL | re.MULTILINE,
    )
    assert draft_literal is not None
    for forbidden_context_field in (
        "context.policy_id",
        "context.requested_at",
        "context.prepared_at",
    ):
        assert forbidden_context_field not in draft_literal.group("body")
    assert 'status: "UNTRUSTED_DRAFT"' in script
    assert 'link.download = DRAFT_FILENAME' in script
    assert "已下载草稿已过时；请重新下载" in script


def test_v23_javascript_syntax_is_valid() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    completed = subprocess.run(
        [node, "--check", str(ASSET_ROOT / "app.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""


def test_v23_node_contract_behavior_has_no_defaults_inference_or_draft_leakage() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    probe = r'''
const fs = require("fs");
const vm = require("vm");
let source = fs.readFileSync(process.argv[1], "utf8");
const marker = "  const documentRoot = globalThis.document;";
if (!source.includes(marker)) throw new Error("test insertion marker missing");
source = source.replace(marker, `  globalThis.__SDC_UI_TEST__ = Object.freeze({
    canonicalDocument,
    sha256Ascii,
    stableId,
    validateContextEnvelope,
    validateHumanInput,
    buildDraft,
    EXPLICIT_EMPTY,
    DRAFT_FILENAME,
  });
${marker}`);
const sandbox = {};
vm.runInNewContext(source, sandbox, {filename: "app.js"});
const api = sandbox.__SDC_UI_TEST__;
if (!api) throw new Error("test API missing");
function check(value, message) { if (!value) throw new Error(message); }

const contextPayload = {
  schema_version: "2.3.0",
  document_type: "sdc.creative-sample-real-asset-qualification-instruction-workspace-context-v2.3",
  profile: "creative-sample-real-asset-qualification-instruction-preparation-v2.3",
  request_id: "real_asset_qualification_request_v2_0123456789abcdefabcd",
  request_sha256: "a".repeat(64),
  requested_at: "2026-08-18T10:00:00Z",
  prepared_at: "2026-08-18T10:30:00Z",
  request_valid_until: "2026-08-19T10:00:00Z",
  policy_id: "creative-sample-real-asset-qualification-policy",
  policy_version: "2.0.0",
  policy_document_sha256: "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031",
  qualification_scope: "ASSET_INTAKE_ONLY",
  qualifier_role: "INDEPENDENT_QUALIFIER",
  qualifier_ref_sha256: "b".repeat(64),
  draft_document_type:
    "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3",
  status: "AWAITING_EXPLICIT_QUALIFIER_INPUT",
  rights_manifest_created: false,
  rights_qualification_performed: false,
  eligible_for_separate_manifest_design_review: false,
  current_gate: "HUMAN_GATE",
  provider_state: "NOT_AUTHORIZED",
  eligible_for_real_generation: false,
  execution_authorized: false,
  posts_allowed: 0,
  provider_requests: 0,
};
const context = {
  ...contextPayload,
  context_id: api.stableId(
    "real_asset_qualification_instruction_context_v23",
    contextPayload,
  ),
};
const envelope = {
  context_sha256: api.sha256Ascii(api.canonicalDocument(context)),
  context,
};
check(
  api.sha256Ascii("abc")
    === "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  "sha256",
);
check(api.validateContextEnvelope(envelope), "valid context");
check(!api.validateContextEnvelope({...envelope, extra: true}), "extra envelope key");
check(
  !api.validateContextEnvelope({...envelope, context_sha256: "0".repeat(64)}),
  "context digest",
);
check(
  !api.validateContextEnvelope({
    ...envelope,
    context: {...context, prepared_at: context.request_valid_until},
  }),
  "context time",
);
const reboundTamper = {...context, request_sha256: "c".repeat(64)};
check(
  !api.validateContextEnvelope({
    context: reboundTamper,
    context_sha256: api.sha256Ascii(api.canonicalDocument(reboundTamper)),
  }),
  "context stable id",
);

const blank = {
  decision_at: "",
  decision: "",
  qualification_issue_codes: [],
  qualification_basis: "",
};
check(!api.validateHumanInput(blank, context).valid, "blank must fail");
const pass = {
  decision_at: "2026-08-18T10:31:00Z",
  decision: "PASS_ASSET_INTAKE_ONLY",
  qualification_issue_codes: [api.EXPLICIT_EMPTY],
  qualification_basis: "Independent human basis.",
};
check(api.validateHumanInput(pass, context).valid, "pass form");
check(
  api.validateHumanInput({...pass, qualification_basis: "😀".repeat(1000)}, context).valid,
  "basis counts Unicode code points",
);
check(
  !api.validateHumanInput({...pass, qualification_basis: "😀".repeat(1001)}, context).valid,
  "basis code point maximum",
);
check(
  !api.validateHumanInput({...pass, qualification_basis: "\u0085boundary"}, context).valid,
  "Python strip boundary",
);
check(
  !api.validateHumanInput({...pass, decision_at: "2026-02-30T10:31:00Z"}, context).valid,
  "calendar",
);
check(
  !api.validateHumanInput({...pass, decision_at: "2026-08-18T10:29:59Z"}, context).valid,
  "prepared lower bound",
);
check(
  !api.validateHumanInput({...pass, qualification_issue_codes: []}, context).valid,
  "pass explicit empty",
);
check(!api.validateHumanInput({...pass, extra: true}, context).valid, "fifth human field");
const rejected = {
  ...pass,
  decision: "REJECTED",
  qualification_issue_codes: ["QUALIFIER_REJECTED_ASSET_INTAKE"],
};
const needs = {
  ...pass,
  decision: "NEEDS_HUMAN_REVIEW",
  qualification_issue_codes: ["OTHER_BLOCKING_ISSUE"],
};
check(api.validateHumanInput(rejected, context).valid, "rejected form");
check(api.validateHumanInput(needs, context).valid, "needs form");
check(
  !api.validateHumanInput({
    ...needs,
    qualification_issue_codes: ["QUALIFIER_REJECTED_ASSET_INTAKE"],
  }, context).valid,
  "needs rejection code",
);

const draft = api.buildDraft(envelope, pass);
const expectedKeys = [
  "context_id", "context_sha256", "decision", "decision_at", "document_type", "profile",
  "qualification_basis", "qualification_issue_codes", "qualifier_ref_sha256", "request_id",
  "request_sha256", "schema_version", "status",
];
check(JSON.stringify(Object.keys(draft).sort()) === JSON.stringify(expectedKeys), "draft shape");
check(draft.status === "UNTRUSTED_DRAFT", "draft status");
check(draft.qualification_issue_codes.length === 0, "sentinel excluded");
check(!Object.hasOwn(draft, "instruction_id"), "no instruction id");
check(!Object.hasOwn(draft, "policy_id"), "no extra context projection");
check(!Object.hasOwn(draft, "prepared_at"), "no prepared time projection");
const canonical = api.canonicalDocument(draft);
check(canonical.endsWith("\n") && !canonical.includes(api.EXPLICIT_EMPTY), "canonical draft bytes");
check(api.DRAFT_FILENAME === "qualification-instruction-draft-v23.json", "neutral filename");
process.stdout.write(JSON.stringify({
  ok: true,
  stable_vector: api.stableId("vector", {z: false, a: "b", nested: {x: 1}}),
}));
'''
    completed = subprocess.run(
        [node, "-e", probe, str(ASSET_ROOT / "app.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    observed = json.loads(completed.stdout)
    stable_payload = json.dumps(
        {"a": "b", "nested": {"x": 1}, "z": False},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    expected_stable_id = (
        f"vector_{hashlib.sha256(stable_payload.encode()).hexdigest()[:20]}"
    )
    assert observed == {"ok": True, "stable_vector": expected_stable_id}


def test_v23_draft_shape_is_exactly_thirteen_fields_and_never_an_instruction() -> None:
    script = _asset("app.js")
    build = re.search(
        r"    const draft = \{\n(?P<body>.*?)^    \};",
        script,
        re.DOTALL | re.MULTILINE,
    )
    assert build is not None
    body = build.group("body")
    fields = re.findall(r"^      ([a-z][a-z0-9_]*):", body, re.MULTILINE)
    assert fields == [
        "schema_version",
        "document_type",
        "profile",
        "context_id",
        "context_sha256",
        "request_id",
        "request_sha256",
        "qualifier_ref_sha256",
        "decision_at",
        "decision",
        "qualification_issue_codes",
        "qualification_basis",
        "status",
    ]
    for forbidden in (
        "instruction_id",
        "qualifier_record_sha256",
        "rights_qualification_performed",
        "rights_manifest_created",
        "eligible_for_separate_manifest_design_review",
        "eligible_for_real_generation",
        "execution_authorized",
        "posts_allowed",
        "provider_requests",
    ):
        assert forbidden not in body
