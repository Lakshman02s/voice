from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage, HumanMessage

from voice_agent.config import Settings
from voice_agent.filesystem import FilesystemContext
from voice_agent.graph import build_graph


@dataclass
class VoiceAgentSession:
    """Keeps message history and current directory across conversation turns."""

    settings: Settings
    fs_context: FilesystemContext
    messages: list[BaseMessage] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.graph = build_graph(self.settings, self.fs_context)

    @classmethod
    def from_settings(cls, settings: Settings) -> "VoiceAgentSession":
        fs_context = FilesystemContext.from_values(
            current_directory=settings.start_directory_path(),
            allowed_roots=settings.allowed_root_paths(),
        )
        return cls(settings=settings, fs_context=fs_context)

    def run_turn(self, transcript: str) -> str:
        self.messages.append(HumanMessage(content=transcript))
        result = self.graph.invoke(
            {
                "messages": self.messages,
                "transcript": transcript,
                "response_text": "",
                "current_directory": str(self.fs_context.current_directory),
                "allowed_roots": [str(root) for root in self.fs_context.allowed_roots],
            }
        )
        self.messages = result["messages"]
        return result["response_text"]
