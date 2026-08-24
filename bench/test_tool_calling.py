"""
Test de tool-calling pour OLYMPE — Palier 1
Compare la capacité de deux modèles à générer un appel d'outil structuré
plutôt qu'une réponse texte libre.

Usage:
    python test_tool_calling.py mlx-community/Qwen3-4B-4bit
    python test_tool_calling.py mlx-community/Qwen3-8B-4bit
"""

import sys
import time
import json
from mlx_lm import load, generate

# Définition d'un outil factice — météo
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Récupère la météo actuelle pour une ville donnée",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Le nom de la ville, ex: Paris"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "L'unité de température"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Démarre un minuteur pour une durée donnée",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Durée en minutes"
                    }
                },
                "required": ["duration_minutes"]
            }
        }
    }
]

# Cas de test : phrase qui doit déclencher un appel d'outil précis
TEST_CASES = [
    {
        "prompt": "Quel temps fait-il à Annecy ?",
        "expected_tool": "get_weather"
    },
    {
        "prompt": "Mets un minuteur de 10 minutes",
        "expected_tool": "set_timer"
    },
    {
        "prompt": "Raconte-moi une blague",
        "expected_tool": None  # ne doit PAS appeler d'outil ici
    }
]


def run_test(model_path):
    print(f"\n{'='*60}")
    print(f"Chargement du modèle : {model_path}")
    print(f"{'='*60}\n")

    load_start = time.time()
    model, tokenizer = load(model_path)
    load_time = time.time() - load_start
    print(f"Modèle chargé en {load_time:.2f}s\n")

    results = []

    for case in TEST_CASES:
        prompt = case["prompt"]
        expected = case["expected_tool"]

        messages = [{"role": "user", "content": prompt}]

        try:
            formatted_prompt = tokenizer.apply_chat_template(
                messages,
                tools=TOOLS,
                add_generation_prompt=True,
                tokenize=False
            )
        except Exception as e:
            print(f"⚠️  Le template de ce modèle ne supporte peut-être pas 'tools': {e}")
            formatted_prompt = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=False
            )

        gen_start = time.time()
        response = generate(
            model,
            tokenizer,
            prompt=formatted_prompt,
            max_tokens=200,
            verbose=False
        )
        gen_time = time.time() - gen_start

        # Détection d'un appel d'outil : on isole uniquement ce qui est
        # APRÈS la balise </think> pour ignorer les mentions de l'outil
        # dans le raisonnement (faux positifs).
        actual_output = response
        if "</think>" in response:
            actual_output = response.split("</think>", 1)[1]

        tool_called = None
        if "<tool_call>" in actual_output:
            try:
                tool_call_str = actual_output.split("<tool_call>", 1)[1].split("</tool_call>", 1)[0].strip()
                tool_call_json = json.loads(tool_call_str)
                tool_called = tool_call_json.get("name")
            except (IndexError, json.JSONDecodeError):
                tool_called = "MALFORMED_JSON"

        correct = (tool_called == expected)

        no_tool_label = "(pas d'outil)"
        print(f"Prompt      : {prompt}")
        print(f"Attendu     : {expected or no_tool_label}")
        print(f"Détecté     : {tool_called or no_tool_label}")
        print(f"Résultat    : {'✅ OK' if correct else '❌ ÉCHEC'}")
        print(f"Temps       : {gen_time:.2f}s")
        print(f"Sortie brute:\n{response}\n")
        print("-" * 60)

        results.append({
            "prompt": prompt,
            "expected": expected,
            "detected": tool_called,
            "correct": correct,
            "time": gen_time
        })

    # Résumé
    n_correct = sum(1 for r in results if r["correct"])
    print(f"\n{'='*60}")
    print(f"RÉSUMÉ — {model_path}")
    print(f"Score tool-calling : {n_correct}/{len(results)}")
    print(f"Temps de chargement : {load_time:.2f}s")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_tool_calling.py <model_path>")
        sys.exit(1)

    model_path = sys.argv[1]
    run_test(model_path)
