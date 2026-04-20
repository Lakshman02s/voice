from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    model_provider: Literal["openai", "ollama", "local"] = Field(default="local")
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4.1-mini")
    openai_organization: str | None = Field(default=None)
    openai_project: str | None = Field(default=None)
    ollama_model: str = Field(default="llama3.1:8b")
    system_prompt: str = Field(
        default="You are a warm, concise, voice-first filesystem assistant."
    )
    allowed_roots: str = Field(default=".:~/Downloads:~/Documents")
    default_start_directory: str = Field(default=".")
    stt_provider: Literal["faster-whisper"] = Field(default="faster-whisper")
    stt_model_size: str = Field(default="base")
    mic_sample_rate: int = Field(default=16000)
    mic_channels: int = Field(default=1)
    mic_duration_seconds: int = Field(default=5)
    mic_device: str | None = Field(default=None)

    def allowed_root_paths(self) -> tuple[Path, ...]:
        parts = [part.strip() for part in self.allowed_roots.split(":") if part.strip()]
        if not parts:
            raise ValueError("ALLOWED_ROOTS must contain at least one path.")
        return tuple(Path(part).expanduser().resolve() for part in parts)

    def start_directory_path(self) -> Path:
        return Path(self.default_start_directory).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
