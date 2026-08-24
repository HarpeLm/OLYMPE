"""
Evalue l'adaptateur LoRA du dispatcheur sur le jeu de test (Palier 4).
Mesure la precision reelle : intent correct + slots corrects.
Toutes les balises speciales sont construites dynamiquement (jamais en litteral).
"""
import json
import sys
from pathlib import Path

import yaml
from mlx_lm import load, generate

ROOT = Path(__file__).resolve().parent.parent

# Construction dynamique des balises pour eviter tout probleme d'encodage
LT = chr(60)
GT = chr(62)
TAG_THINK_OPEN = LT + "think" + GT
TAG_THINK_CLOSE = LT + "/think" + GT
TAG_IM_END = LT + "|im_end|" + GT


def clean_output(text):
    """Retire les blocs de raisonnement et les balises de fin."""
    if TAG_THINK_CLOSE in text:
        text = text.split(TAG_THINK_CLOSE, 1)[1]
    if TAG_THINK_OPEN in text:
        text = text.split(TAG_THINK_OPEN, 1)[0]
    text = text.replace(TAG_IM_END, "")
    return text.strip()


def parse_json(text):
    """Parsing tolerant : cherche le premier objet JSON valide."""
    text = clean_output(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    with open(ROOT / "config" / "models.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    dispatcher = cfg["roles"]["dispatcher"]
    base_model = dispatcher["repo"]
    adapter_path = str(ROOT / dispatcher["adapter"])
    dataset_dir = ROOT / cfg["dispatcher_training"]["output_dir"]

    print(f"Modele : {base_model}")
    print(f"Adaptateur : {adapter_path}")
    model, tokenizer = load(base_model, adapter_path=adapter_path)

    test_examples = load_jsonl(dataset_dir / "test.jsonl")
    print(f"Exemples de test : {len(test_examples)}")
    print("=" * 60)

    intent_ok = 0
    full_ok = 0
    malformed = 0

    for ex in test_examples:
        messages = ex["messages"]
        prompt = tokenizer.apply_chat_template(
            messages[:-1],
            add_generation_prompt=True,
            tokenize=False,
        )
        expected = json.loads(messages[-1]["content"])

        raw = generate(model, tokenizer, prompt=prompt, max_tokens=128, verbose=False)
        predicted = parse_json(raw)

        if predicted is None:
            malformed += 1
            status = "JSON INVALIDE"
        else:
            ok_intent = predicted.get("intent") == expected.get("intent")
            ok_slots = predicted.get("slots", {}) == expected.get("slots", {})
            if ok_intent:
                intent_ok += 1
            if ok_intent and ok_slots:
                full_ok += 1
            status = "OK" if (ok_intent and ok_slots) else ("INTENT OK / SLOTS KO" if ok_intent else "KO")

        print(f"[{status}] user: {messages[1]['content']}")
        if status != "OK":
            print(f"    attendu : {json.dumps(expected, ensure_ascii=False)}")
            got = json.dumps(predicted, ensure_ascii=False) if predicted else raw[:100]
            print(f"    obtenu  : {got}")

    n = len(test_examples)
    print("=" * 60)
    print(f"Precision intent       : {intent_ok}/{n} ({100 * intent_ok / n:.0f}%)")
    print(f"Precision intent+slots : {full_ok}/{n} ({100 * full_ok / n:.0f}%)")
    print(f"JSON malformes         : {malformed}/{n}")


if __name__ == "__main__":
    main()
