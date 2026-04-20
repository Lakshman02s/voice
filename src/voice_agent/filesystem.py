from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class FileAccessError(ValueError):
    """Raised when a path falls outside the allowed safe roots."""


@dataclass(slots=True)
class FilesystemContext:
    """Holds the current session directory and safe access boundaries."""

    current_directory: Path
    allowed_roots: tuple[Path, ...]

    @classmethod
    def from_values(
        cls,
        current_directory: str | Path,
        allowed_roots: Iterable[str | Path],
    ) -> "FilesystemContext":
        roots = tuple(Path(root).expanduser().resolve() for root in allowed_roots)
        if not roots:
            raise ValueError("At least one allowed root is required.")
        current = Path(current_directory).expanduser().resolve()
        context = cls(current_directory=current, allowed_roots=roots)
        context.ensure_allowed(current)
        return context

    def ensure_allowed(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        for root in self.allowed_roots:
            if resolved == root or root in resolved.parents:
                return resolved
        raise FileAccessError(
            f"Access denied for '{resolved}'. Allowed roots: "
            + ", ".join(str(root) for root in self.allowed_roots)
        )

    def resolve_path(self, target: str) -> Path:
        candidate = Path(target).expanduser()
        if not candidate.is_absolute():
            candidate = self.current_directory / candidate
        return self.ensure_allowed(candidate.resolve())


def describe_entries(path: Path) -> str:
    entries = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    if not entries:
        return f"No files or folders found in {path}."

    lines = [f"Contents of {path}:"]
    for entry in entries:
        label = "dir" if entry.is_dir() else "file"
        lines.append(f"- [{label}] {entry.name}")
    return "\n".join(lines)
