# OLYMPE — Journal des décisions techniques

Ce fichier trace les choix d'architecture et de modèles au fil des paliers,
avec le contexte qui a mené à chaque décision. Objectif : ne jamais avoir à
refaire un test déjà fait, ni à se souvenir "pourquoi" de mémoire.

---

## 2026-08-24 — Palier 1 : modèle chat principal

**Décision : Qwen3-8B-4bit retenu pour le rôle `chat` dans `config/models.yaml`**

### Contexte du test

Comparaison Qwen3-4B-4bit vs Qwen3-8B-4bit sur le MacBook Air M5 (16 Go RAM),
sur deux axes : débit de génération et fiabilité du tool-calling
(critère important car ce modèle sert aussi de fallback au dispatcheur
du Palier 4, et gère l'agentivité du Palier 6).

### Résultats mesurés

| Critère | Qwen3-4B-4bit | Qwen3-8B-4bit |
|---|---|---|
| Tool-calling (3 cas de test) | 3/3 | 3/3 |
| Débit génération | 27.2 tokens/s | 14.2 tokens/s |
| Peak memory | 2.38 Go | 4.72 Go |
| Temps de chargement | ~1-2s | ~2-2.5s |

Script de test : `bench/test_tool_calling.py`

### Raisonnement

Les deux modèles scorent à égalité sur le test de tool-calling actuel
(2 outils, 3 cas). Le 4B est ~2x plus rapide et laisse davantage de marge
RAM pour la cohabitation future avec le dispatcheur + STT/TTS (Palier 5).

Le 8B a été choisi malgré ce désavantage vitesse/RAM, en pariant sur sa
meilleure marge de raisonnement pour :
- L'agentivité du Palier 6 (tool-calling sur un catalogue d'outils plus
  large et plus ambigu que les 2 outils testés ici)
- Les intégrations système du Palier 7 (AppleScript/JXA, décisions
  contextuelles plus fines)

**Point de vigilance explicite** : le débit de 14.2 tokens/s est sous la
cible basse de 15-30 tokens/s fixée dans la roadmap. Le Palier 2
(serveur persistant + prefix caching) devrait améliorer la latence
perçue en usage réel, mais ne changera pas le débit de génération brut.
À surveiller une fois la couche vocale en place (Palier 5) — si la
latence perçue reste trop haute à l'usage, ce choix est à reconsidérer
en faveur du 4B.

**Test à refaire** : ce test de tool-calling ne couvre que 2 outils très
simples. Une fois le catalogue d'outils réel du Palier 6 plus étoffé,
relancer une comparaison 4B vs 8B sur des cas plus proches de l'usage
réel pour confirmer ou infirmer ce choix.

---

<!-- Prochaine entrée : Palier 2 — vllm-mlx vs serveur maison -->
