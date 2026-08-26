from pathlib import Path

import pytest

from sdc.media import _ffconcat_document, _ffconcat_quote


def test_ffconcat_document_has_header_lf_and_resolved_paths(tmp_path: Path) -> None:
    first = tmp_path / "first clip.mp4"
    second = tmp_path / "second.mp4"
    document = _ffconcat_document([first, second])
    assert document.startswith("ffconcat version 1.0\n")
    assert document.endswith("\n")
    assert "\r" not in document
    assert f"file '{first.resolve().as_posix()}'\n" in document
    assert f"file '{second.resolve().as_posix()}'\n" in document


def test_ffconcat_quote_escapes_apostrophes(tmp_path: Path) -> None:
    path = tmp_path / "director's-cut.mp4"
    quoted = _ffconcat_quote(path)
    assert "director'\\''s-cut.mp4" in quoted


def test_ffconcat_document_rejects_empty_segment_set() -> None:
    with pytest.raises(ValueError, match="at least one"):
        _ffconcat_document([])
