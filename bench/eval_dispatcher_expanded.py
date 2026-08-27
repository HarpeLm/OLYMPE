import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.dispatcher import Dispatcher

CASES = [
    ("quelle heure est-il", "fallback"),
    ("il est quelle heure", "fallback"),
    ("tu peux me dire l'heure", "fallback"),
    ("quelle heure il est maintenant", "fallback"),
    ("on est quel jour aujourd'hui", "fallback"),
    ("on est le combien", "fallback"),
    ("quelle est la date du jour", "fallback"),
    ("c'est quoi la date aujourd'hui", "fallback"),
    ("mets un minuteur de 10 minutes", "fallback"),
    ("lance un timer de 5 minutes", "fallback"),
    ("règle un compte à rebours de 3 minutes", "fallback"),
    ("préviens-moi dans vingt minutes", "fallback"),
    ("qui était Ada Lovelace", "fallback"),
    ("qui est Emmanuel Macron", "fallback"),
    ("qui est le président du Brésil", "fallback"),
    ("combien d'étapes a gagné Tadej Pogačar sur le Tour de France", "fallback"),
    ("explique-moi comment fonctionne un trou noir", "fallback"),
    ("raconte-moi une blague", "fallback"),
    ("pourquoi le ciel est bleu", "fallback"),
    ("comment fonctionne un moteur thermique", "fallback"),
    ("15 pour cent de 80 ça fait combien", "fallback"),
    ("combien font 17 fois 23", "fallback"),
    ("donne-moi une recette de crêpes", "fallback"),
    ("quel temps fait-il à Paris", "get_weather"),
    ("la météo à Lyon", "get_weather"),
    ("il pleut à Annecy aujourd'hui", "get_weather"),
    ("quelle température à Marseille", "get_weather"),
    ("météo Bordeaux aujourd'hui", "get_weather"),
    ("est-ce qu'il va neiger à Chamonix", "get_weather"),
    ("lance ma playlist détente", "play_music"),
    ("joue ma playlist du soir", "play_music"),
    ("mets de la musique", "play_music"),
    ("joue du jazz", "play_music"),
    ("mets une chanson de Stromae", "play_music"),
    ("pause la musique", "pause_music"),
    ("mets la musique en pause", "pause_music"),
    ("reprends la musique", "resume_music"),
    ("continue la lecture", "resume_music"),
    ("chanson suivante", "next_track"),
    ("passe à la piste suivante", "next_track"),
    ("piste précédente", "previous_track"),
    ("reviens à la chanson d'avant", "previous_track"),
    ("c'est quoi cette chanson", "get_now_playing"),
    ("qu'est-ce qui joue en ce moment", "get_now_playing"),
    ("arrête la musique dans 20 minutes", "sleep_timer"),
    ("coupe la musique dans une demi-heure", "sleep_timer"),
    ("répète cette piste", "repeat_track"),
    ("qu'est-ce qui suit dans mon planning", "get_next_event"),
    ("mon prochain rendez-vous", "get_next_event"),
    ("j'ai quoi aujourd'hui", "get_events_today"),
    ("mes événements de vendredi", "get_events_date"),
    ("qu'est-ce que j'ai demain dans mon agenda", "get_events_date"),
    ("ajoute déjeuner avec Marie demain à midi", "create_event"),
    ("crée un rendez-vous dentiste mardi à 15h", "create_event"),
    ("bloque 15h30 18h pour du travail", "create_event"),
    ("suis-je libre mardi prochain", "check_availability"),
    ("est-ce que je suis dispo vendredi matin", "check_availability"),
    ("cherche mes événements anniversaire", "search_events"),
    ("retrouve mes réunions avec Paul", "search_events"),
    ("ouvre le dossier téléchargements", "open_folder"),
    ("ouvre mon dossier documents", "open_folder"),
    ("mes documents récents", "list_recent_files"),
    ("liste mes fichiers récents", "list_recent_files"),
    ("cherche le fichier budget", "find_file"),
    ("trouve mon fichier CV", "find_file"),
    ("ouvre mon pdf de notes", "open_file"),
    ("ouvre le document facture", "open_file"),
    ("cherche facture dans mes documents", "search_content"),
    ("trouve le mot contrat dans mes fichiers", "search_content"),
    ("allume le bluetooth", "toggle_bluetooth"),
    ("éteins le bluetooth", "toggle_bluetooth"),
    ("active le wifi", "toggle_wifi"),
    ("coupe le wifi", "toggle_wifi"),
    ("monte le volume", "set_volume"),
    ("baisse le volume", "set_volume"),
    ("mets le volume à 50", "set_volume"),
    ("augmente la luminosité", "set_brightness"),
    ("baisse la luminosité", "set_brightness"),
    ("fais une capture d'écran", "take_screenshot"),
    ("prends une capture écran", "take_screenshot"),
    ("mets le Mac en veille", "sleep_mac"),
    ("ouvre Safari", "open_app"),
    ("lance l'application Notes", "open_app"),
    ("ferme Musique", "close_app"),
    ("quitte Safari", "close_app"),
    ("est-ce que je suis connecté au wifi", "get_wifi_status"),
    ("quel est l'état du wifi", "get_wifi_status"),
    ("active airdrop", "toggle_airdrop"),
    ("désactive airdrop", "toggle_airdrop"),
]

def get_field(result, name, default=None):
    if isinstance(result, dict):
        return result.get(name, default)
    return getattr(result, name, default)

def is_fallback(intent, action):
    return action == "fallback" or intent == "general_question"

def main():
    dispatcher = Dispatcher()
    ok = 0
    failures = []

    for i, (text, expected) in enumerate(CASES, 1):
        result = dispatcher.route(text)
        intent = get_field(result, "intent")
        action = get_field(result, "action")
        confidence = get_field(result, "confidence", get_field(result, "confiance", None))

        if expected == "fallback":
            good = is_fallback(intent, action)
        else:
            good = intent == expected

        ok += int(good)

        mark = "✅" if good else "❌"
        print(f"[{i:02d}/{len(CASES)}] {mark} {text}")
        print(f"    attendu={expected} | obtenu={intent} | action={action} | confiance={confidence}")

        if not good:
            failures.append({
                "text": text,
                "expected": expected,
                "got": intent,
                "action": action,
                "confidence": confidence,
            })

    score = ok / len(CASES) * 100
    print()
    print(f"Score : {ok}/{len(CASES)} = {score:.1f}%")

    out = Path("data/dispatcher/eval_expanded_failures.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in failures) + ("\n" if failures else ""),
        encoding="utf-8",
    )

    if failures:
        print(f"Échecs écrits dans {out}")
    else:
        print("Aucun échec.")

if __name__ == "__main__":
    main()
