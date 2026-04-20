import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from voice_agent.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Create a chat model from the configured provider."""

    if settings.model_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when MODEL_PROVIDER is set to 'openai'."
            )

        # Prevent unrelated shell configuration from injecting the wrong org/project.
        if not settings.openai_organization:
            os.environ.pop("OPENAI_ORG", None)
            os.environ.pop("OPENAI_ORGANIZATION", None)
        if not settings.openai_project:
            os.environ.pop("OPENAI_PROJECT", None)

        kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
            "temperature": 0,
        }
        if settings.openai_organization:
            kwargs["organization"] = settings.openai_organization

        return ChatOpenAI(
            **kwargs,
        )

    if settings.model_provider == "ollama":
        return ChatOllama(model=settings.ollama_model, temperature=0)

    raise ValueError(f"Unsupported provider: {settings.model_provider}")
