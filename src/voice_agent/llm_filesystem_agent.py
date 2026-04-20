import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from voice_agent.config import Settings
from voice_agent.filesystem import FilesystemContext, describe_entries
from voice_agent.launcher import launch_application, open_with_default
from voice_agent.llm import build_chat_model


def run_llm_filesystem_agent(
    settings: Settings,
    context: FilesystemContext,
    transcript: str,
) -> str:
    """Use an LLM to plan filesystem steps, execute them safely, and write a reply."""

    llm = build_chat_model(settings)
    plan = _build_plan(llm, settings, context, transcript)
    observations = _execute_plan(plan, context)
    return _build_final_response(llm, settings, context, transcript, observations)


def _build_plan(
    llm: Any,
    settings: Settings,
    context: FilesystemContext,
    transcript: str,
) -> dict[str, Any]:
    system_prompt = SystemMessage(
        content=(
            f"{settings.system_prompt} "
            "You are the planning layer for a read-only filesystem assistant. "
            "Return valid JSON only with no markdown fences. "
            "Schema: "
            '{"steps":[{"action":"change_directory|get_current_directory|list_directory|read_file|search_files|open_application|open_file|respond","path":"optional path","name":"optional app name","query":"optional query","kind":"all|files|folders","message":"optional direct response"}]}. '
            "Use at most 3 steps. "
            "If the user asks to go somewhere and then list or read, include multiple steps. "
            "Never use write/delete/rename/move actions. "
            f"Current directory: {context.current_directory}. "
            f"Allowed roots: {', '.join(str(root) for root in context.allowed_roots)}."
        )
    )
    human_message = HumanMessage(content=f"User request: {transcript}")
    raw = llm.invoke([system_prompt, human_message])
    content = _message_text(raw.content)
    try:
        plan = _extract_json_object(content)
    except Exception:
        return {
            "steps": [
                {
                    "action": "respond",
                    "message": (
                        "I could not create a structured action plan from the request. "
                        f"Raw planner output: {content}"
                    ),
                }
            ]
        }

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        return {"steps": [{"action": "respond", "message": "I could not build a valid action plan."}]}
    return {"steps": steps[:3]}


def _execute_plan(plan: dict[str, Any], context: FilesystemContext) -> list[str]:
    observations: list[str] = []
    for raw_step in plan.get("steps", []):
        if not isinstance(raw_step, dict):
            observations.append("Ignored an invalid non-dictionary step.")
            continue

        action = str(raw_step.get("action", "")).strip()
        path = str(raw_step.get("path", "")).strip()
        name = str(raw_step.get("name", "")).strip()
        query = str(raw_step.get("query", "")).strip()
        kind = str(raw_step.get("kind", "all")).strip() or "all"
        message = str(raw_step.get("message", "")).strip()

        try:
            if action == "change_directory":
                observations.append(_change_directory(context, path))
            elif action == "get_current_directory":
                observations.append(f"Current directory is {context.current_directory}.")
            elif action == "list_directory":
                observations.append(_list_directory(context, path or ".", kind))
            elif action == "read_file":
                observations.append(_read_file(context, path))
            elif action == "search_files":
                observations.append(_search_files(context, query, path or "."))
            elif action == "open_application":
                observations.append(launch_application(name or path))
            elif action == "open_file":
                observations.append(_open_file(context, path))
            elif action == "respond":
                observations.append(message or "No valid action was chosen.")
            else:
                observations.append(f"Unsupported planned action: {action or 'empty action'}.")
        except Exception as exc:  # keep the reply flowing instead of crashing the turn
            observations.append(f"Action '{action}' failed: {exc}")
    return observations


def _build_final_response(
    llm: Any,
    settings: Settings,
    context: FilesystemContext,
    transcript: str,
    observations: list[str],
) -> str:
    system_prompt = SystemMessage(
        content=(
            f"{settings.system_prompt} "
            "You are the response writer for a read-only filesystem assistant. "
            "Use the observations exactly as ground truth. "
            "Do not invent filesystem details. "
            "Keep the answer natural, concise, and voice-friendly."
        )
    )
    human_message = HumanMessage(
        content=(
            f"User request: {transcript}\n"
            f"Current directory after execution: {context.current_directory}\n"
            "Observations:\n"
            + "\n".join(f"- {item}" for item in observations)
        )
    )
    raw = llm.invoke([system_prompt, human_message])
    text = _message_text(raw.content).strip()
    if text:
        return text
    return "\n".join(observations).strip()


def _resolve_existing(context: FilesystemContext, target: str) -> Path:
    raw = target.strip()
    if not raw or raw in {"here", "there", "."}:
        return context.current_directory

    candidates = [raw]
    if not raw.startswith("~/") and "/" not in raw:
        candidates.extend([f"~/{raw}", f"~/Downloads/{raw}", f"~/Documents/{raw}"])

    for candidate in candidates:
        try:
            resolved = context.resolve_path(candidate)
        except Exception:
            continue
        if resolved.exists():
            return resolved
    return context.resolve_path(raw)


def _change_directory(context: FilesystemContext, target: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"Directory not found: {target}"
    if not path.is_dir():
        return f"Path is not a directory: {path}"
    context.current_directory = path
    return f"Current directory changed to {path}"


def _list_directory(context: FilesystemContext, target: str, kind: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"Directory not found: {target}"
    if not path.is_dir():
        return f"Path is not a directory: {path}"

    if kind == "all":
        return describe_entries(path)

    entries = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    if kind == "folders":
        entries = [item for item in entries if item.is_dir()]
    elif kind == "files":
        entries = [item for item in entries if item.is_file()]

    if not entries:
        return f"No {kind} found in {path}."
    lines = [f"{kind.capitalize()} in {path}:"]
    for entry in entries:
        lines.append(f"- {entry.name}")
    return "\n".join(lines)


def _read_file(context: FilesystemContext, target: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"File not found: {target}"
    if path.is_dir():
        return f"{path} is a directory, not a file."
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"{path} is not a plain text file."
    if len(content) > 4000:
        content = content[:4000] + "\n... [truncated]"
    return f"Contents of {path}:\n{content}"


def _search_files(context: FilesystemContext, query: str, target: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"Directory not found: {target}"
    if not path.is_dir():
        return f"Path is not a directory: {path}"

    matches: list[Path] = []
    lowered = query.lower()
    for item in path.rglob("*"):
        if lowered in item.name.lower():
            matches.append(item)
        if len(matches) >= 25:
            break

    if not matches:
        return f"No files or folders matching '{query}' were found under {path}."

    lines = [f"Matches for '{query}' under {path}:"]
    for item in matches:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _open_file(context: FilesystemContext, target: str) -> str:
    path = _resolve_existing(context, target)
    if not path.exists():
        return f"File not found: {target}"
    if path.is_dir():
        return f"{path} is a directory, not a file."
    return open_with_default(str(path))


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if "\n" in cleaned:
            cleaned = cleaned.split("\n", 1)[1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text", "")).strip()
                if text:
                    parts.append(text)
        return " ".join(parts).strip()
    return str(content)
