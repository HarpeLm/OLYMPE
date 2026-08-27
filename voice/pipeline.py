"""
Boucle vocale complète OLYMPE — Palier 6

Orchestration : wake word -> bip -> STT -> dispatcheur -> [action | LLM + outils MCP] -> TTS

Stratégie mémoire (décision P5, documentée dans DECISIONS.md) :
  - Résidents permanents : wake word + dispatcheur + STT + TTS
  - LLM via API HTTP vllm-mlx (serveur persistant, cache KV préservé)
  - Tool-calling : vllm-mlx ne fait PAS la boucle (mesuré le 2026-08-27),
    donc la boucle est orchestrée ici ; les outils sont déclarés ET exécutés
    via le serveur MCP (agent/mcp_server.py), source de vérité unique.
"""
import argparse
import asyncio
import json
import queue
import sys
import time
import uuid
from pathlib import Path

import numpy as np
import sounddevice as sd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"
MCP_SERVER_PATH = ROOT / "agent" / "mcp_server.py"
sys.path.insert(0, str(ROOT))

from voice.wake_word import WakeWordEngine
from voice.stt import STTEngine
from voice.tts import TTSEngine
from router.dispatcher import Dispatcher
from router.prefilter import FAMILIES, repair_calendar_slots, calendar_intent_hint
from agent.memory import Memory

SAMPLE_RATE = 16000
BLOCK_SIZE = 1280

# Construit par concaténation pour éviter tout problème de formatage
THINK_OPEN = "<" + "think>"
THINK_CLOSE = "</" + "think>"

SYSTEM_PROMPT = (
    "Tu es OLYMPE, un assistant vocal local qui tourne sur le Mac de "
    "l'utilisateur. Réponds en français, de façon concise et naturelle, "
    "en une ou deux phrases adaptées à une lecture à voix haute. "
    "Évite les listes, les tableaux et le formatage markdown. "
    "Utilise les outils disponibles quand nécessaire. "
    "MÉMOIRE : si l'utilisateur te demande de te souvenir de quelque chose, "
    "appelle d'abord l'outil remember avec ce fait, puis confirme. "
    "Si on te demande ce dont tu te souviens, appelle recall et réponds "
    "uniquement à partir de son résultat, sans rien inventer."
)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_chat_model_name():
    """Lit le modèle chat depuis config/models.yaml (zéro codé en dur)."""
    cfg = load_config()
    chat = cfg.get("roles", {}).get("chat", {})
    name = chat.get("repo") if isinstance(chat, dict) else chat
    if not name:
        raise KeyError("Role 'chat' absent de config/models.yaml")
    return name


def get_server_endpoint():
    cfg = load_config()
    server = cfg.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", 8000)
    return f"http://{host}:{port}"


def beep(duration=0.18, freq=880, sample_rate=24000):
    """Bip de confirmation après détection du wake word."""
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    audio = (0.25 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


class MCPBridge:
    """Pont vers le serveur MCP d'outils : déclaration + exécution."""

    def _server_params(self):
        from mcp.client.stdio import StdioServerParameters
        return StdioServerParameters(
            command=sys.executable, args=[str(MCP_SERVER_PATH)]
        )

    def list_tools_openai(self):
        """Récupère les outils du serveur MCP au format OpenAI."""
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        async def _list():
            async with stdio_client(self._server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    return [
                        {
                            "type": "function",
                            "function": {
                                "name": t.name,
                                "description": t.description or "",
                                "parameters": t.inputSchema
                                or {"type": "object", "properties": {}},
                            },
                        }
                        for t in tools.tools
                    ]

        return asyncio.run(_list())

    def call_tool(self, name, arguments):
        """Exécute un outil via le serveur MCP."""
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        async def _call():
            async with stdio_client(self._server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    texts = [
                        b.text for b in result.content if getattr(b, "text", None)
                    ]
                    return texts[0] if texts else "(aucun contenu)"

        return asyncio.run(_call())


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


class VoicePipeline:
    def __init__(self, listen_duration=5.0):
        self.listen_duration = listen_duration

        print("[PIPELINE] Initialisation des composants résidents...")
        self.wake = WakeWordEngine()
        self.dispatcher = Dispatcher()
        self.stt = STTEngine()
        self.stt.load()
        self.tts = TTSEngine()
        self.tts.load()
        self.llm = LLMClient()
        self.mcp = MCPBridge()
        self.memory = Memory()
        self.session_id = str(uuid.uuid4())[:8]

        try:
            self.tools = self.mcp.list_tools_openai()
            print(f"[PIPELINE] {len(self.tools)} outil(s) MCP chargé(s).")
        except Exception as e:
            print(f"[PIPELINE] Outils MCP indisponibles : {e}")
            self.tools = []

        print("[PIPELINE] Prêt.")

    def wait_for_wake(self):
        """Bloque jusqu'à détection du wake word. Retourne le score."""
        audio_queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[PIPELINE][Warning] {status}", file=sys.stderr)
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=BLOCK_SIZE,
            callback=callback,
        ):
            while True:
                block = audio_queue.get()
                score = self.wake.process_block(block.squeeze())
                if score > self.wake.threshold:
                    self.wake.reset()
                    return score

    def clean_llm_content(self, content):
        import re as _re
        content = _re.sub("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", content or "")
        """Nettoie toute fuite de raisonnement avant TTS."""
        if not content:
            return ""

        # Cas normal : raisonnement fermé, on garde après la fermeture.
        if THINK_CLOSE in content:
            content = content.split(THINK_CLOSE, 1)[1]

        # Cas dangereux : ouverture sans fermeture.
        # On ne lit jamais le raisonnement à voix haute.
        if THINK_OPEN in content:
            before = content.split(THINK_OPEN, 1)[0].strip()
            return before

        return content.strip()

    def _memory_context(self):
        ctx = self.memory.context_prompt()
        return "\n\n" + ctx if ctx else ""

    def llm_with_tools(self, text):
        """Boucle tool-calling : détecte, exécute via MCP, réinjecte."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + self._memory_context()},
            {"role": "user", "content": text + "\\n/no_think"},
        ]

        for _ in range(3):  # garde-fou anti-boucle infinie
            data = self.llm.chat_completion(
                messages, tools=self.tools or None, max_tokens=1024
            )
            choice = data["choices"][0]
            msg = choice["message"]

            if choice.get("finish_reason") != "tool_calls" or not msg.get(
                "tool_calls"
            ):
                content = msg.get("content") or ""
                content = self.clean_llm_content(content)
                if not content:
                    content = "Désolé, je n'ai pas trouvé de réponse précise."
                return content

            messages.append(msg)
            for tc in msg["tool_calls"]:
                fname = tc["function"]["name"]
                try:
                    fargs = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    fargs = {}

                print(f"[TOOL] Appel : {fname}({fargs})")
                try:
                    result = self.mcp.call_tool(fname, fargs)
                except Exception as e:
                    result = f"Erreur outil : {e}"
                print(f"[TOOL] Résultat : {result}")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )

        return "Désolé, je n'ai pas pu terminer l'action."

    def handle_command(self, text):
        """Route : déterministe (dispatcheur) ou LLM + outils."""
        result = self.dispatcher.route(text)
        intent = result.get("intent")
        action = result.get("action")
        confidence = result.get("confidence")
        print(
            f"[PIPELINE] Intent={intent} | action={action} | confiance={confidence}"
        )

        if action == "deterministic" and intent == "get_events_today":
            import re as _re
            if "aujourd" not in text.lower():
                m = _re.search(
                    r"(après-demain|demain|lundi|mardi|mercredi|jeudi|vendredi|"
                    r"samedi|dimanche|\d{1,2}/\d{1,2}(?:/\d{4})?)", text, _re.I)
                if m:
                    result["intent"] = "get_events_date"
                    result["slots"] = {"date": m.group(1).lower()}
                    result["handler"] = self.dispatcher.schemas.get(
                        "get_events_date", {}).get("handler")
                    intent = "get_events_date"
                    print(f"[REPAIR] rerouté get_events_date : {result['slots']}")

        if action == "fallback":
            in_cal = intent in FAMILIES.get("calendar", set())
            hinted = calendar_intent_hint(text)
            if in_cal or hinted:
                target = intent if in_cal else hinted
                repaired = repair_calendar_slots(text, result.get("slots"))
                if repaired.get("title") or target != "create_event":
                    result["intent"] = target
                    result["slots"] = repaired
                    result["action"] = "deterministic"
                    result["confidence"] = 0.75
                    result["handler"] = self.dispatcher.schemas.get(target, {}).get("handler")
                    action = "deterministic"
                    intent = target
                    print(f"[REPAIR] intent {target} + slots : {repaired}")

        if action == "deterministic":
            response = self.try_execute_handler(result)
            if response is not None:
                return response
            print("[PIPELINE] Handler non implémenté → LLM + outils MCP")
            answer = self.llm_with_tools(text)
            self.memory.log_turn(self.session_id, text, answer)
            return answer

        print("[PIPELINE] Fallback LLM avec outils MCP...")
        answer = self.llm_with_tools(text)
        self.memory.log_turn(self.session_id, text, answer)
        return answer

    def try_execute_handler(self, result):
        """Exécute le handler déterministe s'il existe (intégrations P7)."""
        handler = result.get("handler")
        if not handler or "::" not in handler:
            return None

        path_str, func_name = handler.split("::", 1)
        path = ROOT / path_str
        if not path.exists():
            return None

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("handler_module", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            func = getattr(module, func_name)
            return str(func(**result.get("slots", {})))
        except Exception as e:
            print(f"[PIPELINE] Handler non exécutable ({handler}) : {e}")
            return None

    def run(self):
        print("\n" + "=" * 60)
        print("BOUCLE VOCALE OLYMPE (Palier 6 — tool-calling MCP)")
        print("Dis le mot d'activation, puis ta commande après le bip.")
        print("Ctrl+C pour quitter.")
        print("=" * 60 + "\n")

        try:
            while True:
                score = self.wait_for_wake()
                print(f"\n[PIPELINE] Wake word détecté (score={score:.2f})")

                beep()
                time.sleep(0.3)

                print(f"[PIPELINE] Parle maintenant ({self.listen_duration}s)...")
                text = self.stt.listen(duration=self.listen_duration)

                if not text:
                    print("[PIPELINE] Aucune commande entendue.")
                    self.tts.speak("Je n'ai rien entendu, redis-moi.")
                    continue

                print(f"[PIPELINE] Commande : {text}")
                response = self.handle_command(text)
                print(f"[PIPELINE] Réponse : {response}")
                self.tts.speak(response)

        except KeyboardInterrupt:
            print("\n[PIPELINE] Arrêt.")


def main():
    parser = argparse.ArgumentParser(description="Boucle vocale OLYMPE")
    parser.add_argument(
        "--listen-duration",
        type=float,
        default=5.0,
        help="Durée d'écoute après le wake word (défaut 5s)",
    )
    args = parser.parse_args()

    pipeline = VoicePipeline(listen_duration=args.listen_duration)
    pipeline.run()


if __name__ == "__main__":
    main()
