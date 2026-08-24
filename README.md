# OLYMPE

Assistant vocal local sur MLX — zéro app tierce, zéro modèle codé en dur.

OLYMPE est un assistant vocal pensé pour tourner en local sur Apple Silicon.
L’objectif est de construire un système complet : wake word, STT, LLM, TTS,
tool calling, mémoire persistante et intégrations système, sans dépendre d’une
application tierce visible par l’utilisateur final.

Voir la roadmap complète pour le détail des 7 paliers de développement.

---

## Principes directeurs

1. **Zéro app tierce visible**  
   Tout tourne en local, sous contrôle de l’utilisateur.

2. **Zéro modèle codé en dur**  
   Chaque modèle — LLM, STT, TTS, wake word, dispatcher — est déclaré dans
   `/config/models.yaml` et résolu dynamiquement depuis Hugging Face.

3. **Le gros modèle ne se réveille que si nécessaire**  
   Un petit routeur NLU traite les requêtes simples afin de préserver la
   latence et la mémoire sur une machine 16 Go de RAM.

4. **Rien n’est jeté**  
   Chaque palier produit des artefacts réutilisables : scripts de bench,
   décisions documentées, configuration, logs, datasets.

---

## Matériel cible

- **MacBook Air M5, 16 Go RAM**
  Machine principale de développement et de service final.
  Inférence locale via MLX / Apple Silicon.

- **PC avec RTX 4070 Ti**
  Utilisé ponctuellement pour certains fine-tunings LoRA plus rapides,
  avec export documenté vers le Mac.

---

## État d’avancement

| Palier | Nom | État |
|---|---|---|
| P0 | Setup du dépôt GitHub | Validé |
| P1 | Moteur d’inférence texte | Validé |
| P2 | Serveur persistant | En cours |
| P3 | Registre de modèles dynamique | À venir |
| P4 | Dispatcheur NLU léger | À venir |
| P5 | Couche vocale | À venir |
| P6 | Agentivité & mémoire | À venir |
| P7 | Intégrations système | À venir |

Les décisions techniques sont tracées dans `DECISIONS.md`.

---

## Structure du dépôt

```text
/config        — registre déclaratif des modèles et paramètres
/server        — couche d’inférence persistante
/router        — dispatcheur NLU léger
/voice         — wake word, STT, TTS
/agent         — tool calling, mémoire persistante
/integrations  — AppleScript/JXA, Home Assistant, etc.
/training      — scripts de fine-tuning LoRA, dev uniquement
/bench         — tests A/B modèles et scripts de mesure
/data          — logs, datasets JSONL, données collectées