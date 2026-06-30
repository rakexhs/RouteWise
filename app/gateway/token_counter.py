def count_tokens(text: str, model: str = "gpt-4") -> int:
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text.split()))


def count_messages_tokens(messages: list[dict[str, str]], model: str = "gpt-4") -> int:
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""), model) + 4
    return total
