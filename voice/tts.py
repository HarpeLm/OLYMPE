"""
Synthèse vocale (TTS) — Palier 5

Qwen3-TTS CustomVoice via mlx-audio.
Deux modes :
  1. Voix prédéfinie (voice="serena") — pour démarrer sans enregistrement
  2. Clonage zero-shot (ref_audio="chemin.wav" + ref_text) — pour la voix de la copine

Le modèle ET ses options (voix par défaut, langue, sample rate) sont résolus
depuis config/models.yaml (jamais codés en dur).
Chargement / déchargement à la demande pour préserver la RAM
(stratégie mémoire roadmap §7 : wake word + dispatcheur résidents,
STT/TTS chargés autour de chaque interaction).

Usage module :
    from voice.tts import TTSEngine
    tts = TTSEngine()
    tts.speak("Bonjour, je suis Olympe.")

Usage CLI :
    python voice/tts.py "Bonjour" --voice serena
    python voice/tts.py "Bonjour" --output /tmp/test.wav
    python voice/tts.py "Bonjour" --ref-audio /path/voix.wav --ref-text "texte exact"
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"


def get_role_entry(role):
    """Retourne l'entrée complète d'un rôle depuis config/models.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    roles = config.get("roles", {})
    entry = roles.get(role)
    if entry is None:
        raise KeyError(f"Role '{role}' absent ou non configure dans {CONFIG_PATH}")
    return entry


def get_model_id(role):
    """Résout l'identifiant HF du modèle pour un rôle depuis la config."""
    entry = get_role_entry(role)
    return entry["repo"] if isinstance(entry, dict) else entry


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


def save_wav(path, audio, sample_rate):
    """Sauvegarde en WAV 16-bit via la lib standard (pas de dépendance)."""
    import wave
    audio_int16 = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio_int16 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


def main():
    parser = argparse.ArgumentParser(description="Synthese vocale OLYMPE")
    parser.add_argument("text", nargs="?", help="Texte a synthesizer")
    parser.add_argument("--voice", default=None,
                        help="Voix predéfinie (defaut: valeur config/models.yaml)")
    parser.add_argument("--ref-audio", help="Audio de reference pour clonage zero-shot")
    parser.add_argument("--ref-text", help="Texte exact de l'audio de reference")
    parser.add_argument("--lang", default=None,
                        help="Langue (defaut: valeur config/models.yaml)")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--output", "-o", help="Sauvegarder en WAV au lieu de jouer")
    args = parser.parse_args()

    if not args.text:
        parser.print_help()
        sys.exit(1)

    tts = TTSEngine()
    tts.load()

    if args.output:
        audio = tts.synth(
            args.text,
            voice=args.voice,
            ref_audio=args.ref_audio,
            ref_text=args.ref_text,
            lang_code=args.lang,
            speed=args.speed,
        )
        if audio is not None:
            save_wav(args.output, audio, tts.sample_rate)
            print(f"[TTS] Sauvegarde : {args.output}")
        else:
            print("[TTS] Aucun audio genere.")
    else:
        tts.speak(
            args.text,
            voice=args.voice,
            ref_audio=args.ref_audio,
            ref_text=args.ref_text,
            lang_code=args.lang,
            speed=args.speed,
        )

    tts.unload()


if __name__ == "__main__":
    main()
