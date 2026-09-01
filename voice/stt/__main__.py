from voice.stt._helpers import *
from voice.stt._recorder import AudioRecorder
from voice.stt.engine import STTEngine


def main():
    parser = argparse.ArgumentParser(description="Transcription vocale MJ")
    parser.add_argument("--duration", type=float,
                        help="Duree de capture en secondes (mode one-shot)")
    parser.add_argument("--file", "-f", help="Fichier audio a transcrire")
    parser.add_argument("--continuous", action="store_true",
                        help="Mode continu (Ctrl+C pour quitter)")
    parser.add_argument("--chunk", type=float, default=3.0,
                        help="Duree des segments en mode continu (defaut: 3s)")
    args = parser.parse_args()

    stt = STTEngine()
    stt.load()

    if args.file:
        # Mode fichier
        text = stt.transcribe_file(args.file)
        if text:
            print(f"Transcription : {text}")
        else:
            print("(aucune transcription)")

    elif args.duration:
        # Mode one-shot
        text = stt.listen(duration=args.duration)
        if text:
            print(f"Transcription : {text}")
        else:
            print("(silence ou bruit)")

    elif args.continuous:
        # Mode continu
        print("Transcription en continu (Ctrl+C pour quitter)")
        print("-" * 60)
        try:
            for timestamp, text in stt.listen_continuous(chunk_duration=args.chunk):
                print(f"[{timestamp}] {text}")
        except KeyboardInterrupt:
            print("\nArret.")

    else:
        # Par défaut : mode one-shot 5 secondes
        text = stt.listen(duration=5.0)
        if text:
            print(f"Transcription : {text}")
        else:
            print("(silence ou bruit)")

    stt.unload()


if __name__ == "__main__":
    main()
