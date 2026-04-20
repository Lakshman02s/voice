from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from voice_agent.config import Settings
from voice_agent.filesystem import FilesystemContext
from voice_agent.llm_filesystem_agent import run_llm_filesystem_agent
from voice_agent.llm import build_chat_model
from voice_agent.local_agent import run_local_agent
from voice_agent.prompts import build_system_prompt
from voice_agent.state import VoiceAgentState
from voice_agent.tools import build_tools


def _assistant_node_factory(
    settings: Settings,
    tools: list[Any],
    context: FilesystemContext,
):
    if settings.model_provider == "local":
        def assistant_node(state: VoiceAgentState) -> dict[str, Any]:
            reply = run_local_agent(state["transcript"], context)
            return {"messages": [AIMessage(content=reply)]}

        return assistant_node

    if settings.model_provider == "ollama":
        def assistant_node(state: VoiceAgentState) -> dict[str, Any]:
            reply = run_llm_filesystem_agent(settings, context, state["transcript"])
            return {"messages": [AIMessage(content=reply)]}

        return assistant_node

    llm = build_chat_model(settings).bind_tools(tools)

    def assistant_node(state: VoiceAgentState) -> dict[str, Any]:
        system_message = SystemMessage(
            content=build_system_prompt(
                settings=settings,
                current_directory=str(context.current_directory),
                allowed_roots=[str(root) for root in context.allowed_roots],
            )
        )
        response = llm.invoke([system_message, *state["messages"]])
        return {"messages": [response]}

    return assistant_node


def _extract_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    parts.append(text)
        return " ".join(parts).strip()
    return str(content)


def finalize_node(state: VoiceAgentState) -> dict[str, str]:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        raise TypeError("Expected the final message in state to be an AIMessage.")
    return {
        "response_text": _extract_text(last_message),
        "current_directory": state["current_directory"],
    }


def build_graph(settings: Settings, context: FilesystemContext):
    tools = build_tools(context)
    graph = StateGraph(VoiceAgentState)

    graph.add_node("assistant", _assistant_node_factory(settings, tools, context))
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "assistant")
    if settings.model_provider in {"local", "ollama"}:
        graph.add_edge("assistant", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    graph.add_node("tools", ToolNode(tools))
    graph.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools": "tools",
            END: "finalize",
        },
    )
    graph.add_edge("tools", "assistant")
    graph.add_edge("finalize", END)

    return graph.compile()
