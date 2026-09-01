from voice.tts._helpers import *
from voice.tts.engine import TTSEngine


def main():
    parser = argparse.ArgumentParser(description="Synthese vocale MJ")
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
