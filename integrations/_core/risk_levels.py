"""
Niveaux de risque pour les actions d'intégration.

Trois niveaux, appliqués à toute action de toute intégration future :
- SAFE : consultation, recherche, listing — aucune modification possible
- REVERSIBLE : création, déplacement, modification — annulable manuellement
- DESTRUCTIVE : suppression, action irréversible ou à fort impact

Règle d'exécution :
- SAFE : exécution directe, aucun log spécial
- REVERSIBLE : exécution directe + log dans inference_log.jsonl
- DESTRUCTIVE : confirmation vocale obligatoire avant exécution
"""
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    REVERSIBLE = "reversible"
    DESTRUCTIVE = "destructive"


# Mapping des niveaux vers les comportements
SAFE = RiskLevel.SAFE
REVERSIBLE = RiskLevel.REVERSIBLE
DESTRUCTIVE = RiskLevel.DESTRUCTIVE
