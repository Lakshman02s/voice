from langchain_core.messages import AIMessage

from voice_agent.graph import finalize_node


def test_finalize_node_extracts_plain_text():
    result = finalize_node(
        {
            "messages": [AIMessage(content="Hello from the assistant")],
            "transcript": "hi",
            "response_text": "",
            "current_directory": "/tmp",
            "allowed_roots": ["/tmp"],
        }
    )

    assert result["response_text"] == "Hello from the assistant"


def test_finalize_node_joins_structured_text_blocks():
    result = finalize_node(
        {
            "messages": [
                AIMessage(
                    content=[
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": "world"},
                    ]
                )
            ],
            "transcript": "hi",
            "response_text": "",
            "current_directory": "/tmp",
            "allowed_roots": ["/tmp"],
        }
    )

    assert result["response_text"] == "Hello world"
