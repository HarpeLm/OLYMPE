"""OLYMPE — point d'entrée unique (mode écrit).
Adaptateur mince : toute la logique des outils vit dans agent/tools/.
Tape une phrase, tout est routé :
  [1] dispatcheur regex -> action TaHoma immédiate (0 LLM)
  [2] LLM + tool-calling via agent.tools
  [3] réponse finale affichée
'q' pour quitter."""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from router.orchestrator import orchestrate
from agent.tools import list_tools, run_tool

LLM_URL = "http://127.0.0.1:8000/v1/chat/completions"

SYS = ("Tu es Olympe, assistant personnel local. Réponds brièvement, "
       "en français, comme à l'oral. Utilise les outils quand nécessaire.")

# TOOLS au format OpenAI pour le LLM
TOOLS = [{"type": "function", "function": t} for t in list_tools()]


def post_chat(messages):
    payload = {"model": "local", "messages": messages, "tools": TOOLS,
               "max_tokens": 512, "temperature": 0.7}
    req = urllib.request.Request(
        LLM_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def llm_with_tools(text):
    """Boucle agent : le 8B choisit des outils, on les exécute, il conclut."""
    messages = [{"role": "system", "content": SYS},
                {"role": "user", "content": text}]
    for _ in range(4):
        data = post_chat(messages)
        msg = data["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or ""
        assistant = {"role": "assistant", "content": msg.get("content") or "",
                     "tool_calls": calls}
        if msg.get("reasoning_content"):
            assistant["reasoning_content"] = msg["reasoning_content"]
        messages.append(assistant)
        for c in calls:
            fn = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = run_tool(fn, args)
            except Exception as e:
                result = f"Erreur : {e}"
            print(f"   [outil] {fn}")
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""),
                             "name": fn, "content": str(result)})
    return "(trop d'étapes, je m'arrête là)"


print("OLYMPE (mj.py) — écris une phrase, 'q' pour quitter")
while True:
    try:
        phrase = input("\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAu revoir.")
        break
    if not phrase or phrase.lower() == "q":
        print("Au revoir.")
        break
    try:
        result = orchestrate(phrase)
        if result["handled"]:
            print("  →", result["result"]["message"])
        else:
            print("  →", llm_with_tools(phrase))
    except Exception as e:
        print("  Erreur :", e)
