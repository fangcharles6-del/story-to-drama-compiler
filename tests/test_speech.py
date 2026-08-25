from pathlib import Path

import pytest

from sdc.speech import (
    SpeechSynthesisRequest,
    SpeechSynthesisUnavailable,
    UnavailableSpeechProvider,
)


def test_speech_request_is_pinned_to_master_clock_format() -> None:
    request = SpeechSynthesisRequest(
        line_id="dialogue_line_1",
        text="Do not open that door.",
        voice_id="voice-neutral-zh",
        language="zh-CN",
        target_duration_ms=1800,
    )
    assert request.sample_rate_hz == 48000
    assert request.output_format == "wav"

    with pytest.raises(ValueError, match="48 kHz"):
        SpeechSynthesisRequest(
            line_id="dialogue_line_1",
            text="x",
            voice_id="voice",
            language="en-US",
            sample_rate_hz=44100,
        )


@pytest.mark.asyncio
async def test_default_speech_provider_fails_before_creating_output(tmp_path: Path) -> None:
    destination = tmp_path / "line.wav"
    request = SpeechSynthesisRequest(
        line_id="dialogue_line_1",
        text="Stop.",
        voice_id="voice",
        language="en-US",
    )
    with pytest.raises(SpeechSynthesisUnavailable, match="no approved"):
        await UnavailableSpeechProvider().synthesize(
            request=request,
            destination=destination,
        )
    assert not destination.exists()
