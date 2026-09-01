# MJ — Journal des décisions techniques

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
travail, entraînement d'"MJ" reporté post-P5**

### Ce qui est conservé pour l'entraînement futur

15 échantillons réels de "MJ" enregistrés et validés dans
`voice/wake_samples/` (WAV 16 kHz, mono, 16-bit, 1.5s chacun).

### Plan d'entraînement "MJ" (post-P5)

1. Utiliser le notebook Colab officiel openWakeWord
2. Générer des milliers d'échantillons synthétiques de "MJ" via TTS
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
natif (integrations/calendar.py), dans un calendrier dédié « MJ »
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

---

## 2026-08-28 — Palier 2/11 : Migration vllm-mlx → llama-server (prefix cache sur outils)

**Décision : abandonner vllm-mlx 0.4.1 au profit de llama-server (llama.cpp) pour le serveur d'inférence persistant**

### Contexte — problème de latence persistant

Le Palier 2 avait validé vllm-mlx 0.4.1 avec un gain de 76% grâce au prefix caching (22s → 5s en mode chat pur). Mais une fois le tool-calling activé (15 outils MCP), la latence remontait à **20-25 secondes par requête**, même en cache hit.

### Diagnostic

Test comparatif sur le même prompt avec 15 outils :
- **Test isolé (chat pur, sans outils)** : 3.4s → 1.3s → 1.2s (cache fonctionne)
- **Test pipeline (avec outils)** : 25s → 21s → 21s (cache ne fonctionne pas)

**Cause racine** : vllm-mlx 0.4.1 traite le tool-calling comme un **chemin de code séparé** du chat normal. Le paramètre `tools` dans l'API OpenAI n'est pas couvert par le prefix cache, donc les définitions d'outils (~2000 tokens, le plus gros morceau du prefill) sont retraitées intégralement à chaque requête.

### Alternative évaluée : llama-server (llama.cpp)

llama-server est le moteur d'inférence le plus éprouvé du secteur (utilisé par Ollama, LM Studio, etc.). Sur nos critères :
- Support natif du tool-calling Qwen3 (template officiel via `--jinja`)
- Prefix cache **fonctionnel avec les outils** (prouvé par la communauté)
- API OpenAI-compatible identique (migration transparente)
- Modèles GGUF officiels Qwen3-8B disponibles sur Hugging Face
- Apple Silicon optimisé via Metal

### Résultats mesurés

Installation : `brew install llama.cpp` + téléchargement de `Qwen3-8B-Q4_K_M.gguf` (4.7 Go, quantification Q4_K_M).

Test isolé avec 15 outils :
- **Requête 1** : 8.33s (prefill à froid)
- **Requête 2** : 2.42s (cache hit)
- **Requête 3** : 3.45s (cache hit)
- **Gain** : ~70% entre appel 1 et appels suivants

Tool-calling : `finish_reason=tool_calls`, arguments JSON bien formés, parsing structuré natif.

Migration du pipeline :
- `config/models.yaml` : `engine: llama-cpp`, `repo: models/qwen3-8b-q4_k_m.gguf`
- `server/start.py` : support du binaire `llama-server` + arguments (`-m`, `-c`, `-np`, `-ngl`, `--jinja`)
- Lancement automatique via `python server/start.py`

### Critère de décision

Le test §11.1 de la roadmap ("vllm-mlx comme fondation du serveur, ou repartir sur une couche plus fine ?") est tranché :
- vllm-mlx **abandonné** : limitation structurelle sur le tool-calling (pas de cache)
- llama-server **retenu** : prefix cache fonctionnel, latence fallback divisée par ~8 (de 20s à 2-3s)
- Modèle 8B **conservé** : marge de raisonnement P6/P7 validée une fois le cache actif

### Friction documentée

Le téléchargement initial du GGUF a échoué silencieusement (fichier de 15 octets = 404) à cause d'une URL en minuscules au lieu de majuscules (`qwen3-8b-q4_k_m.gguf` vs `Qwen3-8B-Q4_K_M.gguf`). Commande `hf models list` pour identifier le nom exact avant téléchargement.

### Impact sur la roadmap

Le point §11.1 est clos. Le Palier 2 (serveur persistant) est maintenant **définitivement validé** avec llama-server. La latence de fallback LLM est passée de ~20s à ~3s, ce qui rend le 8B viable en production malgré son débit de génération de 14 tokens/s.

---

---

## 2026-08-28 — Dette technique : contention GPU Metal inter-process

**Problème identifié : latence erratique du dispatcher (0.3s → 10-16s) après un appel LLM via llama-server**

### Diagnostic

Tests systématiques montrant que :
- Le dispatcher seul (en boucle) : stable à 0.24-0.34s
- llama-server seul (en boucle) : stable à 2.8-3.6s  
- Dispatcher **juste après** llama-server : erratique 1.8s → 16.7s

**Cause racine** : contention Metal inter-process sur mémoire unifiée. llama-server (process séparé) et le dispatcher MLX (process Python) utilisent tous deux Metal. Quand llama-server fait du prefill/génération, il monopolise des ressources GPU que le dispatcher attend ensuite pour sa propre inférence.

### Tentatives de résolution (toutes infructueuses)

| Tentative | Résultat |
|---|---|
| `mx.metal.clear_cache()` après LLM | Aucun effet |
| Délai de 0.15s après LLM | Insuffisant |
| Délai de 1-3s après LLM | Insuffisant |
| Réduire llama-server à `-np 1` (1 slot) | Aucun effet |
| Forcer dispatcher sur CPU | mlx_lm ne supporte pas CPU (KeyError) |

### Impact en usage réel

La boucle vocale complète (wake word → STT → dispatcheur → LLM → TTS) inclut naturellement plusieurs secondes de délai entre deux commandes :
- Génération TTS : 2-5s
- Attente wake word : variable
- Transcription STT : 1-2s

Ce délai naturel masque partiellement la contention, mais ne l'élimine pas complètement.

### Décision

**Dette technique acceptée**. La latence moyenne du dispatcher après un fallback LLM est ~5-8s au lieu de 0.3s. Acceptable car :
- Les fallbacks sont rares en usage normal (dispatcheur route correctement 80.9% du temps)
- Le délai naturel de la boucle vocale masque partiellement le problème
- Aucune solution technique propre identifiée sans changement d'architecture majeur

### Solutions non retenues (coût disproportionné)

1. **Dispatcher dans process séparé** : complexité IPC, latence supplémentaire
2. **Dispatcher non-MLX** : abandonner le fine-tuning LoRA investi au Palier 4
3. **Serveur d'inférence différent** : llama-server déjà optimal pour tool-calling + cache

### Leçons apprises

Sur Apple Silicon avec mémoire unifiée, deux process utilisant Metal simultanément peuvent créer une contention GPU imprévisible. Ce n'est pas un bug mais une limitation structurelle de l'architecture.

---

---

## 2026-08-28 — Palier 8 : architecture commune _core/ et contrôle du Finder

**Décision : toutes les intégrations macOS partagent integrations/_core/ (applescript_runner, risk_levels, permissions, confirmation)**

### Contexte

Le Palier 7 (calendrier) avait son propre runner AppleScript. Avant d'ajouter Finder/Rappels/Notes, extraction du commun pour éviter trois copies divergentes.

### Niveaux de risque appliqués

- SAFE : exécution directe (search_file, list_folder, open_file, list_recent_files)
- REVERSIBLE : exécution + is_allowed() (create_folder, move_file)
- DESTRUCTIVE : confirmation vocale obligatoire, jamais d'exécution directe (delete_file vers corbeille, empty_trash)

### Sécurité

- Whitelist config/allowed_paths.yaml : writable / readable / never_touch
- Résolution des ~ et des chemins avant toute action
- Jamais de suppression définitive : delete = déplacement vers la corbeille
- open_file refuse les extensions exécutables (.sh, .command, .pkg...) hors /Applications

### Routage sans retraining

Les intents files existent déjà dans la taxonomie v1.4 (find_file, open_folder, list_recent_files...). Le pré-filtre force les motifs évidents et files_slots() extrait les slots par regex (~0 ms), injectés dans le forcing du dispatcheur. Aucun réentraînement nécessaire.

### Validé

- SAFE/REVERSIBLE : 3 phrases en boucle vocale déterministe (confiance 1.0, zéro fallback 8B)
- DESTRUCTIVE : cycle complet question → non (annulation, fichier intact) → oui (corbeille, retour réel du handler)

---

---

## 2026-08-28 — Leçons AppleScript du contrôle d'apps/documents (P8)

**Décision : trois règles dures pour toute intégration AppleScript**

1. **Jamais résoudre une app non installée** : toute référence `application "X"` sur une app absente ouvre un dialogue modal bloquant (« Où se trouve X ? »). On vérifie d'abord via `ps` que le process tourne (open_app/close_app/close_file).
2. **Tell littéral, pas par variable** : `tell application appName` (variable) compile sans le dictionnaire de l'app — le `get` fonctionne mais `close` reste muet. Les scripts générés inlinent le nom de l'app (forme identique aux commandes manuelles validées).
3. **Jamais de fallback 8B sur un intent forcé en échec** : le modèle génératif hallucinait un succès (« Fermé : … ») après un timeout. Garde dans pipeline.py : réponse d'erreur honnête à la place.

Corollaires acceptés : première fermeture d'une app = pop-up d'autorisation macOS (une fois par app, mémorisée) ; fermeture de document = boîtes « enregistrer ? » natives comme protection ; Finder jamais fermé (NEVER_CLOSE).

---

## 2026-08-29 — Leçon iCloud : corbeille via Foundation, pas via Finder AppleScript (P8)

**Décision : les mises à la corbeille passent par trashItemAtURL (JXA/Foundation), repli ~/.Trash ; jamais par `delete` AppleScript Finder**

### Contexte

Le Desktop (et Documents) de la machine est synchronisé iCloud Drive. Sur un élément syncé, `tell application "Finder" to delete` déclenche une coordination iCloud qui bloque ~37 s puis échoue en error -8013 (« l'élément doit être téléchargé »). Tous les timeouts de delete_folder venaient de là — ni permissions, ni processus orphelins.

### Conséquences générales

- Toute opération AppleScript Finder sur un dossier syncé iCloud peut hanger ; préférer les API Foundation (NSFileManager) ou shutil côté Python.
- trashItemAtURL = même comportement corbeille que le Finder (réversible, « récupérer » possible), sans Apple Events ni pop-up d'autorisation.
- Repli si trashItemAtURL échoue : déplacement direct vers ~/.Trash (jamais de suppression définitive).

### Clôture du catalogue Finder (19 actions)

SAFE : search_file, search_content, list_folder, list_recent_files, open_file, open_folder, locate_file, check_file_exists, get_file_info.
REVERSIBLE : create_folder, move_file, rename_file, copy_file, duplicate_file, compress_file, extract_archive, add_tag, set_favorite (= tag Favoris).
DESTRUCTIVE (confirmation vocale) : delete_file, delete_folder, empty_trash, overwrite_file.

Validé de bout en bout : copie vers Downloads, tags natifs xattr avec casse préservée, dossier vers corbeille en < 2 s, réponses honnêtes en cas d'échec.

---

---

## 2026-08-29 — Wake word « MJ » : leçon de l'expérimentation CNN maison (Palier 5)

**Décision : retour au pipeline officiel openWakeWord ; le CNN maison est abandonné.**

### Contexte

Tentative d'entraîner un wake word « MJ » avec un CNN minuscule (~1 Mo,
2 conv + 1 dense) en MLX, directement sur le Mac, sur un dataset de
~285 positifs / ~560 négatifs (réels + synthétiques Qwen3-TTS + augmentation).

### Résultats mesurés

- Évaluation sur fichiers isolés : 10/10 positifs, 12/12 négatifs.
- En flux continu live : faux positifs inacceptables (« bonjour » score 1.00,
  « Olympique » parfois détecté), malgré seuil 0.8 + période réfractaire 1,2 s.

### Analyse

- Un CNN from scratch sans backbone pré-entraîné n'a pas la robustesse
  nécessaire au flux continu : il mémorise des corrélations fragiles
  (acoustique micro/pièce) plutôt que le motif phonétique.
- Dataset ~3 ordres de grandeur trop petit : les modèles openWakeWord officiels
  s'appuient sur des dizaines de milliers d'heures de négatifs et un backbone
  d'embeddings pré-entraîné sur des données massives.
- L'évaluation sur fichiers isolés n'est PAS prédictive du comportement en
  flux continu — toujours évaluer en conditions réelles de déploiement.

### Conséquence

Le wake word « MJ » sera entraîné via le pipeline officiel openWakeWord
(notebook automatic_model_training), avec génération synthétique française
(Qwen3-TTS) pour respecter la phonétique du mot. Conformément à la roadmap
(Palier 5) : openWakeWord est la solution standard retenue.

---

## 2026-08-31 — Leçon de nommage : jamais utiliser un nom de module stdlib

**Décision : renommage de `integrations/calendar.py` → `integrations/apple_calendar.py`.**

### Contexte

Le fichier `integrations/calendar.py` portait le même nom que le module
standard Python `calendar` (gestion des dates). Quand Python (via
`email._parseaddr`) importait son propre `calendar`, il trouvait d'abord
notre fichier local, qui essayait lui-même d'importer
`integrations._core.applescript_runner` — d'où un `ModuleNotFoundError`.

### Règle

Un module interne ne doit **jamais** avoir le même nom qu'un module de
la stdlib Python ou qu'une bibliothèque tierce installée. Préfixer par
le domaine (`apple_`, `tahoma_`, etc.) quand le nom naturel est ambigu.

---

## 2026-08-31 — Palier 7 : intégration TaHoma (volets Somfy)

### Décision : API locale Overkiz directe plutôt que Home Assistant

**Contexte** : la roadmap recommandait Home Assistant pour la domotique.
Deux options : installer HA (service 24h/24) ou parler directement à la
box TaHoma via son API locale (mode développeur, port 8443).

**Choix retenu** : API Overkiz directe.

**Raisonnement** :
- 100 % local, aucun cloud (cohérent avec la philosophie du projet)
- Moins de pièces mobiles et ~500 Mo de RAM économisés sur 16 Go
- La box expose déjà tout ; le protocole io-homecontrol est
  bidirectionnel (lecture d'état réelle des volets)

**Points de vigilance** :
- Token gitignoré (`config/tahoma.yaml`) — ne jamais committer
- SSL auto-signé : vérification désactivée acceptable uniquement en
  circuit fermé local
- Nommage des états : `core:ClosureState` (0 = ouvert, 100 = fermé)

### Architecture en 3 couches

- `integrations/_core/tahoma_client.py` : client bas niveau (deviceURL +
  commandes brutes), stdlib uniquement
- `integrations/tahoma.py` : couche métier (noms humains, traduction
  pourcentage -> closure), niveau de risque REVERSIBLE
- `agent/mcp_server.py` : 6 outils MCP ajoutés au catalogue existant
  (patch chirurgical, 15 outils précédents intacts → 21 outils total)

### Dispatcheur NLU — patterns TaHoma (router/dispatcher.py v3)

- "ouvre les volets" -> shutters.open_all
- "ferme la chambre de fabian" -> shutters.close {name: Chambre Fabian}
- "ferme la baie vitrée 2" -> shutters.close {name: Baie 2} (synonyme toléré)
- "ouvre à moitié les volets du bureau" -> shutters.set_position
  {percent: 50, name: Bureau}
- "mets les volets à 30%" -> shutters.set_position {percent: 30} (global)
- Garde-fous : vocabulaire de pièces exigé ("ferme la télé" ne matche
  pas), tests orchestrateur en dry-run (aucune action réelle)

## 2026-08-31 — Review de code : les 4 points du plan d'amélioration corrigés

**Décision** : appliquer intégralement le plan d'amélioration du 31/08/2026.

1. **Injection AppleScript (critique)** : `_as_literal()` dans
   `_core/applescript_runner.py` + cadenas AST (`test_no_raw_interpolation.py`)
   + migration des 14 interpolations de `apple_calendar.py` et `finder.py`.
2. **Duplication (élevé)** : registre partagé `agent/tools/` (21 outils,
   un fichier par outil, découverte récursive) ; `mj.py` et `mcp_server.py`
   réduits à des adaptateurs minces (86 et 49 lignes).
3. **empty_trash (moyen)** : garde `confirmed=False` ; seul l'executor de
   confirmation vocale (`_run_confirmed` dans `voice/pipeline.py`) injecte
   `confirmed=True`.
4. **Erreurs silencieuses (faible)** : `except Exception: pass` remplacés par
   des exceptions ciblées avec message de repli dans `agent/tools/` ; les
   adaptateurs de bord remontent l'erreur au lieu de la taire.

**Évolutions futures tracées** : builder AppleScript / `on run argv` ;
Rust limité aux composants candidats (wake word, boîtier embarqué) —
le cœur reste Python (MLX n'a pas de bindings Rust).

## 2026-09-01 — Contrainte < 200 lignes + reconstruction du Dispatcher

**Décisions** :
1. Aucun fichier Python > 200 lignes. Les 7 fichiers hors limite sont
   devenus des packages (finder, apple_calendar, prefilter, tts, stt,
   bridge, pipeline) avec ré-export paresseux `__getattr__` (PEP 562) :
   les imports existants n'ont pas bougé.
2. `router/nlu.py` : classe Dispatcher reconstruite (elle n'avait jamais
   existé — le pipeline vocal était cassé à l'import depuis ecc6ff6).
   Combine prefilter + dispatch volets v5 + intents.yaml, avec garde
   find_spec (déterministe seulement si le module handler existe).
3. MCPBridge supprimé du pipeline : tool-calling direct via agent.tools.

**Leçons tracées** :
- Un fichier déplacé d'un niveau doit passer de `parent.parent` à
  `parents[2]` (bugs CONFIG_PATH/ROOT trouvés dans tts, stt, bridge).
- La régression par import simple a révélé 2 cassures préexistantes
  invisibles en production (CONFIG_PATH, Dispatcher).

## 2026-09-02 — Renommage du projet : OLYMPE → MJ

**Contexte** : Le projet a démarré sous le nom "OLYMPE" (visible dans les prompts, le calendrier macOS, les docs). Le dépôt Git et le dossier de travail s'appellent "MJ". Incohérence de nommage.

**Décision** : Renommer uniformément en "MJ" partout (code, docs, prompts, hotwords STT).

**Exceptions conservées** :
- Le calendrier macOS s'appelle toujours "Olympe" (évite de perdre l'historique des événements)
- Les hotwords STT dans `config/models.yaml` incluent toujours "Olympe" (transition progressive vers "MJ")

**Impact** : Changement cosmétique, aucune fonctionnalité affectée. Le tool-calling et le serveur persistent fonctionnent identiquement.

## 2026-09-02 — Palier 5 atteint : boucle vocale complète

Premier test vocal réel réussi, après réparations (Dispatcher reconstruit,
chemins parents[2], import argparse).

Chaîne validée de bout en bout :
- Wake word hey_jarvis (openWakeWord, seuil 0.5, score 0.52)
- STT Qwen3-ASR-1.7B-4bit (« Quelle heure est-il ? » transcrit correctement)
- Routage nlu.Dispatcher -> fallback -> LLM vllm-mlx + tool-calling
- Outil get_current_time via agent.tools (MCPBridge supprimé)
- TTS Qwen3-TTS-12Hz-1.7B : réponse lue à voix haute

Provisoire : wake word « hey jarvis » en attendant l'entraînement « MJ ».

## 2026-09-02 — Palier 7 : SearXNG local + règle anti-hallucination

**Décision** : SearXNG en conteneur Docker sur 127.0.0.1:8888
(services/searxng/, versionné), outil web_search branché dessus.

**Exception consciente (P7)** : la recherche web est la seule dépendance
externe acceptée — les moteurs interrogés par SearXNG sont distants.
Tout le reste demeure local.

**Anti-hallucination** : le 8B ne doit pas décider lui-même de chercher
(il répondait de mémoire « Vingegaard a gagné le Tour 2025 »). Une règle
regex déterministe (WEB_RE, router/nlu.py) force web_search pour les faits
récents, et la réponse est résumée strictement d'après les résultats
(grounded_web_answer, router/orchestrator.py).

**Unification voix/écrit** : orchestrate() (mode texte) et le pipeline
vocal passent désormais par le même routeur nlu.Dispatcher et la même
fonction ancrée — une seule source de vérité.

**Bug tracé** : openwakeword segfault au Ctrl+C (zsh: segmentation fault).
Non bloquant — contournement : relancer la boucle.
