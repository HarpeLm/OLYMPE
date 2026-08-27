"""
Client HTTP pour le serveur vllm-mlx.
Wrapper simple autour de l'API OpenAI-compatible.
"""
import requests
import json


class LLMClient:
    """Client pour l'API vllm-mlx."""
    
    def __init__(self, base_url="http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        self.model = "mlx-community/Qwen3-8B-4bit"
    
    def chat_completion(self, messages, tools=None, max_tokens=500):
        """
        Appelle /v1/chat/completions avec ou sans outils.
        Retourne la réponse JSON complète.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens
        }
        
        if tools:
            payload["tools"] = tools
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=90
        )
        response.raise_for_status()
        return response.json()
