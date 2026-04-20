# LangGraph Voice File Agent

This project is now focused on the exact use case you described:

- give a spoken-style command
- let the agent understand it
- safely inspect files and folders on your machine
- answer in a natural, voice-friendly way

The current implementation is a text-first version of that voice agent. That is the right way to build it because the reasoning and filesystem tools should be stable before we add microphone input and speaker output.

## Project layout

```text
voice/
├── .env.example
├── README.md
├── docs/
│   └── guide.md
├── pyproject.toml
├── src/
│   └── voice_agent/
│       ├── __init__.py
│       ├── __main__.py
│       ├── audio.py
│       ├── cli.py
│       ├── config.py
│       ├── filesystem.py
│       ├── graph.py
│       ├── llm.py
│       ├── prompts.py
│       ├── session.py
│       ├── state.py
│       └── tools.py
└── tests/
    ├── test_filesystem.py
    └── test_graph.py
```

## Quick start

1. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the project:

```bash
pip install -e ".[dev]"
```

3. Copy the environment file:

```bash
cp .env.example .env
```

4. Pick a provider:

- Recommended: use `MODEL_PROVIDER=ollama` with `OLLAMA_MODEL=qwen2.5:0.5b` for a lightweight local LLM-backed setup.
- For OpenAI, set `MODEL_PROVIDER=openai` and add `OPENAI_API_KEY`.
- `MODEL_PROVIDER=local` still exists as a deterministic fallback, but the main active path is now LLM-backed.

5. Optional: adjust which folders the agent may read in `.env`:

```env
ALLOWED_ROOTS=.:~/Downloads:~/Documents
DEFAULT_START_DIRECTORY=.
```

6. Run a single turn:

```bash
voice-agent chat --text "Go to Downloads and tell me what files are there"
```

7. Run the interactive text loop:

```bash
voice-agent repl
```

8. Install the microphone transcription dependency:

```bash
pip install -e ".[voice]"
```

9. Speak one command through the microphone:

```bash
voice-agent listen --duration 5
```

10. Run repeated spoken turns:

```bash
voice-agent voice-repl --duration 5
```

## What this project now demonstrates

- LangGraph `StateGraph`
- Tool routing with conditional edges
- Shared typed state
- LLM provider abstraction
- Safe local filesystem tool calling
- Current-directory tracking across turns
- Text-based simulation of a voice loop
- Clean separation between agent logic and audio I/O

## What the agent can do

- list files in a folder
- move between allowed directories
- read text files
- search for files by name
- explain results in natural language

Example requests:

- `Go to Downloads and list the files`
- `Open the voice folder`
- `Read README.md`
- `Search for pyproject inside this project`
- `Where am I right now?`
- Speak: `Go to Downloads and list the folders there`

## Safety model

This agent is intentionally read-only for now.

- It can inspect files and folders.
- It cannot edit, delete, move, or rename files.
- It is restricted to the folders defined in `ALLOWED_ROOTS`.

That makes it a much safer starting point for a local machine agent.

## Next reading

- High-level guide: [docs/guide.md](docs/guide.md)
- Full architecture: [docs/architecture.md](docs/architecture.md)
