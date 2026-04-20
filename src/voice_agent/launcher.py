"""Launch applications and open files with default system handlers."""

import shutil
import subprocess
from pathlib import Path


# Common application name aliases → Linux executable names
APP_ALIASES: dict[str, str] = {
    # Code editors
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "code": "code",
    "sublime": "subl",
    "sublime text": "subl",
    "vim": "vim",
    "nvim": "nvim",
    "neovim": "nvim",
    "nano": "nano",
    "gedit": "gedit",
    "text editor": "gedit",
    "kate": "kate",
    "atom": "atom",

    # Browsers
    "chrome": "google-chrome",
    "google chrome": "google-chrome",
    "firefox": "firefox",
    "brave": "brave-browser",
    "chromium": "chromium-browser",
    "edge": "microsoft-edge",
    "microsoft edge": "microsoft-edge",

    # Terminals
    "terminal": "gnome-terminal",
    "konsole": "konsole",
    "xterm": "xterm",
    "terminator": "terminator",
    "alacritty": "alacritty",
    "kitty": "kitty",

    # File managers
    "file manager": "nautilus",
    "files": "nautilus",
    "nautilus": "nautilus",
    "dolphin": "dolphin",
    "thunar": "thunar",
    "nemo": "nemo",

    # System utilities
    "calculator": "gnome-calculator",
    "calc": "gnome-calculator",
    "settings": "gnome-control-center",
    "system settings": "gnome-control-center",
    "system monitor": "gnome-system-monitor",
    "task manager": "gnome-system-monitor",
    "htop": "htop",
    "screenshot": "gnome-screenshot",

    # Media
    "vlc": "vlc",
    "media player": "vlc",
    "gimp": "gimp",
    "image editor": "gimp",
    "audacity": "audacity",
    "obs": "obs",
    "obs studio": "obs",
    "shotcut": "shotcut",
    "kdenlive": "kdenlive",

    # Communication
    "slack": "slack",
    "discord": "discord",
    "telegram": "telegram-desktop",
    "teams": "teams",
    "zoom": "zoom",
    "skype": "skype",

    # Office / productivity
    "libreoffice": "libreoffice",
    "writer": "libreoffice --writer",
    "spreadsheet": "libreoffice --calc",
    "presentation": "libreoffice --impress",
    "thunderbird": "thunderbird",
    "postman": "postman",

    # Development
    "docker desktop": "docker",
    "android studio": "android-studio",
    "pycharm": "pycharm",
    "intellij": "intellij-idea",
    "webstorm": "webstorm",
    "clion": "clion",
}


def resolve_application(name: str) -> str | None:
    """Resolve a spoken application name to its executable command.

    Returns the executable string if found, or None.
    """
    lowered = name.lower().strip()

    # 1. Check aliases first
    if lowered in APP_ALIASES:
        executable = APP_ALIASES[lowered]
        cmd_name = executable.split()[0]
        if shutil.which(cmd_name):
            return executable

    # 2. Check if the name itself is directly executable
    if shutil.which(lowered):
        return lowered

    # 3. Try common naming variations
    variations = [
        lowered.replace(" ", "-"),
        lowered.replace(" ", ""),
        lowered.replace(" ", "_"),
    ]
    for variation in variations:
        if shutil.which(variation):
            return variation

    return None


def is_application(name: str) -> bool:
    """Return True if *name* can be resolved to an installed application."""
    return resolve_application(name) is not None


def launch_application(name: str) -> str:
    """Launch an application by its spoken name.

    Returns a human-readable status message.
    """
    executable = resolve_application(name)
    if executable is None:
        return (
            f"Could not find application '{name}' on this system. "
            "Make sure it is installed and available in your PATH."
        )

    try:
        parts = executable.split()
        subprocess.Popen(
            parts,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"Opened {name} successfully."
    except Exception as exc:
        return f"Failed to open {name}: {exc}"


def open_with_default(filepath: str) -> str:
    """Open a file or URL with the system default application (xdg-open).

    Returns a human-readable status message.
    """
    if not shutil.which("xdg-open"):
        return "xdg-open is not available on this system."

    path = Path(filepath)
    if not path.exists():
        return f"File not found: {filepath}"

    try:
        subprocess.Popen(
            ["xdg-open", str(path.resolve())],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"Opened {path.name} with the default application."
    except Exception as exc:
        return f"Failed to open {filepath}: {exc}"
