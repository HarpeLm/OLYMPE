"""
Dispatcheur NLU OLYMPE — Palier 4.

Couches [2] + [3] de la roadmap :
- prediction intent/slots par le modele LoRA 0.5B
- garde-fous deterministes : validation taxonomie, alias manuels,
  normalisation des slots, score de confiance, fallback
- journalisation de chaque requete (collecte du reel pour les datasets)

Usage :
    python router/dispatcher.py "allume le bluetooth"
    python router/dispatcher.py            # mode interactif
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.prefilter import (prefilter, domain_keywords_present, EXTRA_ALIASES,
                            files_slots, FAMILIES)
import json
import sys
import time
from pathlib import Path

import yaml
from mlx_lm import load, generate

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from router.prompts import build_system_prompt

LT = chr(60)
GT = chr(62)
STRIP_TAGS = [LT + "think" + GT, LT + "/think" + GT, LT + "|im_end|" + GT]

ON_VALUES = {"on", "active", "activer", "allume", "allumer", "oui", "true", "1"}
OFF_VALUES = {"off", "inactive", "desactive", "désactivé", "coupe", "couper",
              "eteins", "éteins", "non", "false", "0"}


class Dispatcher:
    def __init__(self):
        with open(ROOT / "config" / "models.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        with open(ROOT / "router" / "intents.yaml", "r", encoding="utf-8") as f:
            self.taxo = yaml.safe_load(f)

        self.schemas = {}
        for i in self.taxo.get("deterministic_intents", []):
            slots = i.get("slots") or []
            self.schemas[i["name"]] = {
                "keys": {s["name"]: s for s in slots},
                "required": [s["name"] for s in slots if s.get("required")],
                "handler": i.get("handler"),
            }

        alias_path = ROOT / "router" / "aliases.yaml"
        self.aliases = {}
        if alias_path.exists():
            with open(alias_path, "r", encoding="utf-8") as f:
                self.aliases = (yaml.safe_load(f) or {}).get("intent_aliases", {})

        self.threshold = self.taxo.get("confidence", {}).get("threshold", 0.75)

        d = cfg["roles"]["dispatcher"]
        print(f"Chargement du dispatcheur : {d['adapter']}")
        self.model, self.tokenizer = load(d["repo"], adapter_path=str(ROOT / d["adapter"]))
        self.system_prompt = build_system_prompt()

        self.log_path = ROOT / "data" / "dispatcher" / "inference_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _clean(self, text):
        for tag in STRIP_TAGS:
            text = text.replace(tag, "")
        return text.strip()

    def _parse_json(self, text):
        text = self._clean(text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            chunk = text[start:end + 1]
            for variant in (chunk, chunk.replace("'", '"')):
                try:
                    return json.loads(variant)
                except json.JSONDecodeError:
                    continue
        return None

    def _normalize_slots(self, intent, raw_slots):
        schema = self.schemas.get(intent)
        if schema is None or not isinstance(raw_slots, dict):
            return {}
        clean = {}
        for key, value in raw_slots.items():
            if key not in schema["keys"]:
                continue  # slot hors taxonomie : ignore
            spec = schema["keys"][key]
            if spec.get("type") == "enum":
                v = str(value).lower().strip()
                if v in ON_VALUES:
                    clean[key] = "on"
                elif v in OFF_VALUES:
                    clean[key] = "off"
                else:
                    clean[key] = v
            elif spec.get("type") == "integer":
                try:
                    n = int(float(value))
                    clean[key] = max(0, min(100, n)) if key == "level" else n
                except (TypeError, ValueError):
                    continue
            else:
                clean[key] = value
        return clean

    def route(self, text):
        # Pré-filtre regex (roadmap §4 [1]) — court-circuite les motifs évidents
        forced_intent, reason = prefilter(text)
        if forced_intent == "fallback":
            print(f"[PREFILTER] {reason} → fallback forcé")
            entry = {
                "ts": int(time.time()),
                "text": text,
                "raw_intent": None,
                "intent": "general_question",
                "slots": {},
                "confidence": 0.0,
                "action": "fallback",
                "handler": None,
            }
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return entry
        elif forced_intent:
            print(f"[PREFILTER] {reason} → {forced_intent} forcé")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        raw = generate(self.model, self.tokenizer, prompt=prompt,
                       max_tokens=128, verbose=False)

        pred = self._parse_json(raw)
        json_ok = isinstance(pred, dict)
        intent = pred.get("intent") if json_ok else None
        raw_slots = pred.get("slots", {}) if json_ok else {}

        if intent not in self.schemas and intent in EXTRA_ALIASES:
            intent = EXTRA_ALIASES[intent]
        via_alias = False
        if intent not in self.schemas and intent in self.aliases:
            intent = self.aliases[intent]
            via_alias = True

        intent_known = intent in self.schemas
        slots = self._normalize_slots(intent, raw_slots) if intent_known else {}
        required_missing = (
            [k for k in self.schemas[intent]["required"] if k not in slots]
            if intent_known else []
        )

        if not json_ok or not intent_known:
            confidence = 0.0
        elif via_alias:
            confidence = 0.55
        elif required_missing:
            confidence = 0.45
        else:
            # 0.75 au lieu de 0.9 : plus conservateur, laisse passer en fallback
            # les cas ambigus où le modèle est sûr de lui mais se trompe
            confidence = 0.75

        if intent_known and confidence >= self.threshold:
            if not domain_keywords_present(intent, text):
                print(f"[GUARD] {intent} : aucun mot-clé du domaine -> rétrogradé")
                confidence = 0.45

        if intent_known and confidence >= self.threshold:
            action, handler = "deterministic", self.schemas[intent]["handler"]
        else:
            action, handler = "fallback", None

        entry = {
            "ts": int(time.time()),
            "text": text,
            "raw_intent": intent if json_ok else None,
            "intent": intent,
            "slots": slots,
            "confidence": confidence,
            "action": action,
            "handler": handler,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Override si prefilter a forcé un intent déterministe
        if forced_intent and forced_intent != "fallback":
            entry["intent"] = forced_intent
            entry["action"] = "deterministic"
            entry["confidence"] = 1.0
            entry["handler"] = self.schemas.get(forced_intent, {}).get("handler")
            if forced_intent in (FAMILIES.get("files", set()) | {"delete_file", "empty_trash", "locate_file", "open_file", "open_app", "close_app", "close_file"}):
                merged = dict(entry.get("slots") or {})
                merged.update(files_slots(text))
                entry["slots"] = merged

        if entry["intent"] in (FAMILIES.get("files", set()) | {"open_app", "close_app", "close_file"}):
            merged = dict(entry.get("slots") or {})
            merged.update(files_slots(text))
            entry["slots"] = merged

        return entry


def main():
    dispatcher = Dispatcher()

    def run(query):
        r = dispatcher.route(query)
        print(f"Requete  : {query}")
        print(f"Intent   : {r['intent']} (confiance {r['confidence']:.2f})")
        print(f"Slots    : {r['slots']}")
        suffix = f" -> {r['handler']}" if r["handler"] else " -> LLM principal (8B)"
        print(f"Action   : {r['action']}{suffix}")
        print("-" * 55)

    if len(sys.argv) > 1:
        run(" ".join(sys.argv[1:]))
    else:
        print("Mode interactif — Ctrl+D pour quitter")
        while True:
            try:
                q = input("> ").strip()
            except EOFError:
                break
            if q:
                run(q)


if __name__ == "__main__":
    main()
