import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))




def get_stt():
    global STT_ENGINE
    if STT_ENGINE is None:
        from voice.stt import STTEngine
        STT_ENGINE = STTEngine()
    return STT_ENGINE


def get_tts():
    global TTS_ENGINE
    if TTS_ENGINE is None:
        from voice.tts import TTSEngine
        TTS_ENGINE = TTSEngine()
    return TTS_ENGINE


def chat_response(text):
    """Orchestre une réponse : TaHoma (déterministe) ou LLM (fallback)."""
    from router.orchestrator import orchestrate
    
    # 1. Dispatcheur + orchestrateur
    result = orchestrate(text)
    
    if result["handled"]:
        # Intent TaHoma reconnue → réponse déterministe
        return result["result"]["message"]
    
    # 2. Fallback vers llama-server
    import requests
    try:
        resp = requests.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "Tu es Olympe, un assistant vocal local. Réponds brièvement et naturellement en français."},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            },
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erreur LLM : {e}"


def speak(text):
    """Synthétise et joue directement avec TTSEngine.speak (voix serena)."""
    tts = get_tts()
    tts.speak(text)
    return "played"
