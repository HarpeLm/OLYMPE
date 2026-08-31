"""Cadenas anti-régression (review 31/08/2026, point 2).
Scan AST des intégrations : aucune f-string alimentant un script
AppleScript/JXA ne doit interpoler une variable sans _as_literal().

ROUGE avant la migration (liste les trous), VERT après.
Lancement : python3 integrations/_core/test_no_raw_interpolation.py"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Seules expressions autorisées SANS _as_literal : constantes du module
# et valeurs numériques calculées (jamais de saisie utilisateur).
SAFE_EXACT = {
    "CALENDAR_NAME",          # constante du module
    "freq",                   # issu d'un dict interne de valeurs fixes
    "d.year", "d.month", "d.day",
    "target.year", "target.month", "target.day",
    "h", "mi", "dur",         # entiers calculés (parse_time_fr / durée)
    "d.strftime('%d/%m')",    # format interne, pas de saisie utilisateur
}


def iter_script_fstrings(tree):
    """f-strings qui deviennent du AppleScript/JXA : assignées à une
    variable 'script' ou passées directement à run_applescript/run_jxa."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "script" in names and isinstance(node.value, ast.JoinedStr):
                yield node.value
        if isinstance(node, ast.Call):
            fn = node.func
            fname = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
            if fname in ("run_applescript", "run_jxa"):
                for arg in node.args:
                    if isinstance(arg, ast.JoinedStr):
                        yield arg


def scan_file(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []
    for js in iter_script_fstrings(tree):
        for part in js.values:
            if not isinstance(part, ast.FormattedValue):
                continue
            expr = part.value
            if isinstance(expr, ast.Constant):
                continue
            if isinstance(expr, ast.Call):
                fn = expr.func
                if isinstance(fn, ast.Name) and fn.id == "_as_literal":
                    continue
            try:
                src = ast.unparse(expr)
            except Exception:
                src = "<expression>"
            if src in SAFE_EXACT:
                continue
            offenders.append((path.name, src))
    return offenders


bad = []
for f in sorted((ROOT / "integrations").rglob("*.py")):
    if f.name.startswith("test_"):
        continue
    bad += scan_file(f)

if bad:
    print("Interpolations non échappées détectées :")
    for fname, expr in bad:
        print(f"   - {fname} : {{{expr}}}")
    print(f"{len(bad)} trou(s) — à corriger avec _as_literal().")
    sys.exit(1)

print("Aucune interpolation brute dans les scripts AppleScript/JXA")
