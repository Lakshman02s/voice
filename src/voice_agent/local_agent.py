import re
from pathlib import Path

from voice_agent.filesystem import FilesystemContext
from voice_agent.launcher import is_application, launch_application, open_with_default


def _clean_target(text: str) -> str:
    cleaned = text.strip().strip(".")
    for splitter in [" and then ", " then ", " and ", ", and ", ","]:
        if splitter in cleaned.lower():
            index = cleaned.lower().index(splitter)
            cleaned = cleaned[:index].strip()
            break
    prefixes = ("to ", "the ", "folder ", "file ")
    changed = True
    while changed:
        changed = False
        lowered = cleaned.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                changed = True
                break
    return cleaned


def _find_path_fragment(command: str, phrases: list[str]) -> str | None:
    lowered = command.lower()
    for phrase in phrases:
        if phrase in lowered:
            fragment = command[lowered.index(phrase) + len(phrase):]
            fragment = _clean_target(fragment)
            return fragment or None
    return None


def _resolve_existing(context: FilesystemContext, target: str) -> Path:
    candidates = []
    raw = target.strip()
    if not raw or raw in {"here", "there", "."}:
        return context.current_directory
    candidates.append(raw)
    if not raw.startswith("~/") and "/" not in raw:
        candidates.append(f"~/{raw}")
        candidates.append(f"~/Downloads/{raw}")
        candidates.append(f"~/Documents/{raw}")
    for candidate in candidates:
        try:
            resolved = context.resolve_path(candidate)
        except Exception:
            continue
        if resolved.exists():
            return resolved
    return context.resolve_path(raw)


def _list_directory(context: FilesystemContext, target: str = ".", *, kind: str = "all") -> str:
    path = _resolve_existing(context, target)
    if not path.is_dir():
        return f"{path} is not a directory."
    entries = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    if kind == "folders":
        entries = [item for item in entries if item.is_dir()]
    elif kind == "files":
        entries = [item for item in entries if item.is_file()]
    if not entries:
        if kind == "folders":
            return f"No folders found in {path}."
        if kind == "files":
            return f"No files found in {path}."
        return f"No files or folders found in {path}."
    label = "Contents"
    if kind == "folders":
        label = "Folders"
    elif kind == "files":
        label = "Files"
    lines = [f"{label} of {path}:"]
    for entry in entries:
        lines.append(f"- {entry.name}")
    return "\n".join(lines)


def _change_directory(context: FilesystemContext, target: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"I could not find '{target}'."
    if not path.is_dir():
        return f"{path} is not a folder."
    context.current_directory = path
    return f"Current directory changed to {path}."


def _read_file(context: FilesystemContext, target: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"I could not find '{target}'."
    if path.is_dir():
        return f"{path} is a folder, not a file."
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"{path} is not a plain text file."
    if len(content) > 4000:
        content = content[:4000] + "\n... [truncated]"
    return f"Contents of {path}:\n{content}"


def _search(context: FilesystemContext, query: str, target: str = ".") -> str:
    path = _resolve_existing(context, target)
    if not path.is_dir():
        return f"{path} is not a directory."
    matches = []
    for item in path.rglob("*"):
        if query.lower() in item.name.lower():
            matches.append(item)
        if len(matches) >= 25:
            break
    if not matches:
        return f"No files or folders matching '{query}' were found under {path}."
    lines = [f"Matches for '{query}' under {path}:"]
    for item in matches:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _try_open_application(target: str) -> str | None:
    """If *target* looks like an application name, launch it and return a message.

    Returns None if *target* is not a recognized application.
    """
    if is_application(target):
        return launch_application(target)
    return None


def _try_open_file(context: FilesystemContext, target: str) -> str | None:
    """If *target* resolves to an existing file, open it with its default app.

    Returns None if the target is not an existing file.
    """
    try:
        path = _resolve_existing(context, target)
    except Exception:
        return None
    if path.exists() and path.is_file():
        return open_with_default(str(path))
    return None


def run_local_agent(transcript: str, context: FilesystemContext) -> str:
    text = transcript.strip()
    lowered = text.lower()

    if not text:
        return "Please say what file or folder action you want."

    segments = re.split(r"\b(?:and then|then|, and|,)\b", text, flags=re.IGNORECASE)
    outputs: list[str] = []

    for raw_segment in segments:
        command = raw_segment.strip()
        if not command:
            continue
        lower_command = command.lower()

        if any(phrase in lower_command for phrase in ["where am i", "current directory", "current folder"]):
            outputs.append(f"Current directory is {context.current_directory}.")
            continue

        # --- "open" commands: app, file, or directory ---
        if any(phrase in lower_command for phrase in [
            "launch ", "start ", "run ",
        ]):
            target = _find_path_fragment(command, ["launch ", "start ", "run "])
            if target:
                result = _try_open_application(target)
                if result:
                    outputs.append(result)
                    continue
                outputs.append(
                    f"Could not find application '{target}' on this system."
                )
                continue

        if any(phrase in lower_command for phrase in ["go to", "change directory", "move to", "open the", "open "]):
            target = _find_path_fragment(command, ["go to ", "change directory to ", "move to ", "open the ", "open "])
            if target:
                # 1. Is it an application?
                app_result = _try_open_application(target)
                if app_result:
                    outputs.append(app_result)
                    continue

                # 2. Is it a file? Open with default app
                file_result = _try_open_file(context, target)
                if file_result:
                    outputs.append(file_result)
                    continue

                # 3. Fall through to directory navigation
                outputs.append(_change_directory(context, target))
                if "list" in lower_command and "folder" in lower_command:
                    outputs.append(_list_directory(context, ".", kind="folders"))
                elif "list" in lower_command and "file" in lower_command:
                    outputs.append(_list_directory(context, ".", kind="files"))
                elif "list" in lower_command:
                    outputs.append(_list_directory(context))
                continue

        if "list" in lower_command or "what files" in lower_command or "what folders" in lower_command:
            kind = "all"
            if "folder" in lower_command or "directories" in lower_command:
                kind = "folders"
            elif "file" in lower_command:
                kind = "files"
            target = "."
            if " in " in lower_command:
                fragment = command[lower_command.index(" in ") + 4:]
                target = _clean_target(fragment.replace("there", ".").replace("here", "."))
            outputs.append(_list_directory(context, target, kind=kind))
            continue

        if any(phrase in lower_command for phrase in ["read ", "show file", "show me file", "open file"]):
            target = _find_path_fragment(command, ["read ", "show file ", "show me file ", "open file "])
            if target:
                outputs.append(_read_file(context, target))
                continue

        if any(phrase in lower_command for phrase in ["search for ", "find "]):
            query = _find_path_fragment(command, ["search for ", "find "])
            if query:
                outputs.append(_search(context, query))
                continue

        outputs.append(
            "I can help with opening applications, navigating folders, listing files, "
            "reading text files, and searching by name."
        )

    return "\n\n".join(outputs) if outputs else "Please say a filesystem action to perform."

