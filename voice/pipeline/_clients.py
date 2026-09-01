from voice.pipeline._config import get_chat_model_name, get_server_endpoint


class LLMClient:
    """Client HTTP pour l'API vllm-mlx."""

    def __init__(self):
        self.base_url = get_server_endpoint()
        self.model = get_chat_model_name()

    def chat_completion(self, messages, tools=None, max_tokens=500):
        import requests

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        resp = requests.post(
            f"{self.base_url}/v1/chat/completions", json=payload, timeout=90
        )
        resp.raise_for_status()
        return resp.json()