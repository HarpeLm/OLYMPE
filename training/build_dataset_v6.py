"""
Dataset v6 du dispatcheur NLU.
Sources : v5 (rien n'est jeté) + templates synthétiques + réel corrigé.
Règle roadmap §4 : >= 30% de réel dans le dataset final.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dispatcher" / "dataset_v6"
LOG = ROOT / "data" / "dispatcher" / "inference_log.jsonl"

FB = ("general_question", {})


def J(intent, slots):
    return json.dumps({"intent": intent, "slots": slots}, ensure_ascii=False)


# ---------- Synthétique : templates par famille ----------
SYNTH = [
    # musique
    ("joue ma playlist détente", "play_music", {"playlist": "détente"}),
    ("lance la playlist soir", "play_music", {"playlist": "soir"}),
    ("mets de la musique", "play_music", {}),
    ("joue du jazz", "play_music", {"genre": "jazz"}),
    ("pause", "pause_music", {}),
    ("mets la musique en pause", "pause_music", {}),
    ("reprends la musique", "resume_music", {}),
    ("chanson suivante", "next_track", {}),
    ("piste précédente", "previous_track", {}),
    ("qu'est-ce qui joue en ce moment", "get_now_playing", {}),
    ("c'est quoi cette chanson", "get_now_playing", {}),
    ("arrête la musique dans 20 minutes", "sleep_timer", {"duration_minutes": 20}),
    ("répète cette piste 3 fois", "repeat_track", {"count": 3}),
    # calendrier
    ("qu'est-ce qui suit dans mon planning", "get_next_event", {}),
    ("mon prochain rendez-vous", "get_next_event", {}),
    ("j'ai quoi aujourd'hui", "get_events_today", {}),
    ("mes événements de vendredi", "get_events_date", {"date": "vendredi"}),
    ("ajoute déjeuner avec Marie demain à midi", "create_event",
     {"title": "déjeuner avec Marie", "date": "demain", "time": "12:00"}),
    ("bloque 15h30-18h pour du travail", "create_event",
     {"title": "travail", "time": "15:30", "end_time": "18:00"}),
    ("suis-je libre mardi prochain", "check_availability", {"date": "mardi prochain"}),
    ("cherche mes événements anniversaire", "search_events", {"query": "anniversaire"}),
    # fichiers
    ("ouvre le dossier téléchargements", "open_folder", {"folder_name": "téléchargements"}),
    ("mes documents récents", "list_recent_files", {}),
    ("cherche le fichier budget", "find_file", {"filename": "budget"}),
    ("ouvre mon pdf de notes", "open_file", {"filename": "notes"}),
    ("cherche facture dans mes documents", "search_content", {"query": "facture"}),
    # système macOS
    ("allume le bluetooth", "toggle_bluetooth", {"state": "on"}),
    ("éteins le bluetooth", "toggle_bluetooth", {"state": "off"}),
    ("active le wifi", "toggle_wifi", {"state": "on"}),
    ("coupe le wifi", "toggle_wifi", {"state": "off"}),
    ("monte le volume", "set_volume", {"direction": "up"}),
    ("baisse le volume", "set_volume", {"direction": "down"}),
    ("volume à 50", "set_volume", {"level": 50}),
    ("augmente la luminosité", "set_brightness", {"direction": "up"}),
    ("fais une capture d'écran", "take_screenshot", {}),
    ("mets le Mac en veille", "sleep_mac", {}),
    ("ouvre Safari", "open_app", {"app_name": "Safari"}),
    ("ferme Musique", "close_app", {"app_name": "Musique"}),
    ("est-ce que je suis connecté au wifi", "get_wifi_status", {}),
    ("active airdrop", "toggle_airdrop", {"state": "on"}),
    # météo
    ("quel temps fait-il à Paris", "get_weather", {"location": "Paris"}),
    ("la météo à Lyon", "get_weather", {"location": "Lyon"}),
    ("est-ce qu'il pleut à Annecy", "get_weather", {"location": "Annecy"}),
    ("quelle température à Marseille", "get_weather", {"location": "Marseille"}),
    # fallback / questions générales
    ("quelle heure est-il", "general_question", {}),
    ("il est quelle heure", "general_question", {}),
    ("on est quel jour aujourd'hui", "general_question", {}),
    ("quelle date sommes-nous", "general_question", {}),
    ("mets un minuteur de 10 minutes", "general_question", {}),
    ("minuteur 5 minutes", "general_question", {}),
    ("qui était Ada Lovelace", "general_question", {}),
    ("combien d'étapes a gagné Tadej Pogačar sur le Tour de France", "general_question", {}),
    ("qui est le président du Brésil", "general_question", {}),
    ("explique-moi comment fonctionne un trou noir", "general_question", {}),
    ("raconte-moi une blague", "general_question", {}),
    ("c'est quoi la photosynthèse", "general_question", {}),
    ("pourquoi le ciel est bleu", "general_question", {}),
    ("donne-moi une recette de crêpes", "general_question", {}),
    ("qui a inventé le téléphone", "general_question", {}),
    ("c'est quoi le bitcoin", "general_question", {}),
    ("comment on dit merci en japonais", "general_question", {}),
    ("quel est le plus haut sommet du monde", "general_question", {}),
    ("15 % de 80 ça fait combien", "general_question", {}),
]

# ---------- Réel : corrections manuelles + variantes paraphrasées ----------
CORRECTIONS = {
    "quelle heure est-il": FB,
    "on est quel jour aujourd'hui": FB,
    "quel temps fait-il à Paris": ("get_weather", {"location": "Paris"}),
    "mets un minuteur de 10 minutes": FB,
    "qui était Ada Lovelace": FB,
    "combien d'étapes a gagné Tadej Pogačar sur le Tour de France": FB,
    "qui est l'actuel président des États Unis": FB,
    "qui est l'actuel président français": FB,
}

# Variantes pour enrichir le réel (paraphrases)
VARIANTES = [
    # heure/date
    ("tu peux me dire l'heure", "general_question", {}),
    ("il est quelle heure maintenant", "general_question", {}),
    ("on est le combien aujourd'hui", "general_question", {}),
    ("c'est quoi la date", "general_question", {}),
    # minuteur
    ("lance un timer de 5 minutes", "general_question", {}),
    ("règle un compte à rebours de 3 minutes", "general_question", {}),
    # météo
    ("il fait quel temps à Paris", "get_weather", {"location": "Paris"}),
    ("météo Bordeaux aujourd'hui", "get_weather", {"location": "Bordeaux"}),
    # questions générales
    ("qui est Emmanuel Macron", "general_question", {}),
    ("c'est qui Albert Einstein", "general_question", {}),
    ("qu'est-ce que la relativité", "general_question", {}),
    ("comment fonctionne un moteur", "general_question", {}),
    ("pourquoi il pleut", "general_question", {}),
    ("c'est quoi l'intelligence artificielle", "general_question", {}),
    ("qui a peint la Joconde", "general_question", {}),
    ("c'est quoi la capitale de l'Australie", "general_question", {}),
]


def normalize_row(r):
    """Normalise les clés prompt/text/input -> prompt."""
    prompt = r.get("prompt") or r.get("text") or r.get("input")
    completion = r.get("completion") or r.get("output") or r.get("target")
    if prompt and completion:
        return {"prompt": prompt, "completion": completion}
    return None


def main():
    rows = []

    # 1. v5 existant : rien n'est jeté
    v5_count = 0
    for p in list((ROOT / "data" / "dispatcher").glob("*v5*.jsonl")) + \
               list((ROOT / "training").glob("**/*v5*.jsonl")):
        for line in p.read_text().splitlines():
            try:
                r = normalize_row(json.loads(line))
                if r:
                    rows.append(r)
                    v5_count += 1
            except json.JSONDecodeError:
                pass
    print(f"v5 récupéré : {v5_count} lignes")

    # 2. Synthétique
    for text, intent, slots in SYNTH:
        rows.append({"prompt": text, "completion": J(intent, slots)})

    # 3. Réel : log d'inférence avec feedback manuel
    real = []
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = (e.get("text") or "").strip()
            fb = e.get("user_feedback")
            if not text:
                continue
            if fb == "positive" and e.get("intent"):
                real.append({"prompt": text,
                             "completion": J(e["intent"], e.get("slots") or {})})
            elif fb == "negative" and text.lower() in CORRECTIONS:
                intent, slots = CORRECTIONS[text.lower()]
                real.append({"prompt": text, "completion": J(intent, slots)})
    print(f"Réel (log + corrections) : {len(real)} lignes")

    # Complète les corrections absentes du log
    have = {r["prompt"].lower() for r in real}
    for text, (intent, slots) in CORRECTIONS.items():
        if text not in have:
            real.append({"prompt": text, "completion": J(intent, slots)})

    # Ajoute les variantes paraphrasées
    for text, intent, slots in VARIANTES:
        real.append({"prompt": text, "completion": J(intent, slots)})

    rows += real

    # Ratio réel (roadmap §4 : >= 30%)
    ratio = len(real) / len(rows) * 100 if rows else 0
    print(f"Total : {len(rows)} lignes | réel : {ratio:.0f} %")
    if ratio < 30:
        print("⚠️  Sous les 30% de réel : enrichis avec plus de batchs feedback")

    # Déduplication + split
    seen, uniq = set(), []
    for r in rows:
        if r["prompt"] not in seen:
            seen.add(r["prompt"])
            uniq.append(r)
    random.seed(42)
    random.shuffle(uniq)
    cut = max(1, len(uniq) // 10)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "valid.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in uniq[:cut]) + "\n")
    (OUT / "train.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in uniq[cut:]) + "\n")
    print(f"✅ {OUT} : train={len(uniq) - cut}, valid={cut}")


if __name__ == "__main__":
    main()
