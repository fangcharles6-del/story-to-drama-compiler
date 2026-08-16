"""Pure-local media admission checks for Creative Sample real-asset intake."""

from __future__ import annotations

import hashlib
import math
import os
import stat
import struct
import sys
import zlib
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sdc.creative_media import CreativeMediaError, validate_local_path

MAX_REAL_PNG_BYTES = 16 * 1024 * 1024
MAX_REAL_VOICE_WAV_BYTES = 4 * 1024 * 1024
MAX_REAL_BGM_WAV_BYTES = 32 * 1024 * 1024
MIN_IMAGE_DIMENSION = 512
MAX_IMAGE_DIMENSION = 4096
MAX_IMAGE_PIXELS = 16_000_000
MIN_DISTINCT_COLORS = 16
WAV_SAMPLE_RATE = 48_000
VOICE_MIN_DURATION_MS = 250
BGM_DURATION_MS = 72_000
MIN_RMS_MILLIDBFS = -40_000
MAX_RMS_MILLIDBFS = -6_000
MIN_PEAK_MILLIDBFS = -30_000
MAX_PEAK_MILLIDBFS = -100
MAX_SILENCE_PPM = 800_000
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class RealAssetMediaError(RuntimeError):
    """A local media byte stream failed its strict intake profile."""


@dataclass(frozen=True, slots=True)
class SafeLocalFile:
    path: Path
    data: bytes
    sha256: str
    size_bytes: int
    identity: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class PngTechnicalEvidence:
    width: int
    height: int
    color_space: Literal["RGB", "RGBA_OPAQUE"]
    bit_depth: Literal[8]
    interlaced: Literal[False]
    metadata_free: Literal[True]
    active_content_absent: Literal[True]
    distinct_color_count: int
    semantic_privacy_reviewed: Literal[False]


@dataclass(frozen=True, slots=True)
class WavTechnicalEvidence:
    codec: Literal["pcm_s16le"]
    sample_rate_hz: Literal[48000]
    channels: Literal[1, 2]
    duration_ms: int
    sample_count: int
    rms_millidbfs: int
    sample_peak_millidbfs: int
    clipped_sample_count: Literal[0]
    silence_ppm: int
    semantic_content_reviewed: Literal[False]


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def read_safe_local_file(path: Path, *, max_bytes: int) -> SafeLocalFile:
    """Read a bounded, non-linked local file once and bind its opened identity."""
    if max_bytes <= 0:
        raise RealAssetMediaError("media byte limit must be positive")
    try:
        absolute = validate_local_path(path, must_exist=True)
        before = absolute.lstat()
    except (CreativeMediaError, OSError) as exc:
        raise RealAssetMediaError("media path is not an admissible local path") from exc
    attributes = int(getattr(before, "st_file_attributes", 0))
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or bool(attributes & 0x400)
        or before.st_nlink != 1
    ):
        raise RealAssetMediaError("media input must be one non-linked regular file")
    if before.st_size <= 0 or before.st_size > max_bytes:
        raise RealAssetMediaError("media input violates its exact byte boundary")
    try:
        with absolute.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _identity(opened) != _identity(before):
                raise RealAssetMediaError("media identity changed before opened-byte inspection")
            data = handle.read(max_bytes + 1)
        after = absolute.lstat()
    except RealAssetMediaError:
        raise
    except OSError as exc:
        raise RealAssetMediaError("media input could not be read") from exc
    if len(data) != before.st_size or len(data) > max_bytes:
        raise RealAssetMediaError("media bytes changed or exceeded the read boundary")
    if _identity(after) != _identity(before):
        raise RealAssetMediaError("media identity changed after opened-byte inspection")
    return SafeLocalFile(
        path=absolute,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        identity=_identity(before),
    )


def _paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    corner_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= corner_distance:
        return left
    if above_distance <= corner_distance:
        return above
    return upper_left


def _unfilter_png(raw: bytes, *, width: int, height: int, bytes_per_pixel: int) -> bytes:
    row_bytes = width * bytes_per_pixel
    stride = row_bytes + 1
    if len(raw) != stride * height:
        raise RealAssetMediaError("PNG decoded bytes do not match the exact pixel closure")
    output = bytearray(row_bytes * height)
    prior = bytearray(row_bytes)
    for row in range(height):
        source = raw[row * stride : (row + 1) * stride]
        filter_kind = source[0]
        if filter_kind > 4:
            raise RealAssetMediaError("PNG contains an invalid scanline filter")
        current = bytearray(row_bytes)
        for index, encoded in enumerate(source[1:]):
            left = current[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            above = prior[index]
            upper_left = prior[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_kind == 0:
                predictor = 0
            elif filter_kind == 1:
                predictor = left
            elif filter_kind == 2:
                predictor = above
            elif filter_kind == 3:
                predictor = (left + above) // 2
            else:
                predictor = _paeth(left, above, upper_left)
            current[index] = (encoded + predictor) & 0xFF
        output[row * row_bytes : (row + 1) * row_bytes] = current
        prior = current
    return bytes(output)


def _parse_png(data: bytes) -> tuple[PngTechnicalEvidence, bytes]:
    if not data.startswith(_PNG_SIGNATURE):
        raise RealAssetMediaError("real reference image must be PNG bytes")
    offset = len(_PNG_SIGNATURE)
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(data):
        if len(chunks) >= 64 or offset + 12 > len(data):
            raise RealAssetMediaError("PNG chunk structure is invalid or excessive")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if length > MAX_REAL_PNG_BYTES or end > len(data):
            raise RealAssetMediaError("PNG chunk exceeds its bounded file")
        payload = data[offset + 8 : offset + 8 + length]
        observed_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        if observed_crc != zlib.crc32(chunk_type + payload) & 0xFFFFFFFF:
            raise RealAssetMediaError("PNG chunk CRC is invalid")
        chunks.append((chunk_type, payload))
        offset = end
        if chunk_type == b"IEND":
            break
    if offset != len(data):
        raise RealAssetMediaError("PNG contains trailing or polyglot bytes")
    if not chunks or chunks[0][0] != b"IHDR" or chunks[-1] != (b"IEND", b""):
        raise RealAssetMediaError("PNG must have exact IHDR and IEND boundaries")
    if any(kind not in {b"IHDR", b"IDAT", b"IEND"} for kind, _ in chunks):
        raise RealAssetMediaError(
            "PNG metadata, animation, attachment or external content is forbidden"
        )
    if sum(kind == b"IHDR" for kind, _ in chunks) != 1:
        raise RealAssetMediaError("PNG must contain one IHDR chunk")
    idat_indexes = [index for index, (kind, _) in enumerate(chunks) if kind == b"IDAT"]
    if not idat_indexes or idat_indexes != list(range(idat_indexes[0], idat_indexes[-1] + 1)):
        raise RealAssetMediaError("PNG IDAT chunks must form one contiguous sequence")
    ihdr = chunks[0][1]
    if len(ihdr) != 13:
        raise RealAssetMediaError("PNG IHDR is invalid")
    width, height, depth, color_type, compression, filter_method, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    if (
        width < MIN_IMAGE_DIMENSION
        or height < MIN_IMAGE_DIMENSION
        or width > MAX_IMAGE_DIMENSION
        or height > MAX_IMAGE_DIMENSION
        or width * height > MAX_IMAGE_PIXELS
        or depth != 8
        or color_type not in {2, 6}
        or compression != 0
        or filter_method != 0
        or interlace != 0
    ):
        raise RealAssetMediaError("PNG must use the bounded non-interlaced 8-bit RGB/RGBA profile")
    bytes_per_pixel = 3 if color_type == 2 else 4
    expected_size = (width * bytes_per_pixel + 1) * height
    compressed = b"".join(payload for kind, payload in chunks if kind == b"IDAT")
    inflater = zlib.decompressobj()
    try:
        decoded = inflater.decompress(compressed, expected_size + 1)
    except zlib.error as exc:
        raise RealAssetMediaError("PNG pixel stream is not decodable") from exc
    if (
        len(decoded) != expected_size
        or inflater.unused_data
        or inflater.unconsumed_tail
        or not inflater.eof
    ):
        raise RealAssetMediaError("PNG pixel stream does not have an exact bounded closure")
    pixels = _unfilter_png(decoded, width=width, height=height, bytes_per_pixel=bytes_per_pixel)
    colors: set[bytes] = set()
    for offset in range(0, len(pixels), bytes_per_pixel):
        pixel = pixels[offset : offset + bytes_per_pixel]
        if bytes_per_pixel == 4 and pixel[3] != 255:
            raise RealAssetMediaError("RGBA references must be fully opaque for this profile")
        colors.add(pixel)
        if len(colors) >= MIN_DISTINCT_COLORS:
            break
    if len(colors) < MIN_DISTINCT_COLORS:
        raise RealAssetMediaError("PNG has too little active visual content for a real reference")
    evidence = PngTechnicalEvidence(
        width=width,
        height=height,
        color_space="RGB" if color_type == 2 else "RGBA_OPAQUE",
        bit_depth=8,
        interlaced=False,
        metadata_free=True,
        active_content_absent=True,
        distinct_color_count=len(colors),
        semantic_privacy_reviewed=False,
    )
    return evidence, pixels


def inspect_png(
    path: Path, *, forbidden_sha256: tuple[str, ...] = ()
) -> tuple[SafeLocalFile, PngTechnicalEvidence]:
    source = read_safe_local_file(path, max_bytes=MAX_REAL_PNG_BYTES)
    if source.sha256 in set(forbidden_sha256):
        raise RealAssetMediaError("Pilot placeholder bytes cannot be admitted as real media")
    evidence, _ = _parse_png(source.data)
    return source, evidence


def _millidbfs(amplitude: float) -> int:
    if amplitude <= 0:
        raise RealAssetMediaError("silent WAV content is forbidden")
    return int(round(20_000 * math.log10(amplitude / 32768.0)))


def _parse_wav(
    source: SafeLocalFile,
    *,
    expected_channels: Literal[1, 2],
    minimum_duration_ms: int,
    maximum_duration_ms: int,
    exact_duration_ms: int | None,
) -> WavTechnicalEvidence:
    data = source.data
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise RealAssetMediaError("audio input must be a strict RIFF/WAVE file")
    if struct.unpack("<I", data[4:8])[0] != len(data) - 8:
        raise RealAssetMediaError("WAV RIFF length does not close over the exact file")
    offset = 12
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(data):
        if offset + 8 > len(data) or len(chunks) >= 8:
            raise RealAssetMediaError("WAV chunk structure is invalid or excessive")
        kind = data[offset : offset + 4]
        length = struct.unpack("<I", data[offset + 4 : offset + 8])[0]
        start = offset + 8
        end = start + length
        padded_end = end + (length & 1)
        if end > len(data) or padded_end > len(data):
            raise RealAssetMediaError("WAV chunk exceeds its bounded file")
        if padded_end > end and data[end:padded_end] != b"\0":
            raise RealAssetMediaError("WAV chunk padding is not canonical")
        chunks.append((kind, data[start:end]))
        offset = padded_end
    if offset != len(data) or tuple(kind for kind, _ in chunks) != (b"fmt ", b"data"):
        raise RealAssetMediaError("WAV must contain only exact fmt and data chunks")
    fmt, samples_raw = chunks[0][1], chunks[1][1]
    if len(fmt) != 16:
        raise RealAssetMediaError("WAV must use the canonical PCM fmt chunk")
    audio_format, channels, sample_rate, byte_rate, block_align, bits = struct.unpack(
        "<HHIIHH", fmt
    )
    if (
        audio_format != 1
        or channels != expected_channels
        or sample_rate != WAV_SAMPLE_RATE
        or bits != 16
        or block_align != channels * 2
        or byte_rate != sample_rate * block_align
        or not samples_raw
        or len(samples_raw) % block_align
    ):
        raise RealAssetMediaError("WAV must use exact 48 kHz signed PCM16 channel framing")
    frames = len(samples_raw) // block_align
    minimum_frames = (minimum_duration_ms * sample_rate + 999) // 1000
    maximum_frames = maximum_duration_ms * sample_rate // 1000
    if frames < minimum_frames or frames > maximum_frames:
        raise RealAssetMediaError("WAV duration is outside its exact assigned interval")
    if exact_duration_ms is not None and frames * 1000 != exact_duration_ms * sample_rate:
        raise RealAssetMediaError("BGM WAV must cover the exact 72-second master clock")
    values = array("h")
    values.frombytes(samples_raw)
    if sys.byteorder != "little":
        values.byteswap()
    peak = max(abs(value) for value in values)
    clipped = sum(abs(value) >= 32767 for value in values)
    sum_squares = sum(value * value for value in values)
    rms = math.sqrt(sum_squares / len(values))
    peak_mdb = _millidbfs(float(peak))
    rms_mdb = _millidbfs(rms)
    silence = sum(abs(value) <= 327 for value in values)
    silence_ppm = silence * 1_000_000 // len(values)
    if clipped != 0:
        raise RealAssetMediaError("WAV contains clipped samples")
    if not MIN_PEAK_MILLIDBFS <= peak_mdb <= MAX_PEAK_MILLIDBFS:
        raise RealAssetMediaError("WAV sample peak is outside the reviewed profile")
    if not MIN_RMS_MILLIDBFS <= rms_mdb <= MAX_RMS_MILLIDBFS:
        raise RealAssetMediaError("WAV RMS loudness is outside the reviewed profile")
    if silence_ppm > MAX_SILENCE_PPM:
        raise RealAssetMediaError("WAV contains excessive silence")
    duration_ms = frames * 1000 // sample_rate
    return WavTechnicalEvidence(
        codec="pcm_s16le",
        sample_rate_hz=48000,
        channels=expected_channels,
        duration_ms=duration_ms,
        sample_count=len(values),
        rms_millidbfs=rms_mdb,
        sample_peak_millidbfs=peak_mdb,
        clipped_sample_count=0,
        silence_ppm=silence_ppm,
        semantic_content_reviewed=False,
    )


def inspect_voice_wav(
    path: Path, *, maximum_duration_ms: int
) -> tuple[SafeLocalFile, WavTechnicalEvidence]:
    if maximum_duration_ms < VOICE_MIN_DURATION_MS:
        raise RealAssetMediaError("voice interval is shorter than the minimum admitted duration")
    source = read_safe_local_file(path, max_bytes=MAX_REAL_VOICE_WAV_BYTES)
    evidence = _parse_wav(
        source,
        expected_channels=1,
        minimum_duration_ms=VOICE_MIN_DURATION_MS,
        maximum_duration_ms=maximum_duration_ms,
        exact_duration_ms=None,
    )
    return source, evidence


def inspect_bgm_wav(path: Path) -> tuple[SafeLocalFile, WavTechnicalEvidence]:
    source = read_safe_local_file(path, max_bytes=MAX_REAL_BGM_WAV_BYTES)
    evidence = _parse_wav(
        source,
        expected_channels=2,
        minimum_duration_ms=BGM_DURATION_MS,
        maximum_duration_ms=BGM_DURATION_MS,
        exact_duration_ms=BGM_DURATION_MS,
    )
    return source, evidence


__all__ = [
    "BGM_DURATION_MS",
    "MAX_PEAK_MILLIDBFS",
    "MAX_RMS_MILLIDBFS",
    "MAX_SILENCE_PPM",
    "MIN_PEAK_MILLIDBFS",
    "MIN_RMS_MILLIDBFS",
    "PngTechnicalEvidence",
    "RealAssetMediaError",
    "SafeLocalFile",
    "WavTechnicalEvidence",
    "inspect_bgm_wav",
    "inspect_png",
    "inspect_voice_wav",
    "read_safe_local_file",
]
