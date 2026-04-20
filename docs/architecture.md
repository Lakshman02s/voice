# Voice Agent Architecture

## 1. Purpose of this project

This project is a `local voice-controlled filesystem assistant`.

Its job is to let a user say or type commands such as:

- `go to Downloads`
- `what folders are there`
- `read README.md`
- `search for pyproject`

and have the system:

1. understand the request
2. safely inspect the local filesystem
3. preserve conversational context like the current folder
4. return a clear answer

The main learning goal is not only to build a working assistant, but to understand how a voice agent is structured from end to end.

## 2. Core product idea

At a high level, this agent combines three layers:

1. `Input layer`
   This receives user input either as typed text or microphone audio.

2. `Agent layer`
   This interprets the request, decides what action to take, and generates the reply.

3. `Execution layer`
   This performs safe filesystem operations and returns the result.

The architecture is intentionally modular so each layer can be learned, tested, and upgraded independently.

## 3. High-level workflow

### Text workflow

```text
User types command
-> CLI receives text
-> Session sends transcript into agent graph
-> Agent decides action
-> Filesystem layer executes safe read-only operation
-> Agent produces reply
-> CLI prints response
```

### Voice workflow

```text
User speaks into microphone
-> Microphone recorder captures WAV audio
-> Speech-to-text transcriber converts audio to transcript
-> Session sends transcript into agent graph
-> Agent decides action
-> Filesystem layer executes safe read-only operation
-> Agent produces reply
-> CLI prints response
```

### Conceptual architecture

```text
                 +----------------------+
                 |      User Input      |
                 | text or microphone   |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |      CLI Layer       |
                 | chat / repl / listen |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |     Session Layer    |
                 | messages + cwd state |
                 +----------+-----------+
                            |
                            v
             +----------------------------------+
             |         Agent Layer              |
             | LangGraph or local command path  |
             +----------------+-----------------+
                              |
                              v
             +----------------------------------+
             |      Filesystem Safety Layer     |
             | root checks + path resolution    |
             +----------------+-----------------+
                              |
                              v
             +----------------------------------+
             |      Local Machine Resources     |
             | folders, files, search results   |
             +----------------------------------+
```

## 4. Main architectural decision

The most important design decision in this project is:

`The model does not get direct unrestricted access to the machine.`

Instead:

- the agent understands user intent
- Python code performs the real filesystem action
- the filesystem code enforces the safety rules

This matters because it gives:

- predictability
- security
- easier debugging
- cleaner separation of concerns

## 5. Two execution modes in this project

This project currently supports two agent execution styles.

### Mode A: `local`

This is the current easiest and most reliable mode.

In this mode:

- there is no cloud LLM requirement
- there is no tool-calling model requirement
- the transcript is parsed by local Python logic in `local_agent.py`

This mode is especially useful when:

- you want to learn the architecture first
- you want the project to work on your machine immediately
- your hosted model setup is not ready
- your local Ollama models do not support tool calling well

### Mode B: `openai` or `ollama`

In these modes:

- the agent uses a real LLM
- LangGraph can route to tool nodes
- tool calling becomes part of the workflow

This mode is useful when:

- you want more flexible natural language understanding
- you want to experiment with model-based reasoning
- you want to evolve toward a more advanced agent

## 6. Directory and file responsibilities

### `src/voice_agent/config.py`

Responsibility:

- load runtime configuration from `.env`
- provide a single source of truth for providers and audio settings

Important settings:

- `MODEL_PROVIDER`
- `ALLOWED_ROOTS`
- `DEFAULT_START_DIRECTORY`
- `STT_PROVIDER`
- `STT_MODEL_SIZE`
- `MIC_SAMPLE_RATE`
- `MIC_CHANNELS`
- `MIC_DURATION_SECONDS`
- `MIC_DEVICE`

Architectural role:

This file makes the system configurable without changing code.

### `src/voice_agent/cli.py`

Responsibility:

- expose runnable commands
- collect user input
- route input to the session
- print outputs

Commands:

- `chat`
- `repl`
- `listen`
- `voice-repl`
- `warmup-stt`
- `list-input-devices`

Architectural role:

This is the boundary between the user and the internal system.

### `src/voice_agent/session.py`

Responsibility:

- preserve state across turns
- own the conversation history
- keep the filesystem context alive across requests

Architectural role:

The session is what makes multi-turn interaction possible.

Without it, commands like:

- `go to Downloads`
- `what files are there`

would not work naturally, because the second command depends on the first.

### `src/voice_agent/state.py`

Responsibility:

- define the graph state contract

State fields:

- `messages`
- `transcript`
- `response_text`
- `current_directory`
- `allowed_roots`

Architectural role:

This file defines what information moves through the graph.

### `src/voice_agent/graph.py`

Responsibility:

- build the LangGraph workflow
- choose local-path vs LLM-path behavior
- finalize the assistant reply

Architectural role:

This is the orchestration layer.

It decides:

- what node runs
- when tools are used
- when the reply is considered final

### `src/voice_agent/local_agent.py`

Responsibility:

- handle local-mode command interpretation without an LLM
- parse direct filesystem commands
- update current-directory context

Architectural role:

This file is the practical fallback brain when you do not want model dependency.

It provides deterministic behavior for common commands.

### `src/voice_agent/llm.py`

Responsibility:

- create the model client for OpenAI or Ollama

Architectural role:

This isolates provider-specific code from the rest of the system.

Because of this isolation, the graph and CLI do not need to know provider details.

### `src/voice_agent/prompts.py`

Responsibility:

- build the system prompt for LLM-backed modes

Architectural role:

This is where behavioral instructions live:

- stay within allowed roots
- rely on tools instead of guessing
- keep replies natural
- avoid unsafe claims

### `src/voice_agent/tools.py`

Responsibility:

- define model-callable filesystem tools

Current tools:

- `get_current_directory`
- `change_directory`
- `list_directory`
- `read_file`
- `search_files`

Architectural role:

These tools are the controlled interface between the LLM and the machine.

### `src/voice_agent/filesystem.py`

Responsibility:

- resolve paths
- enforce allowed-root boundaries
- reject unsafe paths
- describe directory contents

Architectural role:

This is the main safety gate of the whole project.

### `src/voice_agent/audio.py`

Responsibility:

- microphone recording
- speech-to-text transcription
- audio warmup
- device discovery

Architectural role:

This is the voice I/O adapter layer.

It is intentionally separate from the agent logic so audio changes do not require graph changes.

## 7. Detailed execution flow

### 7.1 `chat` command flow

```text
voice-agent chat --text "go to Downloads"
-> cli.py receives text
-> TextPassthroughTranscriber returns same text
-> Session is created
-> Session invokes graph
-> Graph calls local agent or LLM path
-> Filesystem action runs
-> Final response is printed
```

### 7.2 `repl` flow

```text
voice-agent repl
-> session created once
-> loop waits for input
-> each input becomes transcript
-> session reuses message history and current directory
-> response printed
```

This is important because the filesystem context survives between turns.

### 7.3 `listen` flow

```text
voice-agent listen --duration 7
-> create session
-> record microphone audio into temporary wav
-> transcribe wav using faster-whisper
-> transcript sent into agent
-> agent produces answer
-> answer printed
-> temporary audio removed unless save requested
```

### 7.4 `voice-repl` flow

```text
voice-agent voice-repl
-> session created once
-> each turn records microphone audio
-> STT creates transcript
-> agent responds
-> current directory and message history persist
```

### 7.5 `warmup-stt` flow

```text
voice-agent warmup-stt
-> load faster-whisper model into cache
-> download model if first run
-> prepare for faster later transcription
```

This command exists to separate model download time from user speaking time.

## 8. LangGraph workflow in detail

When `MODEL_PROVIDER` is not `local`, the graph uses LangGraph more fully.

### Graph nodes

1. `assistant`
   The model receives the system prompt plus message history.

2. `tools`
   Tool calls are executed here.

3. `finalize`
   The final assistant message is converted into plain response text.

### Graph path

```text
START
-> assistant
-> if tool call -> tools -> assistant
-> if no tool call -> finalize
-> END
```

### Why this matters

This structure is useful because it separates:

- reasoning
- execution
- response packaging

That makes the system easier to scale later.

## 9. Local-mode workflow in detail

When `MODEL_PROVIDER=local`, the graph still exists, but the assistant node behaves differently.

Instead of calling an external LLM:

- `graph.py` routes to `run_local_agent()`
- `local_agent.py` parses the transcript with deterministic rules
- filesystem context is updated directly

This is a hybrid architecture:

- graph-based orchestration
- local deterministic command handling

That gives you a working system even without an online model.

## 10. Filesystem safety model

This is the most important non-voice part of the system.

### Allowed roots

The agent is limited to folders configured in:

- `ALLOWED_ROOTS`

Examples:

- project directory
- `~/Downloads`
- `~/Documents`

### Path resolution

Every requested path is:

1. expanded
2. resolved relative to current directory if needed
3. normalized to an absolute path
4. checked against allowed roots

If the path is outside allowed roots, access is rejected.

### Read-only scope

The system currently supports only:

- listing directories
- changing current directory inside safe roots
- reading text files
- searching by name

It does not support:

- delete
- write
- rename
- move
- execute arbitrary shell commands

### Why this design is good

This protects the machine from accidental or unsafe actions while you are still learning agent architecture.

## 11. Session and memory design

The project currently uses `session memory`, not long-term persistent memory.

### What is preserved inside a session

- message history
- current directory
- allowed roots

### What is not yet preserved across app restarts

- previous session history
- previous chosen directory
- user preferences

That means:

- `repl` and `voice-repl` remember context while running
- starting a new command starts a fresh session

## 12. Voice pipeline design

### Microphone capture

`MicrophoneRecorder` records:

- sample rate
- channels
- optional selected device

and stores the result in WAV format.

### STT

`FasterWhisperTranscriber`:

- loads a Whisper-compatible model
- transcribes the WAV
- returns plain text

### STT warmup

The transcriber model is cached with `lru_cache`, which helps:

- avoid repeated model initialization
- keep later turns faster

### Input device handling

The system now includes:

- `MIC_DEVICE`
- `list-input-devices`
- silence detection

This matters especially for Bluetooth earbuds, where Linux audio profiles often affect microphone availability.

## 13. Why the Bluetooth issue happens

Bluetooth earbuds often expose different audio modes:

- high-quality playback mode
- headset/handsfree mode with microphone

In many Linux setups:

- playback mode gives better audio output
- headset mode is required for microphone input

So if the transcription shows silence or nonsense, the problem is often not the STT model, but the system audio routing or device profile.

## 14. Error handling strategy

The project currently handles errors at several layers.

### Config errors

Example:

- missing API key
- unsupported provider

### Audio errors

Example:

- PortAudio missing
- microphone package missing
- silent recording
- no speech detected

### Filesystem errors

Example:

- path not found
- outside allowed roots
- file is actually a directory

### Provider errors

Example:

- OpenAI authentication failures
- Ollama model mismatch

This layered error handling is important because voice-agent debugging becomes much easier when failures are categorized clearly.

## 15. Why this architecture is good for learning

This project is a strong learning architecture because it separates the hard parts:

- voice capture
- transcription
- intent/agent reasoning
- safe execution
- conversational state

That gives you a system you can debug piece by piece.

For example:

- if microphone fails, fix `audio.py`
- if transcript is bad, tune STT
- if command interpretation is bad, improve local parsing or prompts
- if unsafe access happens, tighten `filesystem.py`

## 16. Current limitations

This architecture is solid, but still intentionally early-stage.

Current limitations:

- no spoken output yet
- no persistent memory across app restarts
- local parser is rule-based, not deeply semantic
- no confirmation flow for future write actions
- no observability dashboard
- no async streaming voice conversation
- no wake-word support

These are normal and expected for the current phase.

## 17. Recommended future evolution

### Near-term

- add TTS reply audio
- improve microphone device selection UX
- add saved session checkpoints
- improve transcript cleanup
- add richer command references like `open the first one`

### Mid-term

- add persistent memory
- add write actions with confirmation
- add better intent classification
- add structured command objects

### Long-term

- wake-word + always-on listening
- streaming STT
- streaming TTS
- multi-agent coordination
- domain-specific assistants beyond filesystem control

## 18. Mental model of the whole system

The easiest way to think about this project is:

```text
Voice/File Agent
=
Input Adapter
+ Session Memory
+ Agent Brain
+ Safe Filesystem Executor
+ Output Renderer
```

More concretely:

```text
Microphone or text
-> transcript
-> session
-> agent logic
-> safe filesystem action
-> reply
```

That is the real architecture you are building here.

## 19. Summary

This project is a read-only, local-first voice filesystem assistant.

Its architecture is built around these principles:

- separate voice I/O from agent logic
- separate reasoning from filesystem execution
- preserve conversational context in a session
- enforce safety in Python, not in the model alone
- support both deterministic local behavior and LLM-backed behavior

Because of that structure, the project is already a strong foundation for:

- local file navigation by voice
- future spoken replies
- more advanced tool-calling agents
- production-like safety patterns
