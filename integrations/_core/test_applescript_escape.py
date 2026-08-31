"""Test d'injection _as_literal — exigé par la review (point 1).
Vérifie qu'aucune entrée malicieuse ne peut s'évader du littéral :
guillemets, antislashs, tentatives 'end tell', caractères de contrôle."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from integrations._core.applescript_runner import _as_literal

# Un littéral valide : guillemets entourant une suite de caractères
# normaux ou échappés (\.), jamais de guillemet nu à l'intérieur.
LITERAL_OK = re.compile(r'^"(\\.|[^"\\])*"$')

CASES = [
    "Réunion simple",
    'Guillemets " dedans',
    "Antislash \\ seul",
    'x" & (do shell script "ls ~") & "',            # évasion classique
    'end tell\ntell application "Finder" to empty trash',  # injection multi-ligne
    'a\\"b',
    "\x00\x07contrôles\x1b",
    "",
    None,
    42,
    'Événement "Été" \\ 2026 🌞',
]

CASES.append("a" * 600)             # troncature longue
CASES.append("b" * 499 + "\\")       # backslash pile à la limite de coupe
ok = 0
for c in CASES:
    lit = _as_literal(c)
    assert LITERAL_OK.match(lit), f"littéral invalide pour {c!r} : {lit!r}"
    inner = lit[1:-1]
    assert '"' not in inner.replace('\\"', ''), \
        f"guillemet non échappé pour {c!r}"
    ok += 1
    print(f"✅ {str(c)[:38]!r} -> {lit[:55]!r}")

print(f"\n{ok}/{len(CASES)} cas passés — aucune évasion du littéral possible")
