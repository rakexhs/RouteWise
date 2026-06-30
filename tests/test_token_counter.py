from app.gateway.token_counter import count_messages_tokens, count_tokens


def test_count_tokens_heuristic():
    text = "hello world from routewise"
    tokens = count_tokens(text, model="unknown-model-xyz")
    assert tokens >= 1


def test_count_messages_tokens():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    total = count_messages_tokens(messages)
    assert total > 2
