from voice.stt._helpers import *
from voice.stt._recorder import AudioRecorder


class STTEngine:
    """Moteur STT Qwen3-ASR avec chargement / déchargement à la demande."""

    def __init__(self, model_id=None):
        entry = get_role_entry("stt")
        if isinstance(entry, dict):
            self.model_id = model_id or entry["repo"]
            self.lang = entry.get("lang", "French")
            self.sample_rate = entry.get("sample_rate", 16000)
            self.hotwords = entry.get("hotwords", [])
        else:
            self.model_id = model_id or entry
            self.lang = "French"
            self.sample_rate = 16000
            self.hotwords = []
        self.model = None
        self.recorder = AudioRecorder(sample_rate=self.sample_rate)

    def load(self):
        if self.model is not None:
            return
        from mlx_audio.stt import load_model
        print(f"[STT] Chargement : {self.model_id}")
        self.model = load_model(self.model_id)
        print("[STT] Modele charge.")

    def unload(self):
        self.model = None
        try:
            import mlx.core as mx
            mx.clear_cache()
        except Exception:
            pass
        print("[STT] Modele decharge.")

    def transcribe_audio(self, audio):
        """
        Transcrit un tableau numpy float32 (16 kHz, mono).

        Args:
            audio: np.ndarray float32, valeurs dans [-1, 1]

        Returns:
            str: texte transcrit, ou None si silence/bruit
        """
        if self.model is None:
            self.load()

        if audio is None or len(audio) < self.sample_rate * 0.5:
            return None

        # Normaliser en float32 si nécessaire
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        kwargs = {
            "language": self.lang,
            "temperature": 0.0,
            "verbose": False,
        }
        if self.hotwords:
            kwargs["hotwords"] = self.hotwords

        result = self.model.generate(audio, **kwargs)

        # STTOutput a un attribut .text
        if hasattr(result, "text"):
            text = result.text.strip()
        elif isinstance(result, str):
            text = result.strip()
        else:
            text = str(result).strip()

        return text if text else None

    def transcribe_file(self, filepath):
        """Transcrit un fichier audio (WAV, MP3, etc.)."""
        if self.model is None:
            self.load()

        kwargs = {
            "language": self.lang,
            "temperature": 0.0,
            "verbose": False,
        }
        if self.hotwords:
            kwargs["hotwords"] = self.hotwords

        # Qwen3-ASR accepte directement un chemin fichier
        result = self.model.generate(str(filepath), **kwargs)

        if hasattr(result, "text"):
            return result.text.strip()
        elif isinstance(result, str):
            return result.strip()
        else:
            return str(result).strip()

    def listen(self, duration=5.0):
        """
        Capture l'audio du micro pendant `duration` secondes et transcrit.

        Returns:
            str: texte transcrit, ou None
        """
        print(f"[STT] Ecoute pendant {duration}s...")
        self.recorder.start()
        time.sleep(duration)
        self.recorder.stop()

        audio = self.recorder.get_audio(duration)
        if audio is None:
            print("[STT] Aucun audio capture.")
            return None

        return self.transcribe_audio(audio)

    def listen_continuous(self, chunk_duration=3.0):
        """
        Mode continu : transcrit par segments. Générateur.

        Yields:
            tuple: (timestamp, texte transcrit)
        """
        self.recorder.start()
        try:
            while True:
                audio = self.recorder.get_audio(chunk_duration)
                if audio is not None:
                    text = self.transcribe_audio(audio)
                    if text:
                        yield (time.strftime("%H:%M:%S"), text)
        finally:
            self.recorder.stop()
