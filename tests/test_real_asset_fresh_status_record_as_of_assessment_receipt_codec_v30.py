from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, get_args

import pytest
from test_real_asset_fresh_status_evidence_v30 import (
    FreshBundle,
    Upstream,
    _build_bundle,
    _build_upstream,
)
from test_real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    _build as _build_receipt,
)
from test_real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    _independent_canonical_document,
)
from test_real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    _verify as _verify_receipt,
)
from test_real_asset_fresh_status_record_chain_coverage_v30 import (
    CoverageGraph,
    _build_graph,
    _chain,
)
from test_real_asset_fresh_status_record_joint_replay_v30 import (
    _build_alternate_upstream,
)

import sdc.real_asset_fresh_status_record_as_of_assessment_receipt_codec_v30 as codec_module
from sdc.compiler import stable_id
from sdc.real_asset_fresh_status_evidence_v30 import FRESH_STATUS_JSON_MAX_DEPTH
from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_codec_v30 import (
    FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1,
    RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error,
    encode_fresh_status_record_as_of_assessment_receipt_v1_json,
    parse_fresh_status_record_as_of_assessment_receipt_v1_json,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES,
    CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error,
)
from sdc.real_asset_fresh_status_record_chain_coverage_v30 import (
    FreshStatusRecordChainInputV1,
)
from sdc.schemas import MODELS

_RECEIPT_ID_KIND = "real_asset_fresh_status_record_as_of_assessment_receipt_v1"
_FALSE_AUTHORITY_FIELDS = (
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
)
_ZERO_AUTHORITY_FIELDS = (
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
)
_FIVE_THOUSAND_DIGIT_JSON_INTEGER = b"1" + b"0" * 4_999


@pytest.fixture(scope="module")
def upstream() -> Upstream:
    return _build_upstream()


@pytest.fixture(scope="module")
def graph(upstream: Upstream) -> CoverageGraph:
    return _build_graph(upstream)


@pytest.fixture(scope="module")
def bundle(upstream: Upstream, graph: CoverageGraph) -> FreshBundle:
    return _build_bundle(upstream, (graph.target_a, graph.target_b))


@pytest.fixture(scope="module")
def chains(graph: CoverageGraph) -> tuple[FreshStatusRecordChainInputV1, ...]:
    return (
        _chain((graph.genesis_a, graph.target_a), (graph.target_a,)),
        _chain((graph.target_b,), (graph.target_b,)),
    )


def _receipt(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    return _build_receipt(upstream, bundle, chains)


def _assert_codec_error(
    expected_code: str,
    callback: Any,
) -> RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error:
    with pytest.raises(RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error) as captured:
        callback()
    error = captured.value
    assert error.code == expected_code
    assert str(error).startswith(f"{expected_code}:")
    return error


def _render_payload(
    payload: object,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> bytes:
    separators = (",", ":") if indent is None else None
    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            indent=indent,
            separators=separators,
            sort_keys=sort_keys,
        )
        + "\n"
    ).encode("utf-8")


def _nested_array(levels: int) -> object:
    value: object = 0
    for _ in range(levels):
        value = [value]
    return value


def _deep_object_document(levels: int, leaf: bytes = b"0") -> bytes:
    assert levels > 0
    return b'{"x":' * levels + leaf + b"}" * levels


def _deep_array_document(levels: int, leaf: bytes = b"0") -> bytes:
    assert levels > 0
    return b"[" * levels + leaf + b"]" * levels


def _deep_tuple(levels: int) -> tuple[object, ...]:
    assert levels > 0
    value: object = "SYNTHETIC_CATEGORY"
    for _ in range(levels):
        value = (value,)
    assert isinstance(value, tuple)
    return value


def test_codec_round_trip_is_exact_deterministic_and_independently_canonical(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    expected = _independent_canonical_document(receipt)
    first = encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)
    second = encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)
    parsed = parse_fresh_status_record_as_of_assessment_receipt_v1_json(first)

    assert type(first) is bytes
    assert first == second == expected
    assert parsed == receipt
    assert parsed is not receipt
    assert encode_fresh_status_record_as_of_assessment_receipt_v1_json(parsed) == first
    assert first.endswith(b"\n")
    assert not first.endswith(b"\n\n")
    assert not first.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in first
    assert 0 < len(first) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    assert len(first) == 4_719
    assert hashlib.sha256(first).hexdigest() == (
        "b00eba1cd3e27781f1a7f13427689b769f56a0228986f727ec029031a04e08ba"
    )


def test_codec_preserves_every_zero_authority_and_historical_limitation_field(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    parsed = parse_fresh_status_record_as_of_assessment_receipt_v1_json(
        encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)
    )
    assert parsed.current_gate == "HUMAN_GATE"
    assert parsed.provider_state == "NOT_AUTHORIZED"
    assert parsed.present_currentness_asserted is False
    for field in _FALSE_AUTHORITY_FIELDS:
        assert getattr(parsed, field) is False
    for field in _ZERO_AUTHORITY_FIELDS:
        assert type(getattr(parsed, field)) is int
        assert getattr(parsed, field) == 0
    assert parsed.limitation_codes == receipt.limitation_codes


@pytest.mark.parametrize("field", (*_FALSE_AUTHORITY_FIELDS, *_ZERO_AUTHORITY_FIELDS))
def test_every_zero_authority_field_fails_closed_in_both_codec_directions(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    replacement: object = True if field in _FALSE_AUTHORITY_FIELDS else 1
    tampered = receipt.model_copy(update={field: replacement})
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(tampered),
    )

    payload = receipt.model_dump(mode="json")
    payload[field] = replacement
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(payload)
        ),
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("current_gate", "AUTOMATED_GATE"),
        ("provider_state", "AUTHORIZED"),
        ("present_currentness_asserted", True),
        ("usage_restriction", "AUTOMATED_EXECUTION_ALLOWED"),
        ("as_of_assessment_sha256", "0" * 64),
        ("limitation_codes", ("SOURCE_AUTHENTICITY_NOT_PROVEN",)),
        ("receipt_purpose", "CURRENT_AUTHORITY_RECEIPT"),
        ("status", "AUTHORIZED"),
    ),
)
def test_encoder_rejects_every_remaining_gate_digest_limitation_and_status_drift(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
    replacement: object,
) -> None:
    tampered = _receipt(upstream, bundle, chains).model_copy(update={field: replacement})
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(tampered),
    )


@pytest.mark.parametrize(
    "field",
    ("limitation_codes", "recorded_blocking_categories"),
)
def test_encoder_rejects_extremely_deep_tuple_state_without_recursion_leakage(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
) -> None:
    tampered = _receipt(upstream, bundle, chains).model_copy(update={field: _deep_tuple(2_048)})
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(tampered),
    )


def test_encoder_rejects_subject_closure_redirected_to_a_receipt_without_recursion_leakage(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    tampered = receipt.model_copy(update={"subject_closure": receipt})
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(tampered),
    )


def test_public_surface_signatures_and_error_order_are_exact() -> None:
    encode_signature = inspect.signature(
        encode_fresh_status_record_as_of_assessment_receipt_v1_json
    )
    parse_signature = inspect.signature(parse_fresh_status_record_as_of_assessment_receipt_v1_json)
    assert tuple(encode_signature.parameters) == ("receipt",)
    assert tuple(parse_signature.parameters) == ("raw",)
    for parameter in (
        *encode_signature.parameters.values(),
        *parse_signature.parameters.values(),
    ):
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert parameter.default is inspect.Parameter.empty
    assert inspect.get_annotations(
        encode_fresh_status_record_as_of_assessment_receipt_v1_json,
        eval_str=True,
    ) == {
        "receipt": CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
        "return": bytes,
    }
    assert inspect.get_annotations(
        parse_fresh_status_record_as_of_assessment_receipt_v1_json,
        eval_str=True,
    ) == {
        "raw": bytes,
        "return": CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    }

    assert tuple(codec_module.__all__) == (
        "FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1",
        "RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error",
        "encode_fresh_status_record_as_of_assessment_receipt_v1_json",
        "parse_fresh_status_record_as_of_assessment_receipt_v1_json",
    )
    assert get_args(FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1) == (
        "RECEIPT_INPUT_CONTRACT_INVALID",
        "DOCUMENT_BYTES_CONTRACT_INVALID",
        "DOCUMENT_JSON_INVALID",
        "DOCUMENT_ROOT_INVALID",
        "DOCUMENT_DEPTH_EXCEEDED",
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        "DOCUMENT_NOT_CANONICAL",
        "INTERNAL_CODEC_INCONSISTENCY",
    )


def test_encoder_and_parser_do_not_call_each_other_publicly(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    raw = _independent_canonical_document(receipt)
    parse_calls = 0

    def unexpected_parse(_raw: bytes) -> None:
        nonlocal parse_calls
        parse_calls += 1
        raise AssertionError("encoder must not call the public parser")

    monkeypatch.setattr(
        codec_module,
        "parse_fresh_status_record_as_of_assessment_receipt_v1_json",
        unexpected_parse,
    )
    assert encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt) == raw
    assert parse_calls == 0

    encode_calls = 0

    def unexpected_encode(_receipt: object) -> None:
        nonlocal encode_calls
        encode_calls += 1
        raise AssertionError("parser must not call the public encoder")

    monkeypatch.setattr(
        codec_module,
        "encode_fresh_status_record_as_of_assessment_receipt_v1_json",
        unexpected_encode,
    )
    assert parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw) == receipt
    assert encode_calls == 0


@pytest.mark.parametrize(
    "invalid",
    (
        None,
        {},
        "{}",
        b"{}",
        bytearray(b"{}"),
        memoryview(b"{}"),
        object(),
    ),
)
def test_encoder_requires_the_exact_receipt_model_type(invalid: object) -> None:
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(invalid),  # type: ignore[arg-type]
    )


def test_encoder_rejects_subclasses_without_coercion(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    class ReceiptSubclass(CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1):
        pass

    receipt = _receipt(upstream, bundle, chains)
    subclass = ReceiptSubclass.model_validate(receipt.model_dump(mode="python"), strict=True)
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(subclass),
    )


def test_encoder_type_gate_does_not_invoke_attacker_methods() -> None:
    class Trap:
        def model_dump(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("model_dump must remain unreachable")

        def __str__(self) -> str:
            raise AssertionError("str must remain unreachable")

        def __bytes__(self) -> bytes:
            raise AssertionError("bytes must remain unreachable")

    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(Trap()),  # type: ignore[arg-type]
    )


def test_encoder_strictly_revalidates_tampered_and_hidden_model_state(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    tampered = receipt.model_copy(update={"receipt_id": "invalid"})
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(tampered),
    )

    hidden = _receipt(upstream, bundle, chains)
    object.__setattr__(hidden, "__pydantic_private__", {"synthetic_hidden": "state"})
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(hidden),
    )


def test_encoder_rejects_nonfield_state_in_the_receipt_instance_dictionary(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    object.__setattr__(receipt, "synthetic_hidden", "state")
    assert (
        "synthetic_hidden"
        not in CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_fields
    )
    assert receipt.__dict__["synthetic_hidden"] == "state"
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )


def test_encoder_rejects_an_instance_dictionary_key_without_invoking_hash_or_equality(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    class KeyTrap:
        armed = False
        calls = 0

        def __hash__(self) -> int:
            if self.armed:
                self.calls += 1
                raise AssertionError("hidden dictionary key hash must remain unreachable")
            return hash("schema_version")

        def __eq__(self, _other: object) -> bool:
            if self.armed:
                self.calls += 1
                raise AssertionError("hidden dictionary key equality must remain unreachable")
            return False

    receipt = _receipt(upstream, bundle, chains)
    trap = KeyTrap()
    receipt.__dict__[trap] = "synthetic hidden state"
    trap.calls = 0
    trap.armed = True
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )
    assert trap.calls == 0


def test_encoder_rejects_a_fields_set_member_without_invoking_hash_or_equality(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    class MemberTrap:
        armed = False
        calls = 0

        def __hash__(self) -> int:
            if self.armed:
                self.calls += 1
                raise AssertionError("fields-set member hash must remain unreachable")
            return hash("schema_version")

        def __eq__(self, _other: object) -> bool:
            if self.armed:
                self.calls += 1
                raise AssertionError("fields-set member equality must remain unreachable")
            return False

    receipt = _receipt(upstream, bundle, chains)
    trap = MemberTrap()
    receipt.__pydantic_fields_set__.add(trap)  # type: ignore[arg-type]
    trap.calls = 0
    trap.armed = True
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )
    assert trap.calls == 0


def test_encoder_rejects_a_hidden_model_dump_trap_without_calling_it(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    calls = 0

    def hidden_model_dump_trap(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("hidden model_dump callback must remain unreachable")

    object.__setattr__(receipt, "model_dump", hidden_model_dump_trap)
    assert receipt.__dict__["model_dump"] is hidden_model_dump_trap
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )
    assert calls == 0


@pytest.mark.parametrize("target", ("receipt", "subject_closure"))
def test_encoder_rejects_a_hidden_pydantic_serializer_trap_without_calling_it(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    target: str,
) -> None:
    class SerializerTrap:
        calls = 0

        def to_python(self, *_args: object, **_kwargs: object) -> object:
            self.calls += 1
            raise AssertionError("hidden serializer to_python must remain unreachable")

        def to_json(self, *_args: object, **_kwargs: object) -> bytes:
            self.calls += 1
            raise AssertionError("hidden serializer to_json must remain unreachable")

    receipt = _receipt(upstream, bundle, chains)
    model = receipt if target == "receipt" else receipt.subject_closure
    trap = SerializerTrap()
    object.__setattr__(model, "__pydantic_serializer__", trap)
    assert model.__dict__["__pydantic_serializer__"] is trap
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )
    assert trap.calls == 0


@pytest.mark.parametrize("target", ("receipt", "subject_closure"))
def test_encoder_rejects_tampered_pydantic_fields_set_at_every_model_level(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    target: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    model = receipt if target == "receipt" else receipt.subject_closure
    assert model.__pydantic_fields_set__
    object.__setattr__(model, "__pydantic_fields_set__", set())
    assert model.__pydantic_fields_set__ == set()
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )


def test_encoder_input_failure_precedes_canonical_rendering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def unexpected_render(_receipt: object) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("canonical rendering must remain unreachable")

    monkeypatch.setattr(codec_module, "_canonical_document", unexpected_render)
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json({}),  # type: ignore[arg-type]
    )
    assert calls == 0


@pytest.mark.parametrize("hidden_kind", ("private", "nonfield", "fields_set"))
def test_encoder_hidden_state_failure_precedes_canonical_rendering(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    hidden_kind: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    if hidden_kind == "private":
        object.__setattr__(receipt, "__pydantic_private__", {"synthetic": "state"})
    elif hidden_kind == "nonfield":
        object.__setattr__(receipt, "synthetic_hidden", "state")
    else:
        object.__setattr__(receipt, "__pydantic_fields_set__", set())
    calls = 0

    def unexpected_render(_receipt: object) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("canonical renderer must remain unreachable for hidden state")

    monkeypatch.setattr(codec_module, "_canonical_document", unexpected_render)
    _assert_codec_error(
        "RECEIPT_INPUT_CONTRACT_INVALID",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )
    assert calls == 0


@pytest.mark.parametrize(
    "invalid_document",
    (
        b"",
        b"\xef\xbb\xbf{}\n",
        b"{}\n\n",
        b"{}\r\n",
        b"x" * (FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES + 1),
    ),
    ids=("empty", "bom", "double-lf", "crlf", "oversize"),
)
def test_encoder_internal_document_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    invalid_document: bytes,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    monkeypatch.setattr(codec_module, "_canonical_document", lambda _receipt: invalid_document)
    _assert_codec_error(
        "INTERNAL_CODEC_INCONSISTENCY",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )


@pytest.mark.parametrize("failure_type", (ValueError, UnicodeError))
def test_encoder_maps_canonical_renderer_domain_failures_to_internal_error(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    failure_type: type[Exception],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    failure = failure_type("synthetic canonical renderer failure")

    def fail_render(_receipt: object) -> bytes:
        raise failure

    monkeypatch.setattr(codec_module, "_canonical_document", fail_render)
    error = _assert_codec_error(
        "INTERNAL_CODEC_INCONSISTENCY",
        lambda: encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt),
    )
    assert error.__cause__ is failure


@pytest.mark.parametrize(
    "invalid_document",
    ("not-bytes", bytearray(b"not-bytes"), object()),
    ids=("str", "bytearray", "object"),
)
@pytest.mark.parametrize("operation", ("encode", "parse"))
def test_nonbytes_canonical_renderer_results_are_internal_codec_errors(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    invalid_document: object,
    operation: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    raw = _independent_canonical_document(receipt)
    monkeypatch.setattr(codec_module, "_canonical_document", lambda _receipt: invalid_document)
    if operation == "encode":

        def callback() -> object:
            return encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)

    else:

        def callback() -> object:
            return parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw)

    _assert_codec_error("INTERNAL_CODEC_INCONSISTENCY", callback)


class _BytesSubclass(bytes):
    pass


@pytest.mark.parametrize(
    "invalid",
    (
        None,
        "{}",
        {},
        bytearray(b"{}"),
        memoryview(b"{}"),
        _BytesSubclass(b"{}"),
        object(),
    ),
)
def test_parser_accepts_only_exact_builtin_bytes(invalid: object) -> None:
    _assert_codec_error(
        "DOCUMENT_BYTES_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(invalid),  # type: ignore[arg-type]
    )


def test_parser_type_gate_does_not_invoke_attacker_methods() -> None:
    class Trap:
        def __len__(self) -> int:
            raise AssertionError("len must remain unreachable")

        def decode(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("decode must remain unreachable")

        def __bytes__(self) -> bytes:
            raise AssertionError("bytes must remain unreachable")

        def __str__(self) -> str:
            raise AssertionError("str must remain unreachable")

    _assert_codec_error(
        "DOCUMENT_BYTES_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(Trap()),  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    "invalid",
    (
        b"",
        b"\xef\xbb\xbf{}\n",
        b" " * (FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES + 1),
    ),
    ids=("empty", "bom", "oversize"),
)
def test_byte_precheck_precedes_json_decode(
    monkeypatch: pytest.MonkeyPatch,
    invalid: bytes,
) -> None:
    calls = 0

    def unexpected_loads(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("JSON decode must remain unreachable")

    monkeypatch.setattr(codec_module.json, "loads", unexpected_loads)
    _assert_codec_error(
        "DOCUMENT_BYTES_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(invalid),
    )
    assert calls == 0


def test_exact_size_limit_is_admitted_to_json_and_one_extra_byte_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES == 65_536
    real_loads = json.loads
    calls = 0

    def counted_loads(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return real_loads(*args, **kwargs)

    monkeypatch.setattr(codec_module.json, "loads", counted_loads)
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(b" " * 65_536),
    )
    assert calls == 1
    _assert_codec_error(
        "DOCUMENT_BYTES_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(b" " * 65_537),
    )
    assert calls == 1


@pytest.mark.parametrize(
    "invalid",
    (
        b"\x80",
        b"\xc0\xaf",
        b"\xed\xa0\x80",
        b"\xe2\x82",
        b"\xff\xfe{\x00}\x00",
        b"{\x00}",
    ),
)
def test_invalid_utf8_and_embedded_nul_are_json_invalid(invalid: bytes) -> None:
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(invalid),
    )


@pytest.mark.parametrize(
    "invalid",
    (
        b" ",
        b"{",
        b"{} trailing",
        b"{}{}",
        b'{"x": 1,}',
        b'{/*comment*/"x":1}',
        b"\n\xef\xbb\xbf{}",
    ),
)
def test_invalid_json_syntax_is_rejected(invalid: bytes) -> None:
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(invalid),
    )


def test_duplicate_keys_are_rejected_at_every_object_depth(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    raw = _independent_canonical_document(receipt)
    receipt_id_json = json.dumps(receipt.receipt_id).encode("utf-8")
    top_level = b'{"receipt_id":' + receipt_id_json + b"," + raw[1:]
    escaped_equivalent = rb'{"receipt\u005fid":' + receipt_id_json + b"," + raw[1:]
    closure_line = f'"closure_id": "{receipt.subject_closure.closure_id}"'.encode()
    nested = raw.replace(closure_line, closure_line + b",\n    " + closure_line, 1)
    assert nested != raw

    for changed in (top_level, escaped_equivalent, nested):
        _assert_codec_error(
            "DOCUMENT_JSON_INVALID",
            lambda changed=changed: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
                changed
            ),
        )


@pytest.mark.parametrize(
    "constant",
    (b"NaN", b"Infinity", b"-Infinity", b"1e1000000", b"-1e1000000"),
)
def test_nonfinite_json_numbers_are_rejected_before_contract_validation(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    constant: bytes,
) -> None:
    raw = _independent_canonical_document(_receipt(upstream, bundle, chains))
    changed = raw.replace(
        b'"authorized_cost_cny": 0',
        b'"authorized_cost_cny": ' + constant,
        1,
    )
    assert changed != raw
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(changed),
    )


def test_non_nfc_strings_keys_and_surrogates_fail_at_json_admission(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    non_nfc_value = {**payload, "receipt_purpose": "Cafe\u0301"}
    non_nfc_key = {**payload, "Cafe\u0301": True}
    surrogate_key = rb'{"\ud800":0,' + _render_payload(payload)[1:]

    for changed in (
        _render_payload(non_nfc_value),
        _render_payload(non_nfc_key),
        surrogate_key,
    ):
        _assert_codec_error(
            "DOCUMENT_JSON_INVALID",
            lambda changed=changed: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
                changed
            ),
        )

    nfc_but_extra = {**payload, "Café": True}
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(nfc_but_extra)
        ),
    )


@pytest.mark.parametrize(
    "invalid",
    (b"[]", b"null", b'"object"', b"0", b"true"),
)
def test_json_root_must_be_one_object(invalid: bytes) -> None:
    _assert_codec_error(
        "DOCUMENT_ROOT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(invalid),
    )


def test_json_depth_32_reaches_contract_and_33_fails_depth(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    assert FRESH_STATUS_JSON_MAX_DEPTH == 32
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    at_limit = {**payload, "unexpected": _nested_array(31)}
    over_limit = {**payload, "unexpected": _nested_array(32)}
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(at_limit)
        ),
    )
    _assert_codec_error(
        "DOCUMENT_DEPTH_EXCEEDED",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(over_limit)
        ),
    )


def test_extremely_deep_valid_object_uses_fallback_and_reports_depth() -> None:
    raw = _deep_object_document(2_048)
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_DEPTH_EXCEEDED",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_extremely_deep_object_with_a_valid_very_long_integer_reports_depth() -> None:
    assert len(_FIVE_THOUSAND_DIGIT_JSON_INTEGER) == 5_000
    raw = _deep_object_document(2_048, _FIVE_THOUSAND_DIGIT_JSON_INTEGER)
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_DEPTH_EXCEEDED",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_top_level_valid_very_long_integer_preserves_root_precedence() -> None:
    assert len(_FIVE_THOUSAND_DIGIT_JSON_INTEGER) == 5_000
    _assert_codec_error(
        "DOCUMENT_ROOT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _FIVE_THOUSAND_DIGIT_JSON_INTEGER
        ),
    )


def test_shallow_receipt_very_long_integer_reaches_receipt_contract(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    raw = _independent_canonical_document(_receipt(upstream, bundle, chains))
    changed = raw.replace(
        b'"authorized_attempts": 0',
        b'"authorized_attempts": ' + _FIVE_THOUSAND_DIGIT_JSON_INTEGER,
        1,
    )
    assert changed != raw
    assert len(changed) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(changed),
    )


def test_extremely_deep_valid_top_level_array_preserves_root_precedence() -> None:
    raw = _deep_array_document(2_048)
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_ROOT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


@pytest.mark.parametrize(
    "malformation",
    ("missing-close", "bad-token", "trailing-comma"),
)
def test_extremely_deep_malformed_documents_remain_json_invalid(
    malformation: str,
) -> None:
    levels = 2_048
    if malformation == "missing-close":
        raw = b'{"x":' * levels + b"0" + b"}" * (levels - 1)
    elif malformation == "bad-token":
        raw = _deep_object_document(levels, b"@")
    else:
        raw = _deep_object_document(levels, b"0,")
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_extremely_deep_duplicate_key_remains_json_invalid() -> None:
    raw = _deep_object_document(2_048, b'{"duplicate":0,"duplicate":1}')
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


@pytest.mark.parametrize("constant", (b"NaN", b"Infinity", b"1e1000000", b"-1e1000000"))
def test_extremely_deep_nonfinite_number_remains_json_invalid(constant: bytes) -> None:
    raw = _deep_object_document(2_048, constant)
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


@pytest.mark.parametrize("string_value", (rb'"Cafe\u0301"', rb'"\ud800"'))
def test_extremely_deep_noncanonical_unicode_remains_json_invalid(
    string_value: bytes,
) -> None:
    raw = _deep_object_document(2_048, string_value)
    assert len(raw) <= FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_primary_json_recursion_failure_at_shallow_valid_depth_is_internal(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    raw = _independent_canonical_document(_receipt(upstream, bundle, chains))

    def synthetic_primary_recursion(*_args: object, **_kwargs: object) -> object:
        raise RecursionError("synthetic shallow primary decoder recursion")

    monkeypatch.setattr(codec_module.json, "loads", synthetic_primary_recursion)
    _assert_codec_error(
        "INTERNAL_CODEC_INCONSISTENCY",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_root_failure_precedes_depth_for_a_deep_top_level_array() -> None:
    raw = _render_payload(_nested_array(33), indent=None)
    _assert_codec_error(
        "DOCUMENT_ROOT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_json_admission_precedes_root_depth_and_receipt_contract(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    deep = _render_payload({**payload, "unexpected": _nested_array(32)})
    duplicate_and_deep = b'{"schema_version":"1.0.0",' + deep[1:]
    assert duplicate_and_deep.count(b'"schema_version"') == 2
    _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(duplicate_and_deep),
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("authorized_attempts", False),
        ("authorized_attempts", 0.0),
        ("authorized_attempts", "0"),
        ("authorized_attempts", 1),
        ("execution_authorized", 0),
        ("execution_authorized", "false"),
        ("present_currentness_asserted", None),
        ("limitation_codes", None),
    ),
)
def test_decoded_receipt_uses_exact_strict_scalar_and_collection_types(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
    replacement: object,
) -> None:
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    payload[field] = replacement
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(payload)
        ),
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("provided_record_joint_replay_consistent", 1),
        ("provided_record_joint_replay_consistent", 1.0),
        ("provided_record_joint_replay_consistent", "true"),
        ("explicit_as_of_window_assessment_consistent", 1),
        ("explicit_as_of_window_assessment_consistent", 1.0),
        ("explicit_as_of_window_assessment_consistent", "true"),
    ),
)
def test_parser_never_coerces_raw_consistency_scalars_before_strict_contract(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    field: str,
    replacement: object,
) -> None:
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    payload[field] = replacement
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(payload)
        ),
    )


def test_canonical_json_arrays_round_trip_to_the_exact_frozen_tuple_fields(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    raw = encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)
    decoded = json.loads(raw)
    tuple_fields = (
        "recorded_blocking_categories",
        "recorded_indeterminate_categories",
        "limitation_codes",
    )
    assert all(type(decoded[field]) is list for field in tuple_fields)
    parsed = parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw)
    assert all(type(getattr(parsed, field)) is tuple for field in tuple_fields)
    assert all(getattr(parsed, field) == getattr(receipt, field) for field in tuple_fields)


def test_negative_zero_is_semantically_zero_but_not_canonical(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    raw = _independent_canonical_document(_receipt(upstream, bundle, chains))
    changed = raw.replace(
        b'"authorized_cost_cny": 0',
        b'"authorized_cost_cny": -0',
        1,
    )
    assert changed != raw
    _assert_codec_error(
        "DOCUMENT_NOT_CANONICAL",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(changed),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "extra",
        "missing",
        "receipt_id",
        "assessment_digest",
        "assessment_projection_reid",
        "zero_authority",
        "limitations",
        "category_order",
        "purpose",
        "status",
    ),
)
def test_parser_rejects_structurally_canonical_but_invalid_receipt_contracts(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    mutation: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    payload = receipt.model_dump(mode="json")
    if mutation == "extra":
        payload["unexpected"] = True
    elif mutation == "missing":
        payload.pop("receipt_id")
    elif mutation == "receipt_id":
        payload["receipt_id"] = "invalid"
    elif mutation == "assessment_digest":
        payload["as_of_assessment_sha256"] = "0" * 64
    elif mutation == "assessment_projection_reid":
        old_digest = payload["coverage_set_sha256"]
        payload["coverage_set_sha256"] = "0" * 64 if old_digest != "0" * 64 else "1" * 64
        payload["receipt_id"] = stable_id(
            _RECEIPT_ID_KIND,
            {key: value for key, value in payload.items() if key != "receipt_id"},
        )
    elif mutation == "zero_authority":
        payload["provider_state"] = "AUTHORIZED"
    elif mutation == "limitations":
        payload["limitation_codes"] = list(reversed(payload["limitation_codes"]))
    elif mutation == "category_order":
        categories = list(payload["recorded_indeterminate_categories"])
        assert len(categories) > 1
        payload["recorded_indeterminate_categories"] = list(reversed(categories))
    elif mutation == "purpose":
        payload["receipt_purpose"] = "CURRENT_AUTHORITY_RECEIPT"
    else:
        payload["status"] = "AUTHORIZED"
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(payload)
        ),
    )


@pytest.mark.parametrize(
    "missing",
    ("profile", "execution_authorized", "subject_closure.closure_profile"),
)
def test_parser_rejects_missing_defaulted_fields_as_contract_not_canonical_drift(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    missing: str,
) -> None:
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    if missing == "subject_closure.closure_profile":
        subject_closure = payload["subject_closure"]
        assert isinstance(subject_closure, dict)
        subject_closure.pop("closure_profile")
    else:
        payload.pop(missing)
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(
            _render_payload(payload)
        ),
    )


@pytest.mark.parametrize(
    "variant",
    (
        "no_lf",
        "double_lf",
        "crlf",
        "leading_space",
        "trailing_space",
        "minified",
        "four_spaces",
        "reordered",
        "escaped_ascii",
    ),
)
def test_every_semantically_equivalent_noncanonical_document_is_rejected(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    variant: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    raw = _independent_canonical_document(receipt)
    payload = receipt.model_dump(mode="json")
    variants = {
        "no_lf": raw[:-1],
        "double_lf": raw + b"\n",
        "crlf": raw.replace(b"\n", b"\r\n"),
        "leading_space": b" " + raw,
        "trailing_space": raw + b" ",
        "minified": _render_payload(payload, indent=None),
        "four_spaces": _render_payload(payload, indent=4),
        "reordered": _render_payload(payload, sort_keys=False),
        "escaped_ascii": raw.replace(b"HUMAN_GATE", b"HUMAN_\\u0047ATE", 1),
    }
    changed = variants[variant]
    assert changed != raw
    _assert_codec_error(
        "DOCUMENT_NOT_CANONICAL",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(changed),
    )


def test_receipt_contract_failure_precedes_canonical_byte_comparison(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    payload = _receipt(upstream, bundle, chains).model_dump(mode="json")
    payload["unexpected"] = True
    noncanonical = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    _assert_codec_error(
        "DOCUMENT_RECEIPT_CONTRACT_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(noncanonical),
    )


def test_parser_accepts_a_self_consistent_receipt_without_claiming_closure_match(
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    alternate = _build_alternate_upstream()
    alternate_graph = _build_graph(alternate)
    alternate_bundle = _build_bundle(
        alternate,
        (alternate_graph.target_a, alternate_graph.target_b),
    )
    alternate_chains = (
        _chain(
            (alternate_graph.genesis_a, alternate_graph.target_a),
            (alternate_graph.target_a,),
        ),
        _chain((alternate_graph.target_b,), (alternate_graph.target_b,)),
    )
    alternate_receipt = _build_receipt(
        alternate,
        alternate_bundle,
        alternate_chains,
    )
    parsed = parse_fresh_status_record_as_of_assessment_receipt_v1_json(
        encode_fresh_status_record_as_of_assessment_receipt_v1_json(alternate_receipt)
    )
    assert parsed == alternate_receipt
    assert parsed.receipt_id != _receipt(upstream, bundle, chains).receipt_id
    with pytest.raises(RealAssetFreshStatusRecordAsOfAssessmentReceiptV30Error) as captured:
        _verify_receipt(upstream, bundle, chains, parsed)
    assert captured.value.code == "RECEIPT_REPLAY_MISMATCH"


def test_codec_does_not_call_slice_five_or_either_slice_six_public_operation(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
) -> None:
    import sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 as receipt_module
    import sdc.real_asset_fresh_status_record_as_of_assessment_v30 as assessment_module

    receipt = _receipt(upstream, bundle, chains)
    raw = _independent_canonical_document(receipt)
    forbidden_local_names = {
        "assess_fresh_status_evidence_record_as_of_v1",
        "build_fresh_status_record_as_of_assessment_receipt_v1",
        "verify_fresh_status_record_as_of_assessment_receipt_closure_v1",
    }
    assert forbidden_local_names.isdisjoint(vars(codec_module))
    calls = {"assessment": 0, "builder": 0, "verifier": 0}

    def unexpected_assessment(**_: object) -> None:
        calls["assessment"] += 1
        raise AssertionError("codec must not call the public Slice 5 assessment")

    def unexpected_builder(**_: object) -> None:
        calls["builder"] += 1
        raise AssertionError("codec must not call the public Slice 6 builder")

    def unexpected_verifier(**_: object) -> None:
        calls["verifier"] += 1
        raise AssertionError("codec must not replay the upstream closure")

    monkeypatch.setattr(
        assessment_module,
        "assess_fresh_status_evidence_record_as_of_v1",
        unexpected_assessment,
    )
    monkeypatch.setattr(
        receipt_module,
        "build_fresh_status_record_as_of_assessment_receipt_v1",
        unexpected_builder,
    )
    monkeypatch.setattr(
        receipt_module,
        "verify_fresh_status_record_as_of_assessment_receipt_closure_v1",
        unexpected_verifier,
    )
    assert encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt) == raw
    assert parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw) == receipt
    assert calls == {"assessment": 0, "builder": 0, "verifier": 0}


@pytest.mark.parametrize(
    "failure_type",
    (RuntimeError, MemoryError, KeyboardInterrupt, SystemExit),
)
@pytest.mark.parametrize("operation", ("encode", "parse"))
def test_unrelated_runtime_memory_and_process_control_failures_propagate(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    failure_type: type[BaseException],
    operation: str,
) -> None:
    receipt = _receipt(upstream, bundle, chains)
    raw = _independent_canonical_document(receipt)
    failure = failure_type("synthetic non-domain failure")
    if operation == "encode":
        monkeypatch.setattr(
            codec_module,
            "_canonical_document",
            lambda _receipt: (_ for _ in ()).throw(failure),
        )

        def callback() -> object:
            return encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)

    else:
        monkeypatch.setattr(
            codec_module.json,
            "loads",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(failure),
        )

        def callback() -> object:
            return parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw)

    with pytest.raises(failure_type) as captured:
        callback()
    assert captured.value is failure


@pytest.mark.parametrize(
    "invalid_document",
    (
        b"",
        b"\xef\xbb\xbf{}\n",
        b"{}\n\n",
        b"{}\r\n",
        b"x" * (FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES + 1),
    ),
    ids=("empty", "bom", "double-lf", "crlf", "oversize"),
)
def test_parser_detects_impossible_internal_canonical_rendering_drift(
    monkeypatch: pytest.MonkeyPatch,
    upstream: Upstream,
    bundle: FreshBundle,
    chains: tuple[FreshStatusRecordChainInputV1, ...],
    invalid_document: bytes,
) -> None:
    raw = _independent_canonical_document(_receipt(upstream, bundle, chains))
    monkeypatch.setattr(codec_module, "_canonical_document", lambda _receipt: invalid_document)
    _assert_codec_error(
        "INTERNAL_CODEC_INCONSISTENCY",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )


def test_error_messages_do_not_echo_raw_document_bytes() -> None:
    raw = b'{"synthetic_secret_material":"DO_NOT_ECHO"'
    error = _assert_codec_error(
        "DOCUMENT_JSON_INVALID",
        lambda: parse_fresh_status_record_as_of_assessment_receipt_v1_json(raw),
    )
    assert "DO_NOT_ECHO" not in str(error)


def test_codec_adds_no_schema_and_all_eighty_three_registered_schemas_stay_exact() -> None:
    assert len(MODELS) == 83
    assert len({model.__name__ for model in MODELS}) == 83
    expected_names = {f"{model.__name__}.schema.json" for model in MODELS}
    schema_paths = tuple(Path("schemas").glob("*.schema.json"))
    assert len(schema_paths) == 83
    assert {path.name for path in schema_paths} == expected_names
    assert not any("Codec" in path.name for path in schema_paths)
    for model in MODELS:
        path = Path("schemas") / f"{model.__name__}.schema.json"
        expected = (json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        actual = path.read_bytes()
        without_crlf = actual.replace(b"\r\n", b"")
        assert b"\r" not in without_crlf, model.__name__
        if b"\r\n" in actual:
            assert b"\n" not in without_crlf, model.__name__
            actual = actual.replace(b"\r\n", b"\n")
        assert actual == expected, model.__name__


def test_codec_module_is_ast_locked_to_pure_memory_and_no_implicit_clock() -> None:
    source = codec_module.__file__
    assert source is not None
    tree = ast.parse(Path(source).read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    called_names: set[str] = set()
    loaded_names: set[str] = set()

    def dotted_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = dotted_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
            imported_modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name:
                called_names.add(name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loaded_names.add(node.id)

    forbidden_lower_layer_names = {
        "assess_fresh_status_evidence_record_as_of_v1",
        "build_fresh_status_record_as_of_assessment_receipt_v1",
        "verify_fresh_status_record_as_of_assessment_receipt_closure_v1",
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert forbidden_lower_layer_names.isdisjoint(imported_names)
    assert forbidden_lower_layer_names.isdisjoint(loaded_names)
    assert not any(
        called.rsplit(".", maxsplit=1)[-1] in forbidden_lower_layer_names for called in called_names
    )
    assert "sdc.real_asset_fresh_status_record_as_of_assessment_v30" not in imported_modules
    assert forbidden_lower_layer_names.isdisjoint(vars(codec_module))

    assert {module.split(".", maxsplit=1)[0] for module in imported_modules} <= {
        "__future__",
        "json",
        "pydantic",
        "sdc",
        "typing",
        "unicodedata",
    }
    forbidden_components = {
        "argparse",
        "asyncio",
        "click",
        "credential",
        "database",
        "datetime",
        "db",
        "glob",
        "http",
        "httpx",
        "importlib",
        "io",
        "keyring",
        "logging",
        "mmap",
        "multiprocessing",
        "os",
        "pathlib",
        "persistence",
        "pickle",
        "platform",
        "provider",
        "queue",
        "random",
        "requests",
        "runtime",
        "secrets",
        "shelve",
        "shutil",
        "socket",
        "sqlite3",
        "subprocess",
        "sys",
        "tempfile",
        "threading",
        "time",
        "typer",
        "urllib",
        "uuid",
        "worker",
        "zoneinfo",
    }

    def has_forbidden_component(value: str) -> bool:
        return any(
            component == forbidden or component.startswith(f"{forbidden}_")
            for component in value.lower().split(".")
            for forbidden in forbidden_components
        )

    assert not any(has_forbidden_component(module) for module in imported_modules)
    assert not any(has_forbidden_component(name) for name in called_names)
    assert {
        "__import__",
        "builtins.compile",
        "builtins.eval",
        "builtins.exec",
        "builtins.input",
        "builtins.open",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }.isdisjoint(called_names)
    assert not any(
        name.endswith(
            (
                ".now",
                ".utcnow",
                ".today",
                ".time",
                ".monotonic",
                ".perf_counter",
                ".process_time",
                ".sleep",
                ".read",
                ".write",
                ".stat",
            )
        )
        for name in called_names
    )
    assert "__file__" not in loaded_names
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith))
        for node in ast.walk(tree)
    )
    assert not any(
        name.lower().startswith(
            (
                "authorize",
                "cli_",
                "extract_",
                "file_",
                "finalize_",
                "path_",
                "provider_",
                "read_",
                "write_",
            )
        )
        for name in codec_module.__all__
    )
