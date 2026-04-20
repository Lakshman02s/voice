import tempfile
import wave
from dataclasses import dataclass
from functools import lru_cache
import gc
from pathlib import Path
from typing import Protocol

from voice_agent.config import Settings


class Transcriber(Protocol):
    """Convert incoming audio or text into a transcript."""

    def transcribe(self, source: str) -> str:
        ...


class Speaker(Protocol):
    """Deliver the assistant response to the outside world."""

    def speak(self, text: str) -> None:
        ...


@dataclass(slots=True)
class TextPassthroughTranscriber:
    """Treats text input as an already-transcribed utterance."""

    def transcribe(self, source: str) -> str:
        cleaned = source.strip()
        if not cleaned:
            raise ValueError("Input text cannot be empty.")
        return cleaned


@dataclass(slots=True)
class TranscriptFileTranscriber:
    """Reads a transcript from a plain text file for predictable testing."""

    def transcribe(self, source: str) -> str:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {path}")
        return path.read_text(encoding="utf-8").strip()


@dataclass(slots=True)
class ConsoleSpeaker:
    """Simple speaker that prints the response for development."""

    prefix: str = "Assistant"

    def speak(self, text: str) -> None:
        print(f"{self.prefix}: {text}")


@dataclass(slots=True)
class MicrophoneRecorder:
    """Record short microphone clips and save them as WAV files."""

    sample_rate: int = 16000
    channels: int = 1
    device: str | int | None = None

    def record_to_wav(self, duration_seconds: int, output_path: str | None = None) -> Path:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Microphone dependencies are missing. Run `pip install -e \".[voice]\"` "
                "and `pip install -e .` if needed."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                "PortAudio is not installed on this system. Install it with "
                "`sudo apt-get install libportaudio2 portaudio19-dev` and try again."
            ) from exc

        if duration_seconds <= 0:
            raise ValueError("Recording duration must be greater than zero.")

        frames = int(duration_seconds * self.sample_rate)
        audio = sd.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            device=self.device,
        )
        sd.wait()

        peak = int(np.abs(audio).max()) if audio.size else 0
        if peak < 150:
            raise ValueError(
                "Recorded audio is almost silent. Your microphone input may be wrong. "
                "Try `voice-agent list-input-devices`, set MIC_DEVICE in .env, and make "
                "sure your Bluetooth earbuds are using a headset/handsfree profile."
            )

        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            path = Path(temp_file.name)
            temp_file.close()
        else:
            path = Path(output_path)

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(np.asarray(audio, dtype=np.int16).tobytes())

        return path


@dataclass(slots=True)
class FasterWhisperTranscriber:
    """Local speech-to-text using faster-whisper."""

    model_size: str = "base"

    def transcribe(self, source: str) -> str:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        model = _load_faster_whisper_model(self.model_size)
        segments, _ = model.transcribe(str(path))
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        if not transcript:
            raise ValueError("No speech was detected in the recorded audio.")
        return transcript


def build_microphone_recorder(settings: Settings) -> MicrophoneRecorder:
    return MicrophoneRecorder(
        sample_rate=settings.mic_sample_rate,
        channels=settings.mic_channels,
        device=_parse_mic_device(settings.mic_device),
    )


def build_audio_transcriber(settings: Settings) -> Transcriber:
    if settings.stt_provider == "faster-whisper":
        return FasterWhisperTranscriber(model_size=settings.stt_model_size)
    raise ValueError(f"Unsupported STT provider: {settings.stt_provider}")


def warmup_audio_transcriber(settings: Settings) -> None:
    if settings.stt_provider == "faster-whisper":
        _load_faster_whisper_model(settings.stt_model_size)
        return
    raise ValueError(f"Unsupported STT provider: {settings.stt_provider}")


def unload_audio_transcriber(settings: Settings) -> None:
    if settings.stt_provider == "faster-whisper":
        _load_faster_whisper_model.cache_clear()
        gc.collect()
        return
    raise ValueError(f"Unsupported STT provider: {settings.stt_provider}")


def list_input_devices() -> list[str]:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError(
            "Microphone dependencies are missing. Run `pip install -e \".[voice]\"` "
            "and `pip install -e .` if needed."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "PortAudio is not installed on this system. Install it with "
            "`sudo apt-get install libportaudio2 portaudio19-dev` and try again."
        ) from exc

    devices = []
    default_input = sd.default.device[0] if sd.default.device else None
    for index, device in enumerate(sd.query_devices()):
        if int(device["max_input_channels"]) <= 0:
            continue
        marker = "*" if index == default_input else " "
        devices.append(
            f"{marker} {index}: {device['name']} "
            f"(inputs={device['max_input_channels']}, outputs={device['max_output_channels']})"
        )
    return devices


def _parse_mic_device(value: str | None) -> str | int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)
    return cleaned


@lru_cache(maxsize=2)
def _load_faster_whisper_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Run `pip install -e \".[voice]\"`."
        ) from exc

    try:
        return WhisperModel(model_size, device="cpu", compute_type="int8")
    except ValueError:
        return WhisperModel(model_size)
