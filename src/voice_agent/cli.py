from pathlib import Path

import typer
from openai import AuthenticationError

from voice_agent.audio import (
    ConsoleSpeaker,
    TextPassthroughTranscriber,
    build_audio_transcriber,
    build_microphone_recorder,
    list_input_devices,
    unload_audio_transcriber,
    warmup_audio_transcriber,
)
from voice_agent.config import get_settings
from voice_agent.session import VoiceAgentSession

app = typer.Typer(help="LangGraph voice agent starter CLI.")


def _run_turn(text: str) -> str:
    settings = get_settings()
    transcriber = TextPassthroughTranscriber()
    speaker = ConsoleSpeaker()
    session = VoiceAgentSession.from_settings(settings)

    transcript = transcriber.transcribe(text)
    reply = session.run_turn(transcript)
    speaker.speak(reply)
    return reply


def _build_session() -> VoiceAgentSession:
    return VoiceAgentSession.from_settings(get_settings())


def _run_voice_turn(
    session: VoiceAgentSession,
    *,
    duration_seconds: int,
    save_audio_path: str | None = None,
) -> str:
    settings = session.settings
    recorder = build_microphone_recorder(settings)
    transcriber = build_audio_transcriber(settings)
    speaker = ConsoleSpeaker()

    typer.echo(f"Recording for {duration_seconds} seconds. Speak now...")
    audio_path = recorder.record_to_wav(
        duration_seconds=duration_seconds,
        output_path=save_audio_path,
    )
    typer.echo(
        "Transcribing audio now. On the first run, the Whisper model may download "
        "from Hugging Face and take a little time."
    )
    transcript = transcriber.transcribe(str(audio_path))
    typer.echo(f"Transcript: {transcript}")
    unload_audio_transcriber(settings)
    typer.echo("Speech model released. Running the agent now...")
    reply = session.run_turn(transcript)
    speaker.speak(reply)

    if save_audio_path is None and audio_path.exists():
        audio_path.unlink(missing_ok=True)

    return reply


@app.command()
def chat(text: str = typer.Option(..., "--text", "-t", help="Single user utterance.")):
    """Run one conversation turn."""

    try:
        _run_turn(text)
    except AuthenticationError as exc:
        raise typer.BadParameter(
            "OpenAI authentication failed. Check OPENAI_API_KEY and remove any "
            "wrong org/project settings from .env or your shell."
        ) from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def repl():
    """Run an interactive text loop that simulates a voice session."""

    try:
        settings = get_settings()
        transcriber = TextPassthroughTranscriber()
        speaker = ConsoleSpeaker()
        session = VoiceAgentSession.from_settings(settings)

        typer.echo("Voice agent REPL. Type 'exit' or 'quit' to stop.")
        while True:
            user_text = typer.prompt("You")
            if user_text.strip().lower() in {"exit", "quit"}:
                typer.echo("Session ended.")
                raise typer.Exit()
            transcript = transcriber.transcribe(user_text)
            reply = session.run_turn(transcript)
            speaker.speak(reply)
    except AuthenticationError as exc:
        raise typer.BadParameter(
            "OpenAI authentication failed. Check OPENAI_API_KEY and remove any "
            "wrong org/project settings from .env or your shell."
        ) from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def listen(
    duration: int = typer.Option(
        None,
        "--duration",
        "-d",
        help="Recording duration in seconds. Defaults to MIC_DURATION_SECONDS from .env.",
    ),
    save_audio: str | None = typer.Option(
        None,
        "--save-audio",
        help="Optional WAV file path to keep the microphone recording.",
    ),
):
    """Record one spoken command from the microphone and run the agent."""

    try:
        session = _build_session()
        settings = session.settings
        _run_voice_turn(
            session,
            duration_seconds=duration or settings.mic_duration_seconds,
            save_audio_path=save_audio,
        )
    except AuthenticationError as exc:
        raise typer.BadParameter(
            "OpenAI authentication failed. Check OPENAI_API_KEY and remove any "
            "wrong org/project settings from .env or your shell."
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("voice-repl")
def voice_repl(
    duration: int = typer.Option(
        None,
        "--duration",
        "-d",
        help="Recording duration in seconds for each spoken turn.",
    ),
):
    """Run repeated spoken turns using the microphone."""

    try:
        session = _build_session()
        turn_duration = duration or session.settings.mic_duration_seconds

        typer.echo("Voice REPL. Press Enter to record, or type 'exit' to stop.")
        while True:
            command = typer.prompt("Command", default="", show_default=False)
            if command.strip().lower() in {"exit", "quit"}:
                typer.echo("Session ended.")
                raise typer.Exit()
            _run_voice_turn(session, duration_seconds=turn_duration)
    except AuthenticationError as exc:
        raise typer.BadParameter(
            "OpenAI authentication failed. Check OPENAI_API_KEY and remove any "
            "wrong org/project settings from .env or your shell."
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("warmup-stt")
def warmup_stt():
    """Download and load the speech-to-text model before recording."""

    try:
        settings = get_settings()
        typer.echo(
            f"Warming up STT model '{settings.stt_model_size}'. "
            "The first run may download files from Hugging Face."
        )
        warmup_audio_transcriber(settings)
        typer.echo("STT model is ready.")
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("list-input-devices")
def list_input_devices_command():
    """Show microphone-capable audio devices."""

    try:
        devices = list_input_devices()
        if not devices:
            typer.echo("No input devices were found.")
            raise typer.Exit()
        typer.echo("Available input devices:")
        for line in devices:
            typer.echo(line)
    except RuntimeError as exc:
        raise typer.BadParameter(str(exc)) from exc
