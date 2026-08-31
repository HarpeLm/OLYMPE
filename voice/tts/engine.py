from voice.tts._helpers import *


class TTSEngine:
    """Moteur TTS Qwen3-TTS avec chargement / déchargement à la demande."""

    def __init__(self, model_id=None):
        entry = get_role_entry("tts")
        if isinstance(entry, dict):
            self.model_id = model_id or entry["repo"]
            self.default_voice = entry.get("default_voice", "serena")
            self.lang = entry.get("lang", "french")
            self.sample_rate = entry.get("sample_rate", 24000)
        else:
            self.model_id = model_id or entry
            self.default_voice = "serena"
            self.lang = "french"
            self.sample_rate = 24000
        self.model = None

    def load(self):
        if self.model is not None:
            return
        from mlx_audio.tts import load_model
        print(f"[TTS] Chargement : {self.model_id}")
        self.model = load_model(self.model_id)
        print("[TTS] Modele charge.")

    def unload(self):
        self.model = None
        try:
            import mlx.core as mx
            mx.metal.clear_cache()
        except Exception:
            pass
        print("[TTS] Modele decharge.")

    def synth(self, text, voice=None, ref_audio=None, ref_text=None,
              lang_code=None, speed=1.0):
        """
        Génère l'audio (np.float32) pour un texte.

        Args:
            text: Texte à synthétiser
            voice: Voix prédéfinie (serena, vivian, ...) — mode par défaut
            ref_audio: Chemin vers audio de référence — mode clonage
            ref_text: Texte exact de l'audio de référence (requis si ref_audio)
            lang_code: Langue ('french', 'english', 'auto'). None = valeur config.
            speed: Vitesse (1.0 = normal)
        """
        if self.model is None:
            self.load()

        lang = lang_code or self.lang

        # Mode clonage zero-shot OU mode voix prédéfinie
        if ref_audio:
            gen = self.model.generate(
                text,
                ref_audio=ref_audio,
                ref_text=ref_text,
                lang_code=lang,
                speed=speed,
                verbose=False,
            )
        else:
            gen = self.model.generate(
                text,
                voice=voice or self.default_voice,
                lang_code=lang,
                speed=speed,
                verbose=False,
            )

        chunks = []
        for result in gen:
            chunks.append(np.asarray(result.audio, dtype=np.float32))

        if not chunks:
            return None
        return np.concatenate(chunks)

    def speak(self, text, voice=None, ref_audio=None, ref_text=None,
              lang_code=None, speed=1.0):
        """Synthétise puis joue l'audio sur la sortie par défaut."""
        import sounddevice as sd
        audio = self.synth(
            text, voice=voice, ref_audio=ref_audio, ref_text=ref_text,
            lang_code=lang_code, speed=speed,
        )
        if audio is None:
            print("[TTS] Aucun audio genere.")
            return
        sd.play(audio, samplerate=self.sample_rate)
        sd.wait()
