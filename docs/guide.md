# Detailed Guide

## 1. What we are building

A local file voice agent usually has this flow:

```text
User speaks
-> Speech to text
-> LangGraph agent decides what to do
-> LLM answers or calls filesystem tools
-> Final text reply
-> Text to speech
-> Spoken response
```

In this project, the LangGraph part and the filesystem tool layer are fully implemented. The audio layer is still represented with simple interfaces and console-based implementations so you can learn the agent behavior first.

## 2. Why LangGraph?

LangGraph is useful when your agent has steps, branching, memory, or tool loops.

A plain LLM call is enough for simple question-answering.
LangGraph becomes valuable when you need:

- structured state
- retries or guarded steps
- tool calling loops
- multi-step workflows
- persistent memory later

For a file voice agent, this matters because requests are stateful:

- `go to Downloads`
- `what files are there`
- `read the first markdown file`

The second and third requests depend on the earlier context.

## 3. Core architecture in this project

The main pieces are:

- `config.py`
  Loads environment variables and keeps provider settings in one place.

- `llm.py`
  Builds the chat model. Today it supports OpenAI and Ollama.

- `filesystem.py`
  Contains the safe path-resolution logic and allowed-root checks.

- `tools.py`
  Defines callable filesystem tools the agent can use.

- `state.py`
  Defines the graph state structure.

- `graph.py`
  Builds the LangGraph workflow.

- `audio.py`
  Defines the speech input/output abstraction layer.

- `session.py`
  Preserves the current directory and message history across turns.

- `cli.py`
  Gives you an easy way to run and inspect the project.

## 4. Understanding the graph

The graph in this project follows this pattern:

```text
START
-> assistant node
-> if tool needed -> tools node -> assistant node
-> if no tool needed -> finalize node
-> END
```

### Assistant node

This node sends the conversation state to the LLM.

If the LLM decides a tool is needed, it emits tool calls.
If it already has the final answer, it returns a normal AI message.

### Tools node

This node executes tool calls selected by the model.

In this project, the main tools are:

- `get_current_directory`
- `change_directory`
- `list_directory`
- `read_file`
- `search_files`

That is enough to build a practical local file assistant.

### Finalize node

This node extracts the final assistant message into a plain text field so the rest of the system can easily send it to a speaker or UI.

## 5. Why the state matters

LangGraph revolves around state.

The state here keeps:

- `messages`: the full conversation message list
- `transcript`: the most recent user transcript
- `response_text`: the final response in plain text form
- `current_directory`: the current folder in the session
- `allowed_roots`: the folders the agent is allowed to access

This is important because the graph nodes do not pass random variables around. They update shared state in a controlled way.

## 6. Where real voice support plugs in

Real voice agents still need two external adapters:

### Speech to text

Examples:

- OpenAI speech-to-text
- Whisper local model
- Deepgram
- AssemblyAI

### Text to speech

Examples:

- OpenAI TTS
- ElevenLabs
- Azure TTS
- local TTS engines

In this starter, `audio.py` uses simple interfaces so you can replace the placeholder implementations later without changing the graph itself.

That separation is one of the biggest design wins in agent systems.

## 7. How safe filesystem access works

This agent does not let the model freely touch the whole machine.

Instead:

- every tool request goes through `filesystem.py`
- paths are resolved against the current directory
- the final resolved path must stay inside one of the allowed roots
- only read-only operations are exposed

This pattern is important. The LLM chooses intent, but your Python code enforces safety.

## 8. How to grow this into a production voice agent

After you understand the starter, the natural next steps are:

1. Replace the text transcriber with microphone or Whisper-based transcription.
2. Replace console output with a real speech synthesizer.
3. Add richer references like `open the first file` or `read that markdown file`.
4. Add confirmation flow before sensitive actions.
5. Add logging, retries, and observability.

## 9. OpenAI vs Ollama

This project supports both patterns:

### OpenAI

Use this if you want fast setup and strong hosted model performance.

Pros:

- easy to start
- strong general reasoning
- simpler setup

Tradeoff:

- requires API key
- cloud dependency

### Ollama

Use this if you want local inference and privacy-friendly development.

Pros:

- local model hosting
- no per-request cloud cost
- useful for experiments

Tradeoff:

- quality depends on local model
- local setup and hardware matter more

## 10. How to study this project

Best order:

1. Read `filesystem.py`
2. Read `tools.py`
3. Read `state.py`
4. Read `graph.py`
5. Read `session.py`
6. Run `voice-agent chat --text "Go to Downloads and list files"`
7. Run `voice-agent repl`

When you can explain the graph loop in your own words, you are ready to add real audio components.

## 11. Suggested next upgrade

If you want, the next step after this starter should be one of these:

- microphone input + TTS output
- Whisper STT integration
- persistent memory with checkpoints
- file modification tools with explicit confirmation

This starter is a foundation for all of those.
