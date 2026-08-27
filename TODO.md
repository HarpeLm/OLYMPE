# OLYMPE — État d'avancement et tâches

## Paliers complétés
- [x] P0-P6 : voir DECISIONS.md pour le détail

## En cours
- [ ] Wake word "Olympe" (P5 restant)
  - [x] 15 échantillons positifs collectés (`voice/wake_samples/olympe_*.wav`)
  - [ ] Générer échantillons négatifs (bruit, musique, conversations)
  - [ ] Script d'entraînement openWakeWord
  - [ ] Dataset final prêt
  - [ ] Entraînement (PC RTX ou Colab)
  - [ ] Intégration dans `voice/wake_word.py`

## En cours (P7)
- [x] Calendrier Apple : création/lecture/dispo/conflits déterministes
- [x] 7 handlers AppleScript + couche de réparation intent+slots
- [ ] Rappels : create_reminder MCP existe, intent dédié à brancher si besoin
- [ ] Notes Apple via AppleScript

## Décisions en attente (roadmap §11)
- [x] vllm-mlx vs serveur maison → tranché : vllm-mlx (voir DECISIONS P2)
- [x] Qualité TTS acceptable → Kokoro retenu (voir DECISIONS P5)
- [x] Recherche web P7 → SearXNG local accepté comme exception consciente (voir DECISIONS P7)

## Frictions documentées
- cp -r imbrique au lieu de remplacer → rm -rf avant cp -r (voir DECISIONS P4)
- LLM 8B perroquette sans instruction explicite + historique empoisonné → pré-filtre déterministe + prompt explicite (voir DECISIONS P6)
