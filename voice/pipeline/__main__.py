import argparse
from voice.pipeline._pipeline import VoicePipeline


def main():
    parser = argparse.ArgumentParser(description="Boucle vocale MJ")
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
    import os
    try:
        main()
    except KeyboardInterrupt:
        print("\n[PIPELINE] Arrêt.")
        os._exit(0)


