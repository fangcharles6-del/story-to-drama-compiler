"""Pure canonical JSON codec for the immutable v3.0 historical assessment Receipt.

The codec accepts only an in-memory Receipt model or bounded in-memory bytes.  It performs no
filesystem, path, stream, CLI, environment, clock, network, Provider, persistence, credential,
entitlement, or execution operation.  Successful encoding or parsing proves only exact Receipt
contract and canonical-document consistency; it does not replay the upstream closure, establish
present currentness, prove source authenticity or completeness, or grant authority to act.
"""

from __future__ import annotations

import json
import unicodedata
from json.decoder import scanstring  # type: ignore[attr-defined]
from typing import Literal, Never

from pydantic import BaseModel, ValidationError

from sdc.real_asset_fresh_status_evidence_v30 import (
    FRESH_STATUS_JSON_MAX_DEPTH,
    FreshStatusSubjectClosureV1,
)
from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES,
    CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
)

FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1 = Literal[
    "RECEIPT_INPUT_CONTRACT_INVALID",
    "DOCUMENT_BYTES_CONTRACT_INVALID",
    "DOCUMENT_JSON_INVALID",
    "DOCUMENT_ROOT_INVALID",
    "DOCUMENT_DEPTH_EXCEEDED",
    "DOCUMENT_RECEIPT_CONTRACT_INVALID",
    "DOCUMENT_NOT_CANONICAL",
    "INTERNAL_CODEC_INCONSISTENCY",
]


class RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(RuntimeError):
    """The pure canonical Receipt document codec failed closed."""

    code: FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1

    def __init__(
        self,
        code: FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1,
        message: str,
    ) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class _JsonAdmissionError(ValueError):
    """One decoded JSON value violates the canonical JSON admission boundary."""


class _UnsafeModelStateError(ValueError):
    """One supplied model contains state outside its exact declared contract fields."""


class _JsonContainerState:
    """One iterative fallback-parser container frame."""

    kind: Literal["object", "array"]
    state: str
    keys: set[str]

    def __init__(self, kind: Literal["object", "array"]) -> None:
        self.kind = kind
        self.state = "key_or_end" if kind == "object" else "value_or_end"
        self.keys = set()


_JSON_INTEGER_OUTSIDE_RECEIPT_DOMAIN = object()


def _raise(
    code: FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1,
    message: str,
) -> Never:
    raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(code, message)


def _canonical_document(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> bytes:
    return (
        json.dumps(
            _safe_model_projection(receipt, json_mode=True),
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _reject_json_constant(_value: str) -> Never:
    raise _JsonAdmissionError("non-finite JSON number is forbidden")


def _parse_finite_json_float(value: str) -> float:
    try:
        parsed = float(value)
    except (OverflowError, ValueError) as exc:
        raise _JsonAdmissionError("JSON floating-point number is invalid") from exc
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        raise _JsonAdmissionError("non-finite JSON number is forbidden")
    return parsed


def _parse_receipt_json_int(value: str) -> object:
    if value == "0" or value == "-0":
        return 0
    return _JSON_INTEGER_OUTSIDE_RECEIPT_DOMAIN


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _JsonAdmissionError("duplicate JSON key is forbidden")
        result[key] = value
    return result


def _require_canonical_string(value: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _JsonAdmissionError("JSON strings must contain Unicode scalar values") from exc
    if unicodedata.normalize("NFC", value) != value:
        raise _JsonAdmissionError("JSON strings and object keys must use Unicode NFC")


def _inspect_json_tree(root: object) -> int:
    """Validate canonical Unicode and return container depth without recursion."""

    maximum_depth = 0
    pending: list[tuple[object, int]] = [(root, 0)]
    while pending:
        value, parent_depth = pending.pop()
        if type(value) is str:
            assert isinstance(value, str)
            _require_canonical_string(value)
            continue
        if type(value) is dict:
            assert isinstance(value, dict)
            depth = parent_depth + 1
            maximum_depth = max(maximum_depth, depth)
            for key, item in value.items():
                if type(key) is not str:
                    raise _JsonAdmissionError("JSON object key is not a string")
                _require_canonical_string(key)
                pending.append((item, depth))
            continue
        if type(value) is list:
            assert isinstance(value, list)
            depth = parent_depth + 1
            maximum_depth = max(maximum_depth, depth)
            pending.extend((item, depth) for item in value)
    return maximum_depth


def _safe_model_projection(
    value: object,
    *,
    json_mode: bool,
    _model_level: int = 0,
    _seen_models: set[int] | None = None,
) -> object:
    value_type = type(value)
    if (
        value_type is CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
        or value_type is FreshStatusSubjectClosureV1
    ):
        assert isinstance(value, BaseModel)
        if _model_level == 0:
            if value_type is not CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
                raise _UnsafeModelStateError("model graph root is not the exact Receipt type")
        elif _model_level == 1:
            if value_type is not FreshStatusSubjectClosureV1:
                raise _UnsafeModelStateError("Receipt subject closure has the wrong model type")
        else:
            raise _UnsafeModelStateError("Receipt model graph contains a nested model")
        if _seen_models is None:
            _seen_models = set()
        model_identity = id(value)
        if model_identity in _seen_models:
            raise _UnsafeModelStateError("Receipt model graph contains a cycle or alias")
        _seen_models.add(model_identity)

        storage = object.__getattribute__(value, "__dict__")
        fields_set = object.__getattribute__(value, "__pydantic_fields_set__")
        extra = object.__getattribute__(value, "__pydantic_extra__")
        private = object.__getattribute__(value, "__pydantic_private__")
        declared_fields = value_type.model_fields
        declared_names = set(declared_fields)
        if (
            type(storage) is not dict
            or type(fields_set) is not set
            or extra is not None
            or private is not None
        ):
            raise _UnsafeModelStateError("model storage drifted from declared contract fields")
        if any(type(key) is not str for key in storage) or any(
            type(item) is not str for item in fields_set
        ):
            raise _UnsafeModelStateError("model storage names must be exact strings")
        if len(storage) != len(declared_names) or len(fields_set) > len(declared_names):
            raise _UnsafeModelStateError("model storage field count drifted from its contract")
        if set(storage) != declared_names or not fields_set <= declared_names:
            raise _UnsafeModelStateError("model storage drifted from declared contract fields")
        return {
            field: _safe_model_projection(
                storage[field],
                json_mode=json_mode,
                _model_level=(1 if _model_level == 0 and field == "subject_closure" else 2),
                _seen_models=_seen_models,
            )
            for field in declared_fields
        }
    if value_type is tuple:
        assert isinstance(value, tuple)
        if len(value) > 7:
            raise _UnsafeModelStateError("Receipt tuple fields exceed the frozen maximum length")
        if any(type(item) is not str for item in value):
            raise _UnsafeModelStateError(
                "Receipt tuple fields must contain only exact string literals"
            )
        return list(value) if json_mode else value
    if value_type is dict:
        raise _UnsafeModelStateError("Receipt model fields must not contain mappings")
    if value is None or value_type is str or value_type is bool or value_type is int:
        return value
    raise _UnsafeModelStateError("model contains a non-canonical field value type")


def _exact_state_consistent(supplied: object, rebuilt: object) -> bool:
    if type(supplied) is not type(rebuilt):
        return False
    if isinstance(supplied, BaseModel) and isinstance(rebuilt, BaseModel):
        return (
            _exact_state_consistent(supplied.__dict__, rebuilt.__dict__)
            and _exact_state_consistent(
                supplied.__pydantic_fields_set__,
                rebuilt.__pydantic_fields_set__,
            )
            and _exact_state_consistent(supplied.__pydantic_extra__, rebuilt.__pydantic_extra__)
            and _exact_state_consistent(
                supplied.__pydantic_private__,
                rebuilt.__pydantic_private__,
            )
        )
    if isinstance(supplied, dict) and isinstance(rebuilt, dict):
        return supplied.keys() == rebuilt.keys() and all(
            _exact_state_consistent(supplied[key], rebuilt[key]) for key in supplied
        )
    if isinstance(supplied, (list, tuple)) and isinstance(rebuilt, (list, tuple)):
        return len(supplied) == len(rebuilt) and all(
            _exact_state_consistent(supplied_item, rebuilt_item)
            for supplied_item, rebuilt_item in zip(supplied, rebuilt, strict=True)
        )
    return supplied == rebuilt


def _strict_receipt_input(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> tuple[CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1, bytes]:
    if type(receipt) is not CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
        _raise(
            "RECEIPT_INPUT_CONTRACT_INVALID",
            "receipt must be the exact immutable Receipt V1 model type",
        )
    try:
        supplied_projection = _safe_model_projection(receipt, json_mode=False)
    except (AttributeError, TypeError, _UnsafeModelStateError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "RECEIPT_INPUT_CONTRACT_INVALID",
            "receipt contains non-canonical model storage or field state",
        ) from exc
    try:
        rebuilt = CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            supplied_projection,
            strict=True,
        )
    except (AttributeError, TypeError, UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "RECEIPT_INPUT_CONTRACT_INVALID",
            "receipt violates its exact strict immutable contract",
        ) from exc
    if not _exact_state_consistent(receipt, rebuilt) or receipt != rebuilt:
        _raise(
            "RECEIPT_INPUT_CONTRACT_INVALID",
            "receipt changes model state during strict revalidation",
        )
    try:
        rebuilt_document = _canonical_document(rebuilt)
    except (
        AttributeError,
        TypeError,
        UnicodeError,
        _UnsafeModelStateError,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "INTERNAL_CODEC_INCONSISTENCY",
            "a strictly rebuilt Receipt could not be rendered canonically",
        ) from exc
    return rebuilt, rebuilt_document


def encode_fresh_status_record_as_of_assessment_receipt_v1_json(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> bytes:
    """Encode one exact valid Receipt as its bounded canonical UTF-8 JSON document."""

    _, document = _strict_receipt_input(receipt)
    if (
        type(document) is not bytes
        or not document
        or len(document) > FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
        or document.startswith(b"\xef\xbb\xbf")
        or not document.endswith(b"\n")
        or document.endswith(b"\n\n")
        or b"\r" in document
    ):
        _raise(
            "INTERNAL_CODEC_INCONSISTENCY",
            "a strictly valid Receipt did not render as one bounded canonical document",
        )
    return document


def _scan_json_number(text: str, index: int) -> int:
    """Return the exclusive end of one syntactically valid JSON number."""

    length = len(text)
    if text[index] == "-":
        index += 1
        if index >= length:
            raise _JsonAdmissionError("JSON number is invalid")

    if text[index] == "0":
        index += 1
    elif "1" <= text[index] <= "9":
        index += 1
        while index < length and "0" <= text[index] <= "9":
            index += 1
    else:
        raise _JsonAdmissionError("JSON number is invalid")

    if index < length and text[index] == ".":
        index += 1
        fraction_start = index
        while index < length and "0" <= text[index] <= "9":
            index += 1
        if index == fraction_start:
            raise _JsonAdmissionError("JSON number is invalid")

    if index < length and text[index] in "eE":
        index += 1
        if index < length and text[index] in "+-":
            index += 1
        exponent_start = index
        while index < length and "0" <= text[index] <= "9":
            index += 1
        if index == exponent_start:
            raise _JsonAdmissionError("JSON number is invalid")

    return index


def _iter_json_tokens(text: str) -> list[tuple[str, str | None]]:
    index = 0
    length = len(text)
    whitespace = " \t\r\n"
    punctuation = "{}[],:"
    tokens: list[tuple[str, str | None]] = []
    while index < length:
        character = text[index]
        if character in whitespace:
            index += 1
            continue
        if character in punctuation:
            index += 1
            tokens.append((character, None))
            continue
        if character == '"':
            start = index
            index += 1
            while index < length:
                character = text[index]
                if character == '"':
                    index += 1
                    try:
                        decoded, decoded_end = scanstring(
                            text,
                            start + 1,
                            True,
                        )
                    except (UnicodeError, ValueError) as exc:
                        raise _JsonAdmissionError("JSON string token is invalid") from exc
                    if type(decoded) is not str or decoded_end != index:
                        raise _JsonAdmissionError("JSON string token is invalid")
                    _require_canonical_string(decoded)
                    tokens.append(("STRING", decoded))
                    break
                if ord(character) < 0x20:
                    raise _JsonAdmissionError("JSON string contains a control character")
                if character != "\\":
                    index += 1
                    continue
                index += 1
                if index >= length:
                    raise _JsonAdmissionError("JSON string escape is incomplete")
                escape = text[index]
                if escape in '"\\/bfnrt':
                    index += 1
                    continue
                if escape != "u" or index + 4 >= length:
                    raise _JsonAdmissionError("JSON string escape is invalid")
                digits = text[index + 1 : index + 5]
                if len(digits) != 4 or any(
                    digit not in "0123456789abcdefABCDEF" for digit in digits
                ):
                    raise _JsonAdmissionError("JSON Unicode escape is invalid")
                index += 5
            else:
                raise _JsonAdmissionError("JSON string is not terminated")
            continue
        if character == "-" or "0" <= character <= "9":
            start = index
            index = _scan_json_number(text, index)
            token = text[start:index]
            if any(marker in token for marker in ".eE"):
                _parse_finite_json_float(token)
            tokens.append(("SCALAR", None))
            continue
        literal = next(
            (
                candidate
                for candidate in ("true", "false", "null")
                if text.startswith(candidate, index)
            ),
            None,
        )
        if literal is not None:
            index += len(literal)
            tokens.append(("SCALAR", None))
            continue
        raise _JsonAdmissionError("JSON token is invalid")
    return tokens


def _iterative_json_root_and_depth(text: str) -> tuple[str, int]:
    stack: list[_JsonContainerState] = []
    root_kind: str | None = None
    root_complete = False
    maximum_depth = 0

    def begin_value(token_kind: str) -> None:
        nonlocal maximum_depth, root_complete, root_kind
        if token_kind not in {"{", "[", "STRING", "SCALAR"}:
            raise _JsonAdmissionError("JSON value token is invalid")
        if stack:
            parent = stack[-1]
            if parent.state not in {"value", "value_or_end", "value_after_comma"}:
                raise _JsonAdmissionError("JSON value appears in an invalid position")
            if token_kind in {"{", "["}:
                parent.state = "child"
            else:
                parent.state = "comma_or_end"
        elif root_kind is not None or root_complete:
            raise _JsonAdmissionError("JSON contains more than one root value")

        if root_kind is None:
            root_kind = (
                "object" if token_kind == "{" else "array" if token_kind == "[" else "scalar"
            )
        if token_kind == "{":
            stack.append(_JsonContainerState("object"))
            maximum_depth = max(maximum_depth, len(stack))
        elif token_kind == "[":
            stack.append(_JsonContainerState("array"))
            maximum_depth = max(maximum_depth, len(stack))
        elif not stack:
            root_complete = True

    def close_container(expected: Literal["object", "array"]) -> None:
        nonlocal root_complete
        if not stack or stack[-1].kind != expected:
            raise _JsonAdmissionError("JSON container close token is mismatched")
        stack.pop()
        if not stack:
            root_complete = True
            return
        parent = stack[-1]
        if parent.state != "child":
            raise _JsonAdmissionError("JSON child container appears in an invalid position")
        parent.state = "comma_or_end"

    saw_token = False
    for token_kind, token_value in _iter_json_tokens(text):
        saw_token = True
        if not stack:
            if root_complete:
                raise _JsonAdmissionError("JSON contains trailing tokens")
            begin_value(token_kind)
            continue

        current = stack[-1]
        if current.kind == "object":
            if current.state in {"key_or_end", "key"}:
                if token_kind == "}" and current.state == "key_or_end":
                    close_container("object")
                    continue
                if token_kind != "STRING" or type(token_value) is not str:
                    raise _JsonAdmissionError("JSON object key is invalid")
                if token_value in current.keys:
                    raise _JsonAdmissionError("duplicate JSON key is forbidden")
                current.keys.add(token_value)
                current.state = "colon"
                continue
            if current.state == "colon":
                if token_kind != ":":
                    raise _JsonAdmissionError("JSON object colon is missing")
                current.state = "value"
                continue
            if current.state in {"value", "value_after_comma"}:
                begin_value(token_kind)
                continue
            if current.state == "comma_or_end":
                if token_kind == ",":
                    current.state = "key"
                    continue
                if token_kind == "}":
                    close_container("object")
                    continue
                raise _JsonAdmissionError("JSON object separator is invalid")
            raise _JsonAdmissionError("JSON object parser state is invalid")

        if current.state in {"value_or_end", "value_after_comma"}:
            if token_kind == "]" and current.state == "value_or_end":
                close_container("array")
                continue
            begin_value(token_kind)
            continue
        if current.state == "comma_or_end":
            if token_kind == ",":
                current.state = "value_after_comma"
                continue
            if token_kind == "]":
                close_container("array")
                continue
            raise _JsonAdmissionError("JSON array separator is invalid")
        raise _JsonAdmissionError("JSON array parser state is invalid")

    if not saw_token or stack or not root_complete or root_kind is None:
        raise _JsonAdmissionError("JSON document is incomplete")
    return root_kind, maximum_depth


def _fail_after_json_recursion(text: str, cause: RecursionError) -> Never:
    try:
        root_kind, depth = _iterative_json_root_and_depth(text)
    except (_JsonAdmissionError, UnicodeError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_JSON_INVALID",
            "document is not strict canonical-Unicode UTF-8 JSON",
        ) from exc
    if root_kind != "object":
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_ROOT_INVALID",
            "document JSON must contain exactly one top-level object",
        ) from cause
    if depth > FRESH_STATUS_JSON_MAX_DEPTH:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_DEPTH_EXCEEDED",
            f"document exceeds the frozen JSON depth {FRESH_STATUS_JSON_MAX_DEPTH}",
        ) from cause
    raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
        "INTERNAL_CODEC_INCONSISTENCY",
        "the primary JSON parser recursed on a shallow valid object",
    ) from cause


def _admit_json_document(raw: bytes) -> dict[str, object]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_JSON_INVALID",
            "document is not strict canonical-Unicode UTF-8 JSON",
        ) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_parse_finite_json_float,
            parse_int=_parse_receipt_json_int,
        )
        depth = _inspect_json_tree(value)
    except RecursionError as exc:
        _fail_after_json_recursion(text, exc)
    except (
        json.JSONDecodeError,
        _JsonAdmissionError,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_JSON_INVALID",
            "document is not strict canonical-Unicode UTF-8 JSON",
        ) from exc
    if not isinstance(value, dict):
        _raise(
            "DOCUMENT_ROOT_INVALID",
            "document JSON must contain exactly one top-level object",
        )
    if depth > FRESH_STATUS_JSON_MAX_DEPTH:
        _raise(
            "DOCUMENT_DEPTH_EXCEEDED",
            f"document exceeds the frozen JSON depth {FRESH_STATUS_JSON_MAX_DEPTH}",
        )
    return value


def _parse_receipt_contract(
    raw: bytes,
    admitted: dict[str, object],
) -> tuple[CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1, bytes]:
    try:
        candidate = (
            CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate_json(
                raw,
                strict=False,
            )
        )
    except (UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_RECEIPT_CONTRACT_INVALID",
            "document violates the exact strict immutable Receipt V1 contract",
        ) from exc
    try:
        candidate_json_projection = _safe_model_projection(candidate, json_mode=True)
        candidate_python_projection = _safe_model_projection(candidate, json_mode=False)
    except (AttributeError, TypeError, _UnsafeModelStateError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_RECEIPT_CONTRACT_INVALID",
            "document produced non-canonical model storage or field state",
        ) from exc
    if not _exact_state_consistent(admitted, candidate_json_projection):
        _raise(
            "DOCUMENT_RECEIPT_CONTRACT_INVALID",
            "document JSON changes scalar types, fields, or structure during model admission",
        )
    try:
        rebuilt = CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.model_validate(
            candidate_python_projection,
            strict=True,
        )
    except (UnicodeError, ValidationError, ValueError) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "DOCUMENT_RECEIPT_CONTRACT_INVALID",
            "document violates the exact strict immutable Receipt V1 contract",
        ) from exc
    if not _exact_state_consistent(candidate, rebuilt) or candidate != rebuilt:
        _raise(
            "DOCUMENT_RECEIPT_CONTRACT_INVALID",
            "document Receipt changes model state during strict revalidation",
        )
    try:
        rebuilt_document = _canonical_document(rebuilt)
    except (
        AttributeError,
        TypeError,
        UnicodeError,
        _UnsafeModelStateError,
        ValueError,
    ) as exc:
        raise RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error(
            "INTERNAL_CODEC_INCONSISTENCY",
            "a strictly parsed Receipt could not be rendered canonically",
        ) from exc
    if (
        type(rebuilt_document) is not bytes
        or not rebuilt_document
        or len(rebuilt_document) > FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
        or rebuilt_document.startswith(b"\xef\xbb\xbf")
        or not rebuilt_document.endswith(b"\n")
        or rebuilt_document.endswith(b"\n\n")
        or b"\r" in rebuilt_document
    ):
        _raise(
            "INTERNAL_CODEC_INCONSISTENCY",
            "a strictly parsed Receipt did not render as one bounded canonical document",
        )
    return rebuilt, rebuilt_document


def parse_fresh_status_record_as_of_assessment_receipt_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1:
    """Parse only exact bounded canonical Receipt bytes; no closure replay is performed."""

    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES
        or raw.startswith(b"\xef\xbb\xbf")
    ):
        _raise(
            "DOCUMENT_BYTES_CONTRACT_INVALID",
            "document must be exact non-empty bounded BOM-free built-in bytes",
        )
    admitted = _admit_json_document(raw)
    receipt, canonical_document = _parse_receipt_contract(raw, admitted)
    if raw != canonical_document:
        _raise(
            "DOCUMENT_NOT_CANONICAL",
            "document bytes differ from the exact canonical Receipt document",
        )
    return receipt


__all__ = [
    "FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1",
    "RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error",
    "encode_fresh_status_record_as_of_assessment_receipt_v1_json",
    "parse_fresh_status_record_as_of_assessment_receipt_v1_json",
]
