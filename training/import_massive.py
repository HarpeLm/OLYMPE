"""
Import du dataset MASSIVE (Amazon) — sous-ensemble français
Extrait uniquement les intents déjà présents dans la taxonomie MJ.

Licence MASSIVE : CC BY 4.0 (Amazon)
Référence : FitzGerald et al., 2022, arXiv:2204.08582
Source : https://amazon-massive-nlu-dataset.s3.amazonaws.com/

Usage :
    python training/import_massive.py
    python training/import_massive.py --max-per-intent 30
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Mapping intents MASSIVE -> intents MJ
INTENT_MAPPING = {
    # Musique
    "play_music": "play_music",
    "music_settings": "play_music",
    "music_query": "get_now_playing",
    "music_likeness": "play_music",
    # Volume
    "audio_volume_up": "set_volume",
    "audio_volume_down": "set_volume",
    "audio_volume_mute": "set_volume",
    "audio_volume_other": "set_volume",
    # Calendrier
    "calendar_set": "create_event",
    "calendar_query": "get_events_date",
    # Météo
    "weather_query": "get_weather",
    "weather_forecast": "get_weather",
    # Contrôle lecture
    "next": "next_track",
    "previous": "previous_track",
    "pause": "pause_music",
    "stop": "pause_music",
    "resume": "resume_music",
    "repeat_on": "repeat_track",
    # Recherche / actualités
    "news_query": "web_search",
    "qa_factoid": "general_question",
    "qa_definition": "general_question",
    "qa_maths": "general_question",
    # Fallback conversationnel
    "datetime_query": "general_question",
    "datetime_convert": "general_question",
    "greet": "general_question",
    "affirm": "general_question",
    "negate": "general_question",
    "thank_you": "general_question",
    "goodbye": "general_question",
    "confirm": "general_question",
    "dontcare": "general_question",
}


def parse_annot_utt(annot_utt):
    """
    Extrait les slots depuis annot_utt au format MASSIVE.
    Exemple : "joue [music_setting : du jazz] s'il te plaît"
    → {"music_setting": "du jazz"}
    """
    if not annot_utt:
        return {}

    slots = {}
    # Pattern : [slot_name : value]
    pattern = r'\[(\w+)\s*:\s*([^\]]+)\]'
    matches = re.findall(pattern, annot_utt)

    for slot_name, slot_value in matches:
        slots[slot_name.strip()] = slot_value.strip()

    return slots


def normalize_weather_slots(slots):
    """Normalise les slots météo MASSIVE vers le format MJ."""
    normalized = {}
    if "place_name" in slots:
        normalized["location"] = slots["place_name"]
    elif "location" in slots:
        normalized["location"] = slots["location"]
    if "date" in slots:
        normalized["date"] = slots["date"]
    return normalized


def normalize_volume_direction(massive_intent):
    """Déduit la direction du volume depuis l'intent MASSIVE."""
    if massive_intent == "audio_volume_up":
        return {"direction": "up"}
    elif massive_intent == "audio_volume_down":
        return {"direction": "down"}
    elif massive_intent == "audio_volume_mute":
        return {"level": 0}
    return {}


def extract_and_filter(max_per_intent=30):
    """Lit MASSIVE français et extrait les exemples pertinents."""
    massive_path = ROOT / "data" / "dispatcher" / "1.0" / "data" / "fr-FR.jsonl"

    if not massive_path.exists():
        print(f"Erreur : {massive_path} introuvable")
        print("Télécharge d'abord le dataset :")
        print("  cd data/dispatcher")
        print("  curl https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.0.tar.gz -O")
        print("  tar -xzvf amazon-massive-dataset-1.0.tar.gz")
        return [], {}

    print(f"Lecture de {massive_path}")

    examples = []
    intent_counts = {}

    with open(massive_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            massive_intent = item.get("intent", "")

            if massive_intent not in INTENT_MAPPING:
                continue

            olympe_intent = INTENT_MAPPING[massive_intent]

            # Limite par intent
            if intent_counts.get(olympe_intent, 0) >= max_per_intent:
                continue

            utterance = item.get("utt", "").strip()
            if not utterance or len(utterance) < 3:
                continue

            # Parser les slots depuis annot_utt
            raw_slots = parse_annot_utt(item.get("annot_utt", ""))

            # Normalisation spécifique par intent
            if olympe_intent == "get_weather":
                slots = normalize_weather_slots(raw_slots)
            elif olympe_intent == "set_volume":
                slots = normalize_volume_direction(massive_intent)
            else:
                slots = raw_slots

            examples.append({
                "text": utterance,
                "intent": olympe_intent,
                "slots": slots,
            })
            intent_counts[olympe_intent] = intent_counts.get(olympe_intent, 0) + 1

    return examples, intent_counts


def main():
    parser = argparse.ArgumentParser(
        description="Import MASSIVE (français) pour MJ"
    )
    parser.add_argument(
        "--max-per-intent", type=int, default=30,
        help="Nombre max d'exemples par intent (défaut: 30)"
    )
    parser.add_argument(
        "--output", type=str, default="data/dispatcher/massive_fr.jsonl",
        help="Fichier de sortie"
    )
    args = parser.parse_args()

    examples, intent_counts = extract_and_filter(args.max_per_intent)

    # Déduplication par texte
    seen = set()
    deduped = []
    for ex in examples:
        key = ex["text"].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(ex)

    # Sauvegarde
    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in deduped:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Rapport
    print(f"\n{'='*55}")
    print(f"Import MASSIVE terminé")
    print(f"{'='*55}")
    print(f"Fichier : {out_path}")
    print(f"Total exemples (dédupliqués) : {len(deduped)}")
    print(f"\nRépartition par intent :")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"  {intent:25s} : {count}")
    print(f"\nIntents MJ couverts : {len(intent_counts)}")
    print(f"\nAttribution : dataset MASSIVE, Amazon, licence CC BY 4.0")
    print(f"Référence : FitzGerald et al., 2022, arXiv:2204.08582")


if __name__ == "__main__":
    main()
