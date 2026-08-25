"""
Prepare le dataset d'entrainement du dispatcheur (Palier 4).
Fusionne TOUS les fichiers *.jsonl de data/dispatcher/ (seeds + iterations),
deduplique, puis split stratifie vers le format chat mlx-lm.
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from router.prompts import build_system_prompt, format_assistant_answer


def load_config():
    with open(ROOT / "config" / "models.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_seeds(seed_dir):
    examples, seen = [], set()
    for path in sorted(seed_dir.glob("*.jsonl")):
        if path.name == "inference_log.jsonl":
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                key = ex["text"].strip().lower()
                if key not in seen:
                    seen.add(key)
                    examples.append(ex)
        print(f"  + {path.name}")
    return examples


def stratified_split(examples, seed):
    rng = random.Random(seed)
    by_intent = defaultdict(list)
    for ex in examples:
        by_intent[ex["intent"]].append(ex)

    train, valid, test = [], [], []
    for intent, items in by_intent.items():
        rng.shuffle(items)
        n = len(items)
        if n <= 3:
            train += items[:2] if n >= 2 else items
            test += items[2:3] if n >= 3 else []
            valid += items[3:4] if n >= 4 else []
        else:
            n_test = max(1, round(n * 0.15))
            n_valid = max(1, round(n * 0.15))
            test += items[:n_test]
            valid += items[n_test:n_test + n_valid]
            train += items[n_test + n_valid:]

    rng.shuffle(train)
    rng.shuffle(valid)
    rng.shuffle(test)
    return train, valid, test


def to_chat_example(ex, system_prompt):
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ex["text"]},
            {
                "role": "assistant",
                "content": format_assistant_answer(ex["intent"], ex.get("slots", {})),
            },
        ]
    }


def write_jsonl(path, examples, system_prompt):
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(to_chat_example(ex, system_prompt), ensure_ascii=False) + "\n")


def main():
    cfg = load_config()
    t = cfg.get("dispatcher_training", {})

    seed_dir = ROOT / t.get("seed_dir", "data/dispatcher")
    out_dir = ROOT / t.get("output_dir", "data/dispatcher/dataset")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Fichiers de seeds fusionnes :")
    examples = load_all_seeds(seed_dir)
    system_prompt = build_system_prompt()

    train, valid, test = stratified_split(examples, t.get("seed", 42))

    write_jsonl(out_dir / "train.jsonl", train, system_prompt)
    write_jsonl(out_dir / "valid.jsonl", valid, system_prompt)
    write_jsonl(out_dir / "test.jsonl", test, system_prompt)

    intents = sorted({ex["intent"] for ex in examples})
    print(f"Exemples totaux (dedupliques) : {len(examples)}")
    print(f"  train : {len(train)}")
    print(f"  valid : {len(valid)}")
    print(f"  test  : {len(test)}")
    print(f"Intents couverts : {len(intents)}")
    print(f"Dataset ecrit dans : {out_dir}")


if __name__ == "__main__":
    main()
