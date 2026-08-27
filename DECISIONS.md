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

## 2026-08-25 — Palier 2 : serveur persistant vllm-mlx validé

**Décision : vllm-mlx 0.4.1 retenu comme serveur d'inférence**

### Résultats mesurés

| Métrique | Valeur |
|---|---|
| Requête à froid (prefill complet) | 22.42s |
| Requêtes suivantes (cache hit, moyenne) | 5.45s |
| Gain de latence perçue | 76% |

**Décisions confirmées**

- `vllm-mlx 0.4.1` comme serveur d'inférence persistant
- Le prefix caching est actif par défaut (pas d'option CLI nécessaire)
- `--reasoning-parser qwen3` active l'extraction du bloc de raisonnement Qwen3
- Configuration dans `/config/models.yaml` : aucune option vLLM classique 
  (`--max-model-len`, `--enable-prefix-caching`, `--kv-cache-dtype`) n'est 
  supportée par vllm-mlx 0.4.1

**Critère de sortie Palier 2 : VALIDÉ**

---

## 2026-08-25 — Palier 3 : registre dynamique validé

**Critère de sortie** : "Changer de modèle = éditer une ligne de config, jamais le code"

Basculement du rôle `chat` de `Qwen3-8B-4bit` vers `Qwen3-4B-4bit` :
1. Édition d'UNE seule ligne dans `config/models.yaml` (commande `sed`)
2. Zéro modification du code Python (`server/start.py` ou `test_latency.py`)
3. Redémarrage du serveur

**Critère de sortie Palier 3 : VALIDÉ**

---

## 2026-08-25 — Palier 4 : dispatcheur NLU léger (v5 finale)

**Décision : Qwen2.5-0.5B-Instruct fine-tuné en LoRA comme dispatcheur**

### Architecture mise en place

Couches [2] + [3] de la roadmap :
- `router/intents.yaml` : taxonomie déclarative 31 intents déterministes
  (musique, calendrier, fichiers locaux, macOS, météo, web search) + 2 fallbacks
- `router/prompts.py` : prompt système partagé entraînement/inférence,
  schéma des slots (! obligatoire, ? optionnel)
- `router/aliases.yaml` : corrections manuelles (recalibration dans le temps)
- `router/dispatcher.py` : couche [3] avec garde-fous déterministes
  (validation taxonomie, normalisation slots, confiance heuristique, fallback)
- `training/` : pipeline LoRA complet (prepare / train / eval)

### Itérations dataset

| Version | Exemples | Intent | Intent+slots | Type |
|---|---|---|---|---|
| v1 | 64 | 54% | 33% | Synthétique pur |
| v2 | 125 | 74% | 43% | + corrections confusions |
| v3 | 141 | 65% | 48% | + paraphrases ciblées |
| v4 | 179 | 82% | 57% | + phrases réelles (38) |
| **v5** | **191** | **86%** | **61%** | **+ 16 exemples ciblés** |

### Garde-fous couche [3]

- Validation intent contre la taxonomie → inconnu = confiance 0 = fallback
- Normalisation des slots : clés hors taxonomie ignorées, enums mappés
  (active→on, coupe→off), level borné 0-100
- Parsing JSON tolérant (accepte quotes simples, extrait premier objet valide)
- Confiance heuristique : 0.9 OK / 0.55 alias / 0.45 slot requis manquant /
  0.0 invalide. Seuil 0.75 configurable dans router/intents.yaml
- Journalisation dans data/dispatcher/inference_log.jsonl (exclu du repo)

**Critère de sortie P4 : VALIDÉ**
(Le petit modèle route les requêtes simples sans réveiller le 8B ;
les cas hors scope partent en fallback vers le LLM principal)

---

## 2026-08-26 — Palier 5 : TTS validé (Qwen3-TTS CustomVoice)

**Décision : Qwen3-TTS-12Hz-1.7B-CustomVoice-6bit retenu pour le rôle `tts`**

### Contexte — pivot depuis Kokoro

La roadmap recommandait Kokoro pour le démarrage (léger, cohabite avec le LLM 8B
sur 16 Go). Problème : Kokoro n'existe pas en MLX sur HuggingFace. Deux options :

1. Convertir Kokoro nous-mêmes (travail en plus, pour un modèle qu'on jettera ensuite)
2. Pivoter vers un TTS déjà en MLX qui supporte le clonage vocal
   (objectif final : voix de la copine)

Choix : option 2.

### Deux modes d'utilisation

1. **Voix prédéfinie** (voice="serena") : pour démarrer sans enregistrement
2. **Clonage zero-shot** (ref_audio + ref_text) : pour la voix de la copine,
   un échantillon propre de 10-15 secondes suffira

**Critère de sortie P5 (partiel) : TTS VALIDÉ**

---

## 2026-08-26 — Palier 5 : STT validé (Qwen3-ASR)

**Décision : Qwen3-ASR-1.7B-4bit retenu pour le rôle `stt`**

### Contexte — pivot depuis Whisper

La roadmap recommandait Whisper large-v3-turbo. Problème : le chargement
échoue avec une erreur de processor HuggingFace manquant dans le cache local.
Plutôt que de debugger un problème de cache incertain, on pivote vers
Qwen3-ASR qui :
- Est déjà converti MLX et se charge sans erreur
- Cohérent avec l'écosystème Qwen (chat + dispatcheur + TTS + STT)
- Plus léger que Whisper (1.61 Go vs ~3 Go)

**Critère de sortie P5 (partiel) : STT VALIDÉ**

---

## 2026-08-26 — Palier 5 : wake word provisoire (hey_jarvis)

**Décision : `hey_jarvis` (pré-entraîné openWakeWord) comme wake word de
travail, entraînement d'"Olympe" reporté post-P5**

### Ce qui est conservé pour l'entraînement futur

15 échantillons réels de "Olympe" enregistrés et validés dans
`voice/wake_samples/` (WAV 16 kHz, mono, 16-bit, 1.5s chacun).

### Plan d'entraînement "Olympe" (post-P5)

1. Utiliser le notebook Colab officiel openWakeWord
2. Générer des milliers d'échantillons synthétiques de "Olympe" via TTS
3. Inclure les 15 échantillons réels comme données positives
4. Exporter le modèle entraîné dans `voice/wake_models/olympe.onnx`
5. Remplacer UNE ligne dans `config/models.yaml`
6. Zéro changement de code : voice/wake_word.py est config-driven

**Critère de sortie P5 (partiel) : WAKE WORD VALIDÉ** (provisoire)

---

## 2026-08-26 — Palier 5 : boucle vocale complète validée

**Décision : boucle wake → STT → LLM → TTS fonctionnelle, avec déviation mémoire assumée**

### Déviation mémoire par rapport à la roadmap §7

La roadmap supposait : "charger/décharger STT et TTS à la demande autour de
chaque interaction. Coût : quelques centaines de ms de latence additionnelle
par cycle, à mesurer précisément une fois codé."

**Mesure effective** : le chargement d'un modèle de 1.7B prend plusieurs
secondes, même depuis le cache HF. Ce coût par cycle était :
1. Trop élevé pour une conversation fluide
2. Source d'un bug de timing : le bip sonnait avant la fin du chargement

**Décision** : garder STT + TTS résidents permanents, préchargés au démarrage.

### Budget mémoire vérifié

| Composant | Résidence | Empreinte |
|---|---|---|
| Wake word (openWakeWord hey_jarvis) | Résident | < 100 Mo |
| Dispatcheur (Qwen2.5-0.5B LoRA) | Résident | ~0.5 Go |
| STT (Qwen3-ASR-1.7B-4bit) | Résident (déviation) | ~1.6 Go |
| TTS (Qwen3-TTS-12Hz-1.7B-CustomVoice-6bit) | Résident (déviation) | ~2.7 Go |
| Serveur LLM (Qwen3-8B-4bit, processus séparé) | Résident | ~4.7 Go |
| **Total** | | **~10 Go sur 16** |

Marge restante : ~6 Go pour le système et les pics d'activité.

**Critère de sortie P5 : VALIDÉ**

---

## 2026-08-27 — Palier 6 : mémoire persistante SQLite validée

**Décision : mémoire via SQLite local (agent/memory.py), exposée en 3 outils
MCP (remember/recall/forget) + contexte injecté au system prompt +
pré-filtre déterministe pour « souviens-toi que… »**

### Architecture en 3 couches

1. **Pré-filtre déterministe** : regex « souviens-toi que / mémorise que /
   n'oublie pas que » -> écriture directe dans facts, ~0 ms, sans LLM
   (esprit roadmap §4 [1])
2. **Injection de contexte** : 5 faits + 3 tours récents injectés dans le
   system prompt du 8B à chaque requête (réponse immédiate sans outil)
3. **Outils MCP remember/recall/forget** pour les cas flexibles
   (catalogue porté à 12 outils)

### Stockage

data/memory/olympe.db (gitignoré). Table facts (indéfinie) +
table turns (purgée 7 jours). Zéro dépendance externe (sqlite3 = stdlib).

### Friction apprise (documentée pour ne pas la répéter)

Un 8B en `/no_think` avec un prompt vague (« utilise les outils quand
nécessaire ») n'appelle JAMAIS remember : il perroquette. Deux facteurs
aggravants :
- Historique injecté montrant ses propres réponses sans appel
  d'outil (empoisonnement few-shot)
- Réflexe `/no_think` de répondre direct

**Correctifs efficaces** :
- Instruction explicite au system prompt (« si on te demande de te
  souvenir, appelle d'abord remember »)
- Pré-filtre déterministe sur les motifs évidents

Après correctif : remember appelé, fait écrit en base, réponse correcte
en session fraîche.

### Critère de sortie P6 : VALIDÉ

- Tool calling fiable : 12 outils, validés en boucle vocale et en texte
- Mémoire persistante entre sessions : les faits survivent au redémarrage

---

## 2026-08-27 — Palier 4 : chapitre dispatcheur clos (v8 + alias + post-garde)

**Décision : geler le dispatcheur NLU à LoRA v8 + table d'alias + post-garde
par mots-clés de domaine. 80.9% sur bench élargi (89 phrases). Erreurs
restantes rétrogradées en fallback sûr.**

### Résultats mesurés (bench/eval_dispatcher_expanded.py)

| Version | Précision |
|---|---|
| v5 initial | 60% sur 15 phrases, 0/6 hors taxonomie |
| v6 (109 lignes) | 15/15 cas critiques |
| v8 (échecs réels réinjectés) | 67.4% sur 89 phrases |
| v8 + alias + post-garde | **80.9%**, zéro action déterministe hors domaine |

### Architecture de sécurité en 4 couches

1. **Pré-filtre regex** : heure/date/minuteur -> fallback, météo -> get_weather
2. **LoRA v8** : intent + slots en une passe
3. **Table d'alias** : noms inventés -> noms canoniques de la taxonomie
4. **Post-garde** : intent déterministe sans mot-clé de son domaine ->
   rétrogradé en fallback

### Friction documentée (pour ne pas la répéter)

`cp -r X dispatcher-best` **IMBRIQUE** X si best existe : deux cycles
d'entraînement (v7, v8) ont été évalués sans être chargés. Procédure
correcte de swap : `rm -rf training/adapters/dispatcher-best` avant `cp -r`.

### Prochain cycle

Retrain quand inference_log.jsonl aura ~200 phrases réelles nouvelles
(boucle continue roadmap §4, pas de bench manuel).

---

## 2026-08-27 — Palier 7 (anticipé) : recherche web via SearXNG local (EXCEPTION CONSCIENTE)

**Décision : outil MCP web_search adossé à une instance SearXNG auto-hébergée
(Docker sur le Mac), tracé comme exception au principe « zéro app tierce »**

### Pourquoi SearXNG plutôt que Brave / Tavily / DuckDuckGo

- Brave / Tavily : API officielles mais carte bancaire + compte + requête vers un tiers
- DuckDuckGo : pas de clé mais scraping non officiel, fragile
- SearXNG : auto-hébergé, zéro clé, zéro compte, zéro CB ; la seule requête
  sortante part de MON instance vers les moteurs, anonymisée par SearXNG

### Comment l'exception est contenue

- Service isolé dans Docker, lié à 127.0.0.1:8888 (jamais exposé au réseau)
- ~200-300 Mo RAM, --restart unless-stopped
- Outil appelé uniquement par le LLM sur demande explicite de l'utilisateur
- Réversible : supprimer le conteneur + l'outil = exception supprimée

### Setup (commande unique)

    docker run -d --name searxng -p 127.0.0.1:8888:8080 -v "$HOME/searxng/settings.yml:/etc/searxng/settings.yml:ro" --restart unless-stopped searxng/searxng

### Validé en boucle vocale

« président des États-Unis » → web_search → réponse correcte via SearXNG.

---

## 2026-08-28 — Palier 7 : Calendrier Apple déterministe (création/lecture/dispo)

**Décision : intents calendrier exécutés en déterministe via AppleScript
natif (integrations/calendar.py), dans un calendrier dédié « Olympe »
créé automatiquement dans l'app Calendrier. Zéro API tierce.**

### 7 handlers

- create_event : création d'événement unique
- next_event : prochain événement (7 prochains jours)
- events_today : événements du jour
- events_date : événements d'une date donnée
- check_availability : vérification de disponibilité avec détection de conflit
- search : recherche par mots-clés dans les titres
- create_recurring : événements récurrents (yearly/weekly/monthly)

### Couche de réparation déterministe (prefilter + hook pipeline)

- **calendar_intent_hint** : corrige un intent faux (ex. play_music sur
  « bloque une réunion… ») sur marqueurs forts uniquement
- **repair_calendar_slots** : complète title/date/time manquants (confiance
  LoRA 0.45 = slots requis manquants, pas une erreur de classification) :
  extraction regex de la date, de l'heure, et du titre avec nettoyage
  (verbes d'action, marqueurs temporels, connectifs orphelins)
- **Reroute get_events_today → get_events_date** si la phrase contient un
  marqueur de date autre qu'aujourd'hui

### Leçons apprises

- Ne pas baisser le seuil de confiance global : réparer les slots à la
  place (fiable, viable, calibrage conservé)
- Titres nettoyés (« à » orphelin, connectifs) pour ne pas polluer le
  calendrier ; événements parasites supprimables via AppleScript
- Mémoire : faits injectés avec propriétaire explicite (« l'utilisateur »)
  sinon le 8B confond avec ses propres préférences

### Filet de sécurité

3 outils MCP calendrier (create_calendar_event, get_next_calendar_event,
get_todays_events) pour le fallback 8B.

### Validé

- Création (« réunion » vendredi 15h) dans l'app Calendrier
- Lecture (« déjeuner avec Marie »)
- Détection de conflit (« Pas libre : réunion… »)
- 8B non réveillé sur les voies déterministes
