"""
Lance le serveur d'inférence persistant pour OLYMPE.
Lit la configuration depuis /config/models.yaml.
Adapté pour vllm-mlx 0.4.1 (options différentes de vLLM classique).
"""
import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"❌ Config introuvable : {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def module_exists(module_name):
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def normalize_command(command):
    cmd = [str(x) for x in command]

    if not cmd:
        sys.exit("❌ server.command est vide dans config/models.yaml")

    if cmd[0] in {"python", "python3"}:
        cmd[0] = sys.executable

    return cmd


def command_exists(cmd):
    if not cmd:
        return False

    executable = cmd[0]

    if executable == sys.executable:
        if len(cmd) >= 3 and cmd[1] == "-m":
            module_root = cmd[2].split(".")[0]
            return module_exists(module_root)
        return True

    if Path(executable).is_file():
        return True

    return shutil.which(executable) is not None


def build_command(cfg, mcp_config=None):
    roles = cfg.get("roles", {})
    chat = roles.get("chat") or {}
    repo = chat.get("repo")

    if not repo:
        sys.exit("❌ Aucun modèle 'chat' défini dans config/models.yaml")

    server = cfg.get("server", {})
    engine = str(server.get("engine", "vllm-mlx")).lower()
    command = server.get("command")

    if not command:
        if "vllm" in engine:
            command = [sys.executable, "-m", "vllm_mlx.server"]
        else:
            command = [sys.executable, "-m", "mlx_lm.server"]

    cmd = normalize_command(command)

    if not command_exists(cmd):
        sys.exit(
            "❌ Commande serveur introuvable.\n"
            f"Commande configurée : {' '.join(cmd)}\n"
            "Vérifie que le module/serveur est installé dans le venv actif."
        )

    cmd += ["--model", repo]

    host = str(server.get("host", "127.0.0.1"))
    port = str(server.get("port", 8000))
    cmd += ["--host", host, "--port", port]

    # Options spécifiques à vllm-mlx 0.4.1
    if "vllm" in engine:
        reasoning_parser = server.get("reasoning_parser")
        if reasoning_parser:
            cmd += ["--reasoning-parser", str(reasoning_parser)]

        max_tokens = server.get("max_tokens")
        if max_tokens:
            cmd += ["--max-tokens", str(max_tokens)]

        max_request_tokens = server.get("max_request_tokens")
        if max_request_tokens:
            cmd += ["--max-request-tokens", str(max_request_tokens)]

        auto_unload = server.get("auto_unload_idle_seconds")
        if auto_unload is not None:
            cmd += ["--auto-unload-idle-seconds", str(auto_unload)]

        if server.get("continuous_batching", False):
            cmd += ["--continuous-batching"]

        if server.get("lazy_load_model", False):
            cmd += ["--lazy-load-model"]

        if server.get("trust_remote_code", False):
            cmd += ["--trust-remote-code"]

        # Support MCP : argument CLI prioritaire, sinon config YAML
        mcp_path = mcp_config or server.get("mcp_config")
        if mcp_path:
            mcp_path = Path(mcp_path)
            if not mcp_path.is_absolute():
                mcp_path = ROOT / mcp_path
            if not mcp_path.exists():
                sys.exit(f"❌ Fichier MCP introuvable : {mcp_path}")
            cmd += ["--mcp-config", str(mcp_path)]

    extra_args = server.get("extra_args") or []
    cmd += [str(x) for x in extra_args]

    return cmd, repo, engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mcp-config",
        help="Chemin vers le fichier de configuration MCP "
             "(prioritaire sur la valeur dans models.yaml)",
    )
    args = parser.parse_args()

    cfg = load_config()
    cmd, repo, engine = build_command(cfg, mcp_config=args.mcp_config)

    print(f"Moteur : {engine}")
    print(f"Modèle : {repo}")
    print(f"Commande : {' '.join(cmd)}")

    if args.dry_run:
        return

    try:
        subprocess.run(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        print("\n🛑 Serveur arrêté.")
    except FileNotFoundError:
        sys.exit(
            "❌ Commande serveur introuvable. "
            "Vérifie server.command dans config/models.yaml."
        )


if __name__ == "__main__":
    main()
