"""
Entraine le dispatcheur NLU en QLoRA sur le Mac (Palier 4).
Lit TOUT depuis config/models.yaml (modele de base + hyperparametres).
Genere un fichier de config mlx_lm.lora puis lance l'entrainement.
"""
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    with open(ROOT / "config" / "models.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    dispatcher = cfg["roles"].get("dispatcher") or {}
    base_model = dispatcher.get("repo")
    if not base_model:
        sys.exit("Aucun modele 'dispatcher' defini dans config/models.yaml")

    t = cfg.get("dispatcher_training", {})
    adapter_path = ROOT / t.get("adapter_path", "training/adapters/dispatcher-v1")
    adapter_path.parent.mkdir(parents=True, exist_ok=True)

    lora_cfg = {
        "model": base_model,
        "data": str(ROOT / t.get("output_dir", "data/dispatcher/dataset")),
        "train": True,
        "iters": t.get("iters", 200),
        "batch_size": t.get("batch_size", 2),
        "learning_rate": t.get("learning_rate", 2.0e-5),
        "lora_layers": t.get("lora_layers", 16),
        "lora_parameters": {
            "rank": t.get("lora_rank", 8),
            "alpha": t.get("lora_rank", 8) * 2,
            "dropout": 0.05,
            "scale": 2.0,
        },
        "adapter_path": str(adapter_path),
        "seed": t.get("seed", 42),
        "steps_per_report": 25,
        "steps_per_eval": 50,
        "val_batches": 5,
    }

    cfg_path = ROOT / "training" / "lora_dispatcher.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(lora_cfg, f, sort_keys=False)

    cmd = [sys.executable, "-m", "mlx_lm.lora", "--config", str(cfg_path)]
    print(f"Modele de base : {base_model}")
    print(f"Commande : {' '.join(cmd)}")
    print("=" * 60)

    subprocess.run(cmd, cwd=ROOT)


if __name__ == "__main__":
    main()
