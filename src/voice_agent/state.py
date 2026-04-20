from typing import TypedDict

from langgraph.graph import MessagesState


class VoiceAgentState(MessagesState):
    """Shared state passed between LangGraph nodes."""

    transcript: str
    response_text: str
    current_directory: str
    allowed_roots: list[str]
