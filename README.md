# OLYMPE

Assistant vocal local sur MLX — zéro app tierce, zéro modèle codé en dur.

Voir la roadmap complète pour le détail des 7 paliers de développement.

## Structure

- /config — registre déclaratif des modèles (models.yaml)
- /server — couche d'inférence persistante
- /router — dispatcheur NLU léger
- /voice — wake word, STT, TTS
- /agent — tool calling, mémoire persistante
- /integrations — AppleScript/JXA, Home Assistant
- /training — scripts de fine-tuning LoRA (dev only)
- /bench — tests A/B modèles
- /data — logs et datasets
