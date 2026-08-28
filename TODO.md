# OLYMPE — État d'avancement

## Complétés
- [x] P0 : Setup du dépôt GitHub
- [x] P1 : Moteur d'inférence texte (Qwen3-8B-4bit validé)
- [x] P2 : Serveur persistant (vllm-mlx → llama-server, prefix cache actif)
- [x] P3 : Registre de modèles dynamique (config/models.yaml)
- [x] P4 : Dispatcheur NLU léger (v8, 80.9% sur bench élargi)
- [x] P5 : Couche vocale (wake hey_jarvis provisoire + STT Qwen3-ASR + TTS Qwen3-TTS)
- [x] P6 : Agentivité & mémoire (15 outils MCP + SQLite persistante)
- [x] P7 : Intégrations système (Calendrier Apple déterministe)

## En cours
- [ ] P8 : Contrôle des applications macOS
  - [x] Document d'architecture commune (integrations/_core/)
  - [x] Refactor calendar.py vers _core/ (applescript_runner + risk_levels)
  - [x] Couche de permissions (whitelist de dossiers)
  - [x] Confirmation vocale pour actions destructives
  - [x] Finder (search, open, list, create, move, delete)
  - [x] Catalogue Finder 19 actions (SAFE/REVERSIBLE/DESTRUCTIVE, corbeille Foundation anti-iCloud)
  - [x] Ouverture/fermeture d'applications (open_app/close_app, alias FR, garde-fou Finder)
  - [ ] Rappels Apple
  - [ ] Notes Apple

## À venir
- [ ] Wake word "Olympe" personnalisé (remplacer hey_jarvis)
  - [ ] Générer échantillons négatifs (bruit, musique, conversations)
  - [ ] Script de mixage dataset
  - [ ] Entraînement (PC RTX 4070 Ti ou Colab)
  - [ ] Remplacement dans config/models.yaml

## Dette technique
- [ ] Investiguer latence pipeline vs test isolé (17s vs 8s en appel 1)
  - Cause probable : traitements supplémentaires dans le pipeline
  - Impact modéré : cache fonctionne, latence acceptable en usage réel

## Optimisations futures
- [ ] Réduire catalogue d'outils visible selon l'intent (roadmap §6.3)
- [ ] A/B test 4B vs 8B sur prompts réels (si latence redevient bloquante)
- [ ] Quantification KV cache (4-bit ou 8-bit) pour réduire empreinte mémoire

---

## Prochaines étapes
1. **Refactor calendar.py** vers integrations/_core/ (extraction du commun)
2. **Couche de permissions** (config/allowed_paths.yaml + permissions.py)
3. **Confirmation vocale** (confirmation.py avec timeout et contexte de session)
4. **Finder SAFE/REVERSIBLE** (search, open, list, create, move)
5. **Finder DESTRUCTIVE** (delete avec confirmation vocale)

---

## Historique des décisions
Voir DECISIONS.md pour le journal complet des choix techniques.
