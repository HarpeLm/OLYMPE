# OLYMPE

Assistant vocal local sur Apple Silicon — zéro app tierce, zéro modèle codé en dur.

## Philosophie

1. Zéro app tierce visible pour l'utilisateur final — tout tourne en local.
2. Zéro modèle codé en dur — chaque LLM/STT/TTS est déclaré dans config/models.yaml.
3. Le gros modèle ne se réveille que quand c'est nécessaire — un petit routeur dispatche en amont.
4. Rien n'est jeté — chaque palier produit un artefact réutilisable, versionné sur GitHub.

## Matériel

- MacBook Air M5, 16 Go RAM — machine de développement et de service final
- PC avec RTX 4070 Ti — fine-tuning LoRA ponctuel (aller-retour documenté)

## Structure

    /config — registre déclaratif des modèles (models.yaml)
    /server — couche d'inférence persistante (llama-server)
    /router — dispatcheur NLU léger (Qwen2.5-0.5B LoRA)
    /voice — wake word, STT, TTS
    /agent — tool calling (MCP), mémoire persistante (SQLite)
    /integrations — AppleScript/JXA (Calendrier, Finder, Rappels, Notes)
    /training — scripts de fine-tuning LoRA (dev only)
    /bench — tests A/B modèles
    /data — logs et datasets
    /models — GGUF pour llama-server (non versionné)

## Dépendances système

- Python 3.11+ avec venv
- brew install llama.cpp (serveur d'inférence llama-server)
- Modèles MLX téléchargés depuis Hugging Face au premier usage
- GGUF Qwen3-8B-Q4_K_M (~4,7 Go) dans /models/

## Démarrage

    source .venv/bin/activate
    nohup python server/start.py > server.log 2>&1 &
    python voice/pipeline.py

## Documentation

- DECISIONS.md — journal des décisions techniques
- TODO.md — état d'avancement des paliers
- olympe-roadmap-complete.docx — roadmap des 7 paliers
- OLYMPE_Palier8_Controle_Apps.docx — architecture contrôle des apps macOS
