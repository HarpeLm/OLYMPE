from voice.pipeline._config import *
from voice.pipeline._clients import LLMClient
from voice.pipeline._commands import CommandsMixin
from agent.tools import list_tools, run_tool


class VoicePipeline(CommandsMixin):
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
        # MCPBridge supprimé : utilisation directe de agent.tools
        self.memory = Memory()
        self.session_id = str(uuid.uuid4())[:8]

        try:
            self.tools = [{"type": "function", "function": t} for t in list_tools()]
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
        {"role": "system", "content": SYSTEM_PROMPT},
        ]
        ctx = self._memory_context()
        user_content = text + (ctx or "") + "\n/no_think"
        messages.append({"role": "user", "content": user_content})

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
                    result = run_tool(fname, fargs)
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

    def run(self):
        print("\n" + "=" * 60)
        print("BOUCLE VOCALE MJ (Palier 6 — tool-calling MCP)")
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
