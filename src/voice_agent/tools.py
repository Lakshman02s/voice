from pathlib import Path

from langchain_core.tools import tool

from voice_agent.filesystem import FilesystemContext, describe_entries
from voice_agent.launcher import launch_application, open_with_default


def build_tools(context: FilesystemContext):
    @tool
    def get_current_directory() -> str:
        """Return the current directory for this session."""

        return str(context.current_directory)

    @tool
    def change_directory(path: str) -> str:
        """Change the current directory to a safe folder inside the allowed roots."""

        resolved = context.resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {resolved}")
        context.current_directory = resolved
        return f"Current directory changed to {resolved}"

    @tool
    def list_directory(path: str = ".") -> str:
        """List files and folders in the given directory or the current directory."""

        resolved = context.resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {resolved}")
        return describe_entries(resolved)

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the allowed roots."""

        resolved = context.resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        if not resolved.is_file():
            raise IsADirectoryError(f"Path is not a file: {resolved}")
        suffix = resolved.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".mp3", ".wav", ".mkv", ".mp4"}:
            return f"{resolved} exists, but this starter only reads plain text-style files."
        content = resolved.read_text(encoding="utf-8")
        if len(content) > 4000:
            content = content[:4000] + "\n... [truncated]"
        return f"Contents of {resolved}:\n{content}"

    @tool
    def search_files(query: str, path: str = ".") -> str:
        """Search for files and folders by name under a directory."""

        resolved = context.resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {resolved}")

        matches: list[Path] = []
        lowered = query.lower()
        for item in resolved.rglob("*"):
            if lowered in item.name.lower():
                matches.append(item)
            if len(matches) >= 25:
                break

        if not matches:
            return f"No files or folders matching '{query}' were found under {resolved}."

        lines = [f"Matches for '{query}' under {resolved}:"]
        for item in matches:
            label = "dir" if item.is_dir() else "file"
            lines.append(f"- [{label}] {item}")
        return "\n".join(lines)

    @tool
    def open_application(name: str) -> str:
        """Open an application on the system by name. Examples: vscode, firefox, chrome, terminal, calculator, file manager."""

        return launch_application(name)

    @tool
    def open_file(path: str) -> str:
        """Open a file with its default system application. For example, open a PDF in a PDF viewer or an image in an image viewer."""

        resolved = context.resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        if not resolved.is_file():
            raise IsADirectoryError(f"Path is not a file: {resolved}")
        return open_with_default(str(resolved))

    return [
        get_current_directory,
        change_directory,
        list_directory,
        read_file,
        search_files,
        open_application,
        open_file,
    ]
