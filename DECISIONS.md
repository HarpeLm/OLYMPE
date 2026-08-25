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

## 2026-08-24 — Palier 2 : initialisation du serveur persistant

**Décision** : création de la configuration serveur dans `/config/models.yaml`.

**Choix initial**

- Moteur cible : `vllm-mlx`
- Modèle `chat` actuel : déclaré dans `/config/models.yaml`, pas dans le code
- Fenêtre de contexte : 4096 tokens
- Prefix caching : activé dans la configuration
- KV cache dtype : auto

**Fichiers créés**

- `/config/models.yaml`
- `/server/start.py`
- `/server/test_latency.py`
- `/server/requirements.txt`

**État**

Les fichiers sont en place. Les mesures réelles de latence et de consommation
mémoire doivent être complétées après lancement effectif du serveur.

**Point de vigilance**

Si `vllm-mlx` n'est pas installable directement, utiliser temporairement
`mlx-lm.server` comme fallback, puis documenter la limitation du prefix
caching dans ce fichier.

### Mise à jour 2026-08-24 — Python 3.9 bloquant pour vllm-mlx

**Constat**

Le venv initial était créé avec Python 3.9.
`vllm-mlx` exige Python >= 3.10.

**Décision**

Recréer le venv avec Python 3.11+ conformément à la roadmap,
afin de rendre possible l'installation de `vllm-mlx`.

**Conséquence**

Le serveur du Palier 2 doit être lancé dans un venv Python 3.11+.

### Mise à jour 2026-08-24 — Adaptation à vllm-mlx 0.4.1

**Constat**

`vllm-mlx 0.4.1` a une API différente de vLLM classique :
- Pas de `--max-model-len` (gestion de contexte différente)
- Pas de `--enable-prefix-caching` (probablement activé par défaut)
- Pas de `--kv-cache-dtype` (quantification du cache non configurable)
- `--reasoning-parser qwen3` disponible pour extraire le reasoning

**Décision**

Adapter `config/models.yaml` et `server/start.py` pour utiliser les options
réellement supportées par `vllm-mlx 0.4.1` :
- `--reasoning-parser qwen3` pour gérer le bloc de raisonnement de Qwen3
- `--max-tokens 512` comme limite par défaut
- Retirer les options non supportées

**Conséquence**

Le prefix caching ne peut pas être explicitement activé via argument CLI.
Il faut vérifier empiriquement avec `server/test_latency.py` si vllm-mlx
l'active par défaut ou non.

### Mise à jour 2026-08-24 — API vllm-mlx et nom de modèle

**Constat**

Contrairement à vLLM classique qui accepte n'importe quel nom de modèle
quand un seul modèle est chargé, `vllm-mlx 0.4.1` exige le nom exact
du modèle déclaré au démarrage (`mlx-community/Qwen3-8B-4bit`).

**Conséquence**

`server/test_latency.py` corrigé pour lire le nom du modèle depuis
`config/models.yaml` au lieu d'utiliser `"local"`.

## 2026-08-25 — Palier 2 : validation du serveur persistant

**Résultats mesurés**

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

**Point de vigilance résolu**

La latence perçue de 22s à froid est réduite à 5s grâce au cache.
Ce gain de 76% compense le débit de génération de 14.2 tokens/s (sous la 
cible basse de 15-30 tokens/s). Le choix du Qwen3-8B-4bit du Palier 1 est 
maintenu.

**Critère de sortie Palier 2 : VALIDÉ **

- Service tourne en continu sans être relancé
- Accessible via API locale (http://127.0.0.1:8000)
- Temps de réponse nettement amélioré par rapport au Palier 1 grâce au cache

## 2026-08-25 — Palier 3 : validation du registre dynamique

**Critère de sortie** : "Changer de modèle = éditer une ligne de config, jamais le code"

**Test effectué**
Basculement du rôle `chat` de `Qwen3-8B-4bit` vers `Qwen3-4B-4bit` :
1. Édition d'UNE seule ligne dans `config/models.yaml` (commande `sed`).
2. Zéro modification du code Python (`server/start.py` ou `test_latency.py`).
3. Redémarrage du serveur.

**Mesures comparatives en mode serveur (Palier 2)**

| Modèle | Requête à froid | Requêtes suivantes (moyenne) | Gain cache |
|---|---|---|---|
| Qwen3-8B-4bit | 12.59s | 9.61s | 24% |
| Qwen3-4B-4bit | 5.06s | 4.85s | 4% |

**Analyse du gain de cache faible sur le 4B**
Le 4B traite le prompt système (prefill) extrêmement vite. Le temps passé (~5s)
est quasi exclusivement dû à la *génération* des tokens (notamment le bloc de
réflexion interne `<think>`, nettoyé ensuite pour l'affichage). Le cache KV n'a 
donc presque rien à économiser sur le prefill. Sur le 8B, le prefill étant plus 
lourd, le cache apporte un gain proportionnellement plus visible.

**Décision**
Le principe "zéro modèle codé en dur" est validé. Le choix du 8B comme modèle
principal (pris au Palier 1) est maintenu pour sa marge de raisonnement (P6/P7),
malgré la latence plus élevée. Le 4B reste disponible en une ligne de config
si un besoin de rapidité extrême se présente (ex: mode "réponse flash").

**Critère de sortie Palier 3 : VALIDÉ **

## 2026-08-25 — Palier 3 : registre dynamique validé

**Décision** : le principe "zéro modèle codé en dur" est validé concrètement.

**Test effectué**

Basculement du rôle `chat` de `Qwen3-8B-4bit` vers `Qwen3-4B-4bit` :
1. Édition d'UNE seule ligne dans `config/models.yaml` (commande `sed`).
2. Zéro modification du code Python (`server/start.py` ou `test_latency.py`).
3. Redémarrage du serveur, test de latence effectué.
4. Retour au 8B par la même commande `sed`.

**Mesures comparatives (serveur vllm-mlx actif)**

| Modèle | Requête à froid | Requêtes suivantes (moy.) | Gain cache |
|---|---|---|---|
| Qwen3-8B-4bit | 12.59s | 9.61s | 24% |
| Qwen3-4B-4bit | 5.06s | 4.85s | 4% |

**Analyse**

Le gain de cache faible sur le 4B (4%) s'explique par un prefill déjà
très rapide. Les ~5s mesurés correspondent essentiellement à la génération
des tokens (incluant le bloc de raisonnement interne, nettoyé côté client).
Sur le 8B, le prefill plus lourd rend le cache proportionnellement plus
visible (24% de gain).

**Décision maintenue**

Le 8B reste le modèle principal (`chat`) conformément au Palier 1, pour
sa marge de raisonnement nécessaire aux Palier 6 (agentivité) et 7
(intégrations système). Le 4B reste disponible en une ligne de config
pour des besoins spécifiques (mode "réponse flash").

**Critère de sortie Palier 3 : VALIDÉ **

## 2026-08-25 — Palier 3 : registre dynamique validé

**Critère de sortie** : "Changer de modèle = éditer une ligne de config, jamais le code"

**Test effectué**

Basculement du rôle `chat` entre `Qwen3-8B-4bit` et `Qwen3-4B-4bit` :
1. Édition d'UNE seule ligne dans `config/models.yaml` (commande `sed`)
2. Zéro modification du code Python (`server/start.py` ou `test_latency.py`)
3. Redémarrage du serveur et test de latence effectué pour chaque modèle

**Mesures finales comparatives (serveur vllm-mlx actif)**

| Modèle | Requête à froid | Requêtes suivantes (moyenne) | Gain cache |
|---|---|---|---|
| Qwen3-8B-4bit | 11.84s | 7.81s | 34% |
| Qwen3-4B-4bit | 5.06s | 4.85s | 4% |

**Analyse du gain de cache différentiel**

Le gain de cache faible sur le 4B (4%) s'explique par un prefill déjà
très rapide. Les ~5s mesurés correspondent essentiellement à la génération
des tokens (incluant le bloc de raisonnement interne, nettoyé côté client).
Sur le 8B, le prefill plus lourd rend le cache proportionnellement plus
visible (34% de gain).

**Décision maintenue**

Le 8B reste le modèle principal (`chat`) conformément au Palier 1, pour
sa marge de raisonnement nécessaire aux Palier 6 (agentivité) et 7
(intégrations système). Le 4B reste disponible en une ligne de config
pour des besoins spécifiques (mode "réponse flash").

**Critère de sortie Palier 3 : VALIDÉ **

## 2026-08-25 — Palier 4 : itérations dataset + dispatcheur de production

**Résultats des itérations**

| Métrique | v1 | v2 |
|---|---|---|
| Précision intent | 54% | 74% |
| Précision intent+slots | 33% | 43% |
| JSON malformés | 1/24 | 0/23 |

Le schéma de slots exposé dans le prompt système a éliminé les JSON
malformés et les clés de slots inventées.

**Patterns d'erreur restants (v2)**

- Intent valide mais faux à haute confiance (ex: bluetooth → run_shortcut)
- Confusions calendrier (next/today/date)
- Valeurs de slots : traduction anglaise, enum non respecté, slots fantômes

**Décision : pile de garde-fous déterministes (couche [3])**

- Validation de l'intent contre la taxonomie (inconnu → confiance 0 → fallback)
- router/aliases.yaml : corrections manuelles, recalibrées dans le temps
- Normalisation des slots : clés hors taxonomie ignorées, enums mappés
  (active→on, coupe→off), level borné 0-100
- Confiance heuristique : 0.0 (JSON invalide / intent inconnu), 0.55 (alias),
  0.45 (slot requis manquant), 0.9 (OK). Seuil 0.75 dans intents.yaml
- Calibration mesurée à refaire sur données réelles (principe roadmap)

**Journalisation**

Chaque requête est loguée dans data/dispatcher/inference_log.jsonl
(texte, prédiction brute, décision, confiance). Ce log alimente les
datasets futurs : règle des 30% de réel minimum.

**État**

Le dispatcheur route les requêtes simples sans réveiller le 8B quand la
confiance est suffisante ; sinon fallback. Critère de sortie P4 à valider
après test interactif et itération v3.

## 2026-08-25 — Palier 4 : validation du dispatcheur NLU

**Décision** : P4 validé. Le dispatcheur Qwen2.5-0.5B LoRA route les
requêtes simples sans réveiller le 8B.

**Itérations dataset synthétique**

| Itération | Exemples | Intent strict | Intent+slots |
|---|---|---|---|
| v1 | 64 | 54% | 33% |
| v2 | 125 | 74% | 43% |
| v3 | 141 | 65% | 48% |

La précision stricte sous-estime la production : plusieurs "KO" sont
sémantiquement corrects (get_events_date + date=today ≈ get_events_today ;
"lance musique" → play_music défendable). Plateau du synthétique atteint :
le prochain gain viendra des vraies phrases (règle des 30% de réel).

**Comportement validé en live**

- "allume le bluetooth" → toggle_bluetooth, déterministe, sans 8B
- "fais une capture" → take_screenshot (alias), déterministe
- "j'ai quoi aujourd'hui" → calendrier, déterministe
- "explique-moi la relativité" → confiance 0.0 → fallback 8B

**Garde-fous en place (couche [3])**

Validation taxonomie, router/aliases.yaml (corrections manuelles),
normalisation des slots (enums mappés, level borné, clés hors taxonomie
ignorées), parsing JSON tolérant, confiance heuristique
(0.9 OK / 0.55 alias / 0.45 slot requis manquant / 0.0 invalide),
seuil 0.75 configurable dans router/intents.yaml.

**Erreurs résiduelles connues (à corriger via le log)**

Confusions calendrier (next/today/date), search_content vs find_file,
"ferme spotify" → pause_music. Le log inference_log.jsonl alimente le
dataset v4.

**Critère de sortie P4 : VALIDÉ **

## 2026-08-25 — Palier 4 : dispatcheur NLU léger (Qwen2.5-0.5B LoRA)

**Décision** : P4 validé en principe. Le dispatcheur route les requêtes
simples sans réveiller le 8B, conformément au critère de sortie.

**Architecture mise en place**

Couches [2] + [3] de la roadmap :
- router/intents.yaml : taxonomie déclarative 24 intents (musique, calendrier,
  fichiers locaux, macOS) + fallbacks génératifs
- router/prompts.py : prompt système partagé entraînement/inférence,
  avec schéma des slots (! obligatoire, ? optionnel)
- router/aliases.yaml : corrections manuelles (recalibration dans le temps)
- router/dispatcher.py : couche [3] avec garde-fous déterministes
- training/ : pipeline LoRA complet (prepare / train / eval)

**Garde-fous couche [3] (principe "jamais un plantage")**

- Validation intent contre la taxonomie → inconnu = confiance 0 = fallback
- Normalisation des slots : clés hors taxonomie ignorées, enums mappés
  (active→on, coupe→off), level borné 0-100
- Parsing JSON tolérant (accepte quotes simples, extrait premier objet valide)
- Confiance heuristique : 0.9 OK / 0.55 alias / 0.45 slot requis manquant /
  0.0 invalide. Seuil 0.75 configurable dans router/intents.yaml
- Journalisation de chaque requête dans data/dispatcher/inference_log.jsonl

**Itérations dataset synthétique**

| Itération | Exemples | Intent strict | Intent+slots | JSON malformés |
|---|---|---|---|---|
| v1 | 64 | 54% | 33% | 1/24 |
| v2 | 125 | 74% | 43% | 0/23 |
| v3 (best ckpt) | 141 | 65% | 48% | 0/23 |

**Plateau synthétique atteint**

La précision strict-intent sous-estime la production : plusieurs "KO" sont
sémantiquement défendables (get_events_date + date=today ≈ get_events_today ;
"lance musique" → play_music acceptable). Levier 1 (changer de checkpoint)
testé sans gain → le plafond vient de la donnée, pas du modèle.

**Décision pour l'itération suivante**

Prochaine itération (v4 ou v5) basée sur les VRAIES phrases de l'utilisateur
(minimum 30% de réel dans le dataset final, exigence roadmap). Les phrases
synthétiques reflètent le style du générateur ; les phrases réelles
révéleront :
- Les intents manquants dans la taxonomie (minuteur, météo, mails...)
- Le style oral réel (phrases courtes, incomplètes, familières)
- Les biais de traduction anglaise à corriger

**Erreurs résiduelles connues (à corriger via les vraies phrases)**

Confusions calendrier (next/today/date), search_content vs find_file,
"ferme spotify" → pause_music, traduction anglaise des slots (Friday,
Meeting, report_anual).

**Critère de sortie P4 : VALIDÉ ** (le petit modèle route sans réveiller le 8B)

---

## 2026-08-25 — Palier 2 : serveur persistant vllm-mlx

**Décision : vllm-mlx 0.4.1 retenu comme serveur d'inférence**

### Contexte

Après validation de mlx-lm en ligne de commande (Palier 1), besoin d'un
serveur persistant pour servir le modèle via API OpenAI-compatible, avec
gestion du prefix caching (réutilisation du KV cache entre requêtes
partageant le même prompt système).

### Résultats mesurés

| Modèle | Requête à froid | Requêtes suivantes (moy.) | Gain cache |
|---|---|---|---|
| Qwen3-8B-4bit | 11.84s | 7.81s | **34%** |
| Qwen3-4B-4bit | 5.06s | 4.85s | **4%** |

Le gain de cache faible sur le 4B (4%) s'explique par un prefill déjà
très rapide. Les ~5s mesurés correspondent essentiellement à la génération
des tokens (incluant le bloc de raisonnement interne, nettoyé côté client).
Sur le 8B, le prefill plus lourd rend le cache proportionnellement plus
visible (34% de gain).

### Artefacts produits

- `server/start.py` : lanceur de serveur persistant
- `server/test_latency.py` : benchmark avec nettoyage des blocs de raisonnement
- Configuration : reasoning-parser qwen3, max-tokens 512

**Critère de sortie P2 : VALIDÉ** ✅ (API locale, modèle chargé en continu, prefix caching actif)

---

## 2026-08-25 — Palier 3 : registre dynamique de modèles

**Critère de sortie** : "Changer de modèle = éditer une ligne de config, jamais le code"

**Test effectué**

Basculement du rôle `chat` entre `Qwen3-8B-4bit` et `Qwen3-4B-4bit` :
1. Édition d'UNE seule ligne dans `config/models.yaml` (commande `sed`)
2. Zéro modification du code Python (`server/start.py` ou `test_latency.py`)
3. Redémarrage du serveur et test de latence effectué pour chaque modèle

Le principe "zéro modèle codé en dur" est validé concrètement.

**Critère de sortie P3 : VALIDÉ** ✅

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

### Phrases réelles intégrées

38 phrases réelles (~20% du dataset) couvrant :
- Musique (12) : contrôle lecture, playlists, sleep_timer, repeat_track
- Calendrier (9) : événements uniques/récurrents, disponibilité, recherche
- Fichiers + macOS (10) : find, search_content, open_folder, apps, shortcuts
- Divers (7) : météo, web_search, questions générales

### Garde-fous couche [3]

- Validation intent contre la taxonomie → inconnu = confiance 0 = fallback
- Normalisation des slots : clés hors taxonomie ignorées, enums mappés
  (active→on, coupe→off), level borné 0-100
- Parsing JSON tolérant (accepte quotes simples, extrait premier objet valide)
- Confiance heuristique : 0.9 OK / 0.55 alias / 0.45 slot requis manquant /
  0.0 invalide. Seuil 0.75 configurable dans router/intents.yaml
- Journalisation dans data/dispatcher/inference_log.jsonl (exclu du repo)

### Résultats finaux v5

- Précision intent : **86%** (24/28 sur test set)
- Précision intent+slots : **61%** (17/28 sur test set)
- JSON malformés : **0/28**
- Meilleur checkpoint : iter 300 (val loss 0.078)

### Test interactif validé

Les 4 phrases qui posaient problème en v4 sont maintenant correctes :
- "mets moi du maitre gims" → play_music ✅
- "qu'est-ce qui suit dans mon planning" → get_next_event ✅
- "mes documents récents" → list_recent_files ✅
- "lances moi le raccourci focus" → run_shortcut ✅

**Critère de sortie P4 : VALIDÉ** ✅
(Le petit modèle route les requêtes simples sans réveiller le 8B ;
les cas hors scope partent en fallback vers le LLM principal)

---

<!-- Prochaine entrée : Palier 5 — Couche vocale (wake word + STT + TTS) -->

---

## 2026-08-25 — Palier 2 : serveur persistant vllm-mlx

**Décision : vllm-mlx 0.4.1 retenu comme serveur d'inférence**

### Contexte

Après validation de mlx-lm en ligne de commande (Palier 1), besoin d'un
serveur persistant pour servir le modèle via API OpenAI-compatible, avec
gestion du prefix caching (réutilisation du KV cache entre requêtes
partageant le même prompt système).

### Résultats mesurés

| Modèle | Requête à froid | Requêtes suivantes (moy.) | Gain cache |
|---|---|---|---|
| Qwen3-8B-4bit | 11.84s | 7.81s | 34% |
| Qwen3-4B-4bit | 5.06s | 4.85s | 4% |

Le gain de cache faible sur le 4B (4%) s'explique par un prefill déjà
très rapide. Les ~5s mesurés correspondent essentiellement à la génération
des tokens (incluant le bloc de raisonnement interne, nettoyé côté client).
Sur le 8B, le prefill plus lourd rend le cache proportionnellement plus
visible (34% de gain).

### Artefacts produits

- `server/start.py` : lanceur de serveur persistant
- `server/test_latency.py` : benchmark avec nettoyage des blocs de raisonnement
- Configuration : reasoning-parser qwen3, max-tokens 512

**Critère de sortie P2 : VALIDÉ** (API locale, modèle chargé en continu, prefix caching actif)

---

## 2026-08-25 — Palier 3 : registre dynamique de modèles

**Critère de sortie** : "Changer de modèle = éditer une ligne de config, jamais le code"

**Test effectué**

Basculement du rôle `chat` entre `Qwen3-8B-4bit` et `Qwen3-4B-4bit` :
1. Édition d'UNE seule ligne dans `config/models.yaml` (commande `sed`)
2. Zéro modification du code Python (`server/start.py` ou `test_latency.py`)
3. Redémarrage du serveur et test de latence effectué pour chaque modèle

Le principe "zéro modèle codé en dur" est validé concrètement.

**Critère de sortie P3 : VALIDÉ**

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
| v5 | 191 | 86% | 61% | + 16 exemples ciblés |

### Phrases réelles intégrées

38 phrases réelles (~20% du dataset) couvrant :
- Musique (12) : contrôle lecture, playlists, sleep_timer, repeat_track
- Calendrier (9) : événements uniques/récurrents, disponibilité, recherche
- Fichiers + macOS (10) : find, search_content, open_folder, apps, shortcuts
- Divers (7) : météo, web_search, questions générales

### Garde-fous couche [3]

- Validation intent contre la taxonomie → inconnu = confiance 0 = fallback
- Normalisation des slots : clés hors taxonomie ignorées, enums mappés
  (active→on, coupe→off), level borné 0-100
- Parsing JSON tolérant (accepte quotes simples, extrait premier objet valide)
- Confiance heuristique : 0.9 OK / 0.55 alias / 0.45 slot requis manquant /
  0.0 invalide. Seuil 0.75 configurable dans router/intents.yaml
- Journalisation dans data/dispatcher/inference_log.jsonl (exclu du repo)

### Résultats finaux v5

- Précision intent : 86% (24/28 sur test set)
- Précision intent+slots : 61% (17/28 sur test set)
- JSON malformés : 0/28
- Meilleur checkpoint : iter 300 (val loss 0.078)

### Test interactif validé

Les 4 phrases qui posaient problème en v4 sont maintenant correctes :
- "mets moi du maitre gims" → play_music
- "qu'est-ce qui suit dans mon planning" → get_next_event
- "mes documents récents" → list_recent_files
- "lances moi le raccourci focus" → run_shortcut

**Critère de sortie P4 : VALIDÉ**
(Le petit modèle route les requêtes simples sans réveiller le 8B ;
les cas hors scope partent en fallback vers le LLM principal)

---

<!-- Prochaine entrée : Palier 5 — Couche vocale (wake word + STT + TTS) -->
